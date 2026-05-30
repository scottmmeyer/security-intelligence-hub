"""Phase D — Strategic Trim Intelligence unit tests.

Covers:
  - _classify_exposure_origin
  - _compute_pairwise_thematic_overlap
  - _find_overlap_peers
  - _compute_thematic_redundancy_score
  - _compute_trim_priority_score
  - _classify_holding
  - build_strategic_profiles
  - validate_trim_intelligence_consistency
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

from src.portfolio.trim_intelligence import (
    _classify_exposure_origin,
    _compute_pairwise_thematic_overlap,
    _find_overlap_peers,
    _compute_thematic_redundancy_score,
    _compute_trim_priority_score,
    _classify_holding,
    _build_trim_rationale,
    build_strategic_profiles,
    validate_trim_intelligence_consistency,
)
from src.portfolio.models import HoldingStrategicProfile, PortfolioHolding


# ─────────────────────────────────────────────────────────────────────────────
# Minimal factories
# ─────────────────────────────────────────────────────────────────────────────

def _holding(
    symbol: str,
    security_type: str = "ETF",
    strategic_role: str = "CORE_BROAD_US",
    percent_of_portfolio: float = 5.0,
    thematic_mix: tuple = (),
    mega_mix: tuple = (),
    market_value: float = 10000.0,
    description: str = "Test Holding",
    market_cap_bucket: str = "LARGE",
    geography: str = "US",
    sector: str = "Technology",
) -> PortfolioHolding:
    return PortfolioHolding(
        portfolio_snapshot_id="PSNAP-TEST",
        snapshot_date="2025-01-01",
        account_name="Test",
        symbol=symbol,
        description=description,
        quantity=100.0,
        market_value=market_value,
        percent_of_portfolio=percent_of_portfolio,
        asset_class="EQUITIES",
        geography=geography,
        market_cap_bucket=market_cap_bucket,
        mega_subtier="N/A",
        sector=sector,
        industry="ALL",
        security_type=security_type,
        cost_basis=None,
        composite_score=None,
        ess_score_text=None,
        zacks_rating=None,
        benchmark_id=None,
        investable_vehicle_id=None,
        source_file="test.csv",
        created_at_utc="2025-01-01T00:00:00Z",
        exposure_thematic_mix=thematic_mix,
        exposure_mega_subtier_mix=mega_mix,
        strategic_role=strategic_role,
    )


@dataclass
class _FakeOverlay:
    """Minimal overlay stub for unit tests."""
    symbol: str
    signal_direction: str = "NEUTRAL"
    composite_score: Optional[float] = None
    replay_supported: bool = False
    replay_percentile: Optional[float] = None
    percent_of_portfolio: float = 5.0


# ─────────────────────────────────────────────────────────────────────────────
# D.5 — _classify_exposure_origin
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifyExposureOrigin:
    def test_etf_semiconductor_is_thematic(self):
        h = _holding("SMH", security_type="ETF", strategic_role="SEMICONDUCTOR_CONCENTRATION")
        assert _classify_exposure_origin(h) == "ETF_THEMATIC"

    def test_etf_sector_concentration_is_thematic(self):
        h = _holding("XLK", security_type="ETF", strategic_role="SECTOR_CONCENTRATION")
        assert _classify_exposure_origin(h) == "ETF_THEMATIC"

    def test_etf_aggressive_growth_is_thematic(self):
        h = _holding("QQQ", security_type="ETF", strategic_role="AGGRESSIVE_GROWTH_CONCENTRATION")
        assert _classify_exposure_origin(h) == "ETF_THEMATIC"

    def test_etf_core_broad_is_inherited(self):
        h = _holding("VOO", security_type="ETF", strategic_role="CORE_BROAD_US")
        assert _classify_exposure_origin(h) == "ETF_INHERITED"

    def test_etf_stability_core_is_inherited(self):
        h = _holding("BND", security_type="ETF", strategic_role="STABILITY_CORE")
        assert _classify_exposure_origin(h) == "ETF_INHERITED"

    def test_common_stock_is_direct(self):
        h = _holding("NVDA", security_type="Common Stock", strategic_role="SEMICONDUCTOR_CONCENTRATION")
        assert _classify_exposure_origin(h) == "DIRECT_INTENTIONAL"

    def test_non_fund_security_type_is_direct(self):
        h = _holding("AAPL", security_type="STOCK", strategic_role="SECTOR_CONCENTRATION")
        assert _classify_exposure_origin(h) == "DIRECT_INTENTIONAL"


# ─────────────────────────────────────────────────────────────────────────────
# D.3 — _compute_pairwise_thematic_overlap
# ─────────────────────────────────────────────────────────────────────────────

class TestPairwiseThematicOverlap:
    def test_identical_holdings_return_1(self):
        mix = (("AI", 50.0), ("SEMICONDUCTORS", 50.0))
        a = _holding("A", thematic_mix=mix)
        b = _holding("B", thematic_mix=mix)
        assert _compute_pairwise_thematic_overlap(a, b) == pytest.approx(1.0)

    def test_no_overlap_returns_0(self):
        a = _holding("A", thematic_mix=(("AI", 100.0),))
        b = _holding("B", thematic_mix=(("ENERGY", 100.0),))
        assert _compute_pairwise_thematic_overlap(a, b) == pytest.approx(0.0)

    def test_partial_overlap_is_weighted_jaccard(self):
        a = _holding("A", thematic_mix=(("AI", 80.0), ("CLOUD", 20.0)))
        b = _holding("B", thematic_mix=(("AI", 40.0), ("ENERGY", 60.0)))
        # numerator = min(80,40) + min(20,0) + min(0,60) = 40
        # denominator = max(80,40) + max(20,0) + max(0,60) = 80+20+60 = 160
        expected = 40.0 / 160.0
        assert _compute_pairwise_thematic_overlap(a, b) == pytest.approx(expected, rel=0.01)

    def test_empty_thematic_mix_returns_0(self):
        a = _holding("A", thematic_mix=())
        b = _holding("B", thematic_mix=(("AI", 50.0),))
        assert _compute_pairwise_thematic_overlap(a, b) == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# D.3 — _find_overlap_peers
# ─────────────────────────────────────────────────────────────────────────────

class TestFindOverlapPeers:
    def test_returns_peers_above_threshold(self):
        mix = (("AI", 80.0), ("SEMICONDUCTORS", 20.0))
        a = _holding("VOO", thematic_mix=mix)
        b = _holding("QQQ", thematic_mix=mix)
        c = _holding("BND", thematic_mix=(("BONDS", 100.0),))
        peers = _find_overlap_peers("VOO", [a, b, c])
        assert "QQQ" in peers
        assert "BND" not in peers

    def test_no_peers_when_no_thematic_mix(self):
        a = _holding("A", thematic_mix=())
        b = _holding("B", thematic_mix=(("AI", 80.0),))
        peers = _find_overlap_peers("A", [a, b])
        assert peers == []

    def test_symbol_excluded_from_own_peers(self):
        mix = (("AI", 80.0),)
        a = _holding("A", thematic_mix=mix)
        peers = _find_overlap_peers("A", [a])
        assert "A" not in peers


# ─────────────────────────────────────────────────────────────────────────────
# D.3 — _compute_thematic_redundancy_score
# ─────────────────────────────────────────────────────────────────────────────

class TestThematicRedundancyScore:
    def test_single_holding_is_zero(self):
        h = _holding("A", thematic_mix=(("AI", 80.0),))
        score = _compute_thematic_redundancy_score(h, [h])
        assert score == pytest.approx(0.0)

    def test_identical_large_peer_raises_score(self):
        mix = (("AI", 80.0), ("SEMICONDUCTORS", 20.0))
        a = _holding("A", thematic_mix=mix, percent_of_portfolio=10.0)
        b = _holding("B", thematic_mix=mix, percent_of_portfolio=10.0)
        score = _compute_thematic_redundancy_score(a, [a, b])
        assert score > 20.0  # should be significantly redundant

    def test_no_overlap_peer_does_not_raise_score(self):
        a = _holding("A", thematic_mix=(("AI", 100.0),))
        b = _holding("B", thematic_mix=(("ENERGY", 100.0),), percent_of_portfolio=20.0)
        score = _compute_thematic_redundancy_score(a, [a, b])
        assert score == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# D.2 — _compute_trim_priority_score
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeTrimPriorityScore:
    def test_critical_role_gets_negative_penalty(self):
        """CRITICAL strategic importance should reduce trim score substantially."""
        h = _holding("VOO", strategic_role="CORE_BROAD_US", percent_of_portfolio=5.0,
                     thematic_mix=())
        score, factors, _ = _compute_trim_priority_score(
            h, None, {}, [], 0.0, "CRITICAL"
        )
        # CRITICAL adds -25 penalty; score should be low
        assert score < 30.0, f"CRITICAL role should yield low trim score, got {score}"

    def test_direct_intentional_reduces_trim_score(self):
        """DIRECT_INTENTIONAL holdings should get an additional -5 penalty."""
        h_stock = _holding("NVDA", security_type="Common Stock",
                           strategic_role="SECTOR_CONCENTRATION",
                           percent_of_portfolio=5.0, thematic_mix=())
        score_stock, factors_stock, _ = _compute_trim_priority_score(
            h_stock, None, {}, [], 0.0, "MEDIUM"
        )
        # Check that DIRECT_INTENTIONAL factor appears
        factor_names = [f["factor"] for f in factors_stock]
        assert "direct_intentional_ownership" in factor_names

    def test_score_clamped_to_0_100(self):
        """Trim score should never exceed 100 or go below 0."""
        h = _holding("TEST", strategic_role="SYSTEMATIC_MICRO_CAP",
                     percent_of_portfolio=30.0, thematic_mix=())
        score, _, _ = _compute_trim_priority_score(h, None, {}, [], 100.0, "LOW")
        assert 0.0 <= score <= 100.0

    def test_factors_list_is_nonempty(self):
        h = _holding("A", strategic_role="CORE_BROAD_US", thematic_mix=())
        _, factors, _ = _compute_trim_priority_score(h, None, {}, [], 0.0, "CRITICAL")
        assert len(factors) > 0

    def test_overlay_bearish_increases_score(self):
        h = _holding("QQQ", strategic_role="AGGRESSIVE_GROWTH_CONCENTRATION",
                     percent_of_portfolio=5.0, thematic_mix=())
        overlay_neutral = _FakeOverlay("QQQ", signal_direction="NEUTRAL")
        overlay_bearish = _FakeOverlay("QQQ", signal_direction="BEARISH")
        score_neutral, _, _ = _compute_trim_priority_score(h, overlay_neutral, {}, [], 0.0, "MEDIUM")
        score_bearish, _, _ = _compute_trim_priority_score(h, overlay_bearish, {}, [], 0.0, "MEDIUM")
        assert score_bearish >= score_neutral


# ─────────────────────────────────────────────────────────────────────────────
# D.1 — _classify_holding
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifyHolding:
    def test_high_conviction_retain_requires_bullish_plus_low_trim(self):
        h = _holding("NVDA", security_type="Common Stock",
                     strategic_role="SEMICONDUCTOR_CONCENTRATION",
                     thematic_mix=())
        overlay = _FakeOverlay("NVDA", signal_direction="BULLISH", composite_score=0.25,
                               replay_supported=True, replay_percentile=70.0)
        cls = _classify_holding(
            holding=h,
            overlay=overlay,
            trim_score=8.0,
            thematic_redundancy=5.0,
            overlap_peers=[],
            strategic_importance="MEDIUM",
            exposure_origin="DIRECT_INTENTIONAL",
        )
        assert cls == "HIGH_CONVICTION_RETAIN"

    def test_concentration_risk_for_large_overweight_concentrated_etf(self):
        h = _holding("SMH", security_type="ETF",
                     strategic_role="SEMICONDUCTOR_CONCENTRATION",
                     percent_of_portfolio=20.0,
                     thematic_mix=(("SEMICONDUCTORS", 90.0),))
        cls = _classify_holding(
            holding=h,
            overlay=None,
            trim_score=72.0,
            thematic_redundancy=60.0,
            overlap_peers=["QQQ", "NVDA"],
            strategic_importance="MEDIUM",
            exposure_origin="ETF_THEMATIC",
        )
        assert cls in ("CONCENTRATION_RISK", "REDUCIBLE")

    def test_core_compounder_for_critical_bullish(self):
        h = _holding("VOO", security_type="ETF",
                     strategic_role="CORE_BROAD_US",
                     thematic_mix=())
        overlay = _FakeOverlay("VOO", signal_direction="BULLISH", composite_score=0.20)
        cls = _classify_holding(
            holding=h,
            overlay=overlay,
            trim_score=5.0,
            thematic_redundancy=0.0,
            overlap_peers=[],
            strategic_importance="CRITICAL",
            exposure_origin="ETF_INHERITED",
        )
        assert cls in ("CORE_COMPOUNDER", "STRATEGIC_CORE")


# ─────────────────────────────────────────────────────────────────────────────
# build_strategic_profiles
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildStrategicProfiles:
    def _sample_holdings(self):
        return [
            _holding("VOO", security_type="ETF", strategic_role="CORE_BROAD_US",
                     percent_of_portfolio=30.0, thematic_mix=()),
            _holding("QQQ", security_type="ETF", strategic_role="AGGRESSIVE_GROWTH_CONCENTRATION",
                     percent_of_portfolio=15.0, thematic_mix=(("TECH", 80.0), ("AI", 20.0))),
            _holding("SMH", security_type="ETF", strategic_role="SEMICONDUCTOR_CONCENTRATION",
                     percent_of_portfolio=10.0, thematic_mix=(("SEMICONDUCTORS", 90.0), ("AI", 10.0))),
        ]

    def test_returns_profile_for_each_holding(self):
        holdings = self._sample_holdings()
        profiles = build_strategic_profiles("snap_001", holdings, [], {})
        assert len(profiles) == len(holdings)

    def test_sorted_by_trim_priority_score_desc(self):
        holdings = self._sample_holdings()
        profiles = build_strategic_profiles("snap_001", holdings, [], {})
        scores = [p.trim_priority_score for p in profiles]
        assert scores == sorted(scores, reverse=True)

    def test_all_symbols_present(self):
        holdings = self._sample_holdings()
        profiles = build_strategic_profiles("snap_001", holdings, [], {})
        symbols = {p.symbol for p in profiles}
        assert symbols == {"VOO", "QQQ", "SMH"}

    def test_valid_classification_on_each_profile(self):
        valid_cls = {
            "HIGH_CONVICTION_RETAIN", "CORE_COMPOUNDER", "STRATEGIC_CORE",
            "THEMATIC_LEADER", "TACTICAL_GROWTH", "REDUNDANT_EXPOSURE",
            "CONCENTRATION_RISK", "REDUCIBLE",
        }
        profiles = build_strategic_profiles("snap_001", self._sample_holdings(), [], {})
        for p in profiles:
            assert p.strategic_classification in valid_cls, \
                f"Unexpected classification: {p.strategic_classification} for {p.symbol}"

    def test_profile_snapshot_id_matches(self):
        profiles = build_strategic_profiles("snap_XYZ", self._sample_holdings(), [], {})
        for p in profiles:
            assert p.portfolio_snapshot_id == "snap_XYZ"

    def test_trim_factors_is_tuple(self):
        profiles = build_strategic_profiles("snap_001", self._sample_holdings(), [], {})
        for p in profiles:
            assert isinstance(p.trim_factors, tuple)

    def test_trim_score_within_bounds(self):
        profiles = build_strategic_profiles("snap_001", self._sample_holdings(), [], {})
        for p in profiles:
            assert 0.0 <= p.trim_priority_score <= 100.0, \
                f"{p.symbol} trim_priority_score {p.trim_priority_score} out of bounds"


# ─────────────────────────────────────────────────────────────────────────────
# D.9 — validate_trim_intelligence_consistency
# ─────────────────────────────────────────────────────────────────────────────

def _make_profile(**kwargs) -> HoldingStrategicProfile:
    defaults = dict(
        portfolio_snapshot_id="snap_001",
        symbol="TEST",
        security_type="ETF",
        percent_of_portfolio=5.0,
        strategic_classification="TACTICAL_GROWTH",
        trim_priority_score=40.0,
        trim_factors=(),
        thematic_overlap_clusters=(),
        overlap_peers=(),
        thematic_redundancy_score=20.0,
        strategic_role="AGGRESSIVE_GROWTH_CONCENTRATION",
        strategic_importance="MEDIUM",
        exposure_origin="ETF_THEMATIC",
        trim_rationale="",
        retain_rationale="",
        classification_trace="",
        concentration_pressure=0.0,
        diversification_contribution=50.0,
        created_at_utc="2025-01-01T00:00:00Z",
    )
    defaults.update(kwargs)
    return HoldingStrategicProfile(**defaults)


class TestValidateTrimIntelligenceConsistency:
    def test_reducible_critical_generates_warning(self):
        p = _make_profile(strategic_classification="REDUCIBLE", strategic_importance="CRITICAL")
        warnings = validate_trim_intelligence_consistency([p])
        assert any("CRITICAL" in w or "REDUCIBLE" in w for w in warnings)

    def test_high_conviction_high_trim_generates_warning(self):
        p = _make_profile(strategic_classification="HIGH_CONVICTION_RETAIN",
                          trim_priority_score=75.0)
        warnings = validate_trim_intelligence_consistency([p])
        assert any("HIGH_CONVICTION_RETAIN" in w or "trim" in w.lower() for w in warnings)

    def test_clean_profiles_generate_no_warnings(self):
        profiles = [
            _make_profile(symbol="A", strategic_classification="CORE_COMPOUNDER",
                          strategic_importance="CRITICAL", trim_priority_score=10.0),
            _make_profile(symbol="B", strategic_classification="REDUCIBLE",
                          strategic_importance="LOW", trim_priority_score=60.0),
        ]
        warnings = validate_trim_intelligence_consistency(profiles)
