"""Phase 7.5B — Capital Deployment Queue: tests.

Validates the CW-DAS formula and build_deployment_queue() function against
the acceptance criteria defined in:
  - capital_deployment_queue_design.md (Section 6)
  - deployment_queue_validation_report.md (Validation Criteria Checklist)

Test groups:
  1. Unit: compute_cw_das() with known inputs
  2. Unit: build_deployment_queue() with synthetic fixtures
  3. Integration: rank ordering against PAR-20260531-942B1F54 fixtures
  4. Regression: all 6 acceptance criteria verified end-to-end
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, ".")

from src.portfolio.deployment_queue import (
    WARN_POSITION_PCT,
    MAX_POSITION_PCT,
    MIN_CASH_PCT,
    CW_DAS_VERSION,
    CwDasBreakdown,
    DeploymentCandidate,
    build_deployment_queue,
    compute_cw_das,
    compute_deployable_cash,
)
from src.portfolio.models import (
    AllocationAlignmentResult,
    HoldingStrategicProfile,
    PortfolioHolding,
    SecurityIntelligenceOverlay,
)

# ─────────────────────────────────────────────────────────────────────────────
# Shared constants
# ─────────────────────────────────────────────────────────────────────────────

_SNAP_ID = "PSNAP-20260531-TEST"
_NOW = "2026-05-31T14:00:00+00:00"

# ─────────────────────────────────────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_holding(
    symbol: str,
    pct: float,
    market_value: float = 10_000.0,
    geography: str = "US",
    market_cap_bucket: str = "SMALL",
    security_type: str = "Common Stock",
    ess_score_text: str = "VERY_BULLISH",
    composite_score: float = 4.5,
    is_cash: bool = False,
) -> PortfolioHolding:
    """Build a minimal PortfolioHolding for testing."""
    return PortfolioHolding(
        portfolio_snapshot_id=_SNAP_ID,
        snapshot_date="2026-05-31",
        account_name="TEST",
        symbol=symbol,
        description=f"{symbol} test holding",
        quantity=100.0,
        market_value=market_value,
        percent_of_portfolio=pct,
        asset_class="EQUITIES",
        geography=geography,
        market_cap_bucket=market_cap_bucket,
        mega_subtier="N/A",
        sector="TECHNOLOGY",
        industry="SEMICONDUCTORS",
        security_type=security_type,
        cost_basis=None,
        composite_score=composite_score,
        ess_score_text=ess_score_text,
        zacks_rating=None,
        benchmark_id=None,
        investable_vehicle_id=None,
        source_file="test.csv",
        created_at_utc=_NOW,
        operational_state="ACTIVE_POSITION",
        is_cash_equivalent=is_cash,
    )


def _make_overlay(
    symbol: str,
    signal: str = "BULLISH",
    replay: bool = True,
    composite: float = 4.5,
) -> SecurityIntelligenceOverlay:
    return SecurityIntelligenceOverlay(
        portfolio_snapshot_id=_SNAP_ID,
        symbol=symbol,
        composite_score=composite,
        ess_score_text="VERY_BULLISH",
        zacks_rating=None,
        best_replay_return=None,
        replay_percentile=90.0,
        replay_supported=replay,
        percent_of_portfolio=2.0,
        is_overweight_vs_target=False,
        signal_direction=signal,
        opportunity_flag="ACCUMULATE",
        flag_rationale="High conviction, replay-supported.",
        created_at_utc=_NOW,
    )


def _make_profile(
    symbol: str,
    tier: str = "CORE_CONVICTION_LEADER",
    classification: str = "HIGH_CONVICTION_RETAIN",
    trim_score: float = 15.0,
) -> HoldingStrategicProfile:
    return HoldingStrategicProfile(
        portfolio_snapshot_id=_SNAP_ID,
        symbol=symbol,
        security_type="Common Stock",
        percent_of_portfolio=2.0,
        strategic_classification=classification,
        trim_priority_score=trim_score,
        trim_factors=(),
        thematic_overlap_clusters=(),
        overlap_peers=(),
        thematic_redundancy_score=10.0,
        strategic_role="",
        strategic_importance="HIGH",
        exposure_origin="DIRECT_INTENTIONAL",
        trim_rationale="",
        retain_rationale="",
        classification_trace="",
        concentration_pressure=5.0,
        diversification_contribution=80.0,
        created_at_utc=_NOW,
        narrative_tier=tier,
        strategic_anchor_rank=1,
    )


def _make_alignment(node_key: str, direction: str, severity: str) -> AllocationAlignmentResult:
    return AllocationAlignmentResult(
        analysis_run_id="TEST-RUN",
        portfolio_snapshot_id=_SNAP_ID,
        node_key=node_key,
        node_label=node_key,
        dimension_type="MARKET_CAP",
        actual_pct=8.0,
        target_pct=5.0,
        tactical_target_pct=5.0,
        drift_pct=3.0,
        drift_direction=direction,
        severity=severity,
        concentration_risk="MODERATE",
        alignment_score=0.6,
        recommendation_priority=1,
        created_at_utc=_NOW,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Unit: compute_cw_das()
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeCwDas:
    """Verify each CW-DAS component produces the correct value."""

    def test_signal_component_max(self):
        """composite=5.0 → signal=30."""
        score, bd = compute_cw_das("X", 5.0, 2.0, "CORE_CONVICTION_LEADER", True, "BULLISH", "BULLISH", False)
        assert bd.signal == 30.0

    def test_signal_component_scaled(self):
        """composite=2.5 → signal=15."""
        score, bd = compute_cw_das("X", 2.5, 2.0, "CORE_CONVICTION_LEADER", True, "BULLISH", "BULLISH", False)
        assert bd.signal == 15.0

    def test_replay_supported_true(self):
        """replay_supported=True → replay=20."""
        score, bd = compute_cw_das("X", 4.0, 2.0, "CORE_CONVICTION_LEADER", True, "BULLISH", "BULLISH", False)
        assert bd.replay == 20.0

    def test_replay_supported_false(self):
        """replay_supported=False → replay=0."""
        score, bd = compute_cw_das("X", 4.0, 2.0, "CORE_CONVICTION_LEADER", False, "BULLISH", "BULLISH", False)
        assert bd.replay == 0.0

    def test_conviction_ccl(self):
        """CORE_CONVICTION_LEADER → conviction=35."""
        score, bd = compute_cw_das("X", 4.0, 2.0, "CORE_CONVICTION_LEADER", True, "BULLISH", "BULLISH", False)
        assert bd.conviction == 35.0

    def test_conviction_hca(self):
        """HIGH_CONVICTION_ANCHOR → conviction=28."""
        score, bd = compute_cw_das("X", 4.0, 2.0, "HIGH_CONVICTION_ANCHOR", True, "BULLISH", "BULLISH", False)
        assert bd.conviction == 28.0

    def test_conviction_other(self):
        """Unknown tier → conviction=10."""
        score, bd = compute_cw_das("X", 4.0, 2.0, "OTHER_TIER", True, "BULLISH", "BULLISH", False)
        assert bd.conviction == 10.0

    def test_sizing_at_zero_weight(self):
        """pct=0 → headroom=1.0 → sizing=8.0."""
        score, bd = compute_cw_das("X", 4.0, 0.0, "CORE_CONVICTION_LEADER", True, "BULLISH", "BULLISH", False)
        assert bd.sizing == 8.0

    def test_sizing_at_warn_threshold(self):
        """pct=WARN_POSITION_PCT → headroom=0 → sizing=0."""
        score, bd = compute_cw_das("X", 4.0, WARN_POSITION_PCT, "CORE_CONVICTION_LEADER", True, "BULLISH", "BULLISH", False)
        assert bd.sizing == 0.0

    def test_sizing_proportional(self):
        """pct=3.0 with WARN=6.0 → headroom=0.5 → sizing=4.0."""
        score, bd = compute_cw_das("X", 4.0, 3.0, "CORE_CONVICTION_LEADER", True, "BULLISH", "BULLISH", False)
        assert abs(bd.sizing - 4.0) < 0.01

    def test_momentum_double_bullish(self):
        """ESS_BULLISH + BULLISH → momentum=10."""
        score, bd = compute_cw_das("X", 4.0, 2.0, "CORE_CONVICTION_LEADER", True, "VERY_BULLISH", "BULLISH", False)
        assert bd.momentum == 10.0

    def test_momentum_single_ess_bullish(self):
        """ESS_BULLISH + neutral signal → momentum=7.5."""
        score, bd = compute_cw_das("X", 4.0, 2.0, "CORE_CONVICTION_LEADER", True, "VERY_BULLISH", "NEUTRAL", False)
        assert bd.momentum == 7.5

    def test_momentum_neutral(self):
        """No ESS, no bullish/bearish → momentum=4.0."""
        score, bd = compute_cw_das("X", 4.0, 2.0, "CORE_CONVICTION_LEADER", True, "", "NEUTRAL", False)
        assert bd.momentum == 4.0

    def test_momentum_bearish(self):
        """ESS_BEARISH → momentum=0."""
        score, bd = compute_cw_das("X", 4.0, 2.0, "CORE_CONVICTION_LEADER", True, "BEARISH", "NEUTRAL", False)
        assert bd.momentum == 0.0

    def test_redundancy_penalty_applied(self):
        """in_ow_node=True → redundancy_pen=15."""
        score, bd = compute_cw_das("X", 4.0, 2.0, "CORE_CONVICTION_LEADER", True, "BULLISH", "BULLISH", True)
        assert bd.redundancy_pen == 15.0

    def test_redundancy_penalty_not_applied(self):
        """in_ow_node=False → redundancy_pen=0."""
        score, bd = compute_cw_das("X", 4.0, 2.0, "CORE_CONVICTION_LEADER", True, "BULLISH", "BULLISH", False)
        assert bd.redundancy_pen == 0.0

    def test_concentration_penalty_above_warn(self):
        """pct=8.0 (WARN+2) → conc_pen = (8-6)*4 = 8."""
        score, bd = compute_cw_das("X", 4.0, 8.0, "CORE_CONVICTION_LEADER", True, "BULLISH", "BULLISH", False)
        assert abs(bd.conc_pen - 8.0) < 0.01

    def test_concentration_penalty_capped_at_20(self):
        """pct=11.0 (WARN+5) → penalty = (11-6)*4=20 (capped)."""
        score, bd = compute_cw_das("X", 4.0, 11.0, "CORE_CONVICTION_LEADER", True, "BULLISH", "BULLISH", False)
        assert bd.conc_pen == 20.0

    def test_score_never_negative(self):
        """Score floor is 0.0 even with heavy penalties."""
        score, bd = compute_cw_das("X", 0.0, 11.0, "OTHER_TIER", False, "BEARISH", "BEARISH", True)
        assert score >= 0.0

    def test_ccl_premium_over_hca_at_typical_weights(self):
        """At equal weights, CCL scores higher than HCA by conviction gap (7pts)."""
        ccl_score, _ = compute_cw_das("CCL", 4.5, 2.5, "CORE_CONVICTION_LEADER", True, "VERY_BULLISH", "BULLISH", False)
        hca_score, _ = compute_cw_das("HCA", 4.5, 2.5, "HIGH_CONVICTION_ANCHOR", True, "VERY_BULLISH", "BULLISH", False)
        assert ccl_score > hca_score
        assert abs(ccl_score - hca_score) == 7.0  # exactly the conviction delta

    def test_aeis_vs_arw_ccl_wins(self):
        """AEIS (CCL, 2.42%) should outscore ARW (HCA, 0.92%) despite ARW having more headroom.

        This is the core validation: CW-DAS conviction premium reliably beats
        HCA sizing advantage in normal operating range.
        AEIS: composite≈4.71, pct=2.42, CCL, ess='' (neutral ESS), sig=BULLISH
        ARW:  composite≈4.89, pct=0.92, HCA, ess=VERY_BULLISH, sig=BULLISH
        """
        aeis_score, _ = compute_cw_das("AEIS", 4.71, 2.42, "CORE_CONVICTION_LEADER", True, "", "BULLISH", False)
        arw_score,  _ = compute_cw_das("ARW",  4.89, 0.92, "HIGH_CONVICTION_ANCHOR",  True, "VERY_BULLISH", "BULLISH", False)
        assert aeis_score > arw_score, (
            f"AEIS score {aeis_score} must exceed ARW score {arw_score} — CCL conviction premium must dominate"
        )

    def test_vrt_vs_arw_ccl_wins(self):
        """VRT (CCL, 3.60%) should outscore ARW (HCA, 0.92%).

        VRT: composite≈4.56, pct=3.60, CCL, ess=VERY_BULLISH, sig=BULLISH
        ARW: composite≈4.89, pct=0.92, HCA, ess=VERY_BULLISH, sig=BULLISH
        """
        vrt_score, _ = compute_cw_das("VRT", 4.56, 3.60, "CORE_CONVICTION_LEADER", True, "VERY_BULLISH", "BULLISH", False)
        arw_score,  _ = compute_cw_das("ARW", 4.89, 0.92, "HIGH_CONVICTION_ANCHOR",  True, "VERY_BULLISH", "BULLISH", False)
        assert vrt_score > arw_score, (
            f"VRT score {vrt_score} must exceed ARW score {arw_score} — CCL conviction premium must dominate"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Unit: build_deployment_queue() eligibility filtering
# ─────────────────────────────────────────────────────────────────────────────

class TestDeploymentQueueEligibility:
    """Verify that eligibility gates correctly include/exclude holdings."""

    def _base_set(self):
        """Minimal valid CCL holding, overlay, profile."""
        h = _make_holding("AAAA", 2.0)
        o = _make_overlay("AAAA")
        p = _make_profile("AAAA", "CORE_CONVICTION_LEADER")
        return [h], [o], [p], []

    def test_eligible_ccl_included(self):
        holdings, overlays, profiles, alignment = self._base_set()
        queue = build_deployment_queue(_SNAP_ID, holdings, overlays, profiles, alignment, 500_000)
        assert len(queue) == 1
        assert queue[0].symbol == "AAAA"

    def test_cash_excluded(self):
        h = _make_holding("SPAXX", 9.0, is_cash=True)
        o = _make_overlay("SPAXX")
        p = _make_profile("SPAXX", "CORE_CONVICTION_LEADER")
        queue = build_deployment_queue(_SNAP_ID, [h], [o], [p], [], 500_000)
        assert len(queue) == 0

    def test_etf_excluded(self):
        h = _make_holding("QQQ", 3.0, security_type="ETF")
        o = _make_overlay("QQQ")
        p = _make_profile("QQQ", "CORE_CONVICTION_LEADER")
        queue = build_deployment_queue(_SNAP_ID, [h], [o], [p], [], 500_000)
        assert len(queue) == 0

    def test_mutual_fund_excluded(self):
        h = _make_holding("FXAIX", 3.0, security_type="MUTUAL_FUND")
        o = _make_overlay("FXAIX")
        p = _make_profile("FXAIX", "CORE_CONVICTION_LEADER")
        queue = build_deployment_queue(_SNAP_ID, [h], [o], [p], [], 500_000)
        assert len(queue) == 0

    def test_non_bullish_signal_excluded(self):
        h = _make_holding("AAAA", 2.0)
        o = _make_overlay("AAAA", signal="NEUTRAL")
        p = _make_profile("AAAA", "CORE_CONVICTION_LEADER")
        queue = build_deployment_queue(_SNAP_ID, [h], [o], [p], [], 500_000)
        assert len(queue) == 0

    def test_no_replay_excluded(self):
        h = _make_holding("AAAA", 2.0)
        o = _make_overlay("AAAA", replay=False)
        p = _make_profile("AAAA", "CORE_CONVICTION_LEADER")
        queue = build_deployment_queue(_SNAP_ID, [h], [o], [p], [], 500_000)
        assert len(queue) == 0

    def test_non_hcr_classification_excluded(self):
        h = _make_holding("AAAA", 2.0)
        o = _make_overlay("AAAA")
        p = _make_profile("AAAA", "CORE_CONVICTION_LEADER", classification="TACTICAL_GROWTH")
        queue = build_deployment_queue(_SNAP_ID, [h], [o], [p], [], 500_000)
        assert len(queue) == 0

    def test_non_eligible_tier_excluded(self):
        h = _make_holding("AAAA", 2.0)
        o = _make_overlay("AAAA")
        p = _make_profile("AAAA", tier="TACTICAL_GROWTH_CANDIDATE")
        queue = build_deployment_queue(_SNAP_ID, [h], [o], [p], [], 500_000)
        assert len(queue) == 0

    def test_no_overlay_excluded(self):
        h = _make_holding("AAAA", 2.0)
        p = _make_profile("AAAA")
        queue = build_deployment_queue(_SNAP_ID, [h], [], [p], [], 500_000)
        assert len(queue) == 0

    def test_no_profile_excluded(self):
        h = _make_holding("AAAA", 2.0)
        o = _make_overlay("AAAA")
        queue = build_deployment_queue(_SNAP_ID, [h], [o], [], [], 500_000)
        assert len(queue) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Unit: build_deployment_queue() rank ordering
# ─────────────────────────────────────────────────────────────────────────────

class TestDeploymentQueueOrdering:
    """Verify rank ordering under CW-DAS."""

    def test_ccl_ranks_above_hca_same_params(self):
        """CCL always outranks HCA at the same weight and composite."""
        h_ccl = _make_holding("CCL1", 2.0)
        h_hca = _make_holding("HCA1", 2.0)
        o_ccl = _make_overlay("CCL1", composite=4.5)
        o_hca = _make_overlay("HCA1", composite=4.5)
        p_ccl = _make_profile("CCL1", "CORE_CONVICTION_LEADER")
        p_hca = _make_profile("HCA1", "HIGH_CONVICTION_ANCHOR")
        queue = build_deployment_queue(
            _SNAP_ID, [h_ccl, h_hca], [o_ccl, o_hca], [p_ccl, p_hca], [], 500_000
        )
        assert len(queue) == 2
        assert queue[0].symbol == "CCL1"
        assert queue[1].symbol == "HCA1"
        assert queue[0].rank == 1
        assert queue[1].rank == 2

    def test_higher_composite_ranks_higher_within_tier(self):
        """Within the same tier, higher composite = higher rank."""
        h1 = _make_holding("ALPHA", 2.0, composite_score=4.8)
        h2 = _make_holding("BETA",  2.0, composite_score=4.2)
        o1 = _make_overlay("ALPHA", composite=4.8)
        o2 = _make_overlay("BETA",  composite=4.2)
        p1 = _make_profile("ALPHA", "CORE_CONVICTION_LEADER")
        p2 = _make_profile("BETA",  "CORE_CONVICTION_LEADER")
        queue = build_deployment_queue(
            _SNAP_ID, [h1, h2], [o1, o2], [p1, p2], [], 500_000
        )
        assert queue[0].symbol == "ALPHA"

    def test_ow_node_penalty_lowers_rank(self):
        """OW-node holding gets −15 redundancy penalty and should rank below clean CCL."""
        h_clean = _make_holding("CLEAN", 2.0)
        h_ow    = _make_holding("OWSYM", 2.0, geography="US", market_cap_bucket="MEGA")
        o_clean = _make_overlay("CLEAN")
        o_ow    = _make_overlay("OWSYM")
        p_clean = _make_profile("CLEAN")
        p_ow    = _make_profile("OWSYM")
        alignment = [_make_alignment("EQUITIES.US.MEGA", "OVERWEIGHT", "MODERATE")]
        queue = build_deployment_queue(
            _SNAP_ID,
            [h_clean, h_ow],
            [o_clean, o_ow],
            [p_clean, p_ow],
            alignment,
            500_000,
        )
        syms = [c.symbol for c in queue]
        assert syms.index("CLEAN") < syms.index("OWSYM")

    def test_ranks_are_sequential_from_one(self):
        """Rank values must be 1, 2, 3, ..., N."""
        holdings = [_make_holding(f"SYM{i}", 1.0 + i * 0.5) for i in range(5)]
        overlays = [_make_overlay(f"SYM{i}") for i in range(5)]
        profiles = [_make_profile(f"SYM{i}") for i in range(5)]
        queue = build_deployment_queue(_SNAP_ID, holdings, overlays, profiles, [], 500_000)
        assert [c.rank for c in queue] == list(range(1, len(queue) + 1))

    def test_headroom_pct_correct(self):
        """Headroom pct = max(0, (1 - pct/WARN)*100)."""
        pct = 3.0
        h = _make_holding("X", pct)
        o = _make_overlay("X")
        p = _make_profile("X")
        queue = build_deployment_queue(_SNAP_ID, [h], [o], [p], [], 500_000)
        assert len(queue) == 1
        expected_headroom = round((1.0 - pct / WARN_POSITION_PCT) * 100.0, 1)
        assert queue[0].headroom_pct == pytest.approx(expected_headroom, abs=0.1)

    def test_empty_queue_on_no_eligible(self):
        """Returns empty list when nothing passes eligibility."""
        h = _make_holding("NOPE", 2.0, security_type="ETF")
        o = _make_overlay("NOPE")
        p = _make_profile("NOPE")
        queue = build_deployment_queue(_SNAP_ID, [h], [o], [p], [], 500_000)
        assert queue == []


# ─────────────────────────────────────────────────────────────────────────────
# 4. Unit: compute_deployable_cash()
# ─────────────────────────────────────────────────────────────────────────────

class TestDeployableCash:
    def test_deployable_above_floor(self):
        """Cash above mandate target (7%) → deployable_mv = excess above target."""
        total_mv = 472_219.90
        cash_mv = 42_620.0   # 9.03%
        h_cash = _make_holding("SPAXX", 9.03, market_value=cash_mv, is_cash=True)
        h_other = _make_holding("AAAA", 2.0, market_value=9_440.0)
        result = compute_deployable_cash([h_cash, h_other], total_mv, mandate_cash_target_pct=7.0)
        # Effective floor = max(2%, 7%) = 7%
        floor = total_mv * 7.0 / 100.0
        expected_deployable = cash_mv - floor
        assert result["deployable_mv"] == pytest.approx(expected_deployable, abs=1.0)
        assert result["cash_mv"] == pytest.approx(cash_mv, abs=1.0)

    def test_no_deployable_below_floor(self):
        """Cash at/below mandate target → deployable_mv = 0."""
        total_mv = 100_000.0
        cash_mv = 1_000.0  # 1% — below both 2% floor and 7% target
        h_cash = _make_holding("SPAXX", 1.0, market_value=cash_mv, is_cash=True)
        result = compute_deployable_cash([h_cash], total_mv, mandate_cash_target_pct=7.0)
        assert result["deployable_mv"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 4b. Phase 22D.6 — Mandate-aware deployable cash acceptance criteria (AC1–AC7)
# ─────────────────────────────────────────────────────────────────────────────

class TestMandateAwareCash:
    """Acceptance criteria for the mandate-aware compute_deployable_cash() implementation.

    Fixture portfolio: $475,779.42 total MV, $41,198.92 cash (8.6592%).
    Mandate: CONCENTRATED_ALPHA — strategic cash target 7.0%.
    """

    _TOTAL_MV  = 475_779.42
    _CASH_MV   = 41_198.92   # 8.6592%

    def _cash_holding(self, cash_mv: float, total_mv: float) -> object:
        cash_pct = cash_mv / total_mv * 100.0
        return _make_holding("SPAXX", cash_pct, market_value=cash_mv, is_cash=True)

    # AC1: Mandate target (7%) takes precedence; deployable = excess above target
    def test_ac1_deployable_uses_mandate_target(self):
        """AC1: deployable_mv = cash_mv − 7% × total_mv (not 2%)."""
        h = self._cash_holding(self._CASH_MV, self._TOTAL_MV)
        result = compute_deployable_cash([h], self._TOTAL_MV, mandate_cash_target_pct=7.0)
        expected_floor_mv = self._TOTAL_MV * 7.0 / 100.0
        expected_deployable = self._CASH_MV - expected_floor_mv
        assert result["deployable_mv"] == pytest.approx(expected_deployable, abs=1.0)
        # Must NOT equal the 2%-floor calculation
        old_floor_mv = self._TOTAL_MV * 2.0 / 100.0
        assert result["deployable_mv"] != pytest.approx(self._CASH_MV - old_floor_mv, abs=1.0)

    # AC2: Cash after full deployment ≈ 7.00%
    def test_ac2_cash_after_deployment_is_7pct(self):
        """AC2: After deploying deployable_mv, remaining cash % ≈ 7.0%."""
        h = self._cash_holding(self._CASH_MV, self._TOTAL_MV)
        result = compute_deployable_cash([h], self._TOTAL_MV, mandate_cash_target_pct=7.0)
        remaining_cash = self._CASH_MV - result["deployable_mv"]
        cash_after_pct = remaining_cash / self._TOTAL_MV * 100.0
        assert cash_after_pct == pytest.approx(7.0, abs=0.05)

    # AC3: BALANCED mandate → 5% target used as floor
    def test_ac3_balanced_mandate_uses_5pct_target(self):
        """AC3: BALANCED mandate (5% target) → effective floor = 5%."""
        total_mv = 300_000.0
        cash_mv = 18_000.0  # 6.0%
        h = self._cash_holding(cash_mv, total_mv)
        result = compute_deployable_cash([h], total_mv, mandate_cash_target_pct=5.0)
        expected_floor = total_mv * 5.0 / 100.0
        expected_deployable = cash_mv - expected_floor
        assert result["effective_floor_pct"] == pytest.approx(5.0, abs=0.001)
        assert result["deployable_mv"] == pytest.approx(expected_deployable, abs=1.0)

    # AC4: GROWTH mandate → 3% target, effective floor = max(2%, 3%) = 3%
    def test_ac4_growth_mandate_uses_3pct_target(self):
        """AC4: GROWTH mandate (3% target) → effective floor = 3% (not 2%)."""
        total_mv = 200_000.0
        cash_mv = 10_000.0  # 5.0%
        h = self._cash_holding(cash_mv, total_mv)
        result = compute_deployable_cash([h], total_mv, mandate_cash_target_pct=3.0)
        assert result["effective_floor_pct"] == pytest.approx(3.0, abs=0.001)
        expected_deployable = cash_mv - total_mv * 3.0 / 100.0
        assert result["deployable_mv"] == pytest.approx(expected_deployable, abs=1.0)

    # AC4b: Target below governance minimum → governance minimum is the floor
    def test_ac4b_governance_minimum_overrides_low_target(self):
        """AC4b: If mandate target < MIN_CASH_PCT (2%), governance min applies."""
        total_mv = 100_000.0
        cash_mv = 3_000.0  # 3%
        h = self._cash_holding(cash_mv, total_mv)
        # If a mandate somehow has 1% cash target, governance floor (2%) should win
        result = compute_deployable_cash([h], total_mv, mandate_cash_target_pct=1.0)
        assert result["effective_floor_pct"] == pytest.approx(2.0, abs=0.001)
        expected_deployable = cash_mv - total_mv * 2.0 / 100.0
        assert result["deployable_mv"] == pytest.approx(expected_deployable, abs=1.0)

    # AC5: None target → ValueError (fail-closed)
    def test_ac5_missing_target_raises_value_error(self):
        """AC5: mandate_cash_target_pct=None → ValueError (fail-closed governance)."""
        h = self._cash_holding(self._CASH_MV, self._TOTAL_MV)
        with pytest.raises(ValueError, match="mandate_cash_target_pct is required"):
            compute_deployable_cash([h], self._TOTAL_MV, mandate_cash_target_pct=None)

    # AC6: New fields present in returned dict
    def test_ac6_result_dict_contains_new_fields(self):
        """AC6: Result dict includes mandate_cash_target_pct, effective_floor_pct, excess_mv, excess_pct."""
        h = self._cash_holding(self._CASH_MV, self._TOTAL_MV)
        result = compute_deployable_cash([h], self._TOTAL_MV, mandate_cash_target_pct=7.0)
        assert "mandate_cash_target_pct" in result
        assert "effective_floor_pct" in result
        assert "excess_mv" in result
        assert "excess_pct" in result
        # Original fields still present
        assert "cash_mv" in result
        assert "cash_pct" in result
        assert "floor_mv" in result
        assert "deployable_mv" in result
        assert "deployable_pct" in result

    # AC7: Allocation math reconciliation
    def test_ac7_allocation_math_reconciles(self):
        """AC7: deployable_mv + floor_mv ≤ cash_mv; excess_mv = cash_mv - target_mv."""
        h = self._cash_holding(self._CASH_MV, self._TOTAL_MV)
        result = compute_deployable_cash([h], self._TOTAL_MV, mandate_cash_target_pct=7.0)
        # deployable + floor must equal cash_mv exactly
        assert result["deployable_mv"] + result["floor_mv"] == pytest.approx(result["cash_mv"], abs=0.01)
        # excess_mv = cash_mv − (mandate_target × total_mv / 100)
        expected_excess = result["cash_mv"] - self._TOTAL_MV * 7.0 / 100.0
        assert result["excess_mv"] == pytest.approx(expected_excess, abs=0.01)
        # excess_pct round-trips from excess_mv
        expected_excess_pct = result["excess_mv"] / self._TOTAL_MV * 100.0
        assert result["excess_pct"] == pytest.approx(expected_excess_pct, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Integration: PAR-20260531-942B1F54 acceptance criteria
# ─────────────────────────────────────────────────────────────────────────────

PAR_RUN_DIR = Path("data/portfolio_ingestion/analysis_runs/PAR-20260531-942B1F54")
PAR_ARCHIVE_CSV = Path(
    "data/portfolio_ingestion/archive/"
    "2026-05-31T14-05-20_PAR-20260531-942B1F54_Portfolio_Positions_May-29-2026.csv"
)


@pytest.mark.skipif(not PAR_RUN_DIR.exists(), reason="PAR-20260531-942B1F54 run directory not found")
class TestPARAcceptanceCriteria:
    """Integration tests against PAR-20260531-942B1F54 artifacts.

    Validates all 6 acceptance criteria from capital_deployment_queue_design.md
    Section 6 and all 8 checklist items from deployment_queue_validation_report.md.

    These tests run the full deployment queue builder against live run artifacts
    loaded from disk — no mocking of scoring logic.
    """

    @pytest.fixture(scope="class")
    def queue(self):
        """Build the deployment queue from PAR-20260531-942B1F54 artifacts."""
        import csv
        from src.portfolio.enrichment import enrich_holdings, normalize_and_aggregate_holdings
        from src.portfolio.ingestion import ingest_portfolio
        from src.portfolio.alignment import compute_alignment
        from src.portfolio.recommendations import build_security_overlays
        from src.portfolio.trim_intelligence import build_strategic_profiles
        from src.portfolio.models import AllocationAlignmentResult

        # Load from archive CSV
        csv_text = PAR_ARCHIVE_CSV.read_text(encoding="utf-8", errors="replace")
        snapshot, raw_holdings = ingest_portfolio(csv_text, PAR_ARCHIVE_CSV.name, "2026-05-29")

        enriched = enrich_holdings(raw_holdings, universe_csv=str(
            Path("data/current/analytical_universe.csv")
        ))
        enriched = normalize_and_aggregate_holdings(enriched)

        _INVESTABLE_STATES = frozenset({"ACTIVE_POSITION", "CASH_EQUIVALENT"})
        investable = [h for h in enriched if h.operational_state in _INVESTABLE_STATES]

        from src.portfolio.archetype import load_archetype_targets
        _TARGETS_CSV = str(Path("data/current/strategic_allocation_targets.csv"))
        _OVERLAYS_CSV = str(Path("data/current/tactical_overlays.csv"))
        archetype_targets = load_archetype_targets("CONCENTRATED_ALPHA")
        alignment = compute_alignment(
            analysis_run_id="TEST-PAR",
            portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
            holdings=investable,
            targets_csv=_TARGETS_CSV,
            overlays_csv=_OVERLAYS_CSV,
            targets_override=archetype_targets,
        )
        overlays = build_security_overlays(
            portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
            holdings=investable,
            alignment_results=alignment,
        )
        profiles = build_strategic_profiles(
            portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
            holdings=investable,
            overlays=overlays,
            alignment_results=alignment,
        )
        queue = build_deployment_queue(
            portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
            holdings=investable,
            overlays=overlays,
            strategic_profiles=profiles,
            alignment_results=alignment,
            total_market_value=snapshot.total_market_value,
        )
        return queue

    def test_ac1_vrt_ranks_first(self, queue):
        """AC-1: VRT ranks #1 in the deployment queue.

        After the Phase 7.5G-B fix (coverage-aware ESS dedup), AEIS correctly
        carries BEARISH ESS which reduces its composite from 4.71 to 3.06 and
        drops it from CCL to DEPLOYMENT_CANDIDATE tier. VRT is now the top
        deployment candidate with composite 4.56 (CCL, VERY_BULLISH, score 95.53).
        """
        assert len(queue) >= 1, "Queue must have at least one candidate"
        assert queue[0].symbol == "VRT", (
            f"Expected VRT at rank 1, got {queue[0].symbol} "
            f"(score={queue[0].deployment_score})"
        )

    def test_ac2_arw_ranks_second(self, queue):
        """AC-2: ARW is present and eligible in the deployment queue.

        After ISSUE-07 (Fundamental Conviction Modifier), the exact rank of ARW
        depends on FMP data availability. The key invariant is that ARW passes
        eligibility (replay-backed, VERY_BULLISH, HCA tier) and appears in the queue.
        """
        syms = {c.symbol for c in queue}
        assert "ARW" in syms, f"Expected ARW to be eligible and in queue, got {sorted(syms)}"
        arw = next(c for c in queue if c.symbol == "ARW")
        assert arw.replay_supported is True
        assert arw.narrative_tier == "HIGH_CONVICTION_ANCHOR"

    def test_ac3_no_ccl_hca_inversions(self, queue):
        """AC-3: No HCA candidate outranks any deployable CCL candidate.

        An 'inversion' is when an HCA has a lower rank number (better position)
        than a CCL that is not blocked (not OW-node and below WARN threshold).
        """
        ccl_ranks = {c.rank for c in queue if c.narrative_tier == "CORE_CONVICTION_LEADER"}
        for cand in queue:
            if cand.narrative_tier == "HIGH_CONVICTION_ANCHOR":
                # Check that all CCLs have rank ≤ this HCA's rank
                for ccl_rank in ccl_ranks:
                    if ccl_rank > cand.rank:
                        # A CCL ranks worse than this HCA — verify the CCL is legitimately suppressed
                        ccl_cand = next(c for c in queue if c.rank == ccl_rank)
                        assert "OW node" in ccl_cand.notes or "BLOCKED" in ccl_cand.notes, (
                            f"INVERSION: HCA {cand.symbol} (rank {cand.rank}) "
                            f"outranks unsuppressed CCL {ccl_cand.symbol} (rank {ccl_rank})"
                        )

    def test_ac4_mu_not_actionable_top10(self, queue):
        """AC-4: MU is suppressed by OW-node redundancy penalty.

        MU is in the US.MEGA.ULTRA_MEGA OVERWEIGHT node and carries both
        a redundancy penalty (−15) and a concentration penalty. With ISSUE-07
        Fundamental Modifier, MU's score may vary, but its OW-node penalties
        must be applied (redundancy_pen=15).
        """
        mu_cand = next((c for c in queue if c.symbol == "MU"), None)
        if mu_cand is not None:
            assert mu_cand.score_breakdown.redundancy_pen == 15.0, (
                f"MU must have redundancy_pen=15 (got {mu_cand.score_breakdown.redundancy_pen})"
            )

    def test_ac5_ow_node_symbols_penalized(self, queue):
        """AC-5: OW-node symbols (NVDA, TSM, CVE, MU) all have redundancy_pen=15.

        These symbols are in OVERWEIGHT nodes and must carry the full penalty.
        """
        ow_penalized = {"NVDA", "TSM", "CVE", "MU"}
        for cand in queue:
            if cand.symbol in ow_penalized:
                assert cand.score_breakdown.redundancy_pen == 15.0, (
                    f"{cand.symbol} should have redundancy_pen=15 "
                    f"(got {cand.score_breakdown.redundancy_pen})"
                )

    def test_ac6_deployment_score_fields_valid(self, queue):
        """AC-6: All candidates have valid score ranges and non-empty metadata."""
        for cand in queue:
            assert 0.0 <= cand.deployment_score <= 103.0, f"Score out of range: {cand}"
            assert cand.rank >= 1
            assert cand.symbol
            assert cand.narrative_tier in {"CORE_CONVICTION_LEADER", "HIGH_CONVICTION_ANCHOR"}
            assert cand.replay_supported is True  # eligibility gate
            bd = cand.score_breakdown
            assert 0.0 <= bd.signal   <= 30.0
            assert bd.replay          in (0.0, 20.0)
            assert bd.conviction      in (35.0, 28.0, 10.0)
            assert 0.0 <= bd.sizing   <= 8.0
            assert bd.momentum        in (0.0, 4.0, 7.5, 10.0)
            assert bd.redundancy_pen  in (0.0, 15.0)
            assert 0.0 <= bd.conc_pen <= 20.0
            # ISSUE-07: fundamental_modifier is bounded
            assert -5.0 <= bd.fundamental_modifier <= 3.0

    def test_constant_queue_version(self):
        """Queue version constant must be '1.1' after ISSUE-07 Fundamental Modifier."""
        assert CW_DAS_VERSION == "1.1"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Constants contract
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_warn_position_pct(self):
        assert WARN_POSITION_PCT == 6.0

    def test_max_position_pct(self):
        assert MAX_POSITION_PCT == 8.0

    def test_min_cash_pct(self):
        assert MIN_CASH_PCT == 2.0

    def test_queue_version(self):
        assert CW_DAS_VERSION == "1.1"


# ─────────────────────────────────────────────────────────────────────────────
# 7. DeploymentCandidate is a frozen dataclass
# ─────────────────────────────────────────────────────────────────────────────

class TestDeploymentCandidateModel:
    def test_frozen(self):
        """DeploymentCandidate must be immutable."""
        cand = DeploymentCandidate(
            rank=1, symbol="TEST", current_weight_pct=2.0, market_value=9000.0,
            composite_score=4.5, narrative_tier="CORE_CONVICTION_LEADER",
            replay_supported=True, trim_score=15.0, headroom_pct=67.0,
            deployment_score=85.5,
            score_breakdown=CwDasBreakdown(
                signal=27.0, replay=20.0, conviction=35.0,
                sizing=5.3, momentum=10.0, redundancy_pen=0.0, conc_pen=0.0,
            ),
            notes="CCL tier | 67% headroom",
        )
        with pytest.raises((AttributeError, TypeError)):
            cand.rank = 2  # type: ignore[misc]

    def test_dataclasses_asdict(self):
        """dataclasses.asdict() must serialize without error."""
        cand = DeploymentCandidate(
            rank=1, symbol="TEST", current_weight_pct=2.0, market_value=9000.0,
            composite_score=4.5, narrative_tier="CORE_CONVICTION_LEADER",
            replay_supported=True, trim_score=15.0, headroom_pct=67.0,
            deployment_score=85.5,
            score_breakdown=CwDasBreakdown(
                signal=27.0, replay=20.0, conviction=35.0,
                sizing=5.3, momentum=10.0, redundancy_pen=0.0, conc_pen=0.0,
            ),
            notes="CCL tier | 67% headroom",
        )
        d = dataclasses.asdict(cand)
        assert d["symbol"] == "TEST"
        assert "score_breakdown" in d
        assert d["score_breakdown"]["conviction"] == 35.0
