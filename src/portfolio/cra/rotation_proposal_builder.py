"""Rotation Proposal Builder — Phase 23.6A.

Assembles a complete RotationProposal from PAR run artifacts.

Steps:
  1. Load PAR run files
  2. Build CapitalSourceRecords (via capital_source_builder)
  3. Filter pool (exclude blocked, defer deferred)
  4. Read deployment queue
  5. Filter queue to alignment-improving candidates
  6. Allocate capital (CW-DAS rank order)
  7. Generate RotationDeploymentTargets
  8. Estimate portfolio impact
  9. Determine proposal_status and review_flags
  10. Return RotationProposal

NON-NEGOTIABLE:
  - CW-DAS rank order is NEVER modified.
  - deployment_score is NEVER modified.
  - All scoring from upstream; CRA is read-only.

Design source: docs/phase_23_6/03_rotation_framework.md
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .capital_source_builder import build_capital_sources
from .impact_estimator import estimate_impact
from .models import (
    CATEGORY_LOW_CONVICTION,
    STATUS_DRAFT,
    STATUS_OP_REVIEW,
    STATUS_READY,
    CapitalSourceRecord,
    PortfolioImpactEstimate,
    RotationDeploymentTarget,
    RotationProposal,
)

log = logging.getLogger(__name__)

# ── Tuning constants ──────────────────────────────────────────────────────────

# Minimum lot size; allocation stops when remaining pool drops below this
_MINIMUM_LOT_SIZE_USD = 500.0

# Warn threshold (same as deployment_queue module default)
# A candidate uses headroom_pct from queue (how far below its warn threshold).
# headroom > 0 means deployable capital exists.
_HEADROOM_FLOOR = 0.0

# Large pool threshold that triggers operator_review (% of portfolio)
_LARGE_POOL_PCT = 10.0

# ── Allocation node derivation ────────────────────────────────────────────────

def _derive_allocation_node(queue_entry: Dict, holdings_by_sym: Dict) -> str:
    """Derive allocation_node for a queue entry.

    Phase 23.5 added allocation_node to the model, but existing serialized
    PAR runs may not have it.  Fall back to holdings geography + cap tier.
    """
    # Try the persisted field first
    node = (queue_entry.get("allocation_node") or "").strip()
    if node:
        return node

    sym = (queue_entry.get("symbol") or "").upper()
    h = holdings_by_sym.get(sym, {})
    geo = (h.get("geography") or "").upper()
    cap = (h.get("market_cap_bucket") or "").upper()

    if not geo or geo == "UNKNOWN":
        return ""
    if cap and cap not in ("UNKNOWN", "N/A", ""):
        return f"EQUITIES.{geo}.{cap}"
    return f"EQUITIES.{geo}"


# ── Public API ────────────────────────────────────────────────────────────────

def build_rotation_proposal(
    run_dir: str | Path,
    tax_state: Optional[Dict] = None,
    strategic_profiles: Optional[List[Dict]] = None,
) -> RotationProposal:
    """Build a RotationProposal from a PAR run directory.

    Args:
        run_dir:            Path to PAR run directory
                            (e.g. data/portfolio_ingestion/analysis_runs/PAR-xxx).
        tax_state:          Parsed portfolio_alignment_state.json (optional).
                            If None, tax modifiers and policies are disabled.
        strategic_profiles: Parsed strategic_profiles.json list (optional).
                            If None, Category 2 falls back to signals only.

    Returns:
        RotationProposal with all fields populated.

    Raises:
        FileNotFoundError: if required PAR files are missing.
        ValueError:        if critical data is malformed.
    """
    run_dir = Path(run_dir)
    _assert_required_files(run_dir)

    # ── Load PAR artifacts ────────────────────────────────────────────────────
    deployment_queue = _load_json(run_dir / "deployment_queue.json")
    run_metadata     = _load_json(run_dir / "run_metadata.json")
    concentration    = _load_json(run_dir / "concentration.json")
    snapshot         = _load_json(run_dir / "snapshot.json")
    overlays         = _load_csv(run_dir / "security_overlays.csv")
    holdings         = _load_csv(run_dir / "holdings.csv")
    alignment        = _load_csv(run_dir / "alignment.csv")

    run_id       = run_metadata.get("run_id", run_dir.name)
    as_of_date   = str(run_metadata.get("snapshot_date") or snapshot.get("snapshot_date") or "")
    portfolio_mv = float(snapshot.get("total_market_value") or
                         deployment_queue.get("total_market_value") or 0.0)

    # ── Build holdings index ──────────────────────────────────────────────────
    holdings_by_sym: Dict[str, Dict] = {
        (h.get("symbol") or "").upper(): h
        for h in holdings
        if (h.get("symbol") or "").upper()
    }

    # ── Build capital sources ─────────────────────────────────────────────────
    all_sources, suppressed_sources = build_capital_sources(
        overlays=overlays,
        holdings=holdings,
        alignment=alignment,
        deployment_queue=deployment_queue,
        tax_state=tax_state,
        strategic_profiles=strategic_profiles,
    )

    # ── Filter capital pool ───────────────────────────────────────────────────
    # Blocked sources stay visible in sources list but excluded from pool.
    pool_sources = [s for s in all_sources if not s.blocked_by_policy and s.priority != "DEFER"]
    total_capital_pool = sum(s.estimated_proceeds for s in pool_sources)

    # ── Load deployment queue ─────────────────────────────────────────────────
    queue: List[Dict] = deployment_queue.get("queue", [])

    # ── Filter queue to alignment-improving candidates ────────────────────────
    # Exclude: policy_protected=True, headroom_pct ≤ 0
    eligible_queue: List[Dict] = [
        e for e in queue
        if not e.get("policy_protected", False)
        and float(e.get("headroom_pct") or 0) > _HEADROOM_FLOOR
    ]

    # ── Allocate capital in CW-DAS rank order ─────────────────────────────────
    deployments, remaining = _allocate_capital(
        eligible_queue=eligible_queue,
        total_pool=total_capital_pool,
        portfolio_mv=portfolio_mv,
        holdings_by_sym=holdings_by_sym,
    )

    # ── Fix 1: Circular conflict resolution (Phase 23.6B.4) ──────────────────
    # Detect symbols that appear in both capital sources and deployment targets.
    # Resolution (Option A): when a symbol's ONLY source reason is overweight
    # exposure (OVERWEIGHT_REDUCTION category) and it has BULLISH/VERY_BULLISH
    # conviction, remove it from capital sources — the conviction signal wins.
    # A symbol with signal deterioration that also happens to be in the queue
    # retains its source record (system correctly surfaces a conflict).
    _BULLISH_SIGNALS = frozenset({"BULLISH", "VERY_BULLISH"})
    _OW_ONLY_CATEGORIES = frozenset({
        "OVERWEIGHT_REDUCTION",
        "LOW_CONVICTION_REDUCTION",
    })

    deploy_syms: frozenset[str] = frozenset(t.symbol for t in deployments)

    # Build overlay signal lookup for quick conviction check
    _ov_by_sym_lookup: Dict[str, Dict] = {
        (o.get("symbol") or "").upper(): o for o in overlays if (o.get("symbol") or "").upper()
    }

    filtered_sources: List[CapitalSourceRecord] = []
    circular_resolved: List[str] = []  # symbols removed from sources via Option A

    for src in all_sources:
        sym = src.symbol
        if sym not in deploy_syms:
            filtered_sources.append(src)
            continue

        # Symbol is in both sources and deployment targets — resolve conflict
        ov = _ov_by_sym_lookup.get(sym, {})
        sig = (ov.get("signal_direction") or "").upper()
        ess = (ov.get("ess_score_text") or "").upper()
        conviction_bullish = sig in _BULLISH_SIGNALS or ess in _BULLISH_SIGNALS

        if src.category in _OW_ONLY_CATEGORIES and conviction_bullish:
            # Option A: remove from sources — conviction wins over exposure drift
            circular_resolved.append(sym)
            # Also remove from pool_sources
        else:
            # Keep in sources — conflict persists (e.g. signal deterioration + deploy)
            # but is surfaced via review_flags
            filtered_sources.append(src)

    # Rebuild pool after circular resolution
    all_sources = filtered_sources
    pool_sources = [s for s in all_sources if not s.blocked_by_policy and s.priority != "DEFER"]
    total_capital_pool = sum(s.estimated_proceeds for s in pool_sources)

    # ── Estimate portfolio impact ─────────────────────────────────────────────
    impact = estimate_impact(
        sources=pool_sources,
        deployments=deployments,
        alignment=alignment,
        concentration=concentration,
        run_metadata=run_metadata,
        portfolio_mv=portfolio_mv,
    )

    # ── Determine proposal status and review flags ────────────────────────────
    review_flags: List[str] = []
    status = STATUS_DRAFT

    # CORE_ANCHOR present in sources
    for s in all_sources:
        if s.operator_review_required and not s.blocked_by_policy:
            if s.policy_type == "CORE_ANCHOR":
                review_flags.append(f"CORE_ANCHOR policy on {s.symbol} — confirm before executing")

    # Tax Bucket D positions
    for s in pool_sources:
        if s.tax_bucket == "D":
            review_flags.append(f"Bucket D (significant LT gain) detected: {s.symbol}")

    # Large capital pool
    if portfolio_mv > 0 and total_capital_pool / portfolio_mv * 100 > _LARGE_POOL_PCT:
        review_flags.append(
            f"Capital pool ({total_capital_pool / portfolio_mv * 100:.1f}% of portfolio) "
            f"exceeds {_LARGE_POOL_PCT:.0f}% threshold — operator review recommended"
        )

    # Projected weight exceeds current for any target
    for t in deployments:
        if t.projected_weight_pct > 15.0:
            review_flags.append(
                f"{t.symbol} projected weight {t.projected_weight_pct:.1f}% — concentration review"
            )

    if review_flags:
        status = STATUS_OP_REVIEW
    elif deployments and pool_sources:
        status = STATUS_READY
    else:
        status = STATUS_DRAFT

    # ── Add circular resolution info to review flags if any remain ───────────
    # Symbols removed via Option A are informational only (no flag needed).
    # Symbols that remain in both (e.g. signal deterioration + deploy queue)
    # surface as a warning for operator awareness.
    remaining_circular = [
        s.symbol for s in all_sources
        if s.symbol in deploy_syms and not s.blocked_by_policy
    ]
    if remaining_circular:
        review_flags.append(
            f"Signal conflict: {', '.join(remaining_circular)} appear in both capital sources "
            f"and deployment targets — net direction may require operator judgment"
        )
        status = STATUS_OP_REVIEW

    # ── Assemble proposal ────────────────────────────────────────────────────
    proposal_id = _make_proposal_id(run_id, as_of_date)
    now_utc = datetime.now(timezone.utc).isoformat()

    return RotationProposal(
        proposal_id=proposal_id,
        run_id=run_id,
        as_of_date=as_of_date,
        portfolio_mv=round(portfolio_mv, 2),
        total_capital_pool=round(total_capital_pool, 2),
        sources=all_sources,  # all sources, including blocked
        deployments=deployments,
        impact=impact,
        proposal_status=status,
        review_flags=review_flags,
        created_at_utc=now_utc,
        suppressed_sources=suppressed_sources,
    )


# ── Capital allocation ────────────────────────────────────────────────────────

# Tier definitions (mirrors Phase 7.5D Deployment Plan philosophy)
_TIER_CCL = "CORE_CONVICTION_LEADER"
_TIER_HCA = "HIGH_CONVICTION_ANCHOR"

# Tier pool fractions — CCL receives the majority share, HCA splits the rest
# These mirror the Deployment Plan T1/T2/T3 proportions.
_TIER_CCL_FRACTION = 0.50   # 50% of pool to CCL candidates
_TIER_HCA_FRACTION = 0.50   # 50% of pool to HCA candidates

# Per-candidate hard cap: no single position receives more than this fraction
# of the pool in one rotation.  Prevents extreme concentration.
# 20% means a $100K pool can fund at most 5 positions before per-cap binds.
_PER_CANDIDATE_CAP_FRACTION = 0.20

# WARN position threshold — do not project any target above this weight
# (matches deployment_queue.py's WARN_POSITION_PCT default of 6%)
_WARN_POSITION_PCT = 6.0


def _allocate_capital(
    eligible_queue: List[Dict],
    total_pool: float,
    portfolio_mv: float,
    holdings_by_sym: Dict[str, Dict],
) -> Tuple[List[RotationDeploymentTarget], float]:
    """Allocate capital pool to deployment targets using tier-aware distribution.

    Phase 23.6B.2 — replaces naive 50%-cap sequential allocator.

    Algorithm (mirrors Phase 7.5D Deployment Plan philosophy):
      1. Split eligible candidates into CCL and HCA tiers.
      2. Assign CCL tier 50% of the pool, HCA tier the remaining 50%.
      3. Within each tier, distribute proportional to headroom,
         capped at per_candidate_cap (20% of total pool) and
         capped to avoid projecting any target above WARN_POSITION_PCT.
      4. Unspent tier budget rolls down to the next tier.
      5. CW-DAS rank order within each tier is preserved.

    Returns:
        (deployments sorted by original CW-DAS rank, remaining_pool_usd)
    """
    if total_pool < _MINIMUM_LOT_SIZE_USD or not eligible_queue:
        return [], total_pool

    per_candidate_cap = total_pool * _PER_CANDIDATE_CAP_FRACTION

    # Partition by tier (preserving CW-DAS rank order within each tier)
    ccl_entries = [e for e in eligible_queue if e.get("narrative_tier") == _TIER_CCL]
    hca_entries = [e for e in eligible_queue if e.get("narrative_tier") == _TIER_HCA]
    # Any unclassified entries go into HCA bucket
    other_entries = [
        e for e in eligible_queue
        if e.get("narrative_tier") not in (_TIER_CCL, _TIER_HCA)
    ]
    hca_entries = hca_entries + other_entries

    ccl_budget = round(total_pool * _TIER_CCL_FRACTION, 2)
    hca_budget = round(total_pool * _TIER_HCA_FRACTION, 2)

    all_allocs: List[Tuple[float, Dict]] = []  # (amount, queue_entry)

    def _allocate_tier(
        entries: List[Dict],
        budget: float,
    ) -> Tuple[List[Tuple[float, Dict]], float]:
        """Distribute budget across candidates proportional-to-headroom.

        Returns (allocations_list, unspent_budget).
        Each allocation is (suggested_usd, queue_entry).
        """
        if budget < _MINIMUM_LOT_SIZE_USD or not entries:
            return [], budget

        # Compute headroom for each eligible candidate
        eligible = []
        for e in entries:
            hdroom_pct = float(e.get("headroom_pct") or 0.0)
            if hdroom_pct <= 0.0:
                continue
            hdroom_usd = hdroom_pct / 100.0 * portfolio_mv
            if hdroom_usd < _MINIMUM_LOT_SIZE_USD:
                continue
            cur_wt = float(e.get("current_weight_pct") or 0.0)
            eligible.append((e, hdroom_usd, cur_wt))

        if not eligible:
            return [], budget

        total_hdroom = sum(h for _, h, _ in eligible)
        remaining = budget
        allocs: List[Tuple[float, Dict]] = []

        for entry, hdroom_usd, cur_wt in eligible:
            if remaining < _MINIMUM_LOT_SIZE_USD:
                break
            # Proportional share of tier budget
            proportional_share = (hdroom_usd / total_hdroom * budget) if total_hdroom > 0 else 0.0
            # Per-candidate hard cap (20% of total pool)
            # WARN threshold cap: don't push projected weight above 6%
            warn_cap_usd = max(0.0, (_WARN_POSITION_PCT - cur_wt) / 100.0 * portfolio_mv)
            suggested = min(
                proportional_share,
                hdroom_usd,
                remaining,
                per_candidate_cap,
                warn_cap_usd,
            )
            if suggested < _MINIMUM_LOT_SIZE_USD:
                continue
            allocs.append((round(suggested, 2), entry))
            remaining -= round(suggested, 2)

        return allocs, round(remaining, 2)

    # Allocate CCL tier
    ccl_allocs, ccl_unspent = _allocate_tier(ccl_entries, ccl_budget)
    all_allocs.extend(ccl_allocs)

    # Roll unspent CCL budget into HCA
    hca_budget = round(hca_budget + ccl_unspent, 2)

    # Allocate HCA tier
    hca_allocs, hca_unspent = _allocate_tier(hca_entries, hca_budget)
    all_allocs.extend(hca_allocs)

    remaining_pool = round(hca_unspent, 2)

    # Convert allocations to RotationDeploymentTarget, sorting by CW-DAS rank
    all_allocs_sorted = sorted(all_allocs, key=lambda x: int(x[1].get("rank") or 0))

    deployments: List[RotationDeploymentTarget] = []
    for suggested, entry in all_allocs_sorted:
        sym                = (entry.get("symbol") or "").upper()
        current_weight_pct = float(entry.get("current_weight_pct") or 0.0)
        headroom_pct       = float(entry.get("headroom_pct") or 0.0)
        market_value       = float(entry.get("market_value") or 0.0)
        deployment_score   = float(entry.get("deployment_score") or 0.0)
        narrative_tier     = str(entry.get("narrative_tier") or "")
        score_breakdown    = entry.get("score_breakdown") or {}
        notes              = str(entry.get("notes") or "")

        suggested_pct_add  = round((suggested / portfolio_mv * 100) if portfolio_mv > 0 else 0.0, 4)
        projected_weight   = round(current_weight_pct + suggested_pct_add, 4)
        allocation_node    = _derive_allocation_node(entry, holdings_by_sym)

        note_parts = []
        hdroom_usd = headroom_pct / 100.0 * portfolio_mv
        if suggested < hdroom_usd * 0.99:
            if suggested >= per_candidate_cap * 0.99:
                note_parts.append(f"20% cap applied")
            elif projected_weight >= _WARN_POSITION_PCT * 0.99:
                note_parts.append(f"warn-threshold cap applied ({_WARN_POSITION_PCT}%)")
            else:
                tier = "T1-CCL" if narrative_tier == _TIER_CCL else "T2-HCA"
                note_parts.append(f"{tier} proportional share")
        else:
            note_parts.append(f"{headroom_pct:.1f}% headroom — fully funded")
        if notes:
            note_parts.append(notes)

        deployments.append(RotationDeploymentTarget(
            rank=int(entry.get("rank") or 0),
            symbol=sym,
            deployment_score=deployment_score,
            allocation_node=allocation_node,
            narrative_tier=narrative_tier,
            current_weight_pct=current_weight_pct,
            market_value=market_value,
            suggested_amount=suggested,
            suggested_pct_add=suggested_pct_add,
            projected_weight_pct=projected_weight,
            score_breakdown=score_breakdown,
            headroom_pct=headroom_pct,
            allocation_note=" | ".join(note_parts),
        ))

    return deployments, remaining_pool



# ── File loading helpers ──────────────────────────────────────────────────────

_REQUIRED_FILES = (
    "deployment_queue.json",
    "run_metadata.json",
    "security_overlays.csv",
    "holdings.csv",
    "alignment.csv",
)


def _assert_required_files(run_dir: Path) -> None:
    missing = [f for f in _REQUIRED_FILES if not (run_dir / f).exists()]
    if missing:
        raise FileNotFoundError(
            f"CRA: required PAR files missing from {run_dir}: {missing}"
        )


def _load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("CRA: failed to load %s: %s", path, exc)
        return {}


def _load_csv(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    except (OSError, csv.Error) as exc:
        log.warning("CRA: failed to load %s: %s", path, exc)
        return []


# ── Proposal ID generation ────────────────────────────────────────────────────

def _make_proposal_id(run_id: str, as_of_date: str) -> str:
    date_part = (as_of_date or "").replace("-", "")[:8]
    hash_input = f"{run_id}:{date_part}"
    short_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:8].upper()
    return f"CRA-{date_part}-{short_hash}"


# ── Convenience: load proposal from active run ─────────────────────────────────

def build_proposal_from_manifest(
    manifest_path: str | Path,
    runs_root: str | Path,
    tax_state_path: Optional[str | Path] = None,
) -> Optional[RotationProposal]:
    """Build a RotationProposal from the latest PAR run in the manifest.

    Args:
        manifest_path:   Path to data/portfolio_ingestion/manifest.json.
        runs_root:       Path to data/portfolio_ingestion/analysis_runs/.
        tax_state_path:  Path to data/operator/portfolio_alignment_state.json.

    Returns:
        RotationProposal, or None if no valid run is found.
    """
    manifest_path = Path(manifest_path)
    runs_root = Path(runs_root)

    if not manifest_path.exists():
        log.warning("CRA: manifest not found at %s", manifest_path)
        return None

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("CRA: failed to load manifest: %s", exc)
        return None

    portfolios = manifest.get("portfolios", [])
    if not portfolios:
        log.warning("CRA: no portfolios in manifest")
        return None

    # Find latest COMPLETE run (exclude CONCENTRATED_ALPHA runs for regular CRA)
    completed = [
        p for p in portfolios
        if p.get("status") == "COMPLETE"
        and "CONCENTRATED" not in p.get("run_id", "")
    ]
    if not completed:
        log.warning("CRA: no COMPLETE runs found in manifest")
        return None

    latest = completed[-1]
    run_id = latest.get("run_id", "")
    if not run_id:
        log.warning("CRA: latest run has no run_id")
        return None

    run_dir = runs_root / run_id
    if not run_dir.exists():
        log.warning("CRA: run directory not found: %s", run_dir)
        return None

    # Load tax state
    tax_state = None
    if tax_state_path:
        tax_state_path = Path(tax_state_path)
        if tax_state_path.exists():
            try:
                tax_state = json.loads(tax_state_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                log.warning("CRA: failed to load tax state: %s", exc)

    # Load strategic profiles if present
    sp_path = run_dir / "strategic_profiles.json"
    strategic_profiles = None
    if sp_path.exists():
        try:
            data = json.loads(sp_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                strategic_profiles = data
            elif isinstance(data, dict):
                strategic_profiles = data.get("profiles")
        except (json.JSONDecodeError, OSError):
            pass

    return build_rotation_proposal(
        run_dir=run_dir,
        tax_state=tax_state,
        strategic_profiles=strategic_profiles,
    )
