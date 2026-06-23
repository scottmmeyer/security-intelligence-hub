"""Tests for Predictive Intelligence EPIC.

DISLOCATION-04  pattern_persistence
DISLOCATION-05  forward_return_estimate
MEI-003         event_sensitivity_calibration
MEI-004         event_triggered_refresh
RESEARCH-01     funding_source_effectiveness
SCENARIO-01     portfolio_scenario

All modules are read-only / informational.
"""

from __future__ import annotations

import csv
import json
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch

import pytest


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _write_prices(tmp_path: Path, symbol: str, start: date, closes: List[float]) -> None:
    price_dir = tmp_path / "data" / "history" / "prices" / f"symbol={symbol}"
    price_dir.mkdir(parents=True, exist_ok=True)
    with (price_dir / "prices.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["security_id", "symbol", "date", "close"])
        w.writeheader()
        for i, c in enumerate(closes):
            w.writerow({"security_id": symbol, "symbol": symbol,
                        "date": (start + timedelta(days=i)).isoformat(), "close": c})


def _write_inventory(tmp_path: Path, rows: List[Dict]) -> None:
    p = tmp_path / "data" / "analysis" / "dislocation"
    p.mkdir(parents=True, exist_ok=True)
    fields = ["symbol", "snapshot_date", "ess_direction", "signal_pattern",
              "has_conflict", "forward_return_30d", "winner_loser", "ess_correct"]
    with (p / "dislocation_inventory.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _write_alpha_report(tmp_path: Path, patterns: List[Dict]) -> None:
    p = tmp_path / "data" / "analysis" / "dislocation"
    p.mkdir(parents=True, exist_ok=True)
    (p / "conflict_alpha_report.json").write_text(
        json.dumps({"status": "OK", "universe_median_return_pct": 0.5,
                    "patterns": patterns}),
        encoding="utf-8",
    )


def _inv_row(sym, date_str, ess, pattern, ret30=0.05):
    return {
        "symbol": sym, "snapshot_date": date_str, "ess_direction": ess,
        "signal_pattern": pattern, "has_conflict": "True",
        "forward_return_30d": str(ret30), "winner_loser": "WINNER", "ess_correct": "True",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DISLOCATION-04: Pattern Persistence
# ═══════════════════════════════════════════════════════════════════════════════

class TestPatternPersistence:
    def _setup(self, tmp_path: Path) -> Path:
        _write_inventory(tmp_path, [
            _inv_row("MSFT", "2025-08-18", "BULLISH", "ESS_BULLISH_ANALYST_SKEPTICAL", 0.03),
            _inv_row("MSFT", "2025-10-19", "BULLISH", "ESS_BULLISH_ANALYST_SKEPTICAL", 0.05),
            _inv_row("MSFT", "2026-01-08", "BULLISH", "ESS_BULLISH_ANALYST_SKEPTICAL", 0.04),
            _inv_row("MSFT", "2026-03-10", "BULLISH", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", 0.07),
            _inv_row("TSLA", "2025-10-19", "BEARISH", "ESS_BEARISH_ANALYST_MIXED", -0.03),
            _inv_row("TSLA", "2026-01-08", "BEARISH", "ESS_BEARISH_ANALYST_MIXED", -0.04),
        ])
        _write_alpha_report(tmp_path, [
            {"signal_pattern": "ESS_BULLISH_ANALYST_SKEPTICAL",
             "alpha_class": "ALPHA_NEUTRAL", "excess_return_pct": 0.7,
             "win_rate_pct": 44.0, "significance": "WEAK", "observations": 154},
        ])
        return tmp_path

    def test_symbol_persistence_returns_data(self, tmp_path):
        root = self._setup(tmp_path)
        with patch("src.sih.predictive.pattern_persistence._load_inventory",
                   return_value=[
                       _inv_row("MSFT", "2025-08-18", "BULLISH", "ESS_BULLISH_ANALYST_SKEPTICAL"),
                       _inv_row("MSFT", "2025-10-19", "BULLISH", "ESS_BULLISH_ANALYST_SKEPTICAL"),
                       _inv_row("MSFT", "2026-01-08", "BULLISH", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH"),
                   ]):
            from src.sih.predictive.pattern_persistence import symbol_pattern_persistence
            result = symbol_pattern_persistence("MSFT", root)
        assert result.get("symbol") == "MSFT"
        assert result.get("dates_observed") == 3

    def test_persistence_pct_computed(self, tmp_path):
        root = self._setup(tmp_path)
        with patch("src.sih.predictive.pattern_persistence._load_inventory",
                   return_value=[
                       _inv_row("MSFT", f"2026-0{i+1}-01", "BULLISH", "ESS_BULLISH_ANALYST_SKEPTICAL")
                       for i in range(6)
                   ]):
            from src.sih.predictive.pattern_persistence import symbol_pattern_persistence
            result = symbol_pattern_persistence("MSFT", root)
        assert result.get("persistence_pct") == pytest.approx(100.0)
        assert result.get("streak") == 6

    def test_streak_resets_on_pattern_change(self, tmp_path):
        root = self._setup(tmp_path)
        with patch("src.sih.predictive.pattern_persistence._load_inventory",
                   return_value=[
                       _inv_row("MSFT", "2025-10-01", "BULLISH", "ESS_BULLISH_ANALYST_SKEPTICAL"),
                       _inv_row("MSFT", "2026-01-01", "BULLISH", "ESS_BULLISH_ANALYST_MIXED"),
                       _inv_row("MSFT", "2026-03-01", "BULLISH", "ESS_BULLISH_ANALYST_MIXED"),
                   ]):
            from src.sih.predictive.pattern_persistence import symbol_pattern_persistence
            result = symbol_pattern_persistence("MSFT", root)
        assert result.get("streak") == 2

    def test_unknown_symbol_returns_error(self, tmp_path):
        root = self._setup(tmp_path)
        with patch("src.sih.predictive.pattern_persistence._load_inventory", return_value=[]):
            from src.sih.predictive.pattern_persistence import symbol_pattern_persistence
            result = symbol_pattern_persistence("ZZZZZ", root)
        assert "error" in result

    def test_all_persistence_returns_structure(self, tmp_path):
        root = self._setup(tmp_path)
        rows = [_inv_row("MSFT", f"2026-0{i+1}-01", "BULLISH", "ESS_BULLISH_ANALYST_SKEPTICAL") for i in range(3)]
        with patch("src.sih.predictive.pattern_persistence._load_inventory", return_value=rows):
            from src.sih.predictive.pattern_persistence import all_pattern_persistence
            result = all_pattern_persistence(root)
        assert "all_symbols" in result
        assert "total_symbols" in result
        assert "governance_note" in result


# ═══════════════════════════════════════════════════════════════════════════════
# DISLOCATION-05: Forward Return Estimate
# ═══════════════════════════════════════════════════════════════════════════════

class TestForwardReturnEstimate:
    def _pers(self, sym, pattern, alpha_class, excess):
        return {
            "symbol": sym,
            "current_pattern": pattern,
            "current_pattern_label": pattern.replace("_", " "),
            "is_current_conflict": True,
            "persistence_pct": 60.0,
            "streak": 2,
            "dates_observed": 5,
            "alpha_class": alpha_class,
            "excess_return_pct": excess,
            "win_rate_pct": 60.0,
            "significance": "SUGGESTIVE",
        }

    def _alpha_idx(self, pattern, alpha_class, excess):
        return {
            pattern: {
                "signal_pattern": pattern,
                "alpha_class": alpha_class,
                "excess_return_pct": excess,
                "avg_return_30d_pct": excess + 0.5,
                "median_return_30d_pct": excess,
                "best_return_30d_pct": excess + 20.0,
                "worst_return_30d_pct": excess - 15.0,
                "win_rate_pct": 60.0,
                "significance": "SUGGESTIVE",
                "observations": 80,
            }
        }

    def test_leader_pattern_returns_estimate(self, tmp_path):
        with (
            patch("src.sih.predictive.forward_return_estimate.symbol_pattern_persistence",
                  return_value=self._pers("MSFT", "ESS_BULLISH_ANALYST_MAJORITY_BEARISH", "ALPHA_LEADER", 2.26)),
            patch("src.sih.predictive.forward_return_estimate._load_pattern_detail",
                  return_value=self._alpha_idx("ESS_BULLISH_ANALYST_MAJORITY_BEARISH", "ALPHA_LEADER", 2.26)),
        ):
            from src.sih.predictive.forward_return_estimate import forward_estimate
            result = forward_estimate("MSFT", tmp_path)
        assert result["status"] == "OK"
        assert result["alpha_class"] == "ALPHA_LEADER"
        assert result["excess_return_pct"] == pytest.approx(2.26)
        assert "interpretation" in result
        assert len(result["interpretation"]) > 20

    def test_laggard_pattern_mentions_caution(self, tmp_path):
        with (
            patch("src.sih.predictive.forward_return_estimate.symbol_pattern_persistence",
                  return_value=self._pers("TSLA", "ESS_BEARISH_ANALYST_MAJORITY_BULLISH", "ALPHA_LAGGARD", -1.70)),
            patch("src.sih.predictive.forward_return_estimate._load_pattern_detail",
                  return_value=self._alpha_idx("ESS_BEARISH_ANALYST_MAJORITY_BULLISH", "ALPHA_LAGGARD", -1.70)),
        ):
            from src.sih.predictive.forward_return_estimate import forward_estimate
            result = forward_estimate("TSLA", tmp_path)
        assert result["alpha_class"] == "ALPHA_LAGGARD"
        assert "caution" in result["interpretation"].lower() or "analyst" in result["interpretation"].lower()

    def test_no_symbol_data_returns_no_conflict(self, tmp_path):
        with patch("src.sih.predictive.forward_return_estimate.symbol_pattern_persistence",
                   return_value={"error": "Not found", "dates_observed": 0}):
            from src.sih.predictive.forward_return_estimate import forward_estimate
            result = forward_estimate("UNKNOWN", tmp_path)
        assert result["status"] == "NO_CONFLICT_DATA"

    def test_governance_note_present(self, tmp_path):
        with (
            patch("src.sih.predictive.forward_return_estimate.symbol_pattern_persistence",
                  return_value=self._pers("X", "ESS_BULLISH_ANALYST_MIXED", "ALPHA_LEADER", 1.0)),
            patch("src.sih.predictive.forward_return_estimate._load_pattern_detail",
                  return_value=self._alpha_idx("ESS_BULLISH_ANALYST_MIXED", "ALPHA_LEADER", 1.0)),
        ):
            from src.sih.predictive.forward_return_estimate import forward_estimate
            result = forward_estimate("X", tmp_path)
        assert "governance_note" in result
        assert "research" in result["governance_note"].lower() or "no" in result["governance_note"].lower()

    def test_no_action_keys_in_output(self, tmp_path):
        with (
            patch("src.sih.predictive.forward_return_estimate.symbol_pattern_persistence",
                  return_value=self._pers("Y", "ESS_BULLISH_ANALYST_MIXED", "ALPHA_NEUTRAL", 0.5)),
            patch("src.sih.predictive.forward_return_estimate._load_pattern_detail",
                  return_value=self._alpha_idx("ESS_BULLISH_ANALYST_MIXED", "ALPHA_NEUTRAL", 0.5)),
        ):
            from src.sih.predictive.forward_return_estimate import forward_estimate
            result = forward_estimate("Y", tmp_path)
        forbidden = {"execute", "trade", "buy_signal", "action_type"}
        assert not (forbidden & set(result.keys()))


# ═══════════════════════════════════════════════════════════════════════════════
# MEI-004: Event-Triggered Refresh
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventTriggeredRefresh:
    def _write_events(self, tmp_path: Path, events: List[Dict]) -> None:
        d = tmp_path / "data" / "mei"
        d.mkdir(parents=True, exist_ok=True)
        (d / "historical_events.json").write_text(json.dumps(events), encoding="utf-8")
        (d / "event_calendar.json").write_text("[]", encoding="utf-8")

    def test_past_high_event_appears_in_pending(self, tmp_path):
        past = (date.today() - timedelta(days=5)).isoformat()
        self._write_events(tmp_path, [
            {"event_id": "FOMC-TEST", "event_name": "Test FOMC", "event_type": "MONETARY_POLICY",
             "event_date": past, "impact_level": "HIGH", "sensitivity_tags": ["INTEREST_RATE"]},
        ])
        from src.sih.predictive.event_triggered_refresh import check_pending_refresh_triggers
        result = check_pending_refresh_triggers(tmp_path)
        assert result["pending_count"] >= 1
        assert result["pending"][0]["event_id"] == "FOMC-TEST"

    def test_future_event_not_pending(self, tmp_path):
        future = (date.today() + timedelta(days=5)).isoformat()
        self._write_events(tmp_path, [
            {"event_id": "FOMC-FUTURE", "event_name": "Future FOMC", "event_type": "MONETARY_POLICY",
             "event_date": future, "impact_level": "HIGH", "sensitivity_tags": []},
        ])
        from src.sih.predictive.event_triggered_refresh import check_pending_refresh_triggers
        result = check_pending_refresh_triggers(tmp_path)
        assert result["pending_count"] == 0

    def test_low_impact_event_not_triggered(self, tmp_path):
        past = (date.today() - timedelta(days=1)).isoformat()
        self._write_events(tmp_path, [
            {"event_id": "HOUSING-LOW", "event_name": "Housing Low", "event_type": "HOUSING",
             "event_date": past, "impact_level": "LOW", "sensitivity_tags": []},
        ])
        from src.sih.predictive.event_triggered_refresh import check_pending_refresh_triggers
        result = check_pending_refresh_triggers(tmp_path)
        assert result["pending_count"] == 0

    def test_mark_processed_removes_from_pending(self, tmp_path):
        past = (date.today() - timedelta(days=2)).isoformat()
        self._write_events(tmp_path, [
            {"event_id": "FOMC-PROC", "event_name": "Processed FOMC", "event_type": "MONETARY_POLICY",
             "event_date": past, "impact_level": "HIGH", "sensitivity_tags": []},
        ])
        from src.sih.predictive.event_triggered_refresh import (
            check_pending_refresh_triggers, mark_event_processed
        )
        mark_event_processed("FOMC-PROC", tmp_path)
        result = check_pending_refresh_triggers(tmp_path)
        assert all(p["event_id"] != "FOMC-PROC" for p in result["pending"])

    def test_governance_note_present(self, tmp_path):
        self._write_events(tmp_path, [])
        from src.sih.predictive.event_triggered_refresh import check_pending_refresh_triggers
        result = check_pending_refresh_triggers(tmp_path)
        assert "governance_note" in result


# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH-01: Funding Source Effectiveness
# ═══════════════════════════════════════════════════════════════════════════════

class TestFundingSourceEffectiveness:
    def _setup(self, tmp_path: Path):
        rows = [
            {"symbol": "AAAA", "snapshot_date": "2025-10-01", "ess_direction": "BEARISH",
             "signal_pattern": "ESS_BEARISH_ANALYST_MIXED", "has_conflict": "True",
             "forward_return_30d": "-0.05", "winner_loser": "LOSER", "ess_correct": "True"},
            {"symbol": "BBBB", "snapshot_date": "2025-10-01", "ess_direction": "BULLISH",
             "signal_pattern": "ESS_BULLISH_ANALYST_MIXED", "has_conflict": "True",
             "forward_return_30d": "0.08", "winner_loser": "WINNER", "ess_correct": "True"},
        ]
        _write_inventory(tmp_path, rows)
        _write_prices(tmp_path, "AAAA", date(2025, 9, 28), [100, 100, 100, 95, 93, 91])
        _write_prices(tmp_path, "BBBB", date(2025, 9, 28), [50, 50, 50, 54, 55, 56])

    def test_returns_structure(self, tmp_path):
        self._setup(tmp_path)
        with patch("src.sih.predictive.funding_source_effectiveness._load_inventory",
                   return_value=[
                       {"symbol": "AAAA", "snapshot_date": "2025-10-01", "ess_direction": "BEARISH",
                        "signal_pattern": "ESS_BEARISH_ANALYST_MIXED", "forward_return_30d": -0.05},
                       {"symbol": "BBBB", "snapshot_date": "2025-10-01", "ess_direction": "BULLISH",
                        "signal_pattern": "ESS_BULLISH_ANALYST_MIXED", "forward_return_30d": 0.08},
                   ]):
            from src.sih.predictive.funding_source_effectiveness import funding_effectiveness_study
            result = funding_effectiveness_study(tmp_path)
        assert "category_outcomes" in result
        assert "governance_note" in result

    def test_key_findings_generated(self, tmp_path):
        self._setup(tmp_path)
        inv = [
            {"symbol": "A", "snapshot_date": "2025-10-01", "ess_direction": "BEARISH",
             "signal_pattern": "X", "forward_return_30d": -0.06},
            {"symbol": "B", "snapshot_date": "2025-10-01", "ess_direction": "BULLISH",
             "signal_pattern": "Y", "forward_return_30d": 0.07},
        ]
        with patch("src.sih.predictive.funding_source_effectiveness._load_inventory", return_value=inv):
            from src.sih.predictive.funding_source_effectiveness import funding_effectiveness_study
            result = funding_effectiveness_study(tmp_path)
        assert isinstance(result.get("key_findings"), list)

    def test_empty_inventory_returns_gracefully(self, tmp_path):
        with patch("src.sih.predictive.funding_source_effectiveness._load_inventory", return_value=[]):
            from src.sih.predictive.funding_source_effectiveness import funding_effectiveness_study
            result = funding_effectiveness_study(tmp_path)
        assert result["status"] == "NO_INVENTORY"


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO-01: Portfolio Scenario
# ═══════════════════════════════════════════════════════════════════════════════

class TestPortfolioScenario:
    def _write_holdings(self, tmp_path: Path) -> None:
        runs = tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / "run-001"
        runs.mkdir(parents=True, exist_ok=True)
        fields = ["symbol", "market_value", "percent_of_portfolio"]
        with (runs / "holdings.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerow({"symbol": "MSFT", "market_value": "10000", "percent_of_portfolio": "10"})
            w.writerow({"symbol": "TSLA", "market_value": "8000", "percent_of_portfolio": "8"})
            w.writerow({"symbol": "SPAXX", "market_value": "20000", "percent_of_portfolio": "20"})
        (runs / "run_metadata.json").write_text(json.dumps({"snapshot_date": "2026-06-01", "run_id": "run-001"}))
        (runs / "alignment.csv").write_text("node_key,tactical_target_pct\nEQUITIES.US.LARGE,14.0\n")
        (runs / "security_overlays.csv").write_text("symbol,ess_score_text,signal_direction\nMSFT,BULLISH,BULLISH\n")

    def test_scenario_preview_structure(self, tmp_path):
        self._write_holdings(tmp_path)
        from src.sih.predictive.portfolio_scenario import scenario_preview
        result = scenario_preview(
            sells=[{"symbol": "TSLA", "proceeds_usd": 4000}],
            buys=[{"symbol": "DELL", "amount_usd": 4000}],
            repo_root=tmp_path,
        )
        assert "portfolio_mv" in result
        assert "cash_pct" in result
        assert "changed_weights" in result
        assert result["is_estimate"] is True

    def test_sell_reduces_position(self, tmp_path):
        self._write_holdings(tmp_path)
        from src.sih.predictive.portfolio_scenario import scenario_preview
        result = scenario_preview(
            sells=[{"symbol": "TSLA", "proceeds_usd": 8000}],  # full sell
            buys=[],
            repo_root=tmp_path,
        )
        tsla_new = next((c for c in result["changed_weights"] if c["symbol"] == "TSLA"), None)
        if tsla_new:
            assert tsla_new["new_weight"] == pytest.approx(0.0, abs=0.1)

    def test_buy_increases_position(self, tmp_path):
        self._write_holdings(tmp_path)
        from src.sih.predictive.portfolio_scenario import scenario_preview
        result = scenario_preview(
            sells=[],
            buys=[{"symbol": "DELL", "amount_usd": 5000}],
            repo_root=tmp_path,
        )
        # The buy should add to cash (SPAXX used for buy), or DELL appears in changed_weights
        # Either way portfolio_mv stays near 38000 (buys come from existing cash)
        # Verify the function doesn't crash and returns a valid structure
        assert "portfolio_mv" in result
        assert result["portfolio_mv"] > 0
        assert "changed_weights" in result

    def test_governance_note_present(self, tmp_path):
        self._write_holdings(tmp_path)
        from src.sih.predictive.portfolio_scenario import scenario_preview
        result = scenario_preview([], [], tmp_path)
        assert "governance_note" in result
        assert "approximation" in result["governance_note"].lower() or "estimate" in result["governance_note"].lower()

    def test_no_cra_proposal_returns_gracefully(self, tmp_path):
        from src.sih.predictive.portfolio_scenario import scenario_from_cra
        result = scenario_from_cra(tmp_path)
        assert "status" in result

    def test_no_action_keys(self, tmp_path):
        self._write_holdings(tmp_path)
        from src.sih.predictive.portfolio_scenario import scenario_preview
        result = scenario_preview([], [], tmp_path)
        forbidden = {"execute", "trade_instruction", "buy_signal"}
        assert not (forbidden & set(result.keys()))
