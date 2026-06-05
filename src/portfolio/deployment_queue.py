"""Phase 7.5B — Capital Deployment Queue.

Implements the Conviction-Weighted DAS (CW-DAS) scoring model to produce
a ranked capital deployment queue for CONCENTRATED_ALPHA portfolios.

CW-DAS formula (validated in deployment_queue_validation_report.md):
    Signal(0-30) + Replay(0-20) + Conviction(0-35) + Sizing(0-8)
    + Momentum(0-10) − Redundancy_Penalty(0-15) − Concentration_Penalty(0-20)

Conviction weights (vs original DAS CCL=25/HCA=20):
    CORE_CONVICTION_LEADER = 35  (+10)
    HIGH_CONVICTION_ANCHOR = 28  (+8)
    other                  = 10  (unchanged)

Sizing scale: 8 × max(0, 1 − pct/WARN_POSITION_PCT)  (reduced from 15)

All other components (Signal, Replay, Momentum, penalties) are unchanged
from the original DAS specification in phase_7_4a_analysis.py.

Design:
- Additive to existing pipeline — does not modify STI, overlays, or recs
- Read-only against strategic_profiles and overlays already computed
- Generates DeploymentCandidate list sorted by deployment_score descending
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .operator_policy import OperatorPolicyRegistry

from .models import (
    AllocationAlignmentResult,
    HoldingStrategicProfile,
    PortfolioHolding,
    SecurityIntelligenceOverlay,
)

# ─── Constants ────────────────────────────────────────────────────────────────

WARN_POSITION_PCT = 6.0   # soft-warn threshold (matches phase_7_4a_analysis.py)
MAX_POSITION_PCT  = 8.0   # concentration ceiling
MIN_CASH_PCT      = 2.0   # mandate floor — reserve never deployed below this level

CW_DAS_VERSION = "1.0"    # formula version for artifact lineage

# CW-DAS conviction weights
_CCL_CONVICTION   = 35.0
_HCA_CONVICTION   = 28.0
_OTHER_CONVICTION = 10.0

# CW-DAS sizing scale (reduced from 15 to prevent headroom from dominating tier)
_SIZING_SCALE = 8.0

# Eligible narrative tiers
_ELIGIBLE_TIERS = frozenset({"CORE_CONVICTION_LEADER", "HIGH_CONVICTION_ANCHOR"})

# Security types excluded from the deployment queue
_EXCLUDED_SECURITY_TYPES = frozenset({"ETF", "FUND", "MUTUAL_FUND"})


# ─── Models ───────────────────────────────────────────────────────────────────

@dataclasses.dataclass(frozen=True)
class CwDasBreakdown:
    """Component breakdown of a CW-DAS score for explainability.

    All values are rounded to 2 decimal places to avoid floating-point noise
    in downstream JSON serialization.
    """

    signal:         float   # 0–30; derived from composite_score
    replay:         float   # 0 or 20; binary gate on replay_supported
    conviction:     float   # 35 (CCL), 28 (HCA), or 10 (other)
    sizing:         float   # 0–8; headroom relative to WARN_POSITION_PCT
    momentum:       float   # 0, 4.0, 7.5, or 10.0; ESS + signal direction
    redundancy_pen: float   # 0 or 15; overweight allocation node penalty
    conc_pen:       float   # 0–20; concentration penalty above WARN threshold


@dataclasses.dataclass(frozen=True)
class DeploymentCandidate:
    """A single eligible holding ranked by CW-DAS for capital deployment.

    This is a guidance artifact — NOT a trade instruction.  All deployment
    decisions (sizing, lot selection, timing) remain with the operator.

    Eligibility gates applied before this model is produced:
      - replay_supported = True
      - signal_direction = BULLISH
      - strategic_classification = HIGH_CONVICTION_RETAIN
      - narrative_tier in {CCL, HCA}
      - is_cash_equivalent = False
      - security_type not in {ETF, FUND, MUTUAL_FUND}
    """

    rank:               int
    symbol:             str
    current_weight_pct: float     # % of total portfolio (0.0–100.0)
    market_value:       float     # USD
    composite_score:    float     # 0.0–5.0
    narrative_tier:     str       # CORE_CONVICTION_LEADER | HIGH_CONVICTION_ANCHOR
    replay_supported:   bool
    trim_score:         float     # trim_priority_score from STI (lower = more retainable)
    headroom_pct:       float     # 0–100; how far below WARN threshold (0 = at/above WARN)
    deployment_score:   float     # CW-DAS; higher = more attractive for capital deployment
    score_breakdown:    CwDasBreakdown
    notes:              str       # human-readable mandate flags

    # Phase 23.2 — Operator Policy annotations (additive; never affect scores)
    policy_type:        Optional[str]  = None   # active policy type or None
    policy_annotation:  Optional[str]  = None   # human badge text
    policy_protected:   bool           = False  # True iff DO_NOT_SELL active
    policy_rank_boost:  bool           = False  # True iff rank adjusted by PREFERRED_ACCUMULATION
    original_rank:      Optional[int]  = None   # pre-policy rank (for transparency)

    # Phase 23.5 — allocation node for NBA OW-node filtering (additive)
    allocation_node:    str            = ""     # e.g. "EQUITIES.US.LARGE"


# ─── CW-DAS scoring ───────────────────────────────────────────────────────────

def compute_cw_das(
    symbol: str,          # noqa: ARG001 — for callsite clarity
    composite: float,
    pct: float,
    tier: str,
    replay_supported: bool,
    ess_text: str,
    signal_direction: str,
    in_ow_node: bool,
) -> tuple[float, CwDasBreakdown]:
    """Compute the Conviction-Weighted DAS for a single holding.

    Args:
        symbol:           holding ticker (unused in calculation; aids callsite readability)
        composite:        composite signal score (0.0–5.0)
        pct:              current position weight as % of total portfolio (0.0–100.0)
        tier:             narrative_tier string
        replay_supported: True if this holding is in any replay top-N selection
        ess_text:         ESS score text e.g. "VERY_BULLISH", "BULLISH", ""
        signal_direction: signal direction string e.g. "BULLISH", "NEUTRAL"
        in_ow_node:       True if the holding's allocation node is MODERATE+ overweight

    Returns:
        (score, breakdown) where score is max(0, raw) rounded to 2dp
    """
    # 1. Signal (0–30): composite 5.0 maps to 30
    signal_c = min(composite / 5.0 * 30.0, 30.0)

    # 2. Replay (0–20): binary gate
    replay_c = 20.0 if replay_supported else 0.0

    # 3. Conviction (35/28/10): tier-based, higher tier = more conviction weight
    if tier == "CORE_CONVICTION_LEADER":
        conviction_c = _CCL_CONVICTION
    elif tier == "HIGH_CONVICTION_ANCHOR":
        conviction_c = _HCA_CONVICTION
    else:
        conviction_c = _OTHER_CONVICTION

    # 4. Sizing (0–8): headroom below WARN threshold
    headroom = max(0.0, 1.0 - pct / WARN_POSITION_PCT) if WARN_POSITION_PCT else 0.0
    sizing_c = _SIZING_SCALE * headroom

    # 5. Momentum (0–10): ESS + signal direction convergence
    ess = (ess_text or "").upper()
    sig = (signal_direction or "").upper()
    ess_bull = "BULLISH" in ess
    ess_bear = "BEARISH" in ess
    sig_bull = sig == "BULLISH"
    sig_bear = sig == "BEARISH"
    if ess_bull and sig_bull:
        momentum_c = 10.0
    elif ess_bull or sig_bull:
        momentum_c = 7.5
    elif ess_bear or sig_bear:
        momentum_c = 0.0
    else:
        momentum_c = 4.0

    # 6. Redundancy penalty (0–15): node-level overweight mandate conflict
    redundancy_pen = 15.0 if in_ow_node else 0.0

    # 7. Concentration penalty (0–20): graduated above WARN threshold
    conc_pen = 0.0
    if pct > WARN_POSITION_PCT:
        conc_pen = min((pct - WARN_POSITION_PCT) * 4.0, 20.0)

    raw = signal_c + replay_c + conviction_c + sizing_c + momentum_c - redundancy_pen - conc_pen
    score = round(max(0.0, raw), 2)

    breakdown = CwDasBreakdown(
        signal=round(signal_c, 2),
        replay=round(replay_c, 2),
        conviction=round(conviction_c, 2),
        sizing=round(sizing_c, 2),
        momentum=round(momentum_c, 2),
        redundancy_pen=round(redundancy_pen, 2),
        conc_pen=round(conc_pen, 2),
    )
    return score, breakdown


# ─── Eligibility filter ───────────────────────────────────────────────────────

def _is_eligible(
    holding: PortfolioHolding,
    overlay: Optional[SecurityIntelligenceOverlay],
    profile: Optional[HoldingStrategicProfile],
) -> bool:
    """Return True only if the holding passes all deployment eligibility gates."""
    if overlay is None or profile is None:
        return False
    if holding.is_cash_equivalent:
        return False
    sec_type = (holding.security_type or "").strip().upper()
    if sec_type in _EXCLUDED_SECURITY_TYPES:
        return False
    if (overlay.signal_direction or "").upper() != "BULLISH":
        return False
    if not overlay.replay_supported:
        return False
    if profile.strategic_classification != "HIGH_CONVICTION_RETAIN":
        return False
    if profile.narrative_tier not in _ELIGIBLE_TIERS:
        return False
    return True


# ─── OW node resolution ───────────────────────────────────────────────────────

def _build_ow_nodes(alignment_results: list[AllocationAlignmentResult]) -> frozenset[str]:
    """Extract node keys that are MODERATE+ overweight from alignment results."""
    return frozenset(
        r.node_key
        for r in alignment_results
        if r.drift_direction == "OVERWEIGHT" and r.severity in ("HIGH", "MODERATE")
    )


def _holding_in_ow_node(holding: PortfolioHolding, ow_nodes: frozenset[str]) -> bool:
    """Return True if this holding's allocation node is in any OW node."""
    node = f"EQUITIES.{holding.geography}.{holding.market_cap_bucket}"
    return any(
        node.startswith(ow) or ow.startswith(node)
        for ow in ow_nodes
    )


# ─── Notes builder ────────────────────────────────────────────────────────────

def _build_notes(
    pct: float,
    tier: str,
    in_ow_node: bool,
    ow_node_key: Optional[str],
) -> str:
    """Build the human-readable notes string for a DeploymentCandidate."""
    parts: list[str] = []
    tier_label = "CCL tier" if tier == "CORE_CONVICTION_LEADER" else "HCA tier"
    parts.append(tier_label)

    headroom_pct = max(0.0, (1.0 - pct / WARN_POSITION_PCT) * 100)
    if pct >= WARN_POSITION_PCT:
        parts.append(f"BLOCKED: at/above {WARN_POSITION_PCT:.0f}% WARN threshold")
    else:
        parts.append(f"{headroom_pct:.0f}% headroom")

    if in_ow_node and ow_node_key:
        parts.append(f"OW node: {ow_node_key}")

    return " | ".join(parts)


# ─── Main entry point ─────────────────────────────────────────────────────────

def build_deployment_queue(
    portfolio_snapshot_id: str,
    holdings: list[PortfolioHolding],
    overlays: list[SecurityIntelligenceOverlay],
    strategic_profiles: list[HoldingStrategicProfile],
    alignment_results: list[AllocationAlignmentResult],
    total_market_value: float,
) -> list[DeploymentCandidate]:
    """Build the ranked Capital Deployment Queue using CW-DAS scoring.

    Filters all investable holdings to those passing deployment eligibility
    gates, computes the Conviction-Weighted DAS for each, and returns them
    sorted by deployment_score descending (composite as tiebreak).

    This function is purely additive: it reads from already-computed
    strategic_profiles and overlays without modifying them.

    Args:
        portfolio_snapshot_id: snapshot identifier for lineage
        holdings:              list of enriched PortfolioHolding objects
        overlays:              list of SecurityIntelligenceOverlay objects
        strategic_profiles:    list of HoldingStrategicProfile objects from STI
        alignment_results:     list of AllocationAlignmentResult objects
        total_market_value:    total portfolio value (USD) for weight calculations

    Returns:
        List of DeploymentCandidate objects, ranked 1..N by CW-DAS.
        An empty list is returned if no holdings pass eligibility.
    """
    # Build lookup maps
    overlay_by_sym: dict[str, SecurityIntelligenceOverlay] = {
        o.symbol.upper(): o for o in overlays
    }
    profile_by_sym: dict[str, HoldingStrategicProfile] = {
        p.symbol.upper(): p for p in strategic_profiles
    }

    # Overweight nodes for redundancy penalty
    ow_nodes = _build_ow_nodes(alignment_results)

    # Collect candidates
    scored: list[tuple[float, float, DeploymentCandidate]] = []
    # (deployment_score, composite_score, candidate) — for stable sort

    for holding in holdings:
        sym = holding.symbol.upper()
        overlay = overlay_by_sym.get(sym)
        profile = profile_by_sym.get(sym)

        if not _is_eligible(holding, overlay, profile):
            continue

        pct       = holding.percent_of_portfolio
        composite = holding.composite_score or 0.0
        tier      = profile.narrative_tier         # type: ignore[union-attr]
        ess_text  = holding.ess_score_text or ""
        sig_dir   = overlay.signal_direction or ""  # type: ignore[union-attr]

        in_ow = _holding_in_ow_node(holding, ow_nodes)

        # Find the OW node key for notes (first match)
        node = f"EQUITIES.{holding.geography}.{holding.market_cap_bucket}"
        ow_node_key: Optional[str] = None
        if in_ow:
            ow_node_key = next(
                (ow for ow in ow_nodes if node.startswith(ow) or ow.startswith(node)),
                None,
            )

        # Phase 23.5 — canonical allocation node key for this holding
        allocation_node = f"EQUITIES.{holding.geography.upper()}.{holding.market_cap_bucket.upper()}"

        score, breakdown = compute_cw_das(
            symbol=sym,
            composite=composite,
            pct=pct,
            tier=tier,
            replay_supported=overlay.replay_supported,   # type: ignore[union-attr]
            ess_text=ess_text,
            signal_direction=sig_dir,
            in_ow_node=in_ow,
        )

        headroom_pct = round(max(0.0, 1.0 - pct / WARN_POSITION_PCT) * 100.0, 1)
        notes = _build_notes(pct, tier, in_ow, ow_node_key)

        # Placeholder rank; assigned after sorting
        candidate = DeploymentCandidate(
            rank=0,
            symbol=sym,
            current_weight_pct=round(pct, 4),
            market_value=round(holding.market_value, 2),
            composite_score=round(composite, 4),
            narrative_tier=tier,
            replay_supported=overlay.replay_supported,   # type: ignore[union-attr]
            trim_score=round(profile.trim_priority_score or 0.0, 2),  # type: ignore[union-attr]
            headroom_pct=headroom_pct,
            deployment_score=score,
            score_breakdown=breakdown,
            notes=notes,
            allocation_node=allocation_node,
        )
        scored.append((score, composite, candidate))

    # Sort: deployment_score descending, composite descending as tiebreak
    scored.sort(key=lambda t: (-t[0], -t[1]))

    # Assign final ranks (frozen dataclass — rebuild with correct rank)
    result: list[DeploymentCandidate] = []
    for rank, (score, composite, cand) in enumerate(scored, start=1):
        result.append(dataclasses.replace(cand, rank=rank))

    return result


# ─── Cash context helper ─────────────────────────────────────────────────────

def compute_deployable_cash(
    holdings: list[PortfolioHolding],
    total_market_value: float,
    mandate_cash_target_pct: float,
) -> dict[str, float]:
    """Compute cash position and deployable amount above the mandate cash target.

    The effective deployment floor is the higher of:
      - MIN_CASH_PCT (2.0%) — the governance hard minimum enforced by policy
      - mandate_cash_target_pct — the active mandate's strategic cash target

    For CONCENTRATED_ALPHA the mandate target is 7.0%, so only cash genuinely
    above 7.0% is offered as deployable.  The governance floor (2.0%) remains
    a hard backstop but is never the operative threshold when the mandate target
    is higher.

    Args:
        holdings:                 all investable holdings for the run
        total_market_value:       total portfolio MV (USD)
        mandate_cash_target_pct:  CASH node target from the active mandate profile
                                  (e.g. 7.0 for CONCENTRATED_ALPHA).  Required —
                                  caller must source this from the mandate YAML.
                                  Passing None or omitting raises ValueError (fail-closed).

    Returns:
        dict with keys:
          cash_mv                  — total cash MV (USD)
          cash_pct                 — cash as % of total portfolio
          mandate_cash_target_pct  — the mandate target used as the effective floor
          effective_floor_pct      — max(MIN_CASH_PCT, mandate_cash_target_pct)
          floor_mv                 — effective_floor_pct × total_mv (USD)
          excess_pct               — cash_pct − mandate_cash_target_pct
          excess_mv                — cash_mv − (mandate_cash_target_pct × total_mv / 100)
          deployable_mv            — max(0, cash_mv − floor_mv)
          deployable_pct           — deployable_mv as % of total portfolio

    Raises:
        ValueError: if mandate_cash_target_pct is None (fail-closed governance).
    """
    if mandate_cash_target_pct is None:
        raise ValueError(
            "mandate_cash_target_pct is required. "
            "Ensure the active mandate profile includes a CASH node target. "
            "Cannot compute deployable cash without a mandate-defined target."
        )

    cash_mv = sum(h.market_value for h in holdings if h.is_cash_equivalent)
    cash_pct = (cash_mv / total_market_value * 100.0) if total_market_value else 0.0

    # Effective floor: mandate target overrides governance minimum when higher
    effective_floor_pct = max(MIN_CASH_PCT, float(mandate_cash_target_pct))
    floor_mv = total_market_value * effective_floor_pct / 100.0

    # Excess: how far above the mandate target the cash sits (can be negative)
    target_mv = total_market_value * float(mandate_cash_target_pct) / 100.0
    excess_mv = cash_mv - target_mv
    excess_pct = (excess_mv / total_market_value * 100.0) if total_market_value else 0.0

    deployable_mv = max(0.0, cash_mv - floor_mv)
    deployable_pct = (deployable_mv / total_market_value * 100.0) if total_market_value else 0.0

    return {
        "cash_mv":                   round(cash_mv, 2),
        "cash_pct":                  round(cash_pct, 4),
        "mandate_cash_target_pct":   round(float(mandate_cash_target_pct), 4),
        "effective_floor_pct":       round(effective_floor_pct, 4),
        "floor_mv":                  round(floor_mv, 2),
        "excess_mv":                 round(excess_mv, 2),
        "excess_pct":                round(excess_pct, 4),
        "deployable_mv":             round(deployable_mv, 2),
        "deployable_pct":            round(deployable_pct, 4),
    }


# ─── Phase 23.2 — Policy application ─────────────────────────────────────────

def _is_sell_context(candidate: DeploymentCandidate) -> bool:
    """Return True if this deployment candidate is in a sell/reduction context.

    The deployment queue is buy-only by construction (eligibility requires
    BULLISH signal + replay + HIGH_CONVICTION_RETAIN + CCL/HCA tier), so
    sell-context entries will not normally appear here.  This helper is
    provided for correctness and forward compatibility.

    A candidate is considered "sell-context" if its trim_score is above a
    high threshold (>= 60), indicating strategic expendability even if it
    passed buy eligibility gates.
    """
    return candidate.trim_score >= 60.0


def apply_policy_to_queue(
    queue: list[DeploymentCandidate],
    registry: "OperatorPolicyRegistry",
) -> tuple[list[DeploymentCandidate], list[DeploymentCandidate]]:
    """Apply operator policies to the deployment queue.

    Modifies queue ordering and adds policy annotation fields.
    Intelligence scores (deployment_score, composite_score, etc.) are NEVER
    modified.

    Policy application sequence:
      1. Annotate all entries with their active policy type
      2. Identify sell-context entries with DO_NOT_SELL → move to suppressed list
      3. Split remaining into buy cohort and sell cohort
      4. Within buy cohort: boost PREFERRED_ACCUMULATION entries to front
         (tie-break: by original rank / deployment_score)
      5. Within sell cohort: push SELL_LAST entries to tail
         (within-SELL_LAST tie-break: by original rank)
      6. Reassemble and renumber ranks

    Returns:
        (active_queue, suppressed_entries)
        active_queue:      policy-annotated, reranked deployment candidates
        suppressed_entries: DO_NOT_SELL entries removed from execution
    """
    # Step 1: Annotate all entries with policy metadata
    annotated: list[DeploymentCandidate] = []
    for entry in queue:
        pt = registry.active_policy_type(entry.symbol)
        ann = None
        protected = False
        boosted = False
        if pt == "DO_NOT_SELL":
            ann = "🔒 Operator Protected"
            protected = True
        elif pt == "SELL_LAST":
            ann = "⏸ Sell Last"
        elif pt == "CORE_ANCHOR":
            ann = "⚓ Core Anchor"
        elif pt == "PREFERRED_ACCUMULATION":
            ann = "⭐ Preferred Accumulation"
            boosted = True
        annotated.append(dataclasses.replace(
            entry,
            policy_type=pt,
            policy_annotation=ann,
            policy_protected=protected,
            policy_rank_boost=boosted,
            original_rank=entry.rank,
        ))

    # Step 2: Extract DO_NOT_SELL entries that are in sell context → suppressed
    suppressed: list[DeploymentCandidate] = []
    active: list[DeploymentCandidate] = []
    for entry in annotated:
        if entry.policy_type == "DO_NOT_SELL" and _is_sell_context(entry):
            suppressed.append(entry)
        else:
            active.append(entry)

    # Step 3: Partition active into buy cohort and sell cohort
    buy_cohort  = [e for e in active if not _is_sell_context(e)]
    sell_cohort = [e for e in active if _is_sell_context(e)]

    # Step 4: Within buy cohort — PREFERRED_ACCUMULATION to front
    # Preferred entries retain their relative order among themselves (by original_rank)
    buy_preferred = sorted(
        [e for e in buy_cohort if e.policy_rank_boost],
        key=lambda e: (e.original_rank or e.rank),
    )
    buy_normal = [e for e in buy_cohort if not e.policy_rank_boost]
    buy_sorted = buy_preferred + buy_normal

    # Step 5: Within sell cohort — SELL_LAST to tail
    sell_normal = [e for e in sell_cohort if e.policy_type != "SELL_LAST"]
    sell_last   = sorted(
        [e for e in sell_cohort if e.policy_type == "SELL_LAST"],
        key=lambda e: (e.original_rank or e.rank),
    )
    sell_sorted = sell_normal + sell_last

    # Step 6: Reassemble and renumber
    final: list[DeploymentCandidate] = []
    for new_rank, entry in enumerate(buy_sorted + sell_sorted, start=1):
        final.append(dataclasses.replace(entry, rank=new_rank))

    return final, suppressed
