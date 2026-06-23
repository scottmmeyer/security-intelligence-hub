"""Tests for DISLOCATION-06 — Confidence Calibration for Forward Return Estimates.

Covers:
  - _build_prediction_pairs() — reconstruct estimates vs realized
  - _accuracy_bands() — fraction within each error band
  - _bias_direction() — OPTIMISTIC / PESSIMISTIC / NEUTRAL
  - _confidence_level() — VERY_HIGH / HIGH / MEDIUM / LOW / INSUFFICIENT_DATA
  - _compute_pattern_calibration() — full pattern stats
  - calibration_summary() / pattern_calibration() / confidence_summary() — public API
  - enrich_forward_estimate() — DISLOCATION-05 extension

Governance:
  Q6–Q8: No CW-DAS, ESS, recommendation algorithm changes
  Q9: Informational only
  Q10: Closes the predictive-confidence gap
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch

import pytest

from src.sih.predictive.conflict_alpha_calibration import (
    _accuracy_bands,
    _bias_direction,
    _build_prediction_pairs,
    _compute_pattern_calibration,
    _confidence_level,
    calibration_summary,
    confidence_summary,
    enrich_forward_estimate,
    pattern_calibration,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _inv_row(sym: str, pattern: str, ret30, date: str = "2025-10-01") -> Dict:
    return {
        "symbol":           sym,
        "snapshot_date":    date,
        "ess_direction":    "BULLISH",
        "signal_pattern":   pattern,
        "has_conflict":     True,
        "forward_return_30d": ret30,
        "winner_loser":     "WINNER" if (ret30 or 0) > 0.005 else "LOSER",
        "ess_correct":      True,
    }


def _alpha_entry(pattern: str, avg_ret: float, excess_ret: float, n: int = 80) -> Dict:
    return {
        "signal_pattern":        pattern,
        "avg_return_30d_pct":    avg_ret,
        "excess_return_pct":     excess_ret,
        "win_rate_pct":          55.0,
        "alpha_class":           "ALPHA_LEADER" if excess_ret > 1 else "ALPHA_NEUTRAL",
        "significance":          "SUGGESTIVE",
        "observations":          n,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Statistical helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestAccuracyBands:
    def test_all_within_1pp(self):
        errors = [0.5, 0.8, 0.3, 0.9]
        result = _accuracy_bands(errors)
        assert result["within_1pp"] == pytest.approx(100.0)
        assert result["within_2pp"] == pytest.approx(100.0)

    def test_none_within_1pp(self):
        errors = [2.5, 3.0, 4.0, 5.5]
        result = _accuracy_bands(errors)
        assert result["within_1pp"] == pytest.approx(0.0)
        assert result["within_2pp"] == pytest.approx(0.0)  # none ≤ 2.0

    def test_mixed(self):
        errors = [1.0, 3.0, 5.0, 10.0]
        result = _accuracy_bands(errors)
        assert result["within_1pp"] == pytest.approx(25.0)   # only 1.0 ≤ 1.0
        assert result["within_2pp"] == pytest.approx(25.0)   # only 1.0 ≤ 2.0
        assert result["within_5pp"] == pytest.approx(75.0)   # 1.0, 3.0, 5.0 ≤ 5.0
        assert result["within_10pp"] == pytest.approx(100.0)

    def test_empty_returns_empty(self):
        assert _accuracy_bands([]) == {}


class TestBiasDirection:
    def test_optimistic_positive_error(self):
        assert _bias_direction(2.0) == "OPTIMISTIC"

    def test_pessimistic_negative_error(self):
        assert _bias_direction(-2.0) == "PESSIMISTIC"

    def test_neutral_small_error(self):
        assert _bias_direction(0.5) == "NEUTRAL"
        assert _bias_direction(-0.5) == "NEUTRAL"


class TestConfidenceLevel:
    def test_insufficient_data_small_n(self):
        assert _confidence_level(3, 1.0, 0.5) == "INSUFFICIENT_DATA"

    def test_very_high(self):
        assert _confidence_level(60, 1.5, 0.8) == "VERY_HIGH"

    def test_high(self):
        assert _confidence_level(25, 3.0, 0.5) == "HIGH"

    def test_medium(self):
        assert _confidence_level(10, 5.0, 0.5) == "MEDIUM"

    def test_low_high_mae(self):
        assert _confidence_level(10, 8.0, 0.5) == "LOW"

    def test_high_bias_reduces_confidence(self):
        # Good n and MAE, but biased → not VERY_HIGH
        result = _confidence_level(60, 1.5, 2.0)
        assert result != "VERY_HIGH"


# ═══════════════════════════════════════════════════════════════════════════════
# _build_prediction_pairs
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildPredictionPairs:
    def test_pair_produced_when_data_available(self):
        inventory = [_inv_row("AAAA", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", 0.06)]
        alpha_index = {"ESS_BULLISH_ANALYST_MAJORITY_BEARISH": _alpha_entry("ESS_BULLISH_ANALYST_MAJORITY_BEARISH", 2.81, 2.26)}
        pairs = _build_prediction_pairs(inventory, alpha_index, 0.5546)
        assert len(pairs) == 1
        p = pairs[0]
        assert p["symbol"] == "AAAA"
        assert p["predicted_excess_return_pct"] == pytest.approx(2.26)
        assert p["realized_return_pct"] == pytest.approx(6.0)
        assert p["realized_excess_return_pct"] == pytest.approx(6.0 - 0.5546, abs=0.01)

    def test_absolute_error_computed(self):
        inv = [_inv_row("A", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", 0.05)]
        alpha = {"ESS_BULLISH_ANALYST_MAJORITY_BEARISH": _alpha_entry("X", 3.0, 2.26)}
        pairs = _build_prediction_pairs(inv, alpha, 0.5546)
        assert pairs[0]["absolute_error_pp"] >= 0

    def test_missing_alpha_skipped(self):
        inv = [_inv_row("A", "ESS_UNKNOWN_PATTERN", 0.05)]
        pairs = _build_prediction_pairs(inv, {}, 0.0)
        assert pairs == []

    def test_missing_return_skipped(self):
        inv = [_inv_row("A", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", None)]
        inv[0]["forward_return_30d"] = None
        alpha = {"ESS_BULLISH_ANALYST_MAJORITY_BEARISH": _alpha_entry("X", 2.0, 1.5)}
        pairs = _build_prediction_pairs(inv, alpha, 0.0)
        assert pairs == []

    def test_signed_error_direction(self):
        # Predicted excess = 2.0, realized excess = 0.5 → signed_error > 0 (optimistic)
        inv = [_inv_row("A", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", 0.01)]  # 1% → realized excess ≈ 0.4pp
        alpha = {"ESS_BULLISH_ANALYST_MAJORITY_BEARISH": _alpha_entry("X", 2.5, 2.0)}
        pairs = _build_prediction_pairs(inv, alpha, 0.6)
        assert pairs[0]["signed_error_pp"] > 0  # optimistic: predicted 2.0, realized ≈ 0.4


# ═══════════════════════════════════════════════════════════════════════════════
# _compute_pattern_calibration
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputePatternCalibration:
    def _pairs(self, n: int, abs_err: float = 1.5, signed_err: float = 0.5) -> List[Dict]:
        return [
            {"pattern": "TEST_PATTERN", "symbol": f"S{i}",
             "absolute_error_pp": abs_err, "signed_error_pp": signed_err,
             "predicted_excess_return_pct": 2.0, "realized_excess_return_pct": 2.0 - signed_err}
            for i in range(n)
        ]

    def test_zero_obs_returns_insufficient(self):
        result = _compute_pattern_calibration("TEST", [], {})
        assert result["confidence"] == "INSUFFICIENT_DATA"
        assert result["n"] == 0

    def test_sufficient_obs_computes_mae(self):
        result = _compute_pattern_calibration("TEST_PATTERN", self._pairs(30), {"excess_return_pct": 2.0})
        assert result["mae_pp"] == pytest.approx(1.5)
        assert result["n"] == 30

    def test_accuracy_bands_populated(self):
        result = _compute_pattern_calibration("TEST_PATTERN", self._pairs(30, abs_err=0.5), {})
        assert result["accuracy_bands"]["within_1pp"] == pytest.approx(100.0)

    def test_bias_direction_computed(self):
        result = _compute_pattern_calibration("TEST_PATTERN", self._pairs(30, signed_err=3.0), {})
        assert result["bias_direction"] == "OPTIMISTIC"

    def test_confidence_level_set(self):
        result = _compute_pattern_calibration("TEST_PATTERN", self._pairs(60, abs_err=1.5, signed_err=0.5), {})
        assert result["confidence"] in ("VERY_HIGH", "HIGH", "MEDIUM", "LOW", "INSUFFICIENT_DATA")


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

def _mock_inv():
    return [
        _inv_row("AAAA", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", 0.06, "2025-10-01"),
        _inv_row("BBBB", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", 0.02, "2025-10-19"),
        _inv_row("CCCC", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", -0.01, "2026-01-08"),
        _inv_row("DDDD", "ESS_BULLISH_ANALYST_SKEPTICAL", 0.04, "2025-10-01"),
        _inv_row("EEEE", "ESS_BULLISH_ANALYST_SKEPTICAL", 0.01, "2025-10-19"),
    ]


def _mock_alpha():
    return {
        "ESS_BULLISH_ANALYST_MAJORITY_BEARISH": _alpha_entry("ESS_BULLISH_ANALYST_MAJORITY_BEARISH", 2.81, 2.26, n=93),
        "ESS_BULLISH_ANALYST_SKEPTICAL": _alpha_entry("ESS_BULLISH_ANALYST_SKEPTICAL", 2.11, 0.72, n=154),
    }


class TestPublicAPI:
    def _patch(self, tmp_path: Path):
        return (
            patch("src.sih.predictive.conflict_alpha_calibration._load_inventory", return_value=_mock_inv()),
            patch("src.sih.predictive.conflict_alpha_calibration._load_alpha_index", return_value=_mock_alpha()),
        )

    def test_calibration_summary_structure(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = calibration_summary(tmp_path)
        assert "patterns" in result
        assert "total_pairs" in result
        assert "overall_mae_pp" in result
        assert "governance_note" in result

    def test_calibration_summary_has_patterns(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = calibration_summary(tmp_path)
        assert len(result["patterns"]) >= 1

    def test_pattern_calibration_returns_for_known(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = pattern_calibration("ESS_BULLISH_ANALYST_MAJORITY_BEARISH", tmp_path)
        assert result.get("pattern") == "ESS_BULLISH_ANALYST_MAJORITY_BEARISH"
        assert "confidence" in result

    def test_pattern_calibration_error_for_unknown(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = pattern_calibration("NONEXISTENT_PATTERN", tmp_path)
        assert "error" in result or result.get("confidence") == "INSUFFICIENT_DATA"

    def test_confidence_summary_keys(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = confidence_summary(tmp_path)
        for key in ["confidence_counts", "most_reliable", "least_reliable",
                    "overall_mae_pp", "governance_note"]:
            assert key in result

    def test_governance_note_present(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = calibration_summary(tmp_path)
        note = result.get("governance_note", "")
        assert len(note) > 20
        assert "research" in note.lower() or "no" in note.lower()

    def test_no_action_keys(self, tmp_path):
        p1, p2 = self._patch(tmp_path)
        with p1, p2:
            result = calibration_summary(tmp_path)
        forbidden = {"execute", "trade", "buy_signal", "action_type"}
        assert not (forbidden & set(result.keys()))


# ═══════════════════════════════════════════════════════════════════════════════
# enrich_forward_estimate (DISLOCATION-05 extension)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnrichForwardEstimate:
    def _base_estimate(self) -> Dict:
        return {
            "symbol": "MSFT",
            "current_pattern": "ESS_BULLISH_ANALYST_MAJORITY_BEARISH",
            "status": "OK",
            "excess_return_pct": 2.26,
            "alpha_class": "ALPHA_LEADER",
        }

    def test_confidence_added(self, tmp_path):
        cal_data = {
            "patterns": [
                {"pattern": "ESS_BULLISH_ANALYST_MAJORITY_BEARISH",
                 "confidence": "HIGH", "confidence_label": "Well calibrated",
                 "mae_pp": 2.5, "n": 80, "bias_direction": "NEUTRAL",
                 "accuracy_bands": {"within_2pp": 65.0}}
            ]
        }
        with patch("src.sih.predictive.conflict_alpha_calibration._get_calibration",
                   return_value=cal_data):
            result = enrich_forward_estimate(self._base_estimate(), tmp_path)
        assert result["confidence"] == "HIGH"
        assert result["mae_pp"] == pytest.approx(2.5)
        assert "accuracy_bands" in result

    def test_non_ok_estimate_unchanged(self, tmp_path):
        estimate = {"symbol": "X", "status": "NO_CONFLICT_DATA"}
        result = enrich_forward_estimate(estimate, tmp_path)
        assert result == estimate

    def test_missing_calibration_does_not_crash(self, tmp_path):
        with patch("src.sih.predictive.conflict_alpha_calibration._get_calibration",
                   return_value={"patterns": []}):
            result = enrich_forward_estimate(self._base_estimate(), tmp_path)
        assert result["status"] == "OK"  # base estimate preserved
        assert result.get("confidence") == "INSUFFICIENT_DATA"

    def test_governance_note_preserved(self, tmp_path):
        with patch("src.sih.predictive.conflict_alpha_calibration._get_calibration",
                   return_value={"patterns": []}):
            result = enrich_forward_estimate(self._base_estimate(), tmp_path)
        # Base estimate keys preserved
        assert result["excess_return_pct"] == pytest.approx(2.26)


# ═══════════════════════════════════════════════════════════════════════════════
# Q6–Q10 Governance
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceDisloc06:
    """Q6–Q8: No algorithm changes. Q9: Informational. Q10: Closes gap."""

    def test_calibration_module_writes_only_to_dislocation_dir(self, tmp_path):
        with (
            patch("src.sih.predictive.conflict_alpha_calibration._load_inventory", return_value=_mock_inv()),
            patch("src.sih.predictive.conflict_alpha_calibration._load_alpha_index", return_value=_mock_alpha()),
        ):
            from src.sih.predictive.conflict_alpha_calibration import refresh_calibration
            refresh_calibration(tmp_path)
        written = list((tmp_path / "data").rglob("*.json")) if (tmp_path / "data").exists() else []
        paths = [str(f) for f in written]
        for p in paths:
            assert "conflict_alpha_calibration" in p or "dislocation" in p

    def test_confidence_label_is_descriptive(self):
        from src.sih.predictive.conflict_alpha_calibration import _confidence_label
        for level in ("VERY_HIGH", "HIGH", "MEDIUM", "LOW", "INSUFFICIENT_DATA"):
            label = _confidence_label(level)
            assert len(label) > 10

    def test_enrich_does_not_modify_scoring_fields(self, tmp_path):
        base = {
            "symbol": "X", "status": "OK",
            "current_pattern": "ESS_BULLISH_ANALYST_MAJORITY_BEARISH",
            "excess_return_pct": 2.26,
            "alpha_class": "ALPHA_LEADER",
            "n_observations": 93,
        }
        with patch("src.sih.predictive.conflict_alpha_calibration._get_calibration",
                   return_value={"patterns": []}):
            result = enrich_forward_estimate(base, tmp_path)
        # Core fields unchanged
        assert result["excess_return_pct"] == pytest.approx(2.26)
        assert result["alpha_class"] == "ALPHA_LEADER"
        assert result["n_observations"] == 93
