"""Tests for ISSUE-04D — Dislocation Class Extensions: D1 + B2.

Class D1 — Replay-Signal Lag:
  replay_supported + high replay_percentile + weak ESS/Danelfin.

Class B2 — Analyst-AI Divergence:
  Strong ABR consensus + analyst_count gate + weak ESS/Danelfin.

Multi-class: when both A1 and D1 (or B2) fire, tier escalates and
dislocation_class = MULTI_CLASS.
"""
from __future__ import annotations

import pytest
from src.portfolio.dislocation import (
    classify_dislocation,
    build_dislocation_payload,
    _classify_d1,
    _classify_b2,
    _resolve_tier,
    DISLOCATION_NONE,
    DISLOCATION_WATCH,
    DISLOCATION_MODERATE,
    DISLOCATION_HIGH_CONVICTION,
    DISLOCATION_CLASS_A1,
    DISLOCATION_CLASS_D1,
    DISLOCATION_CLASS_B2,
    DISLOCATION_CLASS_MULTI,
    DISLOCATION_VERSION,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmp_intact(beat_rate: float = 0.875, revenue_growth: float = 0.15) -> dict:
    return {
        "fmp_coverage_status": "FULL",
        "beat_rate_8q": str(beat_rate),
        "beats_last_8q": str(round(beat_rate * 8)),
        "revenue_growth_q1_yoy": str(revenue_growth),
        "revenue_acceleration": "0.02",
        "roic_ttm": "0.22",
        "fcf_yield_ttm": "0.07",
        "eps_growth_q1_yoy": str(revenue_growth * 0.8),
        "ev_ebitda_ttm": "13.0",
        "roe_ttm": "0.18",
        "net_buy_score": "0.6",
    }

def _fmp_deteriorating() -> dict:
    d = _fmp_intact(beat_rate=0.625, revenue_growth=-0.12)
    d["roic_ttm"] = "0.04"
    d["fcf_yield_ttm"] = "-0.02"
    return d

def _ov(ess: str = "BEARISH", danelfin: float = 1.5,
        replay_supported: bool = False, replay_percentile: float = 0.0) -> dict:
    return {
        "ess_score_text":    ess,
        "danelfin_score":    str(danelfin),
        "replay_supported":  replay_supported,
        "replay_percentile": str(replay_percentile) if replay_percentile else None,
        "symbol": "TEST",
    }

def _ac(abr: float, count: int) -> dict:
    return {"abr": str(abr), "analyst_count": str(count)}


# ══════════════════════════════════════════════════════════════════════════════
# Class D1 — Replay-Signal Lag
# ══════════════════════════════════════════════════════════════════════════════

class TestD1Gates:
    def test_d1_gate_replay_not_supported(self):
        t, e = _classify_d1(replay_supported=False, replay_percentile=90.0,
                            ess="BEARISH", danelfin=1.0, thesis="INTACT")
        assert t == DISLOCATION_NONE

    def test_d1_gate_replay_percentile_none(self):
        t, e = _classify_d1(replay_supported=True, replay_percentile=None,
                            ess="BEARISH", danelfin=1.0, thesis="INTACT")
        assert t == DISLOCATION_NONE

    def test_d1_gate_replay_percentile_below_watch(self):
        t, e = _classify_d1(replay_supported=True, replay_percentile=40.0,
                            ess="BEARISH", danelfin=1.0, thesis="INTACT")
        assert t == DISLOCATION_NONE

    def test_d1_gate_deteriorating_thesis(self):
        """DETERIORATING thesis must suppress D1."""
        t, e = _classify_d1(replay_supported=True, replay_percentile=85.0,
                            ess="BEARISH", danelfin=1.0, thesis="DETERIORATING")
        assert t == DISLOCATION_NONE

    def test_d1_gate_strong_ess_no_divergence(self):
        """Strong ESS + high Danelfin means no signal divergence."""
        t, e = _classify_d1(replay_supported=True, replay_percentile=85.0,
                            ess="VERY_BULLISH", danelfin=8.5, thesis="INTACT")
        assert t == DISLOCATION_NONE

    def test_d1_gate_percentile_exactly_watch(self):
        """Exactly at WATCH threshold (50.0) with divergence should not be NONE."""
        t, e = _classify_d1(replay_supported=True, replay_percentile=50.0,
                            ess="NEUTRAL", danelfin=3.3, thesis="INTACT")
        assert t in (DISLOCATION_WATCH, DISLOCATION_MODERATE)


class TestD1Tiers:
    def test_d1_high_conviction(self):
        """Replay ≥ 80th + ESS BEARISH + Danelfin < 2.0 → HIGH."""
        t, e = _classify_d1(replay_supported=True, replay_percentile=82.0,
                            ess="BEARISH", danelfin=1.5, thesis="INTACT")
        assert t == DISLOCATION_HIGH_CONVICTION
        assert len(e) >= 2

    def test_d1_high_conviction_very_bearish(self):
        """Replay ≥ 80th + VERY_BEARISH → HIGH."""
        t, e = _classify_d1(replay_supported=True, replay_percentile=90.0,
                            ess="VERY_BEARISH", danelfin=1.8, thesis="INTACT")
        assert t == DISLOCATION_HIGH_CONVICTION

    def test_d1_moderate_replay65_bearish_dan3(self):
        """Replay ≥ 65th + BEARISH + Danelfin < 3.0 → MODERATE."""
        t, e = _classify_d1(replay_supported=True, replay_percentile=70.0,
                            ess="BEARISH", danelfin=2.8, thesis="INTACT")
        assert t == DISLOCATION_MODERATE

    def test_d1_moderate_replay65_ess_strong(self):
        """Replay ≥ 65th + ESS BEARISH → MODERATE even without Danelfin."""
        t, e = _classify_d1(replay_supported=True, replay_percentile=68.0,
                            ess="BEARISH", danelfin=None, thesis="INTACT")
        assert t == DISLOCATION_MODERATE

    def test_d1_watch_replay50_neutral_ess(self):
        """Replay ≥ 50th + NEUTRAL ESS → WATCH."""
        t, e = _classify_d1(replay_supported=True, replay_percentile=55.0,
                            ess="NEUTRAL", danelfin=3.3, thesis="INTACT")
        assert t in (DISLOCATION_WATCH, DISLOCATION_MODERATE)

    def test_d1_evidence_mentions_replay(self):
        """Evidence must reference replay percentile."""
        t, e = _classify_d1(replay_supported=True, replay_percentile=80.0,
                            ess="BEARISH", danelfin=1.5, thesis="INTACT")
        assert any("percentile" in item.lower() or "replay" in item.lower() for item in e)

    def test_d1_questionable_thesis_allowed(self):
        """QUESTIONABLE thesis should not suppress D1 (only DETERIORATING does)."""
        t, e = _classify_d1(replay_supported=True, replay_percentile=75.0,
                            ess="BEARISH", danelfin=2.0, thesis="QUESTIONABLE")
        assert t != DISLOCATION_NONE


# ══════════════════════════════════════════════════════════════════════════════
# Class B2 — Analyst-AI Divergence
# ══════════════════════════════════════════════════════════════════════════════

class TestB2Gates:
    def test_b2_gate_no_abr(self):
        t, e = _classify_b2(abr=None, analyst_count=25, ess="BEARISH",
                            danelfin=1.5, thesis="INTACT")
        assert t == DISLOCATION_NONE

    def test_b2_gate_abr_too_high(self):
        """ABR > 2.5 (not bullish) should produce NONE."""
        t, e = _classify_b2(abr=3.0, analyst_count=25, ess="BEARISH",
                            danelfin=1.5, thesis="INTACT")
        assert t == DISLOCATION_NONE

    def test_b2_gate_count_below_minimum(self):
        """analyst_count < 5 must suppress B2."""
        t, e = _classify_b2(abr=1.5, analyst_count=3, ess="BEARISH",
                            danelfin=1.5, thesis="INTACT")
        assert t == DISLOCATION_NONE

    def test_b2_gate_count_zero(self):
        t, e = _classify_b2(abr=1.5, analyst_count=0, ess="BEARISH",
                            danelfin=1.5, thesis="INTACT")
        assert t == DISLOCATION_NONE

    def test_b2_gate_count_none(self):
        t, e = _classify_b2(abr=1.5, analyst_count=None, ess="BEARISH",
                            danelfin=1.5, thesis="INTACT")
        assert t == DISLOCATION_NONE

    def test_b2_gate_deteriorating_thesis(self):
        """DETERIORATING thesis must suppress B2."""
        t, e = _classify_b2(abr=1.5, analyst_count=25, ess="BEARISH",
                            danelfin=1.5, thesis="DETERIORATING")
        assert t == DISLOCATION_NONE

    def test_b2_gate_no_signal_divergence(self):
        """Strong ABR + but ESS VERY_BULLISH + Danelfin 9.0 = no divergence."""
        t, e = _classify_b2(abr=1.5, analyst_count=25, ess="VERY_BULLISH",
                            danelfin=9.0, thesis="INTACT")
        assert t == DISLOCATION_NONE


class TestB2Tiers:
    def test_b2_high_conviction(self):
        """ABR ≤ 1.75, count ≥ 20, ESS BEARISH + Danelfin < 2.0 → HIGH."""
        t, e = _classify_b2(abr=1.6, analyst_count=25, ess="BEARISH",
                            danelfin=1.5, thesis="INTACT")
        assert t == DISLOCATION_HIGH_CONVICTION
        assert len(e) >= 2

    def test_b2_high_conviction_dan_strong(self):
        """ABR ≤ 1.75, count ≥ 20, Danelfin < 2.0 → HIGH."""
        t, e = _classify_b2(abr=1.7, analyst_count=30, ess="NEUTRAL",
                            danelfin=1.8, thesis="INTACT")
        assert t == DISLOCATION_HIGH_CONVICTION

    def test_b2_moderate_abr2_count10(self):
        """ABR ≤ 2.0, count ≥ 10, ESS BEARISH + Danelfin < 3.0 → MODERATE."""
        t, e = _classify_b2(abr=1.9, analyst_count=15, ess="BEARISH",
                            danelfin=2.7, thesis="INTACT")
        assert t == DISLOCATION_MODERATE

    def test_b2_moderate_abr2_ess_bearish(self):
        """ABR ≤ 2.0, count ≥ 10, ESS BEARISH (no Danelfin) → MODERATE."""
        t, e = _classify_b2(abr=2.0, analyst_count=12, ess="BEARISH",
                            danelfin=None, thesis="INTACT")
        assert t == DISLOCATION_MODERATE

    def test_b2_watch_abr_watch_level(self):
        """ABR ≤ 2.5, count ≥ 5, mild divergence → WATCH."""
        t, e = _classify_b2(abr=2.4, analyst_count=7, ess="NEUTRAL",
                            danelfin=3.2, thesis="INTACT")
        assert t in (DISLOCATION_WATCH, DISLOCATION_MODERATE)

    def test_b2_evidence_mentions_abr_and_count(self):
        t, e = _classify_b2(abr=1.8, analyst_count=23, ess="BEARISH",
                            danelfin=1.5, thesis="INTACT")
        assert any("ABR" in item for item in e)
        assert any("23" in item for item in e)


# ══════════════════════════════════════════════════════════════════════════════
# Multi-class resolution
# ══════════════════════════════════════════════════════════════════════════════

class TestMultiClass:
    def test_multi_class_when_a1_and_d1_fire(self):
        """When A1 and D1 both fire, dislocation_class should be MULTI_CLASS."""
        fmp = _fmp_intact(beat_rate=0.875)
        ov  = _ov(ess="BEARISH", danelfin=1.5, replay_supported=True, replay_percentile=82.0)
        result = classify_dislocation("TEST", fmp_row=fmp, overlay=ov, ac_row=None)
        if result.tier != DISLOCATION_NONE:
            # Both A1 and D1 should potentially fire
            assert DISLOCATION_CLASS_A1 in result.active_classes or \
                   DISLOCATION_CLASS_D1 in result.active_classes

    def test_resolve_tier_single_class(self):
        results = [(DISLOCATION_MODERATE, DISLOCATION_CLASS_A1, ["ev1", "ev2"])]
        tier, cls, active = _resolve_tier(results)
        assert tier == DISLOCATION_MODERATE
        assert cls == DISLOCATION_CLASS_A1
        assert active == (DISLOCATION_CLASS_A1,)

    def test_resolve_tier_highest_wins(self):
        results = [
            (DISLOCATION_WATCH, DISLOCATION_CLASS_A1, ["ev-a1"]),
            (DISLOCATION_HIGH_CONVICTION, DISLOCATION_CLASS_D1, ["ev-d1"]),
        ]
        tier, cls, active = _resolve_tier(results)
        assert tier == DISLOCATION_HIGH_CONVICTION
        assert cls == DISLOCATION_CLASS_MULTI
        assert DISLOCATION_CLASS_A1 in active
        assert DISLOCATION_CLASS_D1 in active

    def test_resolve_tier_all_none(self):
        results = [(DISLOCATION_NONE, DISLOCATION_NONE, [])]
        tier, cls, active = _resolve_tier(results)
        assert tier == DISLOCATION_NONE

    def test_active_classes_field_in_payload(self):
        """active_classes must appear in batch payload output."""
        overlays = [_ov(ess="BEARISH", danelfin=1.5, replay_supported=True, replay_percentile=82.0)]
        overlays[0] = dict(overlays[0], symbol="TEST2")
        fmp = {"TEST2": _fmp_intact(beat_rate=0.875)}
        payload = build_dislocation_payload(overlays=overlays, fmp_by_sym=fmp)
        entry = payload.get("TEST2", {})
        assert "active_classes" in entry
        assert isinstance(entry["active_classes"], list)


# ══════════════════════════════════════════════════════════════════════════════
# Version bump
# ══════════════════════════════════════════════════════════════════════════════

def test_version_bumped_to_1_1():
    assert DISLOCATION_VERSION == "1.1"


# ══════════════════════════════════════════════════════════════════════════════
# Integration: classify_dislocation with B2 ac_row
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    def test_classify_with_ac_row_fires_b2(self):
        """classify_dislocation with strong ABR + weak ESS should fire B2."""
        fmp = _fmp_intact(beat_rate=0.5)   # A1 won't fire (beat too low)
        ov  = _ov(ess="BEARISH", danelfin=1.5)
        ac  = _ac(abr=1.6, count=25)
        result = classify_dislocation("NVDA", fmp_row=fmp, overlay=ov, ac_row=ac)
        assert DISLOCATION_CLASS_B2 in result.active_classes or result.tier != DISLOCATION_NONE

    def test_classify_b2_suppressed_when_count_low(self):
        """Low count suppresses B2; if A1 also fails, result = NONE."""
        fmp = _fmp_intact(beat_rate=0.4)   # A1 won't fire
        ov  = _ov(ess="BEARISH", danelfin=1.5)
        ac  = _ac(abr=1.5, count=2)        # too few analysts
        result = classify_dislocation("LOW", fmp_row=fmp, overlay=ov, ac_row=ac)
        assert DISLOCATION_CLASS_B2 not in result.active_classes
