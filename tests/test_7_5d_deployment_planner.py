"""Phase 7.5D — Capital Deployment Planner: tests.

Validates build_deployment_plan() against the acceptance criteria:
  1. total_allocated <= deployable_cash
  2. No position exceeds MAX_POSITION_PCT after suggested deployment
  3. Projected weights reconcile (current_mv + suggested_add ≈ projected_mv)
  4. CCL-tier candidates are in TIER_1
  5. AEIS and VRT (top 2 in PAR-20260531-F794D952) are in TIER_1
  6. OW-node-blocked candidates are excluded from recommendations
  7. Portfolio impact fields are consistent with recommendations
  8. unallocated_cash + total_allocated ≈ deployable_cash
  9. Tier summaries sum to total_allocated
 10. plan_advisory is non-empty
 11. Zero cash → empty plan (no crash)
 12. Empty queue → empty plan (no crash)

Phase 7.5V — Multiplier Calibration Regression Tests (TestMultiplierCalibration):
 13. CCL conviction multiplier == 1.75
 14. HCA conviction multiplier == 1.25
 15. VRT still ranks #1 when it is the top-ranked CCL candidate
 16. CCL candidate still receives more than any HCA candidate
 17. VRT allocation decreases vs old 3.0/1.0 multiplier baseline
 18. HCA pool allocation share increases vs old 3.0/1.0 baseline
 19. Total deployed cash unchanged (same deployable input)
 20. No candidate receives allocation above available deployable cash
 21. Allocation curve weight function is unchanged (sqrt rank decay)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, ".")

from src.portfolio.deployment_planner import (
    PLANNER_VERSION,
    AllocationRecommendation,
    DeploymentPlan,
    TierSummary,
    build_deployment_plan,
)
from src.portfolio.deployment_queue import MAX_POSITION_PCT, WARN_POSITION_PCT

# ─── Test fixtures ────────────────────────────────────────────────────────────

_REFERENCE_RUN_ID = "PAR-20260531-F794D952"
_REFERENCE_DQ_PATH = (
    Path("data/portfolio_ingestion/analysis_runs")
    / _REFERENCE_RUN_ID
    / "deployment_queue.json"
)


def _load_reference_dq() -> dict:
    """Load the reference run's deployment_queue.json."""
    if not _REFERENCE_DQ_PATH.exists():
        pytest.skip(f"Reference deployment_queue.json not found: {_REFERENCE_DQ_PATH}")
    with open(_REFERENCE_DQ_PATH) as fh:
        return json.load(fh)


def _minimal_dq(queue_items: list[dict], *, cash: float = 10_000.0, total_mv: float = 100_000.0) -> dict:
    """Build a minimal deployment_queue dict for unit testing."""
    return {
        "run_id": "TEST-RUN-001",
        "queue_version": "CW-DAS-1.0",
        "total_market_value": total_mv,
        "cash_context": {
            "cash_mv": cash * 1.5,
            "cash_pct": (cash * 1.5) / total_mv * 100,
            "floor_mv": cash * 0.3,
            "deployable_mv": cash,
            "deployable_pct": cash / total_mv * 100,
        },
        "candidate_count": len(queue_items),
        "queue": queue_items,
    }


def _make_candidate(
    *,
    rank: int,
    symbol: str,
    score: float,
    weight_pct: float,
    tier: str = "HIGH_CONVICTION_ANCHOR",
    replay: bool = True,
    redundancy_pen: float = 0.0,
) -> dict:
    total_mv = 472_219.90  # mirrors reference run
    mv = weight_pct / 100 * total_mv
    headroom = max(0.0, (WARN_POSITION_PCT - weight_pct) / WARN_POSITION_PCT * 100)
    return {
        "rank": rank,
        "symbol": symbol,
        "current_weight_pct": weight_pct,
        "market_value": mv,
        "composite_score": score * 0.1,
        "narrative_tier": tier,
        "replay_supported": replay,
        "trim_score": 10.0,
        "headroom_pct": headroom,
        "deployment_score": score,
        "score_breakdown": {
            "signal": 25.0,
            "replay": 20.0 if replay else 0.0,
            "conviction": 28.0,
            "sizing": 5.0,
            "momentum": 7.5,
            "redundancy_pen": redundancy_pen,
            "conc_pen": 0.0,
        },
        "notes": "",
    }


# ─── Unit tests: empty / edge cases ──────────────────────────────────────────

class TestEdgeCases:
    def test_zero_cash_returns_empty_plan(self):
        dq = _minimal_dq([_make_candidate(rank=1, symbol="AAA", score=90.0, weight_pct=2.0)], cash=0.0)
        plan = build_deployment_plan(dq, deployable_cash=0.0)
        assert isinstance(plan, DeploymentPlan)
        assert plan.total_allocated == 0.0
        assert len(plan.recommendations) == 0

    def test_empty_queue_returns_empty_plan(self):
        dq = _minimal_dq([], cash=10_000.0)
        plan = build_deployment_plan(dq)
        assert plan.total_allocated == 0.0
        assert len(plan.recommendations) == 0

    def test_all_ow_blocked_returns_empty_plan(self):
        items = [
            _make_candidate(rank=i, symbol=f"SY{i}", score=90.0, weight_pct=2.0, redundancy_pen=15.0)
            for i in range(1, 6)
        ]
        dq = _minimal_dq(items, cash=5_000.0)
        plan = build_deployment_plan(dq)
        assert plan.total_allocated == 0.0

    def test_cash_override_respected(self):
        items = [
            _make_candidate(rank=1, symbol="AEIS", score=95.56, weight_pct=2.42,
                            tier="CORE_CONVICTION_LEADER"),
            _make_candidate(rank=2, symbol="VRT",  score=95.53, weight_pct=3.60,
                            tier="CORE_CONVICTION_LEADER"),
        ]
        dq = _minimal_dq(items, cash=33_175.0)
        override_cash = 10_000.0
        plan = build_deployment_plan(dq, deployable_cash=override_cash)
        assert plan.deployable_cash == override_cash
        assert plan.total_allocated <= override_cash + 0.01


# ─── Unit tests: invariants ───────────────────────────────────────────────────

class TestAllocationInvariants:
    def _make_plan(self) -> DeploymentPlan:
        items = [
            _make_candidate(rank=1, symbol="AEIS", score=95.56, weight_pct=2.42,
                            tier="CORE_CONVICTION_LEADER"),
            _make_candidate(rank=2, symbol="VRT",  score=95.53, weight_pct=3.60,
                            tier="CORE_CONVICTION_LEADER"),
            _make_candidate(rank=3, symbol="ARW",  score=94.11, weight_pct=0.92),
            _make_candidate(rank=4, symbol="SNX",  score=93.51, weight_pct=0.86),
            _make_candidate(rank=5, symbol="ATLC", score=93.48, weight_pct=0.89),
        ]
        dq = _minimal_dq(items, cash=20_000.0, total_mv=472_219.90)
        return build_deployment_plan(dq, deployable_cash=20_000.0)

    def test_total_allocated_le_deployable_cash(self):
        plan = self._make_plan()
        assert plan.total_allocated <= plan.deployable_cash + 0.01

    def test_no_position_exceeds_max_position_pct(self):
        plan = self._make_plan()
        total_mv = plan.total_market_value
        for rec in plan.recommendations:
            if rec.suggested_add > 0:
                assert rec.projected_weight_pct <= MAX_POSITION_PCT + 0.01, (
                    f"{rec.symbol}: projected {rec.projected_weight_pct:.2f}% > MAX {MAX_POSITION_PCT}%"
                )

    def test_projected_values_reconcile(self):
        plan = self._make_plan()
        for rec in plan.recommendations:
            expected_mv  = rec.current_market_value + rec.suggested_add
            expected_pct = expected_mv / plan.total_market_value * 100
            assert abs(rec.projected_market_value - expected_mv) < 0.05, (
                f"{rec.symbol}: projected_mv mismatch"
            )
            assert abs(rec.projected_weight_pct - expected_pct) < 0.01, (
                f"{rec.symbol}: projected_pct mismatch"
            )

    def test_unallocated_cash_reconciles(self):
        plan = self._make_plan()
        assert abs(plan.portfolio_impact.unallocated_cash + plan.total_allocated - plan.deployable_cash) < 0.05

    def test_tier_summaries_sum_to_total_allocated(self):
        plan = self._make_plan()
        tier_total = sum(t.total_allocated for t in plan.tier_summaries)
        assert abs(tier_total - plan.total_allocated) < 0.05

    def test_plan_advisory_non_empty(self):
        plan = self._make_plan()
        assert plan.plan_advisory
        assert len(plan.plan_advisory) > 10


# ─── Unit tests: tier assignment ─────────────────────────────────────────────

class TestTierAssignment:
    def test_ccl_candidates_assigned_tier_1(self):
        items = [
            _make_candidate(rank=1, symbol="AEIS", score=95.0, weight_pct=2.5,
                            tier="CORE_CONVICTION_LEADER"),
            _make_candidate(rank=2, symbol="VRT",  score=94.0, weight_pct=3.5,
                            tier="CORE_CONVICTION_LEADER"),
            _make_candidate(rank=3, symbol="ARW",  score=90.0, weight_pct=1.0),
        ]
        dq = _minimal_dq(items, cash=20_000.0, total_mv=472_219.90)
        plan = build_deployment_plan(dq, deployable_cash=20_000.0)
        for rec in plan.recommendations:
            if rec.symbol in ("AEIS", "VRT"):
                assert rec.deployment_tier == "TIER_1", (
                    f"Expected TIER_1 for {rec.symbol}, got {rec.deployment_tier}"
                )

    def test_hca_candidates_not_tier_1(self):
        items = [
            _make_candidate(rank=3, symbol="ARW",  score=90.0, weight_pct=1.0),
            _make_candidate(rank=4, symbol="SNX",  score=89.0, weight_pct=0.9),
        ]
        dq = _minimal_dq(items, cash=5_000.0, total_mv=472_219.90)
        plan = build_deployment_plan(dq, deployable_cash=5_000.0)
        for rec in plan.recommendations:
            assert rec.deployment_tier != "TIER_1"

    def test_ow_blocked_excluded_from_recommendations(self):
        items = [
            _make_candidate(rank=1, symbol="GOOD", score=95.0, weight_pct=2.0),
            _make_candidate(rank=2, symbol="BLKD", score=90.0, weight_pct=2.0,
                            redundancy_pen=15.0),
        ]
        dq = _minimal_dq(items, cash=5_000.0, total_mv=472_219.90)
        plan = build_deployment_plan(dq, deployable_cash=5_000.0)
        syms = {r.symbol for r in plan.recommendations}
        assert "BLKD" not in syms, "OW-blocked candidate should not appear in recommendations"
        assert "GOOD" in syms


# ─── Unit tests: CCL priority ─────────────────────────────────────────────────

class TestCCLPriority:
    def test_ccl_gets_larger_allocation_than_hca(self):
        """CCL candidate at same rank should receive more than HCA peer (3x mult)."""
        items = [
            _make_candidate(rank=1, symbol="CCL1", score=90.0, weight_pct=1.0,
                            tier="CORE_CONVICTION_LEADER"),
            _make_candidate(rank=2, symbol="HCA1", score=90.0, weight_pct=1.0),
        ]
        dq = _minimal_dq(items, cash=10_000.0, total_mv=472_219.90)
        plan = build_deployment_plan(dq, deployable_cash=10_000.0)
        allocs = {r.symbol: r.suggested_add for r in plan.recommendations}
        assert allocs.get("CCL1", 0) > allocs.get("HCA1", 0), (
            "CCL candidate should receive higher allocation than HCA at same score"
        )

    def test_rank_decay_higher_rank_gets_more(self):
        """Rank 1 HCA should receive more than rank 5 HCA."""
        items = [
            _make_candidate(rank=r, symbol=f"SY{r}", score=90.0, weight_pct=1.0)
            for r in range(1, 6)
        ]
        dq = _minimal_dq(items, cash=10_000.0, total_mv=472_219.90)
        plan = build_deployment_plan(dq, deployable_cash=10_000.0)
        allocs = {r.symbol: r.suggested_add for r in plan.recommendations if r.suggested_add > 0}
        if len(allocs) >= 2:
            assert allocs.get("SY1", 0) >= allocs.get("SY5", 0), (
                "Rank 1 should receive >= allocation than rank 5"
            )


# ─── Integration test: reference run ─────────────────────────────────────────

class TestReferenceRun:
    """Tests against PAR-20260531-F794D952 (the canonical validation run)."""

    def test_aeis_and_vrt_in_tier_1(self):
        dq = _load_reference_dq()
        plan = build_deployment_plan(dq)
        tier1_syms = {r.symbol for r in plan.recommendations if r.deployment_tier == "TIER_1"}
        assert "AEIS" in tier1_syms, "AEIS (rank 1, CCL) should be in TIER_1"
        assert "VRT"  in tier1_syms, "VRT  (rank 2, CCL) should be in TIER_1"

    def test_total_allocated_within_deployable_cash(self):
        dq = _load_reference_dq()
        plan = build_deployment_plan(dq)
        assert plan.total_allocated <= plan.deployable_cash + 0.01, (
            f"Allocated ${plan.total_allocated:,.2f} exceeds deployable ${plan.deployable_cash:,.2f}"
        )

    def test_no_position_exceeds_max_pct(self):
        dq = _load_reference_dq()
        plan = build_deployment_plan(dq)
        for rec in plan.recommendations:
            if rec.suggested_add > 0:
                assert rec.projected_weight_pct <= MAX_POSITION_PCT + 0.01, (
                    f"{rec.symbol}: projected {rec.projected_weight_pct:.2f}% > MAX"
                )

    def test_projected_weight_never_exceeds_warn_in_suggestions(self):
        """Planner should cap at WARN_POSITION_PCT by default."""
        dq = _load_reference_dq()
        plan = build_deployment_plan(dq)
        for rec in plan.recommendations:
            if rec.suggested_add > 0:
                assert rec.projected_weight_pct <= WARN_POSITION_PCT + 0.01, (
                    f"{rec.symbol}: projected {rec.projected_weight_pct:.2f}% exceeds WARN {WARN_POSITION_PCT}%"
                )

    def test_aeis_gets_higher_allocation_than_lower_hca(self):
        """AEIS (rank 1, CCL) should receive more than any HCA candidate."""
        dq = _load_reference_dq()
        plan = build_deployment_plan(dq)
        aeis_alloc = next((r.suggested_add for r in plan.recommendations if r.symbol == "AEIS"), 0)
        for rec in plan.recommendations:
            if rec.deployment_tier != "TIER_1":
                assert aeis_alloc >= rec.suggested_add, (
                    f"AEIS alloc ${aeis_alloc:,.2f} < {rec.symbol} ${rec.suggested_add:,.2f}"
                )

    def test_portfolio_impact_cash_after_decreases(self):
        dq = _load_reference_dq()
        plan = build_deployment_plan(dq)
        impact = plan.portfolio_impact
        if plan.total_allocated > 0:
            assert impact.cash_after_mv < impact.cash_before_mv, (
                "Cash MV should decrease after deployment"
            )
            assert impact.cash_after_pct < impact.cash_before_pct

    def test_planner_version_set(self):
        dq = _load_reference_dq()
        plan = build_deployment_plan(dq)
        assert plan.planner_version == PLANNER_VERSION

    def test_at_least_two_tiers_populated(self):
        dq = _load_reference_dq()
        plan = build_deployment_plan(dq)
        populated = [t for t in plan.tier_summaries if t.candidate_count > 0]
        assert len(populated) >= 2, "Expected at least Tier 1 and Tier 2 to have candidates"

    def test_tier_summaries_pct_sums_to_100(self):
        dq = _load_reference_dq()
        plan = build_deployment_plan(dq)
        if plan.total_allocated > 0:
            total_pct = sum(t.pct_of_plan for t in plan.tier_summaries)
            assert abs(total_pct - 100.0) < 1.0, (
                f"Tier pct_of_plan sum {total_pct:.2f}% should be ~100%"
            )

    def test_recommendations_have_rationale(self):
        dq = _load_reference_dq()
        plan = build_deployment_plan(dq)
        for rec in plan.recommendations:
            assert rec.allocation_rationale, f"{rec.symbol} has empty allocation_rationale"

    def test_constraint_statuses_are_valid(self):
        from src.portfolio.deployment_planner import CONSTRAINT_STATUSES
        dq = _load_reference_dq()
        plan = build_deployment_plan(dq)
        for rec in plan.recommendations:
            assert rec.constraint_status in CONSTRAINT_STATUSES, (
                f"{rec.symbol}: invalid constraint_status '{rec.constraint_status}'"
            )


# ─── Phase 7.5V — Multiplier Calibration Regression Tests ────────────────────

class TestMultiplierCalibration:
    """Regression tests confirming Phase 7.5V multiplier calibration values and
    their expected effects. Added per Phase 7.5V acceptance criteria 13–21."""

    # AC-13: CCL multiplier constant is 1.75
    def test_ccl_conviction_mult_is_1_75(self):
        from src.portfolio.deployment_planner import _CCL_CONVICTION_MULT
        assert _CCL_CONVICTION_MULT == 1.75, (
            f"Expected CCL mult=1.75, got {_CCL_CONVICTION_MULT} "
            "(Phase 7.5V calibration)"
        )

    # AC-14: HCA multiplier constant is 1.25
    def test_hca_conviction_mult_is_1_25(self):
        from src.portfolio.deployment_planner import _HCA_CONVICTION_MULT
        assert _HCA_CONVICTION_MULT == 1.25, (
            f"Expected HCA mult=1.25, got {_HCA_CONVICTION_MULT} "
            "(Phase 7.5V calibration)"
        )

    def _make_ccl_hca_plan(
        self, *, ccl_score: float = 95.5, hca_score: float = 94.0, cash: float = 33_000.0
    ) -> "DeploymentPlan":
        """Two-candidate plan: 1 CCL (rank 1) + 1 HCA (rank 2)."""
        items = [
            _make_candidate(rank=1, symbol="CCL_VRT", score=ccl_score, weight_pct=1.0,
                            tier="CORE_CONVICTION_LEADER"),
            _make_candidate(rank=2, symbol="HCA_ARW", score=hca_score, weight_pct=1.0),
        ]
        return build_deployment_plan(_minimal_dq(items, cash=cash, total_mv=472_219.90),
                                     deployable_cash=cash)

    # AC-15: CCL rank-1 candidate still gets the highest allocation
    def test_ccl_rank1_still_has_largest_allocation(self):
        plan = self._make_ccl_hca_plan()
        allocs = {r.symbol: r.suggested_add for r in plan.recommendations}
        assert allocs["CCL_VRT"] > allocs["HCA_ARW"], (
            "CCL rank-1 candidate should still receive more than HCA rank-2 at 1.75/1.25"
        )

    # AC-16: CCL still receives more than any HCA candidate (reference run)
    def test_ccl_gets_more_than_any_hca_reference_run(self):
        dq = _load_reference_dq()
        plan = build_deployment_plan(dq)
        ccl_allocs = [r.suggested_add for r in plan.recommendations if r.deployment_tier == "TIER_1"]
        hca_allocs = [r.suggested_add for r in plan.recommendations if r.deployment_tier != "TIER_1"]
        if ccl_allocs and hca_allocs:
            assert max(ccl_allocs) >= max(hca_allocs), (
                "Max CCL allocation should be >= max HCA allocation even at 1.75/1.25"
            )

    # AC-17: VRT allocation under 1.75/1.25 is lower than it would be at 3.0/1.0
    def test_ccl_allocation_lower_than_old_3x_baseline(self):
        """Compute plan at 1.75/1.25, then simulate old 3.0/1.0 and compare."""
        import math
        from src.portfolio.deployment_planner import _HCA_CONVICTION_MULT

        items = [
            _make_candidate(rank=1, symbol="VRT",  score=95.5,  weight_pct=3.62,
                            tier="CORE_CONVICTION_LEADER"),
            _make_candidate(rank=2, symbol="ARW",  score=94.12, weight_pct=0.91),
            _make_candidate(rank=3, symbol="SNX",  score=93.48, weight_pct=0.89),
            _make_candidate(rank=4, symbol="ATLC", score=93.47, weight_pct=0.90),
            _make_candidate(rank=5, symbol="PSX",  score=93.35, weight_pct=0.88),
        ]
        cash = 33_141.36
        dq   = _minimal_dq(items, cash=cash, total_mv=472_219.90)

        # Current plan (1.75/1.25)
        plan_new = build_deployment_plan(dq, deployable_cash=cash)
        vrt_new  = next(r.suggested_add for r in plan_new.recommendations if r.symbol == "VRT")

        # Simulate old 3.0/1.0 manually via weights
        w_vrt_old  = 95.5  * 3.0  / math.sqrt(1)
        w_arw_old  = 94.12 * 1.0  / math.sqrt(2)
        w_snx_old  = 93.48 * 1.0  / math.sqrt(3)
        w_atlc_old = 93.47 * 1.0  / math.sqrt(4)
        w_psx_old  = 93.35 * 1.0  / math.sqrt(5)
        total_w_old = w_vrt_old + w_arw_old + w_snx_old + w_atlc_old + w_psx_old
        vrt_old = cash * w_vrt_old / total_w_old

        assert vrt_new < vrt_old, (
            f"VRT new alloc ${vrt_new:,.2f} should be < old 3.0/1.0 alloc ${vrt_old:,.2f}"
        )

    # AC-18: HCA pool share increases vs old 3.0/1.0 baseline
    def test_hca_pool_share_higher_than_old_3x_baseline(self):
        """HCA total allocation % should be higher under 1.75/1.25 than under 3.0/1.0."""
        import math

        items = [
            _make_candidate(rank=1, symbol="VRT",  score=95.5,  weight_pct=3.62,
                            tier="CORE_CONVICTION_LEADER"),
            _make_candidate(rank=2, symbol="ARW",  score=94.12, weight_pct=0.91),
            _make_candidate(rank=3, symbol="SNX",  score=93.48, weight_pct=0.89),
            _make_candidate(rank=4, symbol="ATLC", score=93.47, weight_pct=0.90),
            _make_candidate(rank=5, symbol="PSX",  score=93.35, weight_pct=0.88),
        ]
        cash = 33_141.36
        dq   = _minimal_dq(items, cash=cash, total_mv=472_219.90)

        plan_new  = build_deployment_plan(dq, deployable_cash=cash)
        hca_new   = sum(r.suggested_add for r in plan_new.recommendations if r.symbol != "VRT")
        hca_pct_new = hca_new / cash * 100

        # Old 3.0/1.0 weights
        w_vrt  = 95.5  * 3.0 / math.sqrt(1)
        w_arw  = 94.12 * 1.0 / math.sqrt(2)
        w_snx  = 93.48 * 1.0 / math.sqrt(3)
        w_atlc = 93.47 * 1.0 / math.sqrt(4)
        w_psx  = 93.35 * 1.0 / math.sqrt(5)
        total_w = w_vrt + w_arw + w_snx + w_atlc + w_psx
        hca_old_pct = (w_arw + w_snx + w_atlc + w_psx) / total_w * 100

        assert hca_pct_new > hca_old_pct, (
            f"HCA share new={hca_pct_new:.1f}% should exceed old={hca_old_pct:.1f}% at 1.75/1.25"
        )

    # AC-19: Total deployed cash is unchanged (planner still deploys all available cash)
    def test_total_deployed_cash_unchanged(self):
        dq   = _load_reference_dq()
        plan = build_deployment_plan(dq)
        assert abs(plan.total_allocated - plan.deployable_cash) < 1.00, (
            f"Total allocated ${plan.total_allocated:,.2f} differs from "
            f"deployable ${plan.deployable_cash:,.2f} by more than $1 "
            "(multiplier change should not affect total cash deployed)"
        )

    # AC-20: No single candidate receives more than deployable cash
    def test_no_candidate_exceeds_deployable_cash(self):
        dq   = _load_reference_dq()
        plan = build_deployment_plan(dq)
        for rec in plan.recommendations:
            assert rec.suggested_add <= plan.deployable_cash + 0.01, (
                f"{rec.symbol} suggested_add ${rec.suggested_add:,.2f} "
                f"> deployable ${plan.deployable_cash:,.2f}"
            )

    # AC-21: Allocation curve weight function is unchanged (rank 2 ≈ rank1 / sqrt(2) for same score/mult)
    def test_allocation_curve_still_uses_sqrt_rank_decay(self):
        """Verify weight(rank=1) / weight(rank=4) == sqrt(4) = 2.0 for identical score and mult."""
        import math
        items = [
            _make_candidate(rank=1, symbol="SY1", score=90.0, weight_pct=1.0),
            _make_candidate(rank=4, symbol="SY4", score=90.0, weight_pct=1.0),
        ]
        dq   = _minimal_dq(items, cash=10_000.0, total_mv=472_219.90)
        plan = build_deployment_plan(dq, deployable_cash=10_000.0)
        allocs = {r.symbol: r.suggested_add for r in plan.recommendations}
        if allocs.get("SY1", 0) > 0 and allocs.get("SY4", 0) > 0:
            ratio = allocs["SY1"] / allocs["SY4"]
            expected_ratio = math.sqrt(4)  # sqrt(rank4) / sqrt(rank1) = 2.0
            assert abs(ratio - expected_ratio) < 0.05, (
                f"Weight ratio SY1/SY4={ratio:.3f} should be sqrt(4)={expected_ratio:.3f} "
                "(curve must remain sqrt-rank decay)"
            )
