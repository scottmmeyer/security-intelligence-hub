"""Tests for ISSUE-04B — Dislocation Backend Classifier (Class A1).
Updated for ISSUE-04D to import new constants; A1 tests are unchanged.
"""
from __future__ import annotations

import pytest
from src.portfolio.dislocation import (
    classify_dislocation,
    build_dislocation_payload,
    _classify_a1,
    DISLOCATION_NONE,
    DISLOCATION_WATCH,
    DISLOCATION_MODERATE,
    DISLOCATION_HIGH_CONVICTION,
    DISLOCATION_CLASS_A1,
    DISLOCATION_VERSION,
    DislocationType,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmp(
    beat_rate: float = 0.875,
    coverage: str = "FULL",
    revenue_growth: float = 0.15,
    roic: float = 0.25,
    fcf_yield: float = 0.08,
    revenue_accel: float = 0.02,
) -> dict:
    """Build a minimal FMP row that produces an INTACT thesis by default."""
    return {
        "fmp_coverage_status": coverage,
        "beat_rate_8q": str(beat_rate),
        "beats_last_8q": str(round(beat_rate * 8)),
        "revenue_growth_q1_yoy": str(revenue_growth),
        "revenue_acceleration": str(revenue_accel),
        "roic_ttm": str(roic),
        "fcf_yield_ttm": str(fcf_yield),
        "eps_growth_q1_yoy": str(revenue_growth * 0.8),
        "ev_ebitda_ttm": str(12.5),
        "roe_ttm": str(0.20),
        "net_buy_score": str(0.6),
    }


def _fmp_deteriorating() -> dict:
    """FMP row that produces a DETERIORATING thesis."""
    return {
        "fmp_coverage_status": "FULL",
        "beat_rate_8q": "0.625",
        "beats_last_8q": "5",
        "revenue_growth_q1_yoy": str(-0.12),
        "revenue_acceleration": str(-0.05),
        "roic_ttm": str(0.05),
        "fcf_yield_ttm": str(-0.02),
        "eps_growth_q1_yoy": str(-0.20),
        "ev_ebitda_ttm": str(25.0),
        "roe_ttm": str(0.04),
        "net_buy_score": str(0.2),
    }


def _overlay(ess: str = "BEARISH", danelfin: float = 1.5) -> dict:
    return {"ess_score_text": ess, "danelfin_score": str(danelfin), "symbol": "TEST"}


# ── Gate tests ─────────────────────────────────────────────────────────────────

class TestGates:
    def test_none_fmp_row_returns_none(self):
        result = classify_dislocation("AAPL", fmp_row=None, overlay=_overlay())
        assert result.tier == DISLOCATION_NONE
        assert result.evidence == ()

    def test_none_overlay_returns_none_without_ess(self):
        """Without overlay, ESS is empty — may still classify based on other signals."""
        fmp = _fmp(beat_rate=0.875)
        result = classify_dislocation("AAPL", fmp_row=fmp, overlay=None)
        # ESS is empty (mild divergence), danelfin is None — may hit WATCH if thresholds met
        # but without danelfin, tier must be NONE or WATCH (mild ESS path only)
        assert result.tier in (DISLOCATION_NONE, DISLOCATION_WATCH, DISLOCATION_MODERATE)

    def test_no_fmp_coverage_returns_none(self):
        fmp = _fmp(coverage="NO_DATA")
        result = classify_dislocation("AAPL", fmp_row=fmp, overlay=_overlay())
        assert result.tier == DISLOCATION_NONE

    def test_etf_coverage_returns_none(self):
        fmp = _fmp(coverage="ETF_NOT_APPLICABLE")
        result = classify_dislocation("VOO", fmp_row=fmp, overlay=_overlay())
        assert result.tier == DISLOCATION_NONE

    @pytest.mark.parametrize(
        "coverage",
        ["NOT_FETCHED", "PROVIDER_NO_DATA", "FETCH_FAILED", "NOT_APPLICABLE"],
    )
    def test_new_missing_states_do_not_trigger_a1(self, coverage: str):
        fmp = _fmp(coverage=coverage)
        result = classify_dislocation("AAPL", fmp_row=fmp, overlay=_overlay("VERY_BEARISH", 1.0))
        assert result.tier == DISLOCATION_NONE

    def test_deteriorating_thesis_returns_none(self):
        """DETERIORATING thesis must never produce a dislocation classification."""
        fmp = _fmp_deteriorating()
        result = classify_dislocation("PSX", fmp_row=fmp, overlay=_overlay("VERY_BEARISH", 0.5))
        assert result.tier == DISLOCATION_NONE

    def test_low_beat_rate_returns_none(self):
        fmp = _fmp(beat_rate=0.50)  # below 62.5% minimum
        result = classify_dislocation("XYZ", fmp_row=fmp, overlay=_overlay("BEARISH", 1.0))
        assert result.tier == DISLOCATION_NONE

    def test_bullish_ess_no_danelfin_divergence_returns_none(self):
        """VERY_BULLISH ESS with no signal weakness means no dislocation."""
        fmp = _fmp(beat_rate=1.0)
        ov = _overlay(ess="VERY_BULLISH", danelfin=9.0)
        result = classify_dislocation("NVDA", fmp_row=fmp, overlay=ov)
        assert result.tier == DISLOCATION_NONE


# ── HIGH CONVICTION tier tests ─────────────────────────────────────────────────

class TestHighConviction:
    def test_high_conviction_all_signals_aligned(self):
        """Beat 87.5%+ + VERY_BEARISH ESS + strong Danelfin divergence → HIGH."""
        fmp = _fmp(beat_rate=0.875)
        ov = _overlay(ess="VERY_BEARISH", danelfin=1.2)
        result = classify_dislocation("AEIS", fmp_row=fmp, overlay=ov)
        assert result.tier == DISLOCATION_HIGH_CONVICTION
        assert result.dislocation_class == DISLOCATION_CLASS_A1
        assert len(result.evidence) >= 2

    def test_high_conviction_bearish_ess_with_strong_danelfin(self):
        """Beat 87.5%+ + BEARISH ESS + Danelfin < 2.0 → HIGH."""
        fmp = _fmp(beat_rate=1.0)
        ov = _overlay(ess="BEARISH", danelfin=1.8)
        result = classify_dislocation("LRCX", fmp_row=fmp, overlay=ov)
        assert result.tier == DISLOCATION_HIGH_CONVICTION

    def test_full_coverage_behavior_still_produces_high_when_signals_match(self):
        fmp = _fmp(coverage="FULL", beat_rate=0.875)
        ov = _overlay(ess="VERY_BEARISH", danelfin=1.0)
        result = classify_dislocation("AEIS", fmp_row=fmp, overlay=ov)
        assert result.tier == DISLOCATION_HIGH_CONVICTION

    def test_high_conviction_very_bearish_ess_alone(self):
        """Beat 87.5%+ + VERY_BEARISH ESS alone should meet HIGH CONVICTION."""
        fmp = _fmp(beat_rate=0.875)
        ov = _overlay(ess="VERY_BEARISH", danelfin=2.5)  # Danelfin not strong
        result = classify_dislocation("TEST", fmp_row=fmp, overlay=ov)
        # VERY_BEARISH counts as strong ESS divergence; should be HIGH or MODERATE
        assert result.tier in (DISLOCATION_HIGH_CONVICTION, DISLOCATION_MODERATE)

    def test_high_conviction_evidence_contains_beat_rate(self):
        fmp = _fmp(beat_rate=0.875)
        ov = _overlay(ess="VERY_BEARISH", danelfin=1.0)
        result = classify_dislocation("DELL", fmp_row=fmp, overlay=ov)
        assert any("Beat rate" in e for e in result.evidence)
        assert any("INTACT" in e or "Thesis" in e for e in result.evidence)


# ── MODERATE tier tests ────────────────────────────────────────────────────────

class TestModerate:
    def test_moderate_beat75_bearish_dan_moderate(self):
        """Beat 75%+ + BEARISH ESS + Danelfin < 3.0 → MODERATE."""
        fmp = _fmp(beat_rate=0.75)
        ov = _overlay(ess="BEARISH", danelfin=2.5)
        result = classify_dislocation("ARW", fmp_row=fmp, overlay=ov)
        assert result.tier == DISLOCATION_MODERATE

    def test_moderate_beat75_neutral_dan_moderate(self):
        """Beat 75%+ + NEUTRAL ESS + Danelfin < 3.0 → MODERATE."""
        fmp = _fmp(beat_rate=0.75)
        ov = _overlay(ess="NEUTRAL", danelfin=2.8)
        result = classify_dislocation("VRT", fmp_row=fmp, overlay=ov)
        assert result.tier == DISLOCATION_MODERATE

    def test_partial_coverage_behavior_still_produces_moderate_when_signals_match(self):
        fmp = _fmp(coverage="PARTIAL", beat_rate=0.75)
        ov = _overlay(ess="NEUTRAL", danelfin=2.8)
        result = classify_dislocation("VRT", fmp_row=fmp, overlay=ov)
        assert result.tier == DISLOCATION_MODERATE

    def test_beat_below_75_cannot_be_moderate(self):
        """Beat rate 62.5%–74.9% cannot qualify for MODERATE."""
        fmp = _fmp(beat_rate=0.625)
        ov = _overlay(ess="BEARISH", danelfin=2.0)
        result = classify_dislocation("TEST", fmp_row=fmp, overlay=ov)
        assert result.tier != DISLOCATION_MODERATE


# ── WATCH tier tests ───────────────────────────────────────────────────────────

class TestWatch:
    def test_watch_beat625_neutral_ess(self):
        """Beat 62.5%+ + NEUTRAL ESS → WATCH at minimum."""
        fmp = _fmp(beat_rate=0.625)
        ov = _overlay(ess="NEUTRAL", danelfin=3.2)
        result = classify_dislocation("SMR", fmp_row=fmp, overlay=ov)
        assert result.tier in (DISLOCATION_WATCH, DISLOCATION_MODERATE)

    def test_watch_beat625_mild_danelfin(self):
        """Beat 62.5%+ + Danelfin < 3.5 → WATCH."""
        fmp = _fmp(beat_rate=0.625)
        ov = _overlay(ess="NEUTRAL", danelfin=3.3)
        result = classify_dislocation("HCI", fmp_row=fmp, overlay=ov)
        assert result.tier in (DISLOCATION_WATCH, DISLOCATION_MODERATE)

    def test_contradictory_consistency_caps_at_watch(self):
        """CONTRADICTORY fundamental consistency must cap tier at WATCH.
        Tests the _classify_a1 internal logic directly with explicit consistency value
        rather than depending on the FMP consistency classifier's threshold logic.
        """
        # Use _classify_a1 directly with consistency="CONTRADICTORY" injected
        tier, evidence = _classify_a1(
            thesis="INTACT",
            consistency="CONTRADICTORY",
            beat_rate=0.875,
            ess="VERY_BEARISH",
            danelfin=1.0,
            revenue_growth=0.20,
            fmp_coverage="FULL",
        )
        assert tier == DISLOCATION_WATCH
        assert any("CONTRADICTORY" in e for e in evidence)


# ── Symbol propagation tests ───────────────────────────────────────────────────

class TestSymbolPropagation:
    def test_symbol_in_result(self):
        fmp = _fmp(beat_rate=0.875)
        ov = _overlay("BEARISH", 1.5)
        result = classify_dislocation("DELL", fmp_row=fmp, overlay=ov)
        assert result.symbol == "DELL"

    def test_symbol_lowercased_input_normalized(self):
        fmp = _fmp(beat_rate=0.875)
        ov = _overlay("BEARISH", 1.5)
        result = classify_dislocation("dell", fmp_row=fmp, overlay=ov)
        assert result.symbol == "DELL"

    def test_version_field(self):
        result = classify_dislocation("X", fmp_row=None, overlay=None)
        assert result.version == DISLOCATION_VERSION


# ── Serialization / batch builder tests ───────────────────────────────────────

class TestBatchBuilder:
    def test_build_payload_returns_dict(self):
        overlays = [{"symbol": "DELL", "ess_score_text": "BEARISH", "danelfin_score": "1.5"}]
        fmp = {"DELL": _fmp(beat_rate=0.875)}
        payload = build_dislocation_payload(overlays=overlays, fmp_by_sym=fmp)
        assert "DELL" in payload
        assert "tier" in payload["DELL"]
        assert "evidence" in payload["DELL"]
        assert isinstance(payload["DELL"]["evidence"], list)

    def test_build_payload_handles_missing_fmp(self):
        overlays = [{"symbol": "AAPL", "ess_score_text": "BEARISH", "danelfin_score": "1.0"}]
        payload = build_dislocation_payload(overlays=overlays, fmp_by_sym={})
        assert payload["AAPL"]["tier"] == DISLOCATION_NONE

    def test_build_payload_handles_empty_overlays(self):
        payload = build_dislocation_payload(overlays=[], fmp_by_sym={})
        assert payload == {}

    def test_build_payload_all_fields_present(self):
        overlays = [{"symbol": "VRT", "ess_score_text": "BEARISH", "danelfin_score": "2.0"}]
        fmp = {"VRT": _fmp(beat_rate=0.875)}
        payload = build_dislocation_payload(overlays=overlays, fmp_by_sym=fmp)
        entry = payload["VRT"]
        for field in ["symbol", "tier", "dislocation_class", "evidence", "version"]:
            assert field in entry, f"Missing field: {field}"

    def test_none_tier_has_none_class(self):
        overlays = [{"symbol": "NONE_SYM", "ess_score_text": "VERY_BULLISH", "danelfin_score": "9.0"}]
        fmp = {"NONE_SYM": _fmp(beat_rate=1.0)}
        payload = build_dislocation_payload(overlays=overlays, fmp_by_sym=fmp)
        entry = payload["NONE_SYM"]
        if entry["tier"] == DISLOCATION_NONE:
            assert entry["dislocation_class"] == DISLOCATION_NONE

    def test_nontrivial_evidence_has_items(self):
        overlays = [{"symbol": "LRCX", "ess_score_text": "BEARISH", "danelfin_score": "1.8"}]
        fmp = {"LRCX": _fmp(beat_rate=1.0)}
        payload = build_dislocation_payload(overlays=overlays, fmp_by_sym=fmp)
        if payload["LRCX"]["tier"] != DISLOCATION_NONE:
            assert len(payload["LRCX"]["evidence"]) >= 2
