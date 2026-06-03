"""Phase 7.5D — Capital Deployment Planner.

Given deployable cash and the CW-DAS ranked deployment queue, produces a
prioritised allocation plan showing how much capital to direct toward each
candidate.  This is a read-only guidance artifact — no trade generation,
no execution authority, no order files.

Allocation algorithm — rank-weighted proportional:
    weight_i = deployment_score_i × conviction_mult_i / sqrt(rank_i)

    conviction_mult: CCL = 1.75, HCA = 1.25
    (√rank decay concentrates priority capital in top-ranked positions;
     multipliers calibrated to Phase 7.5Q/7.5U evidence — was 3.0/1.0)

Tier assignment (for operator navigation):
    Tier 1 (HIGHEST):  narrative_tier == CORE_CONVICTION_LEADER
    Tier 2 (SECONDARY): HCA candidates with rank ≤ floor(N × TIER2_RANK_PCTILE)
    Tier 3 (OPTIONAL):  all remaining eligible candidates

Per-position caps (applied before redistribution):
    suggested_add ≤ max(0, (WARN_POSITION_PCT − current_pct) × total_mv / 100)
    Note: hard max is MAX_POSITION_PCT; planner targets the WARN level for safety.

Eligibility: headroom_pct > 0 AND no OW-node penalty (redundancy_pen == 0).
"""

from __future__ import annotations

import dataclasses
import math
from datetime import datetime, timezone
from typing import Optional

from .deployment_queue import (
    MAX_POSITION_PCT,
    WARN_POSITION_PCT,
    CW_DAS_VERSION,
)

PLANNER_VERSION = "1.0"

# Conviction multiplier applied to CCL-tier candidates
# Calibrated per Phase 7.5Q/7.5U audit (was 3.0 / 1.0)
_CCL_CONVICTION_MULT = 1.75
_HCA_CONVICTION_MULT = 1.25

# Rank-percentile cutoff separating Tier 2 from Tier 3
_TIER2_RANK_PCTILE = 0.35   # top 35% of full queue → Tier 2

# Minimum allocation to include in the plan (dollar threshold)
_MIN_ALLOCATION = 50.0

# ─── Output models ────────────────────────────────────────────────────────────

DEPLOYMENT_TIERS = ("TIER_1", "TIER_2", "TIER_3")

CONSTRAINT_STATUSES = ("DEPLOYABLE", "WARN_THRESHOLD", "AT_MAX", "BLOCKED")


@dataclasses.dataclass(frozen=True)
class AllocationRecommendation:
    """Per-holding allocation recommendation produced by the deployment planner."""
    rank:                   int        # original CW-DAS rank
    symbol:                 str
    deployment_tier:        str        # "TIER_1" | "TIER_2" | "TIER_3"
    current_market_value:   float      # USD
    current_weight_pct:     float      # % of total portfolio
    suggested_add:          float      # USD recommended to deploy here
    projected_market_value: float      # USD after suggested deployment
    projected_weight_pct:   float      # % after deployment
    headroom_to_warn:       float      # USD remaining to WARN threshold after add
    constraint_status:      str        # "DEPLOYABLE" | "WARN_THRESHOLD" | "AT_MAX" | "BLOCKED"
    allocation_rationale:   str        # brief human-readable explanation


@dataclasses.dataclass(frozen=True)
class TierSummary:
    tier:            str    # "TIER_1" | "TIER_2" | "TIER_3"
    candidate_count: int
    total_allocated: float
    pct_of_plan:     float  # % of total_allocated across all tiers


@dataclasses.dataclass(frozen=True)
class PortfolioImpact:
    total_market_value:        float   # unchanged (cash → equity swap within portfolio)
    cash_before_pct:           float
    cash_after_pct:            float
    cash_before_mv:            float
    cash_after_mv:             float
    positions_at_warn_before:  int     # count of positions ≥ WARN_POSITION_PCT
    positions_at_warn_after:   int
    total_deployed:            float
    unallocated_cash:          float   # deployable_cash − total_deployed


@dataclasses.dataclass(frozen=True)
class DeploymentPlan:
    """Full deployment plan produced by build_deployment_plan()."""
    run_id:              str
    planner_version:     str
    generated_at:        str
    deployable_cash:     float
    total_market_value:  float
    recommendations:     tuple[AllocationRecommendation, ...]
    total_allocated:     float
    tier_summaries:      tuple[TierSummary, ...]
    portfolio_impact:    PortfolioImpact
    plan_advisory:       str   # one-line operator note


# ─── Public API ───────────────────────────────────────────────────────────────

def build_deployment_plan(
    deployment_queue_data: dict,
    deployable_cash: Optional[float] = None,
) -> DeploymentPlan:
    """Build a capital deployment plan from an existing deployment queue artifact.

    Args:
        deployment_queue_data: Parsed deployment_queue.json dict (must contain
            "queue", "cash_context", "total_market_value", "run_id" keys).
        deployable_cash: Override the deployable cash amount (USD).  If None,
            uses ``cash_context.deployable_mv`` from the queue data.

    Returns:
        DeploymentPlan with per-holding allocation recommendations and
        portfolio-level impact estimates.  Guidance only — no execution.
    """
    run_id = str(deployment_queue_data.get("run_id", "UNKNOWN"))
    total_mv = float(deployment_queue_data.get("total_market_value", 0.0))
    cash_ctx = deployment_queue_data.get("cash_context") or {}

    if deployable_cash is None:
        deployable_cash = float(cash_ctx.get("deployable_mv", 0.0))

    raw_queue: list[dict] = list(deployment_queue_data.get("queue") or [])
    queue_size = len(raw_queue)

    now_utc = datetime.now(timezone.utc).isoformat()

    # Determine Tier 2 rank cutoff (based on full queue size, not eligible count)
    tier2_cutoff = math.floor(queue_size * _TIER2_RANK_PCTILE) or 1

    # ── Eligibility filter ────────────────────────────────────────────────────
    eligible: list[dict] = []
    for c in raw_queue:
        bd = c.get("score_breakdown") or {}
        ow_blocked  = float(bd.get("redundancy_pen", 0)) > 0
        headroom_ok = float(c.get("headroom_pct", 0)) > 0
        if not ow_blocked and headroom_ok:
            eligible.append(c)

    # Edge case: empty queue or no cash
    if not eligible or deployable_cash <= 0.0:
        empty_impact = PortfolioImpact(
            total_market_value=total_mv,
            cash_before_pct=float(cash_ctx.get("cash_pct", 0)),
            cash_after_pct=float(cash_ctx.get("cash_pct", 0)),
            cash_before_mv=float(cash_ctx.get("cash_mv", 0)),
            cash_after_mv=float(cash_ctx.get("cash_mv", 0)),
            positions_at_warn_before=0,
            positions_at_warn_after=0,
            total_deployed=0.0,
            unallocated_cash=deployable_cash,
        )
        return DeploymentPlan(
            run_id=run_id,
            planner_version=PLANNER_VERSION,
            generated_at=now_utc,
            deployable_cash=deployable_cash,
            total_market_value=total_mv,
            recommendations=(),
            total_allocated=0.0,
            tier_summaries=(),
            portfolio_impact=empty_impact,
            plan_advisory="No eligible candidates or no deployable cash.",
        )

    # ── Tier assignment ───────────────────────────────────────────────────────
    def _tier(c: dict) -> str:
        if c.get("narrative_tier") == "CORE_CONVICTION_LEADER":
            return "TIER_1"
        if int(c.get("rank", 9999)) <= tier2_cutoff:
            return "TIER_2"
        return "TIER_3"

    # ── Conviction multiplier ─────────────────────────────────────────────────
    def _conv_mult(c: dict) -> float:
        if c.get("narrative_tier") == "CORE_CONVICTION_LEADER":
            return _CCL_CONVICTION_MULT
        return _HCA_CONVICTION_MULT

    # ── Allocation weights ────────────────────────────────────────────────────
    # weight_i = deployment_score_i × conviction_mult_i / sqrt(rank_i)
    def _weight(c: dict) -> float:
        score = float(c.get("deployment_score", 0.0))
        rank  = max(1, int(c.get("rank", 1)))
        return score * _conv_mult(c) / math.sqrt(rank)

    weights = {c["symbol"]: _weight(c) for c in eligible}
    total_weight = sum(weights.values())

    if total_weight <= 0.0:
        total_weight = 1.0   # guard against degenerate case

    # ── First-pass proportional allocation ───────────────────────────────────
    raw_allocs: dict[str, float] = {
        sym: (w / total_weight) * deployable_cash
        for sym, w in weights.items()
    }

    # ── Per-position cap at WARN threshold ───────────────────────────────────
    # Anything above WARN requires explicit operator override — planner targets WARN.
    def _max_add_to_warn(c: dict) -> float:
        return max(0.0, (WARN_POSITION_PCT - float(c["current_weight_pct"])) / 100.0 * total_mv)

    capped: dict[str, float] = {}
    overflow = 0.0
    uncapped_weight = 0.0

    for c in eligible:
        sym = c["symbol"]
        cap = _max_add_to_warn(c)
        ra  = raw_allocs[sym]
        if ra > cap:
            capped[sym] = cap
            overflow += ra - cap
        else:
            capped[sym] = ra
            uncapped_weight += weights[sym]

    # ── Redistribute overflow to uncapped candidates ──────────────────────────
    if overflow > 0.0 and uncapped_weight > 0.0:
        for c in eligible:
            sym = c["symbol"]
            if capped[sym] < _max_add_to_warn(c):   # still has room
                extra = (weights[sym] / uncapped_weight) * overflow
                new_val = capped[sym] + extra
                hard_cap = _max_add_to_warn(c)
                capped[sym] = min(new_val, hard_cap)

    # ── Build recommendations ─────────────────────────────────────────────────
    recommendations: list[AllocationRecommendation] = []
    total_deployed = 0.0

    # Pre-compute before-state for portfolio impact
    cash_mv_before = float(cash_ctx.get("cash_mv", 0.0))
    cash_pct_before = float(cash_ctx.get("cash_pct", 0.0))
    positions_at_warn_before = sum(
        1 for c in raw_queue
        if float(c.get("current_weight_pct", 0)) >= WARN_POSITION_PCT
    )

    for c in eligible:
        sym = c["symbol"]
        alloc = round(capped.get(sym, 0.0), 2)

        if alloc < _MIN_ALLOCATION:
            alloc = 0.0

        current_mv     = float(c.get("market_value", 0.0))
        current_pct    = float(c.get("current_weight_pct", 0.0))
        projected_mv   = current_mv + alloc
        projected_pct  = (projected_mv / total_mv * 100.0) if total_mv > 0 else 0.0
        headroom_after = max(0.0, (WARN_POSITION_PCT - projected_pct) / 100.0 * total_mv)
        max_to_warn    = _max_add_to_warn(c)

        # Constraint status
        if current_pct >= MAX_POSITION_PCT:
            status = "AT_MAX"
        elif current_pct >= WARN_POSITION_PCT:
            status = "WARN_THRESHOLD"
        elif projected_pct > WARN_POSITION_PCT:
            status = "WARN_THRESHOLD"
        else:
            status = "DEPLOYABLE"

        # Rationale (brief)
        tier = _tier(c)
        tier_label = {"TIER_1": "Tier 1 — CCL", "TIER_2": "Tier 2 — HCA top", "TIER_3": "Tier 3 — optional"}[tier]
        rationale = (
            f"Rank #{c['rank']} | {tier_label} | "
            f"score={c['deployment_score']:.1f} | "
            f"headroom={c['headroom_pct']:.1f}% | "
            f"projected → {projected_pct:.2f}%"
        )
        if alloc == 0.0:
            rationale += " | allocation below minimum threshold"

        recommendations.append(AllocationRecommendation(
            rank=int(c.get("rank", 0)),
            symbol=sym,
            deployment_tier=tier,
            current_market_value=round(current_mv, 2),
            current_weight_pct=round(current_pct, 4),
            suggested_add=round(alloc, 2),
            projected_market_value=round(projected_mv, 2),
            projected_weight_pct=round(projected_pct, 4),
            headroom_to_warn=round(headroom_after, 2),
            constraint_status=status,
            allocation_rationale=rationale,
        ))
        total_deployed += alloc

    total_deployed = round(total_deployed, 2)
    unallocated   = round(deployable_cash - total_deployed, 2)

    # ── Tier summaries ────────────────────────────────────────────────────────
    tier_sums: dict[str, dict] = {t: {"count": 0, "allocated": 0.0} for t in DEPLOYMENT_TIERS}
    for rec in recommendations:
        tier_sums[rec.deployment_tier]["count"]     += 1
        tier_sums[rec.deployment_tier]["allocated"] += rec.suggested_add

    tier_summaries = tuple(
        TierSummary(
            tier=t,
            candidate_count=tier_sums[t]["count"],
            total_allocated=round(tier_sums[t]["allocated"], 2),
            pct_of_plan=round(
                (tier_sums[t]["allocated"] / total_deployed * 100.0) if total_deployed > 0 else 0.0,
                2,
            ),
        )
        for t in DEPLOYMENT_TIERS
    )

    # ── Portfolio impact ──────────────────────────────────────────────────────
    cash_mv_after  = cash_mv_before - total_deployed
    cash_pct_after = (cash_mv_after / total_mv * 100.0) if total_mv > 0 else 0.0

    # Count positions that will cross WARN threshold after deployment
    deployed_by_sym = {r.symbol: r.suggested_add for r in recommendations}
    positions_at_warn_after = sum(
        1 for c in raw_queue
        if (float(c.get("current_weight_pct", 0)) + deployed_by_sym.get(c["symbol"], 0.0) / total_mv * 100.0)
        >= WARN_POSITION_PCT
    )

    portfolio_impact = PortfolioImpact(
        total_market_value=round(total_mv, 2),
        cash_before_pct=round(cash_pct_before, 4),
        cash_after_pct=round(cash_pct_after, 4),
        cash_before_mv=round(cash_mv_before, 2),
        cash_after_mv=round(cash_mv_after, 2),
        positions_at_warn_before=positions_at_warn_before,
        positions_at_warn_after=positions_at_warn_after,
        total_deployed=total_deployed,
        unallocated_cash=unallocated,
    )

    # ── Plan advisory ─────────────────────────────────────────────────────────
    t1_sum = tier_sums["TIER_1"]["allocated"]
    t1_count = tier_sums["TIER_1"]["count"]
    plan_advisory = (
        f"Deploy Tier 1 first (${t1_sum:,.0f} across {t1_count} CCL holdings), "
        f"then Tier 2, then Tier 3 as capacity allows. "
        f"${unallocated:,.0f} remains unallocated below minimum threshold. "
        f"Guidance only — all amounts require operator confirmation."
    )

    return DeploymentPlan(
        run_id=run_id,
        planner_version=PLANNER_VERSION,
        generated_at=now_utc,
        deployable_cash=round(deployable_cash, 2),
        total_market_value=round(total_mv, 2),
        recommendations=tuple(recommendations),
        total_allocated=total_deployed,
        tier_summaries=tier_summaries,
        portfolio_impact=portfolio_impact,
        plan_advisory=plan_advisory,
    )
