"""Unified Conviction Framework — Phase 7.7A Foundation.

Layer 1 of the UCF: read-only synthesis over existing conviction signals.

This module never recomputes any source signal (composite_score,
narrative_tier, CW-DAS, replay_supported, etc.).  It only reads them and
produces a single UnifiedConvictionVerdict per holding.

Key design constraints (from conviction_framework_design.md):
  - UCF is additive only: reads Layer 0 outputs, writes Layer 1 output.
  - Conflict flags are advisory: they never change the primary UCF label.
  - UCF rank is a unified cross-tier ranking that supersedes both
    strategic_anchor_rank and cw_das_rank as a portfolio-wide ordering.
  - Six labels, ordered by conviction strength:
      CORE_CONVICTION_LEADER > HIGH_CONVICTION_ANCHOR >
      DEPLOYMENT_CANDIDATE > TACTICAL_GROWTH > MAINTAIN > TRIM_WATCH
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

UCF_VERSION = "1.0"

# Six canonical UCF labels (highest → lowest conviction)
UCF_LABELS = (
    "CORE_CONVICTION_LEADER",
    "HIGH_CONVICTION_ANCHOR",
    "DEPLOYMENT_CANDIDATE",
    "TACTICAL_GROWTH",
    "MAINTAIN",
    "TRIM_WATCH",
)

# Tier component score (0–100) by UCF label
_TIER_SCORE: dict[str, float] = {
    "CORE_CONVICTION_LEADER": 100.0,
    "HIGH_CONVICTION_ANCHOR": 80.0,
    "DEPLOYMENT_CANDIDATE":   60.0,
    "TACTICAL_GROWTH":        40.0,
    "MAINTAIN":               20.0,
    "TRIM_WATCH":              0.0,
}

# Strategic classifications that trigger TRIM_WATCH
_TRIM_CLASSIFICATIONS = frozenset({
    "REDUCIBLE",
    "REDUNDANT_EXPOSURE",
    "CONCENTRATION_RISK",
})

# ESS momentum scores (0–100)
_ESS_MOMENTUM: dict[str, float] = {
    "VERY_BULLISH":       100.0,
    "STRONG_BULLISH":     100.0,
    "BULLISH":            100.0,
    "MODERATELY_BULLISH":  75.0,
    "NEUTRAL":             50.0,
    "MODERATELY_BEARISH":  25.0,
    "BEARISH":              0.0,
    "VERY_BEARISH":         0.0,
}

# Signal direction fallback for momentum when ESS is absent
_SIGNAL_MOMENTUM: dict[str, float] = {
    "BULLISH":  75.0,
    "NEUTRAL":  50.0,
    "BEARISH":   0.0,
    "UNKNOWN":  25.0,
}

# Concentration threshold (matching deployment_queue constants)
_WARN_POSITION_PCT = 6.0

# OW-node penalty (deducted from UCF score when is_overweight active)
_OW_SCORE_PENALTY = 10.0

# Maximum trim signal penalty
_MAX_TRIM_PENALTY = 15.0

# CCL queue top-quartile fraction (top 25% of eligible queue → UCF CCL)
_CCL_QUARTILE_FRACTION = 0.25

# HCA queue top-half fraction
_HCA_HALF_FRACTION = 0.50


# ─────────────────────────────────────────────────────────────────────────────
# Output model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class UnifiedConvictionVerdict:
    """Single-holding verdict from the Unified Conviction Framework.

    Read-only synthesis layer — all source signals are preserved verbatim
    from their originating systems.  UCF adds ucf_label, ucf_rank,
    ucf_score, conflict_flags, and signal_summary.

    Fields
    ------
    ucf_label           One of six canonical UCF conviction labels.
    ucf_rank            Portfolio-wide rank (1 = highest conviction).
    ucf_score           0–100 weighted synthesis score (higher = stronger).
    conflict_flags      Zero or more advisory flag strings.
    signal_summary      One-line canonical narrative for the operator.

    Source signals (unchanged from originating systems)
    ---------------------------------------------------
    composite_score     From analytical_universe / STI overlay.
    signal_direction    From security_overlays (build_security_overlays).
    narrative_tier      From STI (build_strategic_profiles → _assign_narrative_tiers).
    replay_supported    From build_security_overlays.
    replay_percentile   From build_security_overlays (None if not available).
    trim_priority_score From build_strategic_profiles.
    cw_das_score        From build_deployment_queue (None if not in queue).
    cw_das_rank         From build_deployment_queue (None if not in queue).

    Deployment intent
    -----------------
    deployment_eligible True if symbol appears in the CW-DAS deployment queue.
    deployment_blocked  True if in queue but is_overweight node is active.
    deployment_block_reason  Human-readable reason for deployment block.
    """

    # Identity
    symbol: str

    # UCF synthesis output
    ucf_label: str                      # One of UCF_LABELS
    ucf_rank: int                       # 1 = highest conviction globally
    ucf_score: float                    # 0–100

    # Advisory conflict flags (never change label; surface for operator)
    conflict_flags: tuple[str, ...]     # immutable tuple of flag strings
    signal_summary: str                 # one-line canonical narrative

    # Source signals (read-only — not recomputed by UCF)
    composite_score: Optional[float]
    signal_direction: str
    narrative_tier: str
    replay_supported: bool
    replay_percentile: Optional[float]
    trim_priority_score: float
    cw_das_score: Optional[float]       # None if not in deployment queue
    cw_das_rank: Optional[int]          # None if not in deployment queue

    # Deployment intent
    deployment_eligible: bool
    deployment_blocked: bool
    deployment_block_reason: Optional[str]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fget(obj, attr: str, default=None):
    """Safely read an attribute from a dataclass or dict, handling NaN/None."""
    if isinstance(obj, dict):
        v = obj.get(attr, default)
    else:
        v = getattr(obj, attr, default)
    if v is None:
        return default
    if isinstance(v, float) and math.isnan(v):
        return default
    return v


def _bool(v) -> bool:
    """Normalise truthy value — handles 'True'/'False' strings from CSV."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return bool(v)


def _assign_label(
    narrative_tier: str,
    strategic_classification: str,
    signal_direction: str,
    composite: Optional[float],
    replay_supported: bool,
    trim_priority_score: float,
    is_overweight: bool,
    cw_das_rank: Optional[int],
    queue_size: int,
) -> str:
    """Determine UCF label using the documented decision hierarchy.

    Priority order (first match wins):
      1. TRIM_WATCH
      2. CORE_CONVICTION_LEADER
      3. HIGH_CONVICTION_ANCHOR
      4. DEPLOYMENT_CANDIDATE
      5. TACTICAL_GROWTH
      6. MAINTAIN (default)
    """
    comp = composite or 0.0
    sig  = (signal_direction or "UNKNOWN").upper()

    # ── 1. TRIM_WATCH ───────────────────────────────────────────────────────
    # Path A: structural trim classification
    if strategic_classification in _TRIM_CLASSIFICATIONS:
        return "TRIM_WATCH"
    # Path B: high trim score (>= 50 = most expendable)
    if trim_priority_score >= 50.0:
        return "TRIM_WATCH"
    # Path C: BEARISH signal direction (regardless of tier)
    if sig == "BEARISH":
        return "TRIM_WATCH"

    # ── 2. CORE_CONVICTION_LEADER ───────────────────────────────────────────
    # All conditions must be true:
    #   - STI assigned CORE_CONVICTION_LEADER tier (gates: BULLISH + replay +
    #     composite ≥ 4.0 + weight ≥ 1.5% + trim < 30)
    #   - CW-DAS rank places holding in top quartile of eligible queue
    #   - No OW node redundancy penalty active
    if queue_size > 0:
        quartile_cutoff = max(1, math.ceil(queue_size * _CCL_QUARTILE_FRACTION))
    else:
        quartile_cutoff = 0

    if (
        narrative_tier == "CORE_CONVICTION_LEADER"
        and cw_das_rank is not None
        and cw_das_rank <= quartile_cutoff
        and not is_overweight
    ):
        return "CORE_CONVICTION_LEADER"

    # ── 3. HIGH_CONVICTION_ANCHOR ───────────────────────────────────────────
    # Path A: CCL tier blocked by OW node (conviction intact; deployment gated)
    if narrative_tier == "CORE_CONVICTION_LEADER" and is_overweight:
        return "HIGH_CONVICTION_ANCHOR"

    # Path B: CCL or HCA tier + strong signal (CCL not top-quartile falls here)
    if (
        narrative_tier in ("CORE_CONVICTION_LEADER", "HIGH_CONVICTION_ANCHOR")
        and comp >= 3.5
        and sig in ("BULLISH", "NEUTRAL")
    ):
        return "HIGH_CONVICTION_ANCHOR"

    # Path C: top half of queue + replay-backed (catches lower-composite HCA)
    if queue_size > 0:
        half_cutoff = max(1, math.ceil(queue_size * _HCA_HALF_FRACTION))
    else:
        half_cutoff = 0

    if (
        cw_das_rank is not None
        and cw_das_rank <= half_cutoff
        and replay_supported
    ):
        return "HIGH_CONVICTION_ANCHOR"

    # ── 4. DEPLOYMENT_CANDIDATE ─────────────────────────────────────────────
    # Replay-backed, positive signal, positive composite — but below HCA threshold
    if (
        replay_supported
        and comp >= 3.0
        and sig in ("BULLISH", "NEUTRAL")
        and not is_overweight
    ):
        return "DEPLOYMENT_CANDIDATE"

    # ── 5. TACTICAL_GROWTH ──────────────────────────────────────────────────
    # Active growth position: TGC tier + positive signal + meaningful composite
    if (
        narrative_tier == "TACTICAL_GROWTH_CANDIDATE"
        and comp >= 2.5
        and sig in ("BULLISH", "NEUTRAL")
    ):
        return "TACTICAL_GROWTH"

    # ── 6. MAINTAIN (default) ───────────────────────────────────────────────
    return "MAINTAIN"


def _compute_conflict_flags(
    narrative_tier: str,
    strategic_classification: str,
    ucf_label: str,
    signal_direction: str,
    composite: Optional[float],
    ess_score_text: Optional[str],
    replay_supported: bool,
    trim_priority_score: float,
    is_overweight: bool,
) -> tuple[str, ...]:
    """Return tuple of advisory conflict flags.

    Flags are additive — they never alter ucf_label.
    Multiple flags may fire for the same holding.
    """
    flags: list[str] = []
    comp = composite or 0.0
    sig  = (signal_direction or "UNKNOWN").upper()
    ess  = (ess_score_text or "").upper()

    # ── CONVICTION_OW_TENSION ───────────────────────────────────────────────
    # Strong conviction tier (CCL/HCA in STI) + OW node blocking deployment.
    if (
        narrative_tier in ("CORE_CONVICTION_LEADER", "HIGH_CONVICTION_ANCHOR")
        and is_overweight
    ):
        flags.append("CONVICTION_OW_TENSION")

    # ── REPLAY_LOSS ─────────────────────────────────────────────────────────
    # BULLISH signal + high composite, but replay support absent.
    # (Represents a methodology gap — sectors without replay strategy.)
    if (
        sig == "BULLISH"
        and comp >= 3.5
        and not replay_supported
    ):
        flags.append("REPLAY_LOSS")

    # ── COMPOSITE_ESS_DIVERGE ───────────────────────────────────────────────
    # ESS direction and composite/signal direction contradict.
    ess_bearish = ess in ("BEARISH", "VERY_BEARISH", "MODERATELY_BEARISH")
    ess_bullish = ess in ("BULLISH", "VERY_BULLISH", "STRONG_BULLISH", "MODERATELY_BULLISH")
    if ess_bearish and sig in ("BULLISH", "NEUTRAL") and comp >= 3.0:
        flags.append("COMPOSITE_ESS_DIVERGE")
    elif ess_bullish and sig == "BEARISH":
        flags.append("COMPOSITE_ESS_DIVERGE")

    # ── SIGNAL_TIER_MISMATCH ────────────────────────────────────────────────
    # ESS is strongly bullish but UCF label is below anchor strength.
    # Signals ahead of current tier assignment — often a replay gap.
    if (
        ess_bullish
        and ucf_label in ("TACTICAL_GROWTH", "MAINTAIN", "TRIM_WATCH")
    ):
        flags.append("SIGNAL_TIER_MISMATCH")

    # ── TRIM_RETAIN_CONFLICT ────────────────────────────────────────────────
    # Classification says retain (HIGH_CONVICTION_RETAIN) but trim score is
    # very high — internal contradiction in STI layer.
    if (
        strategic_classification == "HIGH_CONVICTION_RETAIN"
        and trim_priority_score >= 50.0
    ):
        flags.append("TRIM_RETAIN_CONFLICT")

    return tuple(flags)


def _compute_ucf_score(
    ucf_label: str,
    composite: Optional[float],
    replay_supported: bool,
    replay_percentile: Optional[float],
    ess_score_text: Optional[str],
    signal_direction: str,
    weight_pct: float,
    trim_priority_score: float,
    is_overweight: bool,
    cw_das_score: Optional[float],
) -> float:
    """Compute UCF score (0–100) from weighted conviction signal synthesis.

    Formula (from conviction_framework_design.md §6):
      ucf_score = (
          signal_component    × 0.30
        + replay_component    × 0.20
        + tier_component      × 0.25
        + momentum_component  × 0.15
        + sizing_component    × 0.10
      ) - penalty_deductions

    Components:
      signal:    composite_score / 5 × 100  (0–100)
      replay:    100 if replay_supported; percentile (0–100) if available
      tier:      tier_score for ucf_label (100/80/60/40/20/0)
      momentum:  ESS-based (100/75/50/25/0), fallback to signal_direction
      sizing:    headroom_pct = max(0, (1 - weight_pct/6.0)) × 100

    Penalties:
      OW node:       −10.0 if is_overweight
      concentration: −min((weight_pct − 6.0) × 4.0, 20.0) if weight_pct > 6%
      trim signal:   −min(trim_priority_score × 0.1, 15.0)

    Result is clamped to [0.0, 100.0].
    """
    comp = composite or 0.0
    sig  = (signal_direction or "UNKNOWN").upper()
    ess  = (ess_score_text or "").upper()

    # Signal component: composite on 0–100 scale
    signal_component = (comp / 5.0) * 100.0

    # Replay component: full credit if supported; use percentile if available
    if replay_supported:
        if replay_percentile is not None and not math.isnan(replay_percentile):
            replay_component = float(replay_percentile)
        else:
            replay_component = 100.0
    else:
        replay_component = 0.0

    # Tier component: maps UCF label to conviction strength score
    tier_component = _TIER_SCORE.get(ucf_label, 0.0)

    # Momentum component: prefer ESS direction, fall back to signal_direction
    if ess and ess in _ESS_MOMENTUM:
        momentum_component = _ESS_MOMENTUM[ess]
    else:
        momentum_component = _SIGNAL_MOMENTUM.get(sig, 25.0)

    # Sizing component: headroom to 6% position limit
    headroom_pct = max(0.0, (1.0 - weight_pct / _WARN_POSITION_PCT)) * 100.0
    sizing_component = headroom_pct

    # Weighted sum
    raw = (
        signal_component   * 0.30
        + replay_component * 0.20
        + tier_component   * 0.25
        + momentum_component * 0.15
        + sizing_component * 0.10
    )

    # Penalty deductions
    ow_penalty    = _OW_SCORE_PENALTY if is_overweight else 0.0
    conc_penalty  = min(max(weight_pct - _WARN_POSITION_PCT, 0.0) * 4.0, 20.0)
    trim_penalty  = min(trim_priority_score * 0.1, _MAX_TRIM_PENALTY)

    score = raw - ow_penalty - conc_penalty - trim_penalty

    return round(max(0.0, min(100.0, score)), 2)


def _build_signal_summary(
    symbol: str,
    ucf_label: str,
    signal_direction: str,
    composite: Optional[float],
    replay_supported: bool,
    conflict_flags: tuple[str, ...],
    is_overweight: bool,
) -> str:
    """Generate a one-line canonical conviction narrative for the operator."""
    comp_str = f"{composite:.2f}" if composite is not None else "—"
    sig = (signal_direction or "UNKNOWN").upper()
    replay_str = "replay-backed" if replay_supported else "no replay"

    if ucf_label == "CORE_CONVICTION_LEADER":
        return (
            f"{symbol} — Core conviction leader: {sig} signal, {replay_str}, "
            f"composite {comp_str}. Best deployment target."
        )
    elif ucf_label == "HIGH_CONVICTION_ANCHOR":
        ow_note = " (deployment blocked — OW node)" if "CONVICTION_OW_TENSION" in conflict_flags else ""
        return (
            f"{symbol} — High conviction anchor: {sig} signal, {replay_str}, "
            f"composite {comp_str}{ow_note}."
        )
    elif ucf_label == "DEPLOYMENT_CANDIDATE":
        return (
            f"{symbol} — Deployment candidate: {sig} signal, {replay_str}, "
            f"composite {comp_str}. Deploy if top candidates at capacity."
        )
    elif ucf_label == "TACTICAL_GROWTH":
        replay_note = " — missing replay coverage" if not replay_supported else ""
        return (
            f"{symbol} — Tactical growth: {sig} signal, composite {comp_str}{replay_note}. "
            f"Hold; do not prioritize for new cash."
        )
    elif ucf_label == "TRIM_WATCH":
        return (
            f"{symbol} — TRIM WATCH: {sig} signal, composite {comp_str}. "
            f"Do not add. Evaluate reduction at next rebalance."
        )
    else:  # MAINTAIN
        return f"{symbol} — Maintain: neutral/structural hold, no strong conviction signal."


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def build_ucf_verdicts(
    profiles: list,
    overlays: list,
    deployment_queue: dict,
) -> list[UnifiedConvictionVerdict]:
    """Build a UCF verdict for every holding in the portfolio.

    This is a **read-only synthesis function** — it never recomputes any source
    signal.  It reads strategic profiles, security overlays, and the deployment
    queue, then synthesises them into one ``UnifiedConvictionVerdict`` per
    holding.

    Args:
        profiles:         list[HoldingStrategicProfile] from build_strategic_profiles()
        overlays:         list[SecurityIntelligenceOverlay] from build_security_overlays()
        deployment_queue: dict as produced by build_deployment_queue() and stored
                          in deployment_queue.json — must contain a "queue" list.

    Returns:
        list[UnifiedConvictionVerdict] sorted by ucf_rank ascending (rank 1 first).
    """
    # ── Build lookup maps ────────────────────────────────────────────────────
    overlay_by_sym: dict[str, object] = {
        (_fget(o, "symbol", "") or "").upper(): o
        for o in overlays
    }

    # Queue items by symbol
    queue_items: list[dict] = deployment_queue.get("queue", [])
    queue_by_sym: dict[str, dict] = {
        item["symbol"].upper(): item for item in queue_items
    }
    queue_size = len(queue_items)

    # ── Compute pre-ranked verdicts (without ucf_rank) ───────────────────────
    unranked: list[tuple[float, str, dict]] = []  # (ucf_score, symbol, kwargs)

    for profile in profiles:
        sym     = (_fget(profile, "symbol", "") or "").upper()
        overlay = overlay_by_sym.get(sym)
        q_item  = queue_by_sym.get(sym)

        # ── Read source signals ──────────────────────────────────────────────
        narrative_tier     = _fget(profile, "narrative_tier", "") or ""
        strat_class        = _fget(profile, "strategic_classification", "") or ""
        trim_score         = float(_fget(profile, "trim_priority_score", 0.0) or 0.0)

        composite          = _fget(overlay, "composite_score")
        if composite is not None:
            composite = float(composite)
        signal_dir         = str(_fget(overlay, "signal_direction", "UNKNOWN") or "UNKNOWN").upper()
        ess_text           = str(_fget(overlay, "ess_score_text", "") or "")
        replay_sup         = _bool(_fget(overlay, "replay_supported", False))
        replay_pct_raw     = _fget(overlay, "replay_percentile")
        replay_pct         = float(replay_pct_raw) if replay_pct_raw is not None else None
        weight_pct         = float(_fget(overlay, "percent_of_portfolio", 0.0) or 0.0)
        is_ow              = _bool(_fget(overlay, "is_overweight_vs_target", False))

        # Queue-derived fields
        cw_das_score: Optional[float] = None
        cw_das_rank:  Optional[int]   = None
        deployment_eligible            = q_item is not None
        deployment_blocked             = False
        deployment_block_reason: Optional[str] = None

        if q_item:
            cw_das_score = float(q_item.get("deployment_score") or 0.0)
            cw_das_rank  = int(q_item.get("rank") or 0)
            # Block detection: is_overweight flag on overlay (OW node active)
            # Cross-checked with redundancy_pen in score_breakdown
            score_breakdown = q_item.get("score_breakdown") or {}
            redundancy_pen  = float(score_breakdown.get("redundancy_pen", 0.0) or 0.0)
            if is_ow or redundancy_pen > 0.0:
                deployment_blocked       = True
                deployment_block_reason  = (
                    "Overweight allocation node active — add blocked until node rebalances"
                )

        # ── Label assignment ─────────────────────────────────────────────────
        ucf_label = _assign_label(
            narrative_tier=narrative_tier,
            strategic_classification=strat_class,
            signal_direction=signal_dir,
            composite=composite,
            replay_supported=replay_sup,
            trim_priority_score=trim_score,
            is_overweight=is_ow,
            cw_das_rank=cw_das_rank,
            queue_size=queue_size,
        )

        # ── Conflict flags ───────────────────────────────────────────────────
        conflict_flags = _compute_conflict_flags(
            narrative_tier=narrative_tier,
            strategic_classification=strat_class,
            ucf_label=ucf_label,
            signal_direction=signal_dir,
            composite=composite,
            ess_score_text=ess_text,
            replay_supported=replay_sup,
            trim_priority_score=trim_score,
            is_overweight=is_ow,
        )

        # ── UCF score ────────────────────────────────────────────────────────
        ucf_score = _compute_ucf_score(
            ucf_label=ucf_label,
            composite=composite,
            replay_supported=replay_sup,
            replay_percentile=replay_pct,
            ess_score_text=ess_text,
            signal_direction=signal_dir,
            weight_pct=weight_pct,
            trim_priority_score=trim_score,
            is_overweight=is_ow,
            cw_das_score=cw_das_score,
        )

        # ── Signal summary ───────────────────────────────────────────────────
        signal_summary = _build_signal_summary(
            symbol=sym,
            ucf_label=ucf_label,
            signal_direction=signal_dir,
            composite=composite,
            replay_supported=replay_sup,
            conflict_flags=conflict_flags,
            is_overweight=is_ow,
        )

        unranked.append((
            ucf_score,
            sym,
            dict(
                symbol=sym,
                ucf_label=ucf_label,
                ucf_rank=0,         # assigned below
                ucf_score=ucf_score,
                conflict_flags=conflict_flags,
                signal_summary=signal_summary,
                composite_score=composite,
                signal_direction=signal_dir,
                narrative_tier=narrative_tier,
                replay_supported=replay_sup,
                replay_percentile=replay_pct,
                trim_priority_score=trim_score,
                cw_das_score=cw_das_score,
                cw_das_rank=cw_das_rank,
                deployment_eligible=deployment_eligible,
                deployment_blocked=deployment_blocked,
                deployment_block_reason=deployment_block_reason,
            ),
        ))

    # ── Global UCF rank ──────────────────────────────────────────────────────
    # Rank within label tier first (tier order), then by ucf_score desc,
    # then by symbol for determinism.  TRIM_WATCH positions appear last.
    _LABEL_ORDER = {label: i for i, label in enumerate(UCF_LABELS[:-1])}
    _LABEL_ORDER["TRIM_WATCH"] = len(UCF_LABELS)  # bottom of ranking

    def _rank_key(item: tuple) -> tuple:
        ucf_score, sym, kwargs = item
        tier_order = _LABEL_ORDER.get(kwargs["ucf_label"], 99)
        return (tier_order, -ucf_score, sym)

    sorted_unranked = sorted(unranked, key=_rank_key)

    verdicts: list[UnifiedConvictionVerdict] = []
    for rank, (ucf_score, sym, kwargs) in enumerate(sorted_unranked, start=1):
        kwargs["ucf_rank"] = rank
        verdicts.append(UnifiedConvictionVerdict(**kwargs))

    return verdicts
