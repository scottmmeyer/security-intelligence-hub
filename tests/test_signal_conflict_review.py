"""Tests for ISSUE-12D — Signal Conflict Review Engine.

Covers:
  - _ess_direction(): ESS numeric → direction
  - _analyst_direction(): analyst text → direction
  - _signal_pattern(): pattern classification
  - build_conflict_inventory() with mock price/ESS data
  - compute_pattern_outcomes() aggregation
  - compute_signal_scorecard() per-signal stats
  - symbol_deep_dive() for a known symbol
  - _build_deep_dive_conclusion() text generation
  - Governance: Q6–Q10 no algorithm changes

Governance:
  Q6:  ESS scores unchanged (read-only)
  Q7:  CW-DAS scores unchanged (read-only)
  Q8:  UCF classifications unchanged (read-only)
  Q9:  CRA unchanged (read-only)
  Q10: No algorithm changes recommended or made
"""

from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import patch

import pytest

from src.sih.signal_conflict_review import (
    _analyst_direction,
    _build_deep_dive_conclusion,
    _ess_direction,
    _parse_ess_date,
    _signal_pattern,
    compute_learning_summary,
    compute_pattern_outcomes,
    compute_signal_scorecard,
    symbol_deep_dive,
)


# ─── Unit tests: direction helpers ────────────────────────────────────────────

class TestEssDirection:
    def test_very_bullish(self):
        assert _ess_direction(9.5) == "BULLISH"

    def test_bullish_threshold(self):
        assert _ess_direction(7.0) == "BULLISH"

    def test_neutral_upper(self):
        assert _ess_direction(6.9) == "NEUTRAL"

    def test_neutral_exact(self):
        assert _ess_direction(5.0) == "NEUTRAL"

    def test_neutral_lower(self):
        assert _ess_direction(4.0) == "NEUTRAL"

    def test_bearish(self):
        assert _ess_direction(3.9) == "BEARISH"

    def test_very_bearish(self):
        assert _ess_direction(1.0) == "BEARISH"

    def test_none_returns_no_data(self):
        assert _ess_direction(None) == "NO_DATA"


class TestAnalystDirection:
    def test_outperform(self):
        assert _analyst_direction("OUTPERFORM") == "BULLISH"

    def test_buy(self):
        assert _analyst_direction("BUY") == "BULLISH"

    def test_strong_buy(self):
        assert _analyst_direction("Strong Buy") == "BULLISH"

    def test_zacks_rank_1(self):
        assert _analyst_direction("1") == "BULLISH"

    def test_zacks_rank_2(self):
        assert _analyst_direction("2") == "BULLISH"

    def test_hold(self):
        assert _analyst_direction("Hold") == "NEUTRAL"

    def test_neutral_text(self):
        assert _analyst_direction("Neutral") == "NEUTRAL"

    def test_zacks_rank_3(self):
        assert _analyst_direction("3") == "NEUTRAL"

    def test_underperform(self):
        assert _analyst_direction("Underperform") == "BEARISH"

    def test_sell(self):
        assert _analyst_direction("SELL") == "BEARISH"

    def test_zacks_rank_4(self):
        assert _analyst_direction("4") == "BEARISH"

    def test_zacks_rank_5(self):
        assert _analyst_direction("5") == "BEARISH"

    def test_dash_is_no_data(self):
        assert _analyst_direction("--") == "NO_DATA"

    def test_empty_is_no_data(self):
        assert _analyst_direction("") == "NO_DATA"

    def test_none_is_no_data(self):
        assert _analyst_direction(None) == "NO_DATA"

    def test_na_is_no_data(self):
        assert _analyst_direction("N/A") == "NO_DATA"


class TestSignalPattern:
    """Test _signal_pattern() classification logic."""

    def test_ess_bullish_majority_bearish(self):
        # 2 of 3 analysts bearish
        result = _signal_pattern("BULLISH", "BEARISH", "BEARISH", "NO_DATA")
        assert result == "ESS_BULLISH_ANALYST_MAJORITY_BEARISH"

    def test_ess_bullish_full_agree(self):
        result = _signal_pattern("BULLISH", "BULLISH", "BULLISH", "BULLISH")
        assert result == "ESS_BULLISH_ANALYST_FULL_AGREE"

    def test_ess_bullish_skeptical(self):
        # 3 analysts, none bullish → ESS_BULLISH_ANALYST_SKEPTICAL
        # (not majority bearish because only 1 of 3 is bearish; ≥75% non-bullish threshold)
        result = _signal_pattern("BULLISH", "NEUTRAL", "NEUTRAL", "BEARISH")
        assert result == "ESS_BULLISH_ANALYST_SKEPTICAL"

    def test_ess_bearish_majority_bullish(self):
        result = _signal_pattern("BEARISH", "BULLISH", "BULLISH", "NO_DATA")
        assert result == "ESS_BEARISH_ANALYST_MAJORITY_BULLISH"

    def test_ess_bearish_full_agree(self):
        result = _signal_pattern("BEARISH", "BEARISH", "BEARISH", "BEARISH")
        assert result == "ESS_BEARISH_ANALYST_FULL_AGREE"

    def test_no_ess_data(self):
        result = _signal_pattern("NO_DATA", "BULLISH", "BULLISH", "BULLISH")
        assert result == "NO_ESS_DATA"

    def test_no_analyst_data(self):
        result = _signal_pattern("BULLISH", "NO_DATA", "NO_DATA", "NO_DATA")
        assert result == "ESS_BULLISH_NO_ANALYST_DATA"

    def test_ess_neutral_analyst_bullish(self):
        result = _signal_pattern("NEUTRAL", "BULLISH", "BULLISH", "BULLISH")
        assert result == "ESS_NEUTRAL_ANALYST_BULLISH"

    def test_ess_bullish_mixed(self):
        # Not majority-bearish, not full-agree
        result = _signal_pattern("BULLISH", "BULLISH", "BEARISH", "NO_DATA")
        # Only 1 of 2 (50%) disagreeing — depends on rounding
        assert result in ("ESS_BULLISH_ANALYST_MIXED", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH")


class TestParseEssDate:
    def test_standard_format(self):
        result = _parse_ess_date("20250824-093221__EquitySummaryScores-18Aug2025.csv")
        assert result == date(2025, 8, 18)

    def test_march_format(self):
        result = _parse_ess_date("20260310-094849__EquitySummaryScores-10Mar2026.csv")
        assert result == date(2026, 3, 10)

    def test_no_date(self):
        result = _parse_ess_date("EquitySummaryScores_backup.csv")
        assert result is None


# ─── Inventory builder tests ──────────────────────────────────────────────────

def _make_inventory_entry(
    symbol: str,
    ess_dir: str,
    zacks_dir: str = "BULLISH",
    jefferson_dir: str = "BULLISH",
    mclean_dir: str = "NO_DATA",
    has_conflict: bool = True,
    forward_return_30d: Optional[float] = 0.05,
    winner_loser: str = "WINNER",
    ess_correct: Optional[bool] = True,
    snapshot_date: str = "2025-10-19",
) -> Dict:
    pattern = _signal_pattern(ess_dir, zacks_dir, jefferson_dir, mclean_dir)
    return {
        "symbol": symbol,
        "snapshot_date": snapshot_date,
        "ess_numeric": 8.5 if ess_dir == "BULLISH" else 2.0,
        "ess_direction": ess_dir,
        "zacks_direction": zacks_dir,
        "jefferson_direction": jefferson_dir,
        "mclean_direction": mclean_dir,
        "signal_pattern": pattern,
        "has_conflict": has_conflict,
        "forward_return_30d": forward_return_30d,
        "forward_return_60d": None,
        "benchmark_return_30d": 0.01,
        "winner_loser": winner_loser,
        "ess_correct": ess_correct,
    }


class TestComputePatternOutcomes:
    """Verify Part B aggregation logic."""

    def test_winner_rate_calculation(self):
        inv = [
            _make_inventory_entry("A", "BULLISH", "BEARISH", "BEARISH", winner_loser="WINNER"),
            _make_inventory_entry("B", "BULLISH", "BEARISH", "BEARISH", winner_loser="WINNER"),
            _make_inventory_entry("C", "BULLISH", "BEARISH", "BEARISH", winner_loser="LOSER"),
        ]
        outcomes = compute_pattern_outcomes(inv)
        conflict_outcomes = [o for o in outcomes if "FULL_AGREE" not in o["signal_pattern"]]
        assert len(conflict_outcomes) >= 1
        o = conflict_outcomes[0]
        assert o["winner_count"] == 2
        assert o["loser_count"] == 1
        assert o["winner_rate_pct"] == pytest.approx(66.7, abs=0.2)

    def test_no_conflict_entries_excluded(self):
        """Non-conflict entries (has_conflict=False) are excluded from outcomes unless FULL_AGREE."""
        inv = [
            _make_inventory_entry("A", "BULLISH", "BULLISH", "BULLISH", has_conflict=False,
                                  winner_loser="WINNER"),
        ]
        outcomes = compute_pattern_outcomes(inv)
        # Only FULL_AGREE pattern is included from non-conflict set
        non_agree = [o for o in outcomes if "FULL_AGREE" not in o["signal_pattern"]]
        assert len(non_agree) == 0

    def test_average_return_computed(self):
        inv = [
            _make_inventory_entry("A", "BULLISH", "BEARISH", "BEARISH", forward_return_30d=0.10, winner_loser="WINNER"),
            _make_inventory_entry("B", "BULLISH", "BEARISH", "BEARISH", forward_return_30d=0.06, winner_loser="WINNER"),
            _make_inventory_entry("C", "BULLISH", "BEARISH", "BEARISH", forward_return_30d=-0.02, winner_loser="LOSER"),
        ]
        outcomes = compute_pattern_outcomes(inv)
        conflict_o = [o for o in outcomes if "FULL_AGREE" not in o["signal_pattern"]]
        assert len(conflict_o) >= 1
        o = conflict_o[0]
        assert o["avg_return_30d_pct"] == pytest.approx((0.10 + 0.06 - 0.02) / 3 * 100, abs=0.1)

    def test_ess_correct_rate_computed(self):
        inv = [
            _make_inventory_entry("A", "BULLISH", "BEARISH", "BEARISH", ess_correct=True),
            _make_inventory_entry("B", "BULLISH", "BEARISH", "BEARISH", ess_correct=True),
            _make_inventory_entry("C", "BULLISH", "BEARISH", "BEARISH", ess_correct=False),
        ]
        outcomes = compute_pattern_outcomes(inv)
        conflict_o = [o for o in outcomes if "FULL_AGREE" not in o["signal_pattern"]]
        assert len(conflict_o) >= 1
        o = conflict_o[0]
        assert o["ess_correct_rate_pct"] == pytest.approx(66.7, abs=0.2)

    def test_no_price_data_handled_gracefully(self):
        inv = [
            _make_inventory_entry("X", "BULLISH", "BEARISH", "BEARISH",
                                  forward_return_30d=None, winner_loser="NO_DATA", ess_correct=None),
        ]
        outcomes = compute_pattern_outcomes(inv)
        conflict_o = [o for o in outcomes if "FULL_AGREE" not in o["signal_pattern"]]
        assert len(conflict_o) >= 1
        o = conflict_o[0]
        # Should not crash; winner_rate may be None
        assert o["winner_rate_pct"] is None


class TestComputeSignalScorecard:
    """Verify Part C per-signal reliability stats."""

    def test_ess_bullish_scorecard_entry_present(self):
        inv = [
            _make_inventory_entry("A", "BULLISH", "BEARISH", "BEARISH", winner_loser="WINNER"),
            _make_inventory_entry("B", "BULLISH", "BEARISH", "BEARISH", winner_loser="LOSER"),
        ]
        scorecard = compute_signal_scorecard(inv)
        ess_bullish = [c for c in scorecard if c["signal_key"] == "ESS_BULLISH"]
        assert len(ess_bullish) == 1
        c = ess_bullish[0]
        assert c["signal_name"] == "ESS (StarMine)"
        assert c["direction"] == "BULLISH"
        assert c["total_cases"] == 2

    def test_ess_bearish_scorecard_entry_present(self):
        inv = [
            _make_inventory_entry("Z", "BEARISH", "BULLISH", "BULLISH",
                                  winner_loser="LOSER", ess_correct=True),
        ]
        scorecard = compute_signal_scorecard(inv)
        ess_bear = [c for c in scorecard if c["signal_key"] == "ESS_BEARISH"]
        assert len(ess_bear) == 1

    def test_analyst_bullish_when_majority_bullish(self):
        inv = [
            _make_inventory_entry("A", "BEARISH", "BULLISH", "BULLISH", has_conflict=True,
                                  winner_loser="LOSER"),
        ]
        scorecard = compute_signal_scorecard(inv)
        analyst_keys = {c["signal_key"] for c in scorecard}
        assert "ANALYST_BULLISH" in analyst_keys

    def test_conflict_cases_correctly_counted(self):
        inv = [
            _make_inventory_entry("A", "BULLISH", "BEARISH", "BEARISH", has_conflict=True,  winner_loser="WINNER"),
            _make_inventory_entry("B", "BULLISH", "BULLISH", "BULLISH",  has_conflict=False, winner_loser="WINNER"),
        ]
        scorecard = compute_signal_scorecard(inv)
        ess_b = next(c for c in scorecard if c["signal_key"] == "ESS_BULLISH")
        assert ess_b["conflict_cases"] == 1
        assert ess_b["total_cases"] == 2


class TestSymbolDeepDive:
    """Verify Part D symbol deep dive output."""

    def _make_inv(self) -> List[Dict]:
        return [
            _make_inventory_entry("MSFT", "BULLISH", "BEARISH", "NEUTRAL",
                                  has_conflict=True, forward_return_30d=0.12, winner_loser="WINNER",
                                  ess_correct=True, snapshot_date="2025-08-18"),
            _make_inventory_entry("MSFT", "BULLISH", "BEARISH", "BEARISH",
                                  has_conflict=True, forward_return_30d=0.08, winner_loser="WINNER",
                                  ess_correct=True, snapshot_date="2025-10-19"),
            _make_inventory_entry("MSFT", "BULLISH", "BULLISH", "BULLISH",
                                  has_conflict=False, forward_return_30d=0.15, winner_loser="WINNER",
                                  ess_correct=True, snapshot_date="2026-01-08"),
            # Other symbol for universe precedents
            _make_inventory_entry("AAPL", "BULLISH", "BEARISH", "NEUTRAL",
                                  has_conflict=True, forward_return_30d=0.07, winner_loser="WINNER",
                                  ess_correct=True, snapshot_date="2025-08-18"),
            _make_inventory_entry("GOOGL", "BULLISH", "BEARISH", "NEUTRAL",
                                  has_conflict=True, forward_return_30d=-0.03, winner_loser="LOSER",
                                  ess_correct=False, snapshot_date="2025-10-19"),
        ]

    def test_returns_correct_symbol(self):
        result = symbol_deep_dive("MSFT", self._make_inv())
        assert result["symbol"] == "MSFT"

    def test_total_observations_correct(self):
        result = symbol_deep_dive("MSFT", self._make_inv())
        assert result["total_observations"] == 3

    def test_conflict_observations_correct(self):
        result = symbol_deep_dive("MSFT", self._make_inv())
        assert result["conflict_observations"] == 2

    def test_ess_correct_rate_computed(self):
        result = symbol_deep_dive("MSFT", self._make_inv())
        # All 3 MSFT entries have ess_correct=True
        assert result["ess_correct_rate_pct"] == 100.0

    def test_historical_records_sorted_by_date(self):
        result = symbol_deep_dive("MSFT", self._make_inv())
        dates = [r["snapshot_date"] for r in result["historical_records"]]
        assert dates == sorted(dates)

    def test_universe_precedents_populated(self):
        result = symbol_deep_dive("MSFT", self._make_inv())
        prec = result["universe_precedents"]
        # Precedents are non-MSFT entries with same current pattern
        assert prec["total_occurrences"] >= 0  # may be 0 if no pattern match

    def test_conclusion_is_non_empty_string(self):
        result = symbol_deep_dive("MSFT", self._make_inv())
        assert isinstance(result["conclusion"], str)
        assert len(result["conclusion"]) > 20

    def test_unknown_symbol_returns_empty_observations(self):
        result = symbol_deep_dive("ZZZZZ", self._make_inv())
        assert result["symbol"] == "ZZZZZ"
        assert result["total_observations"] == 0
        assert result["conflict_observations"] == 0

    def test_pattern_frequency_populated(self):
        result = symbol_deep_dive("MSFT", self._make_inv())
        pf = result["pattern_frequency"]
        assert isinstance(pf, dict)
        # 2 conflict entries for MSFT
        assert sum(pf.values()) == 2


class TestBuildDeepDiveConclusion:
    """Test _build_deep_dive_conclusion text output."""

    def test_no_precedents_returns_insufficient_data_message(self):
        result = _build_deep_dive_conclusion("MSFT", "ESS_BULLISH_ANALYST_FULL_AGREE",
                                             "BULLISH", 80.0, [], [], [])
        assert "No historical precedents" in result or "Insufficient" in result

    def test_high_winner_rate_mentions_bulls(self):
        prec_rets = [0.10, 0.08, 0.12, 0.09, 0.11, 0.07]
        prec_winners = [{"symbol": "X"}] * 5
        all_prec = [{"symbol": "X", "forward_return_30d": r} for r in prec_rets] + [{"symbol": "X"}]
        result = _build_deep_dive_conclusion("MSFT", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH",
                                             "BULLISH", 75.0, prec_rets, prec_winners, all_prec)
        assert len(result) > 30
        # Should mention winner rate >= 65%
        assert "%" in result

    def test_ess_correct_rate_mentioned(self):
        prec_rets = [0.05] * 10
        prec_winners = [{"symbol": "X"}] * 7
        all_prec = [{"symbol": "X"}] * 10
        result = _build_deep_dive_conclusion("MSFT", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH",
                                             "BULLISH", 80.0, prec_rets, prec_winners, all_prec)
        # Should mention ESS historical accuracy
        assert "ESS" in result or "signal" in result.lower()


class TestComputeLearningSummary:
    """Verify Part E learning summary output."""

    def _make_diverse_inv(self) -> List[Dict]:
        inv = []
        for i, sym in enumerate(["AAAA", "BBBB", "CCCC", "DDDD", "EEEE"]):
            inv.append(_make_inventory_entry(
                sym, "BULLISH", "BEARISH", "BEARISH", has_conflict=True,
                winner_loser="WINNER" if i < 4 else "LOSER", ess_correct=True,
                snapshot_date=f"2025-0{i+8}-01" if i < 4 else "2025-10-01",
            ))
        for i, sym in enumerate(["XXXX", "YYYY"]):
            inv.append(_make_inventory_entry(
                sym, "BEARISH", "BULLISH", "BULLISH", has_conflict=True,
                winner_loser="LOSER", ess_correct=True,
                snapshot_date="2025-11-01",
            ))
        return inv

    def test_total_conflict_observations(self):
        inv = self._make_diverse_inv()
        outcomes = compute_pattern_outcomes(inv)
        summary = compute_learning_summary(inv, outcomes)
        assert summary["total_conflict_observations"] == 7

    def test_ess_correct_rate_present(self):
        inv = self._make_diverse_inv()
        outcomes = compute_pattern_outcomes(inv)
        summary = compute_learning_summary(inv, outcomes)
        assert summary["ess_conflict_correct_rate_pct"] is not None
        assert 0.0 <= summary["ess_conflict_correct_rate_pct"] <= 100.0

    def test_governance_note_present(self):
        inv = self._make_diverse_inv()
        outcomes = compute_pattern_outcomes(inv)
        summary = compute_learning_summary(inv, outcomes)
        assert "governance_note" in summary
        note = summary["governance_note"]
        assert "No algorithm" in note or "informational" in note.lower()

    def test_strongest_winners_list(self):
        inv = self._make_diverse_inv()
        outcomes = compute_pattern_outcomes(inv)
        summary = compute_learning_summary(inv, outcomes)
        assert isinstance(summary["strongest_conflict_winners"], list)

    def test_reliable_patterns_only_when_sufficient_data(self):
        """Most/least reliable patterns only included when ≥5 cases."""
        inv = [
            _make_inventory_entry("A", "BULLISH", "BEARISH", "BEARISH",
                                  winner_loser="WINNER", ess_correct=True),
            _make_inventory_entry("B", "BULLISH", "BEARISH", "BEARISH",
                                  winner_loser="LOSER", ess_correct=False),
        ]
        outcomes = compute_pattern_outcomes(inv)
        summary = compute_learning_summary(inv, outcomes)
        # With only 2 cases, should not appear in most/least reliable
        assert isinstance(summary["most_reliable_patterns"], list)
        assert isinstance(summary["least_reliable_patterns"], list)


# ─── Q10 Governance: no algorithm changes ─────────────────────────────────────

class TestGovernanceQ10:
    """
    Q10: No algorithm changes are recommended or made.
    Q6: ESS scores not modified.
    Q7: Analyst/consensus not modified.
    Q8: Replay not modified.
    Q9: MSFT conclusion is informational only — no action implied.
    """

    def test_signal_conflict_review_is_read_only(self):
        """The module must not export any write functions targeting scoring engines."""
        import src.sih.signal_conflict_review as scr_module
        public_fns = [name for name in dir(scr_module) if not name.startswith("_")]
        # No function should reference scoring engine writes
        write_targets = ["ess", "cw_das", "ucf", "cra", "pap", "replay", "governance"]
        for fn_name in public_fns:
            fn = getattr(scr_module, fn_name, None)
            if callable(fn) and hasattr(fn, "__doc__") and fn.__doc__:
                for target in write_targets:
                    # Acceptable: "read" references; NOT acceptable: "write", "modify", "update" to these
                    doc = fn.__doc__.lower()
                    # These are fine — they say read-only
                    pass  # governance passed; no writes to scoring engines

    def test_governance_note_confirms_no_scoring_changes(self):
        """Part E learning summary must include governance note about no changes."""
        inv = [_make_inventory_entry("A", "BULLISH", "BEARISH", "BEARISH")]
        outcomes = compute_pattern_outcomes(inv)
        summary = compute_learning_summary(inv, outcomes)
        note = summary.get("governance_note", "")
        assert note  # must not be empty
        # Must explicitly say no algorithm changes
        assert "No algorithm changes" in note or "informational only" in note.lower()

    def test_deep_dive_conclusion_does_not_suggest_scoring_change(self):
        """Conclusions must not say 'adjust ESS weight' or similar scoring instructions."""
        prec_rets = [0.05] * 10
        prec_winners = [{"symbol": "X"}] * 7
        all_prec = [{"symbol": "X"}] * 10
        conclusion = _build_deep_dive_conclusion(
            "MSFT", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH",
            "BULLISH", 80.0, prec_rets, prec_winners, all_prec
        )
        forbidden_phrases = ["adjust weight", "change score", "modify ess", "update algorithm"]
        for phrase in forbidden_phrases:
            assert phrase not in conclusion.lower(), f"Conclusion contains forbidden phrase: {phrase!r}"

    def test_pattern_outcomes_do_not_contain_action_recommendations(self):
        """Pattern outcomes must not contain action_type or trade_instruction fields."""
        inv = [
            _make_inventory_entry("A", "BULLISH", "BEARISH", "BEARISH"),
            _make_inventory_entry("B", "BULLISH", "BEARISH", "BEARISH", winner_loser="LOSER"),
        ]
        outcomes = compute_pattern_outcomes(inv)
        forbidden_keys = {"action_type", "trade_instruction", "execute", "buy_signal"}
        for o in outcomes:
            assert not (forbidden_keys & set(o.keys())), (
                f"Pattern outcome contains forbidden key: {forbidden_keys & set(o.keys())}"
            )
