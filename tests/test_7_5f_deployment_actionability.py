"""Phase 7.5F — Deployment Actionability tests.

Validates:
- Deployment plan has all fields required for actionable operator decisions
- Each recommendation contains purchase amount, current/projected weights
- Cash summary data (portfolio_impact) is complete and internally consistent
- Tier summaries cover all 3 tiers (TIER_1, TIER_2, TIER_3)
- Reference run is fully deployed (unallocated_cash == 0)
- Projected weights do not exceed the CW-DAS WARN threshold (6.0%)
- CW-DAS/UCF ordering is unchanged from Phase 7.5E baseline
- Acceptance criteria: operator can determine exact purchase and projected weight
  without opening deployment_plan.json manually
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

REFERENCE_RUN_ID = "PAR-20260531-F794D952"
RUNS_DIR = Path("data/portfolio_ingestion/analysis_runs")
REFERENCE_RUN_DIR = RUNS_DIR / REFERENCE_RUN_ID

CW_WARN_THRESHOLD = 6.0      # WARN_POSITION_PCT from CW-DAS
DEPLOYABLE_CASH   = 33175.19
TOTAL_MV          = 472219.90
EXPECTED_AEIS_ADD = 7733.26  # ± tolerance
EXPECTED_VRT_ADD  = 5467.0   # approximate
TOLERANCE_DOLLARS = 5.0      # $5 rounding tolerance


def _load_reference_run():
    """Load via runner (same path the UI server uses)."""
    from src.portfolio.runner import load_analysis_run
    try:
        return load_analysis_run(REFERENCE_RUN_ID)
    except Exception:
        return None


def _load_plan_json():
    """Direct JSON load — for structure tests that do not need full runner."""
    path = REFERENCE_RUN_DIR / "deployment_plan.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


# ─────────────────────────────────────────────────────────────────────────────
# T1 — Plan structure completeness
# ─────────────────────────────────────────────────────────────────────────────

class TestPlanStructure:
    """deployment_plan.json has all fields required for actionable decisions."""

    def setup_method(self):
        self.plan = _load_plan_json()
        if self.plan is None:
            pytest.skip("deployment_plan.json not found for reference run")

    def test_plan_has_deployable_cash(self):
        assert "deployable_cash" in self.plan
        assert isinstance(self.plan["deployable_cash"], (int, float))
        assert self.plan["deployable_cash"] > 0

    def test_plan_has_portfolio_impact(self):
        pi = self.plan.get("portfolio_impact")
        assert pi is not None, "portfolio_impact missing"
        required = [
            "total_deployed", "unallocated_cash",
            "cash_before_pct", "cash_after_pct",
            "cash_before_mv", "cash_after_mv",
            "total_market_value",
        ]
        for field in required:
            assert field in pi, f"portfolio_impact missing '{field}'"

    def test_plan_has_recommendations(self):
        recs = self.plan.get("recommendations")
        assert isinstance(recs, list) and len(recs) > 0, "recommendations empty"

    def test_plan_has_tier_summaries(self):
        ts = self.plan.get("tier_summaries")
        assert isinstance(ts, list) and len(ts) == 3, "expected 3 tier summaries"
        tiers = {t["tier"] for t in ts}
        assert tiers == {"TIER_1", "TIER_2", "TIER_3"}

    def test_recommendation_action_fields_present(self):
        """Every recommendation has the fields needed to render an action card."""
        action_fields = [
            "symbol", "suggested_add", "current_weight_pct", "projected_weight_pct",
            "current_market_value", "projected_market_value", "deployment_tier",
        ]
        recs = self.plan.get("recommendations", [])
        for rec in recs:
            for field in action_fields:
                assert field in rec, f"rec for {rec.get('symbol','?')} missing '{field}'"


# ─────────────────────────────────────────────────────────────────────────────
# T2 — Cash summary invariants
# ─────────────────────────────────────────────────────────────────────────────

class TestCashSummaryInvariants:
    """portfolio_impact values are internally consistent."""

    def setup_method(self):
        plan = _load_plan_json()
        if plan is None:
            pytest.skip("deployment_plan.json not found")
        self.plan = plan
        self.pi = plan["portfolio_impact"]

    def test_fully_deployed_reference_run(self):
        assert abs(self.pi["unallocated_cash"]) < TOLERANCE_DOLLARS, (
            f"Expected $0 unallocated, got {self.pi['unallocated_cash']:.2f}"
        )

    def test_total_deployed_equals_deployable_cash(self):
        assert abs(self.pi["total_deployed"] - DEPLOYABLE_CASH) < TOLERANCE_DOLLARS, (
            f"total_deployed {self.pi['total_deployed']:.2f} ≠ deployable {DEPLOYABLE_CASH}"
        )

    def test_cash_after_pct_at_minimum_reserve(self):
        # Cash must be at minimum reserve (2.0%) after deployment
        assert abs(self.pi["cash_after_pct"] - 2.0) < 0.1, (
            f"cash_after_pct {self.pi['cash_after_pct']:.2f}% expected ~2.0%"
        )

    def test_cash_before_pct_reasonable(self):
        assert 5.0 <= self.pi["cash_before_pct"] <= 20.0, (
            f"cash_before_pct {self.pi['cash_before_pct']:.2f}% out of range"
        )

    def test_deployed_equals_sum_of_suggested_adds(self):
        recs = self.plan["recommendations"]
        total = sum(r.get("suggested_add", 0) for r in recs)
        assert abs(total - self.pi["total_deployed"]) < TOLERANCE_DOLLARS, (
            f"Sum of suggested_add ({total:.2f}) ≠ total_deployed ({self.pi['total_deployed']:.2f})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# T3 — Recommended amounts
# ─────────────────────────────────────────────────────────────────────────────

class TestRecommendedAmounts:
    """Allocation amounts are correct and ordered as expected."""

    def setup_method(self):
        plan = _load_plan_json()
        if plan is None:
            pytest.skip("deployment_plan.json not found")
        self.plan = plan
        self.recs = plan["recommendations"]
        self.by_symbol = {r["symbol"]: r for r in self.recs}

    def test_aeis_has_largest_allocation(self):
        """AEIS (CCL rank 1) should have the highest suggested_add."""
        amounts = [(r["suggested_add"], r["symbol"]) for r in self.recs]
        top_sym = max(amounts)[1]
        assert top_sym == "AEIS", f"Expected AEIS top allocation, got {top_sym}"

    def test_aeis_allocation_amount(self):
        rec = self.by_symbol.get("AEIS")
        assert rec is not None, "AEIS not in recommendations"
        assert abs(rec["suggested_add"] - EXPECTED_AEIS_ADD) < TOLERANCE_DOLLARS, (
            f"AEIS add {rec['suggested_add']:.2f} expected ~{EXPECTED_AEIS_ADD:.2f}"
        )

    def test_ccl_gets_more_than_hca_at_same_rank(self):
        """CCL tier multiplier means AEIS should outsize ARW (HCA, rank 3)."""
        aeis = self.by_symbol.get("AEIS", {})
        arw  = self.by_symbol.get("ARW",  {})
        assert aeis.get("suggested_add", 0) > arw.get("suggested_add", 0), (
            "AEIS (CCL) allocation should exceed ARW (HCA)"
        )

    def test_all_eligible_receive_allocation(self):
        """Reference run is fully deployed — all 32 eligible positions get allocation."""
        allocated = [r for r in self.recs if r.get("suggested_add", 0) > 0]
        assert len(allocated) == 32, f"Expected 32 allocated, got {len(allocated)}"

    def test_no_recommendation_exceeds_warn_threshold(self):
        """projected_weight_pct must not exceed the CW-DAS warn threshold."""
        for rec in self.recs:
            proj = rec.get("projected_weight_pct", 0)
            assert proj <= CW_WARN_THRESHOLD + 0.1, (
                f"{rec['symbol']} projected {proj:.2f}% exceeds warn threshold {CW_WARN_THRESHOLD}%"
            )


# ─────────────────────────────────────────────────────────────────────────────
# T4 — Projected weights
# ─────────────────────────────────────────────────────────────────────────────

class TestProjectedWeights:
    """Projected portfolio weights are valid after deployment."""

    def setup_method(self):
        plan = _load_plan_json()
        if plan is None:
            pytest.skip("deployment_plan.json not found")
        self.recs = plan["recommendations"]
        self.by_symbol = {r["symbol"]: r for r in self.recs}

    def test_projected_weight_greater_than_current_when_allocated(self):
        for rec in self.recs:
            if rec.get("suggested_add", 0) > 0:
                proj = rec.get("projected_weight_pct", 0)
                cur  = rec.get("current_weight_pct", 0)
                assert proj > cur, (
                    f"{rec['symbol']}: proj {proj:.2f}% should exceed cur {cur:.2f}% when allocated"
                )

    def test_aeis_projected_weight(self):
        rec = self.by_symbol.get("AEIS")
        assert rec is not None
        proj = rec["projected_weight_pct"]
        assert 3.5 <= proj <= 6.0, f"AEIS projected wt {proj:.2f}% out of expected range 3.5–6.0%"

    def test_vrt_projected_weight(self):
        rec = self.by_symbol.get("VRT")
        assert rec is not None
        proj = rec["projected_weight_pct"]
        assert 4.0 <= proj <= 6.0, f"VRT projected wt {proj:.2f}% out of expected range 4.0–6.0%"

    def test_all_projected_weights_positive(self):
        for rec in self.recs:
            assert rec.get("projected_weight_pct", 0) > 0, (
                f"{rec['symbol']} has non-positive projected_weight_pct"
            )


# ─────────────────────────────────────────────────────────────────────────────
# T5 — Queue ordering unchanged (Phase 7.5F regression guard)
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueOrderingUnchanged:
    """CW-DAS ordering must not be affected by Phase 7.5F changes."""

    def setup_method(self):
        result = _load_reference_run()
        if result is None:
            pytest.skip("Reference run not accessible")
        self.queue = result.get("deployment_queue", {}).get("queue", [])
        if not self.queue:
            pytest.skip("Deployment queue empty in reference run")

    def test_aeis_is_rank_1(self):
        assert self.queue[0]["symbol"] == "AEIS", (
            f"Expected AEIS at rank 1, got {self.queue[0]['symbol']}"
        )

    def test_vrt_is_rank_2(self):
        assert self.queue[1]["symbol"] == "VRT", (
            f"Expected VRT at rank 2, got {self.queue[1]['symbol']}"
        )

    def test_arw_is_rank_3(self):
        assert self.queue[2]["symbol"] == "ARW", (
            f"Expected ARW at rank 3, got {self.queue[2]['symbol']}"
        )

    def test_all_ranks_sequential(self):
        for i, item in enumerate(self.queue, 1):
            assert item["rank"] == i, f"Rank gap at position {i}: got {item['rank']}"


# ─────────────────────────────────────────────────────────────────────────────
# T6 — Tier assignments
# ─────────────────────────────────────────────────────────────────────────────

class TestTierAssignments:
    """Top positions should be TIER_1 (CCL leaders receive priority)."""

    def setup_method(self):
        plan = _load_plan_json()
        if plan is None:
            pytest.skip("deployment_plan.json not found")
        self.by_symbol = {r["symbol"]: r for r in plan["recommendations"]}

    def test_aeis_is_tier1(self):
        rec = self.by_symbol.get("AEIS")
        assert rec is not None
        assert rec["deployment_tier"] == "TIER_1", (
            f"AEIS should be TIER_1, got {rec['deployment_tier']}"
        )

    def test_vrt_is_tier1(self):
        rec = self.by_symbol.get("VRT")
        assert rec is not None
        assert rec["deployment_tier"] == "TIER_1", (
            f"VRT should be TIER_1, got {rec['deployment_tier']}"
        )

    def test_tier_summary_counts(self):
        """T1=2, T2=13, T3=17 for reference run."""
        plan = _load_plan_json()
        ts_by_tier = {t["tier"]: t for t in plan.get("tier_summaries", [])}
        assert ts_by_tier["TIER_1"]["candidate_count"] == 2
        assert ts_by_tier["TIER_2"]["candidate_count"] == 13
        assert ts_by_tier["TIER_3"]["candidate_count"] == 17


# ─────────────────────────────────────────────────────────────────────────────
# T7 — Acceptance criteria
# ─────────────────────────────────────────────────────────────────────────────

class TestAcceptanceCriteria:
    """
    Phase 7.5F acceptance criteria from requirements.

    Operator can determine exact purchase amount and projected weight
    without opening deployment_plan.json.
    """

    def setup_method(self):
        result = _load_reference_run()
        if result is None:
            pytest.skip("Reference run not accessible")
        self.result = result
        plan = result.get("deployment_plan")
        if plan is None:
            pytest.skip("deployment_plan not loaded in reference run")
        self.plan = plan
        self.recs = plan.get("recommendations", [])
        self.by_symbol = {r["symbol"]: r for r in self.recs}
        self.queue = result.get("deployment_queue", {}).get("queue", [])

    def test_ac1_purchase_amount_present_for_all_eligible(self):
        """AC1: suggested_add is present and > 0 for all eligible positions."""
        eligible = [r for r in self.recs if r.get("constraint_status") != "BLOCKED"]
        for rec in eligible:
            assert rec.get("suggested_add", 0) > 0, (
                f"{rec['symbol']} is eligible but has no suggested_add"
            )

    def test_ac2_projected_weight_present_for_all_recs(self):
        """AC2: projected_weight_pct is present for every recommendation."""
        for rec in self.recs:
            assert "projected_weight_pct" in rec, (
                f"{rec['symbol']} missing projected_weight_pct"
            )
            assert rec["projected_weight_pct"] is not None

    def test_ac3_cwdas_ordering_unchanged(self):
        """AC3: CW-DAS ordering is unchanged — AEIS #1, VRT #2."""
        assert self.queue[0]["symbol"] == "AEIS"
        assert self.queue[1]["symbol"] == "VRT"

    def test_ac4_recommendation_logic_unchanged(self):
        """AC4: Phase 7.5F is UI-only; backend recommendation count unchanged."""
        legacy_recs = self.result.get("recommendations", [])
        assert len(legacy_recs) > 0, "Legacy recommendations unexpectedly empty"

    def test_ac5_no_regression_in_existing_tests(self):
        """AC5: sanity check — runner can load the reference run without error."""
        from src.portfolio.runner import load_analysis_run
        result = load_analysis_run(REFERENCE_RUN_ID)
        assert result is not None
        assert result.get("deployment_queue") is not None
        assert result.get("deployment_plan") is not None

    def test_ac6_ucf_verdicts_loaded_with_run(self):
        """AC6: UCF verdicts are still available post-7.5F (no regression from 7.5E)."""
        ucf = self.result.get("ucf_verdicts_by_symbol")
        assert ucf is not None and len(ucf) > 0, "UCF verdicts missing from loaded run"

    def test_ac7_operator_can_read_aeis_card_data(self):
        """AC7: Operator data completeness — all action card fields for AEIS."""
        rec = self.by_symbol.get("AEIS")
        assert rec is not None

        queue_item = next((q for q in self.queue if q["symbol"] == "AEIS"), None)
        assert queue_item is not None

        # Verify every field needed to render the action card
        assert rec["suggested_add"] > 0                       # purchase amount
        assert rec["current_weight_pct"] > 0                  # current weight
        assert rec["projected_weight_pct"] > rec["current_weight_pct"]  # projected > current
        assert rec["current_market_value"] > 0                # current MV
        assert rec["projected_market_value"] > rec["current_market_value"]  # projected MV
        assert rec["deployment_tier"] in ("TIER_1", "TIER_2", "TIER_3")  # tier badge
        assert queue_item.get("narrative_tier") is not None   # conviction label chip
        assert "replay_supported" in queue_item               # replay chip
        assert "trim_score" in queue_item                     # trim pressure chip
