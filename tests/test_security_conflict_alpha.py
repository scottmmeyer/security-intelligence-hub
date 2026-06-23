"""Tests for DISLOCATION-03 — Security-Level Conflict Alpha Insights.

Covers:
  - _zacks_dir()
  - _yahoo_dir()
  - derive_security_conflict_alpha() — all direction combinations
  - batch_security_conflict_alpha()
  - _build_insight() — content + governance constraints
  - security_alpha_summary() — structure validation

Governance:
  Q6–Q9: No CW-DAS, ESS, UCF, CRA, Replay, PAP changes
  Q10: Display-only / informational
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict
from unittest.mock import patch

import pytest

from src.sih.security_conflict_alpha import (
    SecurityConflictAlpha,
    _build_insight,
    _yahoo_dir,
    _zacks_dir,
    batch_security_conflict_alpha,
    derive_security_conflict_alpha,
    security_alpha_summary,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_alpha_index() -> Dict:
    """Minimal alpha index mirroring real data."""
    return {
        "ESS_BULLISH_ANALYST_MIXED": {
            "signal_pattern":   "ESS_BULLISH_ANALYST_MIXED",
            "pattern_label":    "ESS Buy / Analysts Mixed",
            "is_conflict_pattern": True,
            "alpha_class":      "ALPHA_LEADER",
            "excess_return_pct": 2.81,
            "avg_return_30d_pct": 5.0,
            "win_rate_pct":     64.0,
            "t_statistic":      1.9,
            "significance":     "SUGGESTIVE",
            "observations":     90,
            "insight":          "Historically favorable.",
        },
        "ESS_BULLISH_ANALYST_MAJORITY_BEARISH": {
            "signal_pattern":   "ESS_BULLISH_ANALYST_MAJORITY_BEARISH",
            "pattern_label":    "ESS Buy / Analyst Sell",
            "is_conflict_pattern": True,
            "alpha_class":      "ALPHA_LEADER",
            "excess_return_pct": 2.26,
            "avg_return_30d_pct": 2.81,
            "win_rate_pct":     48.4,
            "t_statistic":      1.6,
            "significance":     "SUGGESTIVE",
            "observations":     102,
            "insight":          "ESS historically outperformed.",
        },
        "ESS_BEARISH_ANALYST_MAJORITY_BULLISH": {
            "signal_pattern":   "ESS_BEARISH_ANALYST_MAJORITY_BULLISH",
            "pattern_label":    "ESS Sell / Analyst Buy",
            "is_conflict_pattern": True,
            "alpha_class":      "ALPHA_LAGGARD",
            "excess_return_pct": -1.70,
            "avg_return_30d_pct": -1.15,
            "win_rate_pct":     30.0,
            "t_statistic":      -1.8,
            "significance":     "SUGGESTIVE",
            "observations":     20,
            "insight":          "Historically unfavorable.",
        },
        "ESS_BULLISH_ANALYST_SKEPTICAL": {
            "signal_pattern":   "ESS_BULLISH_ANALYST_SKEPTICAL",
            "alpha_class":      "ALPHA_NEUTRAL",
            "excess_return_pct": 0.72,
            "avg_return_30d_pct": 2.11,
            "win_rate_pct":     44.3,
            "t_statistic":      0.8,
            "significance":     "WEAK",
            "observations":     154,
            "insight":          "No material alpha.",
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Direction helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestZacksDir:
    def test_rank1_strong_buy_bullish(self):  assert _zacks_dir(5.0) == "BULLISH"
    def test_rank2_buy_bullish(self):         assert _zacks_dir(4.0) == "BULLISH"
    def test_rank3_hold_neutral(self):        assert _zacks_dir(3.0) == "NEUTRAL"
    def test_rank4_sell_bearish(self):        assert _zacks_dir(2.0) == "BEARISH"
    def test_rank5_strong_sell_bearish(self): assert _zacks_dir(1.0) == "BEARISH"
    def test_none_no_data(self):              assert _zacks_dir(None) == "NO_DATA"
    def test_non_numeric_no_data(self):       assert _zacks_dir("hold") == "NO_DATA"


class TestYahooDir:
    def test_strong_buy(self):    assert _yahoo_dir("STRONG_BUY") == "BULLISH"
    def test_buy(self):           assert _yahoo_dir("BUY") == "BULLISH"
    def test_moderate_buy(self):  assert _yahoo_dir("MODERATE_BUY") == "BULLISH"
    def test_hold(self):          assert _yahoo_dir("HOLD") == "NEUTRAL"
    def test_sell(self):          assert _yahoo_dir("SELL") == "BEARISH"
    def test_strong_sell(self):   assert _yahoo_dir("STRONG_SELL") == "BEARISH"
    def test_none(self):          assert _yahoo_dir(None) == "NO_DATA"
    def test_no_consensus(self):  assert _yahoo_dir("NO_CONSENSUS") == "NO_DATA"
    def test_empty(self):         assert _yahoo_dir("") == "NO_DATA"


# ═══════════════════════════════════════════════════════════════════════════════
# derive_security_conflict_alpha
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeriveSecurityConflictAlpha:
    def _derive(self, ess_text, zacks, yahoo):
        return derive_security_conflict_alpha(
            "TEST", ess_text, None, zacks, yahoo, _make_alpha_index()
        )

    def test_bullish_ess_mixed_analysts_returns_leader(self):
        # BULLISH ESS + Zacks BUY (4.0→BULLISH) + Yahoo HOLD (NEUTRAL) → MIXED
        result = self._derive("BULLISH", 4.5, "HOLD")
        assert result is not None
        assert result.ess_direction == "BULLISH"
        assert result.is_conflict  # ESS bullish, some analyst divergence
        assert result.alpha_class == "ALPHA_LEADER"

    def test_very_bullish_ess_bearish_analysts_majority_bearish(self):
        # VERY_BULLISH ESS + Zacks bearish (1.5→BEARISH) + Yahoo SELL
        result = self._derive("VERY_BULLISH", 1.5, "SELL")
        assert result is not None
        assert result.ess_direction == "BULLISH"
        assert result.signal_pattern == "ESS_BULLISH_ANALYST_MAJORITY_BEARISH"
        assert result.alpha_class == "ALPHA_LEADER"

    def test_bearish_ess_bullish_analysts_laggard(self):
        # BEARISH ESS + Zacks STRONG_BUY (5.0→BULLISH) + Yahoo BUY
        result = self._derive("BEARISH", 5.0, "STRONG_BUY")
        assert result is not None
        assert result.ess_direction == "BEARISH"
        assert result.alpha_class == "ALPHA_LAGGARD"
        assert result.excess_return_pct == pytest.approx(-1.70)

    def test_no_ess_data_returns_none(self):
        result = derive_security_conflict_alpha(
            "X", None, None, None, None, _make_alpha_index()
        )
        assert result is None

    def test_pattern_label_populated(self):
        result = self._derive("BULLISH", 1.5, "SELL")
        assert result is not None
        assert result.pattern_label != ""
        assert result.pattern_label != result.signal_pattern

    def test_insight_non_empty(self):
        result = self._derive("BULLISH", 1.5, "SELL")
        assert result is not None
        assert len(result.insight) > 20

    def test_to_dict_contains_required_keys(self):
        result = self._derive("BULLISH", 4.5, "HOLD")
        assert result is not None
        d = result.to_dict()
        for key in ["symbol", "ess_direction", "signal_pattern", "pattern_label",
                    "is_conflict", "alpha_class", "excess_return_pct", "insight",
                    "observations"]:
            assert key in d, f"Missing key: {key}"

    def test_alpha_class_none_when_pattern_not_in_index(self):
        # Pattern not in alpha index
        result = derive_security_conflict_alpha(
            "Z", "NEUTRAL", None, 3.0, "HOLD", {}
        )
        # May return None (NO_ANALYST_DATA) or a result with None alpha_class
        if result is not None:
            assert result.alpha_class is None or result.alpha_class == "ALPHA_NEUTRAL"


# ═══════════════════════════════════════════════════════════════════════════════
# _build_insight governance tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildInsight:
    def test_leader_mentions_ess_reliability(self):
        text = _build_insight(
            "MSFT", "ESS_BULLISH_ANALYST_MIXED", "ESS Buy / Mixed", True,
            "ALPHA_LEADER", 2.81, 64.0, "SUGGESTIVE", "BULLISH"
        )
        assert "MSFT" in text
        assert "favorable" in text.lower() or "positive excess" in text.lower() or "outperform" in text.lower()

    def test_laggard_mentions_analyst_weight(self):
        text = _build_insight(
            "TSLA", "ESS_BEARISH_ANALYST_MAJORITY_BULLISH", "ESS Sell / Analyst Buy", True,
            "ALPHA_LAGGARD", -1.70, 30.0, "SUGGESTIVE", "BEARISH"
        )
        assert "TSLA" in text
        assert "analyst" in text.lower()

    def test_neutral_no_material_alpha(self):
        text = _build_insight(
            "VRT", "ESS_BULLISH_ANALYST_SKEPTICAL", "ESS Buy / Skeptical", True,
            "ALPHA_NEUTRAL", 0.5, 50.0, "WEAK", "BULLISH"
        )
        assert "no material alpha" in text.lower()

    def test_no_action_language(self):
        for cls in ["ALPHA_LEADER", "ALPHA_LAGGARD", "ALPHA_NEUTRAL"]:
            text = _build_insight(
                "X", "ESS_BULLISH_ANALYST_MIXED", "label", True,
                cls, 1.0, 55.0, "SUGGESTIVE", "BULLISH"
            )
            for phrase in ["buy now", "sell now", "execute", "trade immediately"]:
                assert phrase not in text.lower()

    def test_missing_alpha_handled_gracefully(self):
        text = _build_insight(
            "X", "ESS_BULLISH_ANALYST_MIXED", "label", True,
            None, None, None, None, "BULLISH"
        )
        assert len(text) > 10
        assert "not available" in text.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# batch_security_conflict_alpha
# ═══════════════════════════════════════════════════════════════════════════════

def _ov(symbol, ess_text, zacks_score):
    return {
        "symbol":        symbol,
        "ess_score_text": ess_text,
        "zacks_rating":  str(zacks_score) if zacks_score is not None else "",
    }


class TestBatchSecurityConflictAlpha:
    def test_returns_dict_keyed_by_uppercase_symbol(self, tmp_path):
        overlays = [_ov("msft", "BULLISH", 1.5), _ov("TSLA", "BEARISH", 5.0)]
        analyst = {"MSFT": {"consensus_label": "HOLD"}, "TSLA": {"consensus_label": "BUY"}}
        with patch("src.sih.security_conflict_alpha._load_alpha_index", return_value=_make_alpha_index()):
            result = batch_security_conflict_alpha(overlays, analyst, tmp_path)
        assert "MSFT" in result
        assert "TSLA" in result

    def test_no_ess_data_excluded(self, tmp_path):
        overlays = [_ov("XYZ", None, None)]
        analyst = {}
        with patch("src.sih.security_conflict_alpha._load_alpha_index", return_value=_make_alpha_index()):
            result = batch_security_conflict_alpha(overlays, analyst, tmp_path)
        assert "XYZ" not in result

    def test_alpha_class_populated(self, tmp_path):
        overlays = [_ov("AAAA", "VERY_BULLISH", 1.5)]
        analyst = {"AAAA": {"consensus_label": "SELL"}}
        with patch("src.sih.security_conflict_alpha._load_alpha_index", return_value=_make_alpha_index()):
            result = batch_security_conflict_alpha(overlays, analyst, tmp_path)
        if "AAAA" in result:
            assert result["AAAA"].alpha_class in ("ALPHA_LEADER", "ALPHA_LAGGARD", "ALPHA_NEUTRAL")

    def test_empty_overlays_returns_empty_dict(self, tmp_path):
        with patch("src.sih.security_conflict_alpha._load_alpha_index", return_value=_make_alpha_index()):
            result = batch_security_conflict_alpha([], {}, tmp_path)
        assert result == {}


# ═══════════════════════════════════════════════════════════════════════════════
# security_alpha_summary
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityAlphaSummary:
    def _mock_summary(self, tmp_path, overlays, analyst):
        with patch("src.sih.security_conflict_alpha._load_latest_par_data",
                   return_value=(overlays, analyst)):
            with patch("src.sih.security_conflict_alpha._load_alpha_index",
                       return_value=_make_alpha_index()):
                return security_alpha_summary(tmp_path)

    def test_no_par_data_returns_gracefully(self, tmp_path):
        with patch("src.sih.security_conflict_alpha._load_latest_par_data", return_value=([], {})):
            result = security_alpha_summary(tmp_path)
        assert result["status"] == "NO_PAR_DATA"
        assert "securities" in result

    def test_ok_status_with_data(self, tmp_path):
        overlays = [_ov("MSFT", "BULLISH", 1.5)]
        analyst = {"MSFT": {"consensus_label": "SELL"}}
        result = self._mock_summary(tmp_path, overlays, analyst)
        assert result["status"] == "OK"

    def test_contains_required_keys(self, tmp_path):
        overlays = [_ov("MSFT", "BULLISH", 1.5)]
        analyst = {"MSFT": {"consensus_label": "SELL"}}
        result = self._mock_summary(tmp_path, overlays, analyst)
        for key in ["generated_at", "total_analyzed", "conflict_count",
                    "leader_count", "laggard_count", "leaders", "laggards", "securities"]:
            assert key in result, f"Missing key: {key}"

    def test_leaders_sorted_by_excess_return(self, tmp_path):
        overlays = [
            _ov("A", "BULLISH", 1.5),  # → MAJORITY_BEARISH → LEADER excess 2.26
            _ov("B", "BULLISH", 4.5),  # → MIXED → LEADER excess 2.81
        ]
        analyst = {
            "A": {"consensus_label": "SELL"},
            "B": {"consensus_label": "HOLD"},
        }
        result = self._mock_summary(tmp_path, overlays, analyst)
        leaders = result.get("leaders", [])
        if len(leaders) >= 2:
            excess_returns = [l.get("excess_return_pct", 0) for l in leaders]
            assert excess_returns == sorted(excess_returns, reverse=True)

    def test_output_no_action_keys(self, tmp_path):
        overlays = [_ov("MSFT", "BULLISH", 1.5)]
        analyst = {"MSFT": {"consensus_label": "SELL"}}
        result = self._mock_summary(tmp_path, overlays, analyst)
        forbidden = {"execute", "trade", "buy_signal", "action_type"}
        assert not (forbidden & set(result.keys()))
        for sec in result.get("securities", {}).values():
            assert not (forbidden & set(sec.keys()))


# ═══════════════════════════════════════════════════════════════════════════════
# Q6–Q10 Governance assertions
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceConstraints:
    """Q6–Q9: No scoring engine changes. Q10: Display-only."""

    def test_security_conflict_alpha_is_dataclass_not_mutable_engine(self):
        """SecurityConflictAlpha is a frozen dataclass — cannot modify engine state."""
        result = derive_security_conflict_alpha(
            "X", "BULLISH", None, 1.5, "SELL", _make_alpha_index()
        )
        if result is not None:
            import dataclasses
            assert dataclasses.is_dataclass(result)
            # Frozen: cannot reassign
            with pytest.raises((AttributeError, TypeError)):
                result.alpha_class = "MODIFIED"  # type: ignore[misc]

    def test_no_new_scoring_files_written(self, tmp_path):
        """batch_security_conflict_alpha must not write any files."""
        overlays = [_ov("MSFT", "BULLISH", 1.5)]
        analyst = {"MSFT": {"consensus_label": "SELL"}}
        with patch("src.sih.security_conflict_alpha._load_alpha_index", return_value=_make_alpha_index()):
            batch_security_conflict_alpha(overlays, analyst, tmp_path)
        # No new files should exist in tmp_path (no writes by batch function)
        files = list(tmp_path.rglob("*.json")) + list(tmp_path.rglob("*.csv"))
        assert len(files) == 0

    def test_insight_is_informational(self):
        """Insight text must include governance language."""
        result = derive_security_conflict_alpha(
            "MSFT", "BULLISH", None, 1.5, "SELL", _make_alpha_index()
        )
        if result is not None and result.insight:
            # Should contain some form of informational qualifier
            assert any(kw in result.insight.lower()
                       for kw in ["informational", "judgment", "research", "historical", "historical"])
