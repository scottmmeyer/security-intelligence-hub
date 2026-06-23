"""Tests for DISLOCATION-07 — Directional Accuracy Analysis.

Tests all parts:
  Part A: Direction classification
  Part B: Prediction pair building
  Part C: Directional accuracy metrics (hit rate, precision, recall, FPR, FNR, balanced acc)
  Part D: Pattern reliability ranking
  Comparative: Magnitude vs directional analysis
  Public API: directional_accuracy, pattern_directional, directional_summary, refresh_directional
  Governance: research-only assertions
"""

import json
import math
import pytest
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch

from src.sih.predictive.directional_accuracy import (
    _classify_direction,
    _predicted_direction,
    _build_directional_pairs,
    _compute_directional_metrics,
    _reliability_class,
    _reliability_label,
    _compute_pattern_directional,
    _comparative_analysis,
    directional_accuracy,
    pattern_directional,
    directional_summary,
    refresh_directional,
)


# ─── Test helpers ─────────────────────────────────────────────────────────────

def _inv_row(sym: str, pattern: str, ret30, date: str = "2025-10-01") -> Dict:
    return {
        "symbol":             sym,
        "snapshot_date":      date,
        "ess_direction":      "BULLISH",
        "signal_pattern":     pattern,
        "has_conflict":       True,
        "forward_return_30d": ret30,
        "winner_loser":       "WINNER" if (ret30 or 0) > 0.005 else "LOSER",
        "ess_correct":        True,
    }


def _mock_inv():
    """Inventory with two patterns, mix of positive/negative outcomes."""
    rows = []
    # ESS_BULLISH_ANALYST_SKEPTICAL: 7 positive, 3 negative excess returns → hit rate ~70% if pred=POSITIVE
    for i in range(7):
        rows.append(_inv_row(f"SYM{i}", "ESS_BULLISH_ANALYST_SKEPTICAL", 0.03))   # +3% → positive excess
    for i in range(3):
        rows.append(_inv_row(f"NEG{i}", "ESS_BULLISH_ANALYST_SKEPTICAL", -0.02))  # -2% → negative excess
    # ESS_BULLISH_ANALYST_MIXED: 5 rows with minimal return (neutral)
    for i in range(5):
        rows.append(_inv_row(f"OTH{i}", "ESS_BULLISH_ANALYST_MIXED", 0.002))
    return rows


def _mock_alpha():
    return {
        "ESS_BULLISH_ANALYST_SKEPTICAL": {
            "signal_pattern":      "ESS_BULLISH_ANALYST_SKEPTICAL",
            "excess_return_pct":   2.0,   # predicts POSITIVE
            "avg_return_30d_pct":  2.5,
            "win_rate_pct":        65.0,
            "alpha_class":         "ALPHA_LEADER",
            "observations":        10,
        },
        "ESS_BULLISH_ANALYST_MIXED": {
            "signal_pattern":      "ESS_BULLISH_ANALYST_MIXED",
            "excess_return_pct":  -1.5,  # predicts NEGATIVE
            "avg_return_30d_pct":  0.1,
            "win_rate_pct":        48.0,
            "alpha_class":         "ALPHA_NEUTRAL",
            "observations":        5,
        },
    }


UNIVERSE_MEDIAN = 0.55  # 0.55% universe median (returns in pct)


# ─── TestClassifyDirection ─────────────────────────────────────────────────────

class TestClassifyDirection:
    def test_positive_above_threshold(self):
        assert _classify_direction(1.0) == "POSITIVE"

    def test_negative_below_threshold(self):
        assert _classify_direction(-1.0) == "NEGATIVE"

    def test_neutral_at_zero(self):
        assert _classify_direction(0.0) == "NEUTRAL"

    def test_neutral_just_inside_threshold(self):
        assert _classify_direction(0.4) == "NEUTRAL"
        assert _classify_direction(-0.4) == "NEUTRAL"

    def test_boundary_positive(self):
        assert _classify_direction(0.5) == "NEUTRAL"  # not strictly >
        assert _classify_direction(0.51) == "POSITIVE"

    def test_boundary_negative(self):
        assert _classify_direction(-0.5) == "NEUTRAL"  # not strictly <
        assert _classify_direction(-0.51) == "NEGATIVE"


# ─── TestPredictedDirection ────────────────────────────────────────────────────

class TestPredictedDirection:
    def test_positive_alpha(self):
        assert _predicted_direction({"excess_return_pct": 2.0}) == "POSITIVE"

    def test_negative_alpha(self):
        assert _predicted_direction({"excess_return_pct": -1.5}) == "NEGATIVE"

    def test_neutral_alpha(self):
        assert _predicted_direction({"excess_return_pct": 0.3}) == "NEUTRAL"

    def test_missing_excess(self):
        assert _predicted_direction({}) == "NEUTRAL"

    def test_none_excess(self):
        assert _predicted_direction({"excess_return_pct": None}) == "NEUTRAL"


# ─── TestBuildDirectionalPairs ────────────────────────────────────────────────

class TestBuildDirectionalPairs:
    def test_produces_pairs_for_attributed_rows(self):
        inv   = _mock_inv()
        alpha = _mock_alpha()
        pairs = _build_directional_pairs(inv, alpha, UNIVERSE_MEDIAN)
        # 10 TEST_PATTERN + 5 OTHER_PATTERN = 15
        assert len(pairs) == 15

    def test_skips_missing_return(self):
        inv = [_inv_row("SYM", "TEST_PATTERN", None)]
        pairs = _build_directional_pairs(inv, _mock_alpha(), UNIVERSE_MEDIAN)
        assert len(pairs) == 0

    def test_skips_unknown_pattern(self):
        inv = [_inv_row("SYM", "UNKNOWN_PATTERN", 0.02)]
        pairs = _build_directional_pairs(inv, _mock_alpha(), UNIVERSE_MEDIAN)
        assert len(pairs) == 0

    def test_skips_no_ess_data(self):
        inv = [_inv_row("SYM", "NO_ESS_DATA", 0.02)]
        pairs = _build_directional_pairs(inv, _mock_alpha(), UNIVERSE_MEDIAN)
        assert len(pairs) == 0

    def test_pair_fields(self):
        inv   = [_inv_row("AAPL", "ESS_BULLISH_ANALYST_SKEPTICAL", 0.03)]
        pairs = _build_directional_pairs(inv, _mock_alpha(), UNIVERSE_MEDIAN)
        assert len(pairs) == 1
        p = pairs[0]
        assert p["symbol"]              == "AAPL"
        assert p["pattern"]             == "ESS_BULLISH_ANALYST_SKEPTICAL"
        assert p["predicted_direction"] == "POSITIVE"    # excess_return_pct=2.0
        assert "actual_direction" in p
        assert "is_hit" in p
        assert isinstance(p["is_hit"], bool)

    def test_hit_true_when_directions_match(self):
        # +3% return → realized_excess = 3.0 - 0.55 = 2.45 → POSITIVE
        inv = [_inv_row("X", "ESS_BULLISH_ANALYST_SKEPTICAL", 0.03)]
        pairs = _build_directional_pairs(inv, _mock_alpha(), UNIVERSE_MEDIAN)
        assert pairs[0]["is_hit"] is True  # predicted POSITIVE, actual POSITIVE

    def test_hit_false_when_directions_differ(self):
        # -5% return → realized_excess = -5.0 - 0.55 → NEGATIVE, predicted POSITIVE → miss
        inv = [_inv_row("X", "ESS_BULLISH_ANALYST_SKEPTICAL", -0.05)]
        pairs = _build_directional_pairs(inv, _mock_alpha(), UNIVERSE_MEDIAN)
        assert pairs[0]["is_hit"] is False


# ─── TestComputeDirectionalMetrics ────────────────────────────────────────────

class TestComputeDirectionalMetrics:
    def _make_pairs(self, pred_dirs: List[str], actual_dirs: List[str]) -> List[Dict]:
        return [
            {
                "symbol": f"S{i}",
                "pattern": "P",
                "predicted_direction": pd,
                "actual_direction": ad,
                "is_hit": pd == ad,
            }
            for i, (pd, ad) in enumerate(zip(pred_dirs, actual_dirs))
        ]

    def test_empty_returns_n_zero(self):
        result = _compute_directional_metrics([])
        assert result["n"] == 0
        assert result.get("hit_rate") is None

    def test_all_hits(self):
        pairs = self._make_pairs(
            ["POSITIVE"] * 5,
            ["POSITIVE"] * 5,
        )
        result = _compute_directional_metrics(pairs)
        assert result["hit_rate"] == 100.0
        assert result["hits"] == 5

    def test_no_hits(self):
        pairs = self._make_pairs(
            ["POSITIVE"] * 5,
            ["NEGATIVE"] * 5,
        )
        result = _compute_directional_metrics(pairs)
        assert result["hit_rate"] == 0.0

    def test_hit_rate_calculation(self):
        pairs = self._make_pairs(
            ["POSITIVE"] * 6 + ["POSITIVE"] * 4,
            ["POSITIVE"] * 6 + ["NEGATIVE"] * 4,
        )
        result = _compute_directional_metrics(pairs)
        assert result["hit_rate"] == 60.0

    def test_precision_computed(self):
        # 4 TP, 1 FP → precision = 4/5 = 80%
        pairs = self._make_pairs(
            ["POSITIVE"] * 5,
            ["POSITIVE"] * 4 + ["NEGATIVE"] * 1,
        )
        result = _compute_directional_metrics(pairs)
        assert result["precision"] == 80.0

    def test_recall_computed(self):
        # 3 TP, 2 FN (predicted NEGATIVE but actual POSITIVE) → recall = 3/5 = 60%
        pairs = self._make_pairs(
            ["POSITIVE"] * 3 + ["NEGATIVE"] * 2,
            ["POSITIVE"] * 3 + ["POSITIVE"] * 2,
        )
        result = _compute_directional_metrics(pairs)
        assert result["recall"] == 60.0

    def test_confusion_matrix_present(self):
        pairs = self._make_pairs(
            ["POSITIVE", "POSITIVE", "NEGATIVE", "NEGATIVE"],
            ["POSITIVE", "NEGATIVE", "NEGATIVE", "POSITIVE"],
        )
        result = _compute_directional_metrics(pairs)
        cm = result["confusion_matrix"]
        assert cm["tp"] == 1
        assert cm["fp"] == 1
        assert cm["tn"] == 1
        assert cm["fn"] == 1

    def test_direction_distributions_present(self):
        pairs = self._make_pairs(
            ["POSITIVE", "NEGATIVE", "NEUTRAL"],
            ["POSITIVE", "POSITIVE", "NEGATIVE"],
        )
        result = _compute_directional_metrics(pairs)
        assert "predicted_distribution" in result
        assert "actual_distribution" in result
        assert result["predicted_distribution"]["POSITIVE"] == 1
        assert result["predicted_distribution"]["NEGATIVE"] == 1
        assert result["predicted_distribution"]["NEUTRAL"] == 1

    def test_balanced_accuracy_computed(self):
        # Perfect separation: 3 TP, 0 FP, 2 TN, 0 FN
        pairs = self._make_pairs(
            ["POSITIVE"] * 3 + ["NEGATIVE"] * 2,
            ["POSITIVE"] * 3 + ["NEGATIVE"] * 2,
        )
        result = _compute_directional_metrics(pairs)
        assert result["balanced_accuracy"] == pytest.approx(100.0)


# ─── TestReliabilityClass ─────────────────────────────────────────────────────

class TestReliabilityClass:
    def test_insufficient_data_n_too_small(self):
        assert _reliability_class(5, 75.0) == "INSUFFICIENT_DATA"

    def test_very_strong(self):
        assert _reliability_class(50, 70.0) == "VERY_STRONG"

    def test_strong(self):
        assert _reliability_class(50, 65.0) == "STRONG"

    def test_moderate(self):
        assert _reliability_class(50, 57.0) == "MODERATE"

    def test_weak(self):
        assert _reliability_class(50, 52.0) == "WEAK"

    def test_none_hit_rate(self):
        assert _reliability_class(100, None) == "INSUFFICIENT_DATA"

    def test_boundary_very_strong(self):
        assert _reliability_class(20, 70.0) == "VERY_STRONG"

    def test_boundary_strong(self):
        assert _reliability_class(20, 60.0) == "STRONG"

    def test_boundary_moderate(self):
        assert _reliability_class(20, 55.0) == "MODERATE"


# ─── TestReliabilityLabel ─────────────────────────────────────────────────────

class TestReliabilityLabel:
    def test_all_levels_return_string(self):
        for level in ["VERY_STRONG", "STRONG", "MODERATE", "WEAK", "INSUFFICIENT_DATA"]:
            label = _reliability_label(level)
            assert isinstance(label, str)
            assert len(label) > 5

    def test_very_strong_mentions_70(self):
        assert "70%" in _reliability_label("VERY_STRONG")

    def test_insufficient_mentions_insufficient(self):
        assert "Insufficient" in _reliability_label("INSUFFICIENT_DATA")


# ─── TestComputePatternDirectional ────────────────────────────────────────────

class TestComputePatternDirectional:
    def _pairs_for_pattern(self, n_pos: int, n_neg: int, pattern: str = "TEST_PATTERN") -> List[Dict]:
        """Build pairs: n_pos positive predictions that hit, n_neg that miss."""
        pairs = []
        for _ in range(n_pos):
            pairs.append({
                "symbol": "A",
                "pattern": pattern,
                "predicted_direction": "POSITIVE",
                "actual_direction": "POSITIVE",
                "is_hit": True,
                "predicted_excess_pct": 2.0,
                "realized_excess_pct": 2.5,
            })
        for _ in range(n_neg):
            pairs.append({
                "symbol": "B",
                "pattern": pattern,
                "predicted_direction": "POSITIVE",
                "actual_direction": "NEGATIVE",
                "is_hit": False,
                "predicted_excess_pct": 2.0,
                "realized_excess_pct": -1.5,
            })
        return pairs

    def test_empty_pattern_returns_insufficient(self):
        result = _compute_pattern_directional("EMPTY_PATTERN", [], {})
        assert result["reliability"] == "INSUFFICIENT_DATA"
        assert result["n"] == 0

    def test_hit_rate_computed(self):
        pairs = self._pairs_for_pattern(14, 6)
        result = _compute_pattern_directional("TEST_PATTERN", pairs, {"excess_return_pct": 2.0})
        assert result["hit_rate"] == pytest.approx(70.0)

    def test_reliability_set(self):
        pairs = self._pairs_for_pattern(14, 6, "TEST_PATTERN")
        result = _compute_pattern_directional("TEST_PATTERN", pairs, {"excess_return_pct": 2.0})
        assert result["reliability"] in ("VERY_STRONG", "STRONG", "MODERATE", "WEAK", "INSUFFICIENT_DATA")

    def test_pattern_label_populated(self):
        result = _compute_pattern_directional("ESS_BULLISH_ANALYST_MAJORITY_BEARISH", [], {})
        assert result["pattern_label"] == "ESS Buy / Analyst Sell"

    def test_alpha_context_forwarded(self):
        pairs = self._pairs_for_pattern(5, 5, "TEST_PATTERN")
        alpha = {"excess_return_pct": 1.5, "alpha_class": "ALPHA_LEADER", "win_rate_pct": 60.0}
        result = _compute_pattern_directional("TEST_PATTERN", pairs, alpha)
        assert result["alpha_class"] == "ALPHA_LEADER"
        assert result["win_rate_pct"] == 60.0


# ─── TestComparativeAnalysis ──────────────────────────────────────────────────

class TestComparativeAnalysis:
    def _dir_patterns(self, hit_rate: float, n: int = 100) -> List[Dict]:
        return [{
            "pattern": "TEST_PATTERN",
            "pattern_label": "Test",
            "n": n,
            "hit_rate": hit_rate,
            "reliability": "STRONG",
            "predicted_direction": "POSITIVE",
        }]

    def test_directional_verdict_high_hit_rate(self):
        result = _comparative_analysis(self._dir_patterns(65.0), None)
        assert result["verdict"] == "DIRECTIONAL"

    def test_directional_marginal_moderate_hit_rate(self):
        result = _comparative_analysis(self._dir_patterns(57.0), None)
        assert result["verdict"] == "DIRECTIONAL_MARGINAL"

    def test_neither_verdict_low_hit_rate(self):
        result = _comparative_analysis(self._dir_patterns(48.0), None)
        assert result["verdict"] == "NEITHER"

    def test_avg_hit_rate_computed(self):
        result = _comparative_analysis(self._dir_patterns(65.0), None)
        assert result["avg_directional_hit_rate"] == pytest.approx(65.0)

    def test_no_data_graceful(self):
        result = _comparative_analysis([], None)
        assert result["avg_directional_hit_rate"] is None

    def test_calibration_data_integrated(self):
        cal_data = {
            "patterns": [{"pattern": "TEST_PATTERN", "mae_pp": 7.5, "confidence": "LOW"}]
        }
        result = _comparative_analysis(self._dir_patterns(65.0), cal_data)
        # Should integrate MAE from calibration
        pat = next((p for p in result["patterns"] if p["pattern"] == "TEST_PATTERN"), None)
        assert pat is not None
        assert pat["magnitude_mae_pp"] == 7.5


# ─── TestPublicAPI ────────────────────────────────────────────────────────────

class TestPublicAPI:
    def _patch(self, tmp_path: Path):
        return (
            patch("src.sih.predictive.directional_accuracy._load_inventory",
                  return_value=_mock_inv()),
            patch("src.sih.predictive.directional_accuracy._load_alpha_index",
                  return_value=_mock_alpha()),
        )

    def test_directional_accuracy_returns_dict(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = directional_accuracy(tmp_path)
        assert isinstance(result, dict)

    def test_directional_accuracy_has_status_ok(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = directional_accuracy(tmp_path)
        assert result["status"] == "OK"

    def test_directional_accuracy_has_patterns(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = directional_accuracy(tmp_path)
        assert "patterns" in result
        assert len(result["patterns"]) > 0

    def test_directional_accuracy_has_overall(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = directional_accuracy(tmp_path)
        assert "overall" in result
        assert "hit_rate" in result["overall"]

    def test_directional_accuracy_has_comparative(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = directional_accuracy(tmp_path)
        assert "comparative" in result
        assert "verdict" in result["comparative"]

    def test_directional_accuracy_has_governance_note(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = directional_accuracy(tmp_path)
        assert "governance_note" in result

    def test_pattern_directional_known_pattern(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = pattern_directional("ESS_BULLISH_ANALYST_SKEPTICAL", tmp_path)
        assert result.get("pattern") == "ESS_BULLISH_ANALYST_SKEPTICAL"
        assert "hit_rate" in result

    def test_pattern_directional_unknown_returns_error(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = pattern_directional("NONEXISTENT", tmp_path)
        assert "error" in result or result.get("reliability") == "INSUFFICIENT_DATA"

    def test_directional_summary_structure(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = directional_summary(tmp_path)
        assert "overall_hit_rate" in result
        assert "verdict" in result
        assert "patterns" in result
        assert "governance_note" in result

    def test_refresh_directional_returns_meta(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = refresh_directional(tmp_path)
        assert result.get("ok") is True
        assert "total_pairs" in result
        assert "overall_hit_rate" in result
        assert "verdict" in result


# ─── TestGovernanceDisloc07 ───────────────────────────────────────────────────

class TestGovernanceDisloc07:
    """DISLOCATION-07 must not touch scoring or recommendation engines."""

    def _patch(self, tmp_path: Path):
        return (
            patch("src.sih.predictive.directional_accuracy._load_inventory",
                  return_value=_mock_inv()),
            patch("src.sih.predictive.directional_accuracy._load_alpha_index",
                  return_value=_mock_alpha()),
        )

    def test_governance_note_present(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = directional_accuracy(tmp_path)
        note = result.get("governance_note", "")
        assert "research-only" in note.lower() or "informational" in note.lower()

    def test_no_ess_modification_claimed(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = directional_accuracy(tmp_path)
        note = result.get("governance_note", "").upper()
        assert "ESS" in note
        assert "CW-DAS" in note or "CWDAS" in note or "CW" in note

    def test_no_recommendation_keys_in_output(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = directional_accuracy(tmp_path)
        forbidden = {"recommendation", "action", "buy", "sell", "rebalance"}
        top_level_keys = set(k.lower() for k in result.keys())
        assert not forbidden & top_level_keys

    def test_total_pairs_count(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = directional_accuracy(tmp_path)
        # 10 TEST_PATTERN + 5 OTHER_PATTERN rows with returns
        assert result["total_pairs"] == 15

    def test_version_field_present(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = directional_accuracy(tmp_path)
        assert result.get("version") == "1.0"

    def test_direction_thresholds_documented(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = directional_accuracy(tmp_path)
        thresholds = result.get("direction_thresholds", {})
        assert "positive_above_pp" in thresholds
        assert "negative_below_pp" in thresholds
        assert thresholds["positive_above_pp"] == 0.5
        assert thresholds["negative_below_pp"] == -0.5
