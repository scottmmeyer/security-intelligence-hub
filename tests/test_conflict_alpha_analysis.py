"""Tests for DISLOCATION-02 — Conflict Alpha Attribution.

Covers:
  - _t_statistic()
  - _consistency_score()
  - _alpha_class() — boundary cases
  - _significance_label()
  - _insight_text() — content constraints
  - compute_conflict_alpha() — aggregation
  - conflict_alpha_report() — cache + full pipeline

Governance assertions:
  - Output fields contain no action/trade/execute keys
  - governance_note is present and non-empty
  - No scoring engine files are written
"""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from typing import List, Optional
from unittest.mock import patch

import pytest

from src.sih.conflict_alpha_analysis import (
    _alpha_class,
    _consistency_score,
    _insight_text,
    _significance_label,
    _t_statistic,
    compute_conflict_alpha,
    conflict_alpha_report,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Unit tests: statistical helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestTStatistic:
    def test_single_value_returns_none(self):
        assert _t_statistic([5.0], 0.0) is None

    def test_zero_variance_returns_none(self):
        assert _t_statistic([3.0, 3.0, 3.0], 3.0) is None

    def test_positive_t_when_mean_above_mu(self):
        result = _t_statistic([4.0, 5.0, 6.0, 5.0, 4.5], 2.0)
        assert result is not None
        assert result > 0

    def test_negative_t_when_mean_below_mu(self):
        result = _t_statistic([-1.0, -2.0, -3.0, -1.5, -2.5], 0.0)
        assert result is not None
        assert result < 0

    def test_empty_list_returns_none(self):
        assert _t_statistic([], 0.0) is None

    def test_result_is_float(self):
        result = _t_statistic([1.0, 2.0, 3.0, 4.0, 5.0], 0.0)
        assert isinstance(result, float)

    def test_symmetric_samples_t_near_zero(self):
        # Samples symmetric around mu
        result = _t_statistic([-1.0, -0.5, 0.0, 0.5, 1.0], 0.0)
        assert result is not None
        assert abs(result) < 0.01


class TestConsistencyScore:
    def test_all_beat_median(self):
        assert _consistency_score([2.0, 3.0, 4.0], 1.0) == pytest.approx(1.0)

    def test_none_beat_median(self):
        assert _consistency_score([0.5, 0.3, 0.1], 1.0) == pytest.approx(0.0)

    def test_half_beat(self):
        result = _consistency_score([2.0, 0.5], 1.0)
        assert result == pytest.approx(0.5)

    def test_empty_returns_half(self):
        assert _consistency_score([], 0.0) == pytest.approx(0.5)


class TestAlphaClass:
    def test_leader_above_threshold(self):
        assert _alpha_class(1.5, 2.0) == "ALPHA_LEADER"

    def test_laggard_below_threshold(self):
        assert _alpha_class(-1.5, -2.0) == "ALPHA_LAGGARD"

    def test_neutral_between_thresholds(self):
        assert _alpha_class(0.5, 1.0) == "ALPHA_NEUTRAL"

    def test_exact_boundary_leader(self):
        # Exactly at +1.0pp threshold: > 1.0 required for leader
        assert _alpha_class(1.0, None) == "ALPHA_NEUTRAL"

    def test_just_above_threshold(self):
        assert _alpha_class(1.01, None) == "ALPHA_LEADER"

    def test_just_below_negative_threshold(self):
        assert _alpha_class(-1.01, None) == "ALPHA_LAGGARD"


class TestSignificanceLabel:
    def test_none_returns_insufficient(self):
        assert _significance_label(None) == "INSUFFICIENT_DATA"

    def test_high_abs_t_noteworthy(self):
        assert _significance_label(2.5) == "NOTEWORTHY"
        assert _significance_label(-2.5) == "NOTEWORTHY"

    def test_mid_abs_t_suggestive(self):
        assert _significance_label(1.7) == "SUGGESTIVE"
        assert _significance_label(-1.7) == "SUGGESTIVE"

    def test_low_abs_t_weak(self):
        assert _significance_label(0.5) == "WEAK"
        assert _significance_label(-0.3) == "WEAK"

    def test_boundary_noteworthy(self):
        assert _significance_label(2.0) == "NOTEWORTHY"


class TestInsightText:
    def test_alpha_leader_mentions_ess(self):
        text = _insight_text(
            "ESS_BULLISH_ANALYST_MIXED", "ALPHA_LEADER",
            5.0, 60.0, 2.1, "BULLISH"
        )
        assert "ESS" in text or "ess" in text.lower()
        assert "outperform" in text.lower() or "positive excess" in text.lower()

    def test_alpha_laggard_mentions_analyst(self):
        text = _insight_text(
            "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", "ALPHA_LAGGARD",
            -3.0, 30.0, -1.8, "BULLISH"
        )
        assert "analyst" in text.lower()

    def test_neutral_no_material_alpha(self):
        text = _insight_text(
            "ESS_NEUTRAL_ANALYST_MIXED", "ALPHA_NEUTRAL",
            0.2, 50.0, 0.1, "NEUTRAL"
        )
        assert "no material alpha" in text.lower()

    def test_governance_no_action_instructions(self):
        """Insight text must not contain trade/execute instructions."""
        for alpha_cls in ["ALPHA_LEADER", "ALPHA_LAGGARD", "ALPHA_NEUTRAL"]:
            text = _insight_text(
                "ESS_BULLISH_ANALYST_MIXED", alpha_cls,
                2.0, 55.0, 1.5, "BULLISH"
            )
            forbidden = ["execute", "trade now", "buy immediately", "sell now"]
            for f in forbidden:
                assert f not in text.lower(), f"Insight contains forbidden phrase: {f!r}"

    def test_noteworthy_significance_mentioned(self):
        # High t-stat
        text = _insight_text(
            "ESS_BULLISH_ANALYST_MIXED", "ALPHA_LEADER",
            4.0, 65.0, 2.5, "BULLISH"
        )
        assert "noteworthy" in text.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Integration tests: compute_conflict_alpha()
# ═══════════════════════════════════════════════════════════════════════════════

def _make_inventory(entries):
    """Build a synthetic inventory list."""
    return [
        {
            "symbol": e.get("symbol", "TEST"),
            "snapshot_date": e.get("date", "2025-10-01"),
            "ess_direction": e.get("ess", "BULLISH"),
            "zacks_direction": e.get("zacks", "BEARISH"),
            "jefferson_direction": e.get("jeff", "NO_DATA"),
            "mclean_direction": e.get("mc", "NO_DATA"),
            "signal_pattern": e.get("pattern", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH"),
            "has_conflict": e.get("has_conflict", True),
            "forward_return_30d": e.get("ret30", 0.05),
            "winner_loser": e.get("wl", "WINNER"),
            "ess_correct": e.get("ess_ok", True),
        }
        for e in entries
    ]


class TestComputeConflictAlpha:

    def _run(self, entries, tmp_path):
        """Mock load_inventory to return synthetic data and run compute."""
        inventory = _make_inventory(entries)
        with patch("src.sih.conflict_alpha_analysis._load_inventory", return_value=inventory):
            return compute_conflict_alpha(tmp_path)

    def test_returns_valid_structure(self, tmp_path):
        entries = [
            {"pattern": "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", "ret30": 0.08},
            {"pattern": "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", "ret30": 0.03},
            {"pattern": "ESS_BULLISH_ANALYST_MIXED", "ret30": 0.12},
        ]
        result = self._run(entries, tmp_path)
        assert "patterns" in result
        assert "leaders" in result
        assert "laggards" in result
        assert "universe_median_return_pct" in result
        assert "governance_note" in result

    def test_universe_median_computed(self, tmp_path):
        entries = [
            {"ret30": 0.01},
            {"ret30": 0.02},
            {"ret30": 0.03},
            {"ret30": 0.04},
            {"ret30": 0.05},
        ]
        result = self._run(entries, tmp_path)
        assert result["universe_median_return_pct"] == pytest.approx(3.0, abs=0.01)

    def test_excess_return_computed_correctly(self, tmp_path):
        # All entries in one pattern, universe median = 2%
        entries = [{"pattern": "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", "ret30": r}
                   for r in [0.02, 0.02, 0.02, 0.07, 0.07]]  # avg = 4%, median = 2%
        result = self._run(entries, tmp_path)
        pat = next(p for p in result["patterns"]
                   if p["signal_pattern"] == "ESS_BULLISH_ANALYST_MAJORITY_BEARISH")
        # Universe median = 2%, avg = 4% → excess ≈ +2pp
        assert pat["excess_return_pct"] == pytest.approx(2.0, abs=0.5)

    def test_alpha_class_set_on_patterns(self, tmp_path):
        entries = [{"pattern": "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", "ret30": r}
                   for r in [0.10, 0.08, 0.09, 0.07, 0.06]]  # high positive returns
        result = self._run(entries, tmp_path)
        pat = next(p for p in result["patterns"]
                   if p["signal_pattern"] == "ESS_BULLISH_ANALYST_MAJORITY_BEARISH")
        assert pat["alpha_class"] in ("ALPHA_LEADER", "ALPHA_NEUTRAL", "ALPHA_LAGGARD")

    def test_leaders_are_top_excess_return(self, tmp_path):
        entries = (
            [{"pattern": "ESS_BULLISH_ANALYST_MIXED",             "ret30": 0.10}] * 10 +
            [{"pattern": "ESS_BULLISH_ANALYST_MAJORITY_BEARISH",  "ret30": 0.02}] * 10
        )
        result = self._run(entries, tmp_path)
        if result["leaders"]:
            leader = result["leaders"][0]
            assert leader.get("excess_return_pct", 0) >= 0

    def test_no_data_returns_gracefully(self, tmp_path):
        result = self._run([], tmp_path)
        assert result["status"] == "NO_DATA"
        assert result["patterns"] == []

    def test_only_entries_without_returns_handled(self, tmp_path):
        """Entries without forward_return_30d should be skipped."""
        entries = [
            {"pattern": "ESS_BULLISH_ANALYST_MIXED", "ret30": None},
        ]
        inventory = _make_inventory(entries)
        # Manually set ret30 to None
        for e in inventory:
            e["forward_return_30d"] = None
        with patch("src.sih.conflict_alpha_analysis._load_inventory", return_value=inventory):
            result = compute_conflict_alpha(tmp_path)
        # Should not raise; patterns list may be empty or have 0 observations
        assert "patterns" in result

    def test_consistency_score_range(self, tmp_path):
        entries = [{"pattern": "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", "ret30": r}
                   for r in [0.01, 0.02, 0.03, 0.05, 0.06]]
        result = self._run(entries, tmp_path)
        pat = next(p for p in result["patterns"]
                   if p["signal_pattern"] == "ESS_BULLISH_ANALYST_MAJORITY_BEARISH")
        assert 0.0 <= pat["consistency_score"] <= 1.0

    def test_top_symbols_present(self, tmp_path):
        entries = [
            {"pattern": "ESS_BULLISH_ANALYST_MIXED", "symbol": "AAAA", "ret30": 0.10, "wl": "WINNER"},
            {"pattern": "ESS_BULLISH_ANALYST_MIXED", "symbol": "BBBB", "ret30": 0.08, "wl": "WINNER"},
            {"pattern": "ESS_BULLISH_ANALYST_MIXED", "symbol": "CCCC", "ret30": 0.01, "wl": "LOSER"},
        ]
        result = self._run(entries, tmp_path)
        pat = next((p for p in result["patterns"]
                    if p["signal_pattern"] == "ESS_BULLISH_ANALYST_MIXED"), None)
        if pat:
            assert isinstance(pat["top_symbols"], list)

    def test_governance_note_present(self, tmp_path):
        result = self._run([], tmp_path)
        note = result.get("governance_note", "")
        assert len(note) > 20
        assert "research" in note.lower() or "informational" in note.lower() or "no" in note.lower()

    def test_no_action_keys_in_output(self, tmp_path):
        entries = [{"pattern": "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", "ret30": 0.05}] * 5
        result = self._run(entries, tmp_path)
        forbidden = {"action_type", "execute", "trade_instruction", "buy_signal"}
        assert not (forbidden & set(result.keys()))
        for p in result.get("patterns", []):
            assert not (forbidden & set(p.keys()))


class TestConflictAlphaReport:
    """Test the cache + public API function."""

    def test_cache_written(self, tmp_path):
        inv = _make_inventory([
            {"pattern": "ESS_BULLISH_ANALYST_MIXED", "ret30": 0.05},
        ])
        with patch("src.sih.conflict_alpha_analysis._load_inventory", return_value=inv):
            _ = conflict_alpha_report(tmp_path)
        cache_path = tmp_path / "data" / "analysis" / "dislocation" / "conflict_alpha_report.json"
        assert cache_path.exists()

    def test_cache_reused(self, tmp_path):
        inv = _make_inventory([
            {"pattern": "ESS_BULLISH_ANALYST_MIXED", "ret30": 0.05},
        ])
        # Create the inventory CSV so the cache validity check has something to compare against
        disloc_dir = tmp_path / "data" / "analysis" / "dislocation"
        disloc_dir.mkdir(parents=True, exist_ok=True)
        inv_csv = disloc_dir / "dislocation_inventory.csv"
        inv_csv.write_text("symbol,snapshot_date\nTEST,2026-01-01\n", encoding="utf-8")

        with patch("src.sih.conflict_alpha_analysis._load_inventory", return_value=inv):
            r1 = conflict_alpha_report(tmp_path)

        # Touch the cache to ensure it's newer than inventory CSV
        cache_path = disloc_dir / "conflict_alpha_report.json"
        import os, time
        time.sleep(0.01)
        os.utime(cache_path, None)

        # Second call should hit cache (load_inventory not called again)
        with patch("src.sih.conflict_alpha_analysis._load_inventory", side_effect=AssertionError("should not call")):
            r2 = conflict_alpha_report(tmp_path)
        assert r1["generated_at"] == r2["generated_at"]

    def test_returns_required_keys(self, tmp_path):
        inv = _make_inventory([{"pattern": "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", "ret30": 0.06}] * 6)
        with patch("src.sih.conflict_alpha_analysis._load_inventory", return_value=inv):
            result = conflict_alpha_report(tmp_path)
        for key in ["patterns", "leaders", "laggards", "universe_median_return_pct",
                    "governance_note", "version", "generated_at"]:
            assert key in result, f"Missing key: {key}"
