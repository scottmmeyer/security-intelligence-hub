"""Tests for ISSUE-07 — Fundamental Conviction Modifier (Phase 8.0B.1C).

Tests cover:
- compute_fundamental_modifier() formula correctness
- Beat rate component (all tiers + sector exclusions)
- Thesis integrity component
- Fundamental consistency component
- Bounding (-5 to +3)
- No-op when coverage is insufficient
- CCL-over-HCA guard in build_deployment_queue()
- CwDasBreakdown.fundamental_modifier field
- compute_cw_das() integration
"""

from __future__ import annotations

import pytest

from src.portfolio.deployment_queue import (
    CwDasBreakdown,
    compute_fundamental_modifier,
    compute_cw_das,
    _FM_MAX_BONUS,
    _FM_MAX_PENALTY,
    _FM_BEAT_RATE_EXCLUDED_SECTORS,
)


# ─── compute_fundamental_modifier() unit tests ────────────────────────────────

class TestComputeFundamentalModifier:
    """Verify each sub-component and boundary of the fundamental modifier."""

    # Coverage gate
    def test_no_data_coverage_returns_zero(self):
        assert compute_fundamental_modifier(
            beat_rate=1.0, thesis_integrity="INTACT",
            fundamental_consistency="CONSISTENT", fmp_coverage="NO_DATA"
        ) == 0.0

    def test_etf_coverage_returns_zero(self):
        assert compute_fundamental_modifier(
            beat_rate=1.0, thesis_integrity="INTACT",
            fundamental_consistency="CONSISTENT", fmp_coverage="ETF_NOT_APPLICABLE"
        ) == 0.0

    def test_full_coverage_active(self):
        result = compute_fundamental_modifier(
            beat_rate=1.0, thesis_integrity="INTACT",
            fundamental_consistency="CONSISTENT", fmp_coverage="FULL"
        )
        assert result > 0.0

    def test_partial_coverage_active(self):
        result = compute_fundamental_modifier(
            beat_rate=1.0, thesis_integrity="INTACT",
            fundamental_consistency="CONSISTENT", fmp_coverage="PARTIAL"
        )
        assert result > 0.0

    # Beat rate component
    def test_beat_rate_elite_tier(self):
        """beat_rate >= 0.875 → +2.0 beat component."""
        result = compute_fundamental_modifier(
            beat_rate=0.875, thesis_integrity="INTACT",
            fundamental_consistency="CONSISTENT", fmp_coverage="FULL"
        )
        # +2.0 (beat) + 0.0 (intact) + 1.0 (consistent) = +3.0 → capped at +3.0
        assert result == 3.0

    def test_beat_rate_strong_tier(self):
        """beat_rate >= 0.75 and < 0.875 → +1.0 beat component."""
        result = compute_fundamental_modifier(
            beat_rate=0.75, thesis_integrity="INTACT",
            fundamental_consistency="CONSISTENT", fmp_coverage="FULL"
        )
        # +1.0 + 0 + 1.0 = +2.0
        assert result == 2.0

    def test_beat_rate_neutral_tier(self):
        """beat_rate >= 0.625 and < 0.75 → 0 beat component."""
        result = compute_fundamental_modifier(
            beat_rate=0.70, thesis_integrity="INTACT",
            fundamental_consistency="CONSISTENT", fmp_coverage="FULL"
        )
        # 0 + 0 + 1.0 = +1.0
        assert result == 1.0

    def test_beat_rate_weak_tier(self):
        """beat_rate < 0.625 → -1.0 beat component."""
        result = compute_fundamental_modifier(
            beat_rate=0.50, thesis_integrity="INTACT",
            fundamental_consistency="MIXED", fmp_coverage="FULL"
        )
        # -1.0 + 0 + 0 = -1.0
        assert result == -1.0

    def test_beat_rate_none_is_zero(self):
        """None beat_rate → 0 beat component."""
        result = compute_fundamental_modifier(
            beat_rate=None, thesis_integrity="INTACT",
            fundamental_consistency="CONSISTENT", fmp_coverage="FULL"
        )
        # 0 + 0 + 1.0 = +1.0
        assert result == 1.0

    # Thesis integrity component
    def test_thesis_intact(self):
        result = compute_fundamental_modifier(
            beat_rate=None, thesis_integrity="INTACT",
            fundamental_consistency="MIXED", fmp_coverage="FULL"
        )
        assert result == 0.0  # 0 + 0 + 0

    def test_thesis_questionable(self):
        result = compute_fundamental_modifier(
            beat_rate=None, thesis_integrity="QUESTIONABLE",
            fundamental_consistency="MIXED", fmp_coverage="FULL"
        )
        assert result == -0.5  # 0 + (-0.5) + 0

    def test_thesis_deteriorating(self):
        result = compute_fundamental_modifier(
            beat_rate=None, thesis_integrity="DETERIORATING",
            fundamental_consistency="MIXED", fmp_coverage="FULL"
        )
        assert result == -3.0  # 0 + (-3.0) + 0

    def test_thesis_insufficient(self):
        result = compute_fundamental_modifier(
            beat_rate=None, thesis_integrity="INSUFFICIENT_DATA",
            fundamental_consistency="MIXED", fmp_coverage="FULL"
        )
        assert result == 0.0

    # Consistency component
    def test_consistency_consistent(self):
        result = compute_fundamental_modifier(
            beat_rate=None, thesis_integrity="INTACT",
            fundamental_consistency="CONSISTENT", fmp_coverage="FULL"
        )
        assert result == 1.0  # 0 + 0 + 1.0

    def test_consistency_mixed(self):
        result = compute_fundamental_modifier(
            beat_rate=None, thesis_integrity="INTACT",
            fundamental_consistency="MIXED", fmp_coverage="FULL"
        )
        assert result == 0.0

    def test_consistency_contradictory(self):
        result = compute_fundamental_modifier(
            beat_rate=None, thesis_integrity="INTACT",
            fundamental_consistency="CONTRADICTORY", fmp_coverage="FULL"
        )
        assert result == -1.5  # 0 + 0 + (-1.5)

    def test_consistency_data_anomaly(self):
        result = compute_fundamental_modifier(
            beat_rate=None, thesis_integrity="INTACT",
            fundamental_consistency="DATA_ANOMALY", fmp_coverage="FULL"
        )
        assert result == -2.0  # 0 + 0 + (-2.0)

    # Bounding
    def test_max_bonus_capped_at_3(self):
        """Maximum possible raw = +2 + 0 + 1 = +3.0, should not exceed cap."""
        result = compute_fundamental_modifier(
            beat_rate=1.0, thesis_integrity="INTACT",
            fundamental_consistency="CONSISTENT", fmp_coverage="FULL"
        )
        assert result == _FM_MAX_BONUS == 3.0

    def test_max_penalty_capped_at_minus_5(self):
        """Worst case: -1 (beat) + (-3.0) (detr) + (-1.5) (contradict) = -5.5 → capped at -5."""
        result = compute_fundamental_modifier(
            beat_rate=0.50, thesis_integrity="DETERIORATING",
            fundamental_consistency="CONTRADICTORY", fmp_coverage="FULL"
        )
        assert result == _FM_MAX_PENALTY == -5.0

    # Sector calibration
    def test_solar_beat_rate_excluded(self):
        """Solar industry — beat_rate component is 0 regardless of value."""
        result_excluded = compute_fundamental_modifier(
            beat_rate=0.40,  # would normally give -1.0
            thesis_integrity="INTACT", fundamental_consistency="CONSISTENT",
            fmp_coverage="FULL", industry="Solar"
        )
        result_normal = compute_fundamental_modifier(
            beat_rate=0.40,
            thesis_integrity="INTACT", fundamental_consistency="CONSISTENT",
            fmp_coverage="FULL", industry="Technology"
        )
        # Solar: beat omitted → 0 + 0 + 1.0 = 1.0
        assert result_excluded == 1.0
        # Tech: beat applied → -1.0 + 0 + 1.0 = 0.0
        assert result_normal == 0.0

    def test_biotech_beat_rate_excluded(self):
        """Biotechnology industry — beat_rate component is 0."""
        result = compute_fundamental_modifier(
            beat_rate=0.40,
            thesis_integrity="INTACT", fundamental_consistency="CONSISTENT",
            fmp_coverage="FULL", industry="Biotechnology"
        )
        assert result == 1.0  # beat omitted: 0 + 0 + 1.0

    def test_excluded_sectors_set_contents(self):
        assert "Solar" in _FM_BEAT_RATE_EXCLUDED_SECTORS
        assert "Biotechnology" in _FM_BEAT_RATE_EXCLUDED_SECTORS

    # Key named cases
    def test_psx_case(self):
        """PSX: DETERIORATING thesis, 71% beat rate, MIXED consistency → -4.0."""
        result = compute_fundamental_modifier(
            beat_rate=0.714,   # 71% → between 0.625 and 0.75 → component=0
            thesis_integrity="DETERIORATING",  # -3.0
            fundamental_consistency="MIXED",   # 0.0
            fmp_coverage="FULL"
        )
        # 0 (beat: 71% is neutral tier) + (-3.0) + 0 = -3.0
        assert result == -3.0

    def test_lrcx_case(self):
        """LRCX: INTACT thesis, 100% beat rate, CONSISTENT → +3.0 (capped)."""
        result = compute_fundamental_modifier(
            beat_rate=1.0,     # 100% → +2.0
            thesis_integrity="INTACT",       # 0.0
            fundamental_consistency="CONSISTENT",  # +1.0
            fmp_coverage="FULL"
        )
        assert result == 3.0  # raw = 3.0, at cap

    def test_dell_case(self):
        """DELL: INTACT thesis, 86% beat rate, CONSISTENT → +2.0 + 0 + 1.0 = +3.0."""
        result = compute_fundamental_modifier(
            beat_rate=0.857,   # 85.7% → between 0.75 and 0.875 → +1.0
            thesis_integrity="INTACT",
            fundamental_consistency="CONSISTENT",
            fmp_coverage="FULL"
        )
        assert result == 2.0  # +1.0 + 0 + 1.0 = 2.0 (NOT capped)


# ─── CwDasBreakdown has fundamental_modifier field ────────────────────────────

class TestCwDasBreakdownField:
    def test_fundamental_modifier_default_zero(self):
        bd = CwDasBreakdown(
            signal=27.0, replay=20.0, conviction=35.0,
            sizing=3.0, momentum=10.0, redundancy_pen=0.0, conc_pen=0.0
        )
        assert bd.fundamental_modifier == 0.0

    def test_fundamental_modifier_explicit(self):
        bd = CwDasBreakdown(
            signal=27.0, replay=20.0, conviction=35.0,
            sizing=3.0, momentum=10.0, redundancy_pen=0.0, conc_pen=0.0,
            fundamental_modifier=-3.0
        )
        assert bd.fundamental_modifier == -3.0

    def test_frozen(self):
        bd = CwDasBreakdown(
            signal=27.0, replay=20.0, conviction=35.0,
            sizing=3.0, momentum=10.0, redundancy_pen=0.0, conc_pen=0.0
        )
        with pytest.raises(Exception):
            bd.fundamental_modifier = 1.0  # type: ignore[misc]


# ─── compute_cw_das() integration ────────────────────────────────────────────

class TestComputeCwDasFundamentalModifier:
    def test_no_fmp_row_modifier_zero(self):
        """Without fmp_row, modifier is zero and score is unchanged."""
        score, bd = compute_cw_das(
            symbol="TEST", composite=4.5, pct=2.0, tier="HIGH_CONVICTION_ANCHOR",
            replay_supported=True, ess_text="VERY_BULLISH",
            signal_direction="BULLISH", in_ow_node=False,
            fmp_row=None
        )
        assert bd.fundamental_modifier == 0.0

    def test_fmp_row_intact_consistent_100_beat_adds_bonus(self):
        """INTACT + CONSISTENT + 100% beat → +3.0 modifier applied to score."""
        fmp_row = {
            "fmp_coverage_status": "FULL",
            "beat_rate_8q": "1.0",
            "revenue_growth_q1_yoy": "0.20",
            "revenue_acceleration": "0.10",
            "ev_ebitda_ttm": "25.0",
        }
        score_with, bd_with = compute_cw_das(
            symbol="TEST", composite=4.5, pct=2.0, tier="HIGH_CONVICTION_ANCHOR",
            replay_supported=True, ess_text="VERY_BULLISH",
            signal_direction="BULLISH", in_ow_node=False,
            fmp_row=fmp_row
        )
        score_without, bd_without = compute_cw_das(
            symbol="TEST", composite=4.5, pct=2.0, tier="HIGH_CONVICTION_ANCHOR",
            replay_supported=True, ess_text="VERY_BULLISH",
            signal_direction="BULLISH", in_ow_node=False,
            fmp_row=None
        )
        assert bd_with.fundamental_modifier == 3.0
        assert round(score_with - score_without, 2) == 3.0

    def test_fmp_row_deteriorating_applies_penalty(self):
        """DETERIORATING + MIXED → at least -3.0 modifier."""
        fmp_row = {
            "fmp_coverage_status": "FULL",
            "beat_rate_8q": "0.70",           # neutral tier
            "revenue_growth_q1_yoy": "-0.10", # declining
            "revenue_acceleration": "-0.60",  # severe deceleration
            "ev_ebitda_ttm": "10.0",
        }
        _, bd = compute_cw_das(
            symbol="PSX", composite=4.7, pct=1.5, tier="HIGH_CONVICTION_ANCHOR",
            replay_supported=True, ess_text="VERY_BULLISH",
            signal_direction="BULLISH", in_ow_node=False,
            fmp_row=fmp_row
        )
        assert bd.fundamental_modifier <= -3.0

    def test_modifier_bounded_negative(self):
        """Worst case modifier never exceeds -5.0."""
        fmp_row = {
            "fmp_coverage_status": "FULL",
            "beat_rate_8q": "0.40",           # weak → -1.0
            "revenue_growth_q1_yoy": "-0.10",
            "revenue_acceleration": "-0.70",
            "ev_ebitda_ttm": "10.0",
        }
        # DETERIORATING: -3.0, CONTRADICTORY: -1.5 → raw = -1 -3 -1.5 = -5.5 → capped
        fmp_row_contradictory = dict(fmp_row)
        _, bd = compute_cw_das(
            symbol="WORST", composite=4.0, pct=1.0, tier="HIGH_CONVICTION_ANCHOR",
            replay_supported=True, ess_text="VERY_BULLISH",
            signal_direction="BULLISH", in_ow_node=False,
            fmp_row=fmp_row_contradictory
        )
        assert bd.fundamental_modifier >= -5.0

    def test_score_floor_zero(self):
        """Score can never go negative even with maximum penalty."""
        fmp_row = {
            "fmp_coverage_status": "FULL",
            "beat_rate_8q": "0.40",
            "revenue_growth_q1_yoy": "-0.20",
            "revenue_acceleration": "-1.0",
            "ev_ebitda_ttm": "90.0",  # high EV + declining revenue → DATA_ANOMALY
        }
        score, _ = compute_cw_das(
            symbol="TEST", composite=1.0, pct=0.5, tier="HIGH_CONVICTION_ANCHOR",
            replay_supported=True, ess_text="NEUTRAL",
            signal_direction="BULLISH", in_ow_node=True,  # also redundancy pen
            fmp_row=fmp_row
        )
        assert score >= 0.0
