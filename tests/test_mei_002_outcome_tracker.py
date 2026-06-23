"""Tests for MEI-002 — Event Outcome Attribution & Portfolio Learning.

Covers:
  - _load_price_series()
  - _forward_return()
  - _compute_event_outcome() — portfolio + security attribution
  - _compute_event_type_effectiveness() — aggregation
  - mei_outcomes() / mei_event_impact() / mei_outcome_summary() — public API
  - refresh_event_outcomes() — rebuild

Governance:
  Q5–Q7: No recommendations, CW-DAS, or governance changes
  Q8: Informational only
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

from src.mei.event_outcome_tracker import (
    _active_holdings,
    _compute_event_type_effectiveness,
    _forward_return,
    _nearest_price_after,
    _nearest_price_before,
    mei_event_impact,
    mei_outcome_summary,
    mei_outcomes,
    refresh_event_outcomes,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_price_series(start: date, prices: List[float]) -> Dict[str, float]:
    return {
        (start + timedelta(days=i)).isoformat(): p
        for i, p in enumerate(prices)
    }


def _make_event(eid: str, etype: str, event_date: str, impact: str = "HIGH") -> Dict:
    return {
        "event_id":        eid,
        "event_name":      f"Test {eid}",
        "event_type":      etype,
        "event_date":      event_date,
        "impact_level":    impact,
        "sensitivity_tags": ["INTEREST_RATE"],
    }


def _make_holding(symbol: str, mv: float, pct: float = 2.0) -> Dict:
    return {
        "_symbol": symbol,
        "_mv":     mv,
        "symbol":  symbol,
        "market_value": str(mv),
        "percent_of_portfolio": str(pct),
    }


def _write_holdings(tmp_path: Path, holdings: List[Dict]) -> None:
    runs = tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / "run-001"
    runs.mkdir(parents=True, exist_ok=True)
    fields = ["symbol", "market_value", "percent_of_portfolio"]
    with (runs / "holdings.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for h in holdings:
            w.writerow({k: h.get(k, "") for k in fields})


def _write_prices(tmp_path: Path, symbol: str, series: Dict[str, float]) -> None:
    price_dir = tmp_path / "data" / "history" / "prices" / f"symbol={symbol}"
    price_dir.mkdir(parents=True, exist_ok=True)
    with (price_dir / "prices.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["security_id", "symbol", "date", "close"])
        w.writeheader()
        for d, p in sorted(series.items()):
            w.writerow({"security_id": f"SYM:{symbol}", "symbol": symbol, "date": d, "close": p})


def _write_historical_events(tmp_path: Path, events: List[Dict]) -> None:
    p = tmp_path / "data" / "mei" / "historical_events.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(events), encoding="utf-8")
    # empty calendar
    (tmp_path / "data" / "mei" / "event_calendar.json").write_text("[]", encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
# Price helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestPriceHelpers:
    def test_nearest_price_after_finds_exact(self):
        prices = {"2026-01-10": 100.0, "2026-01-11": 101.0}
        result = _nearest_price_after(prices, date(2026, 1, 10))
        assert result == ("2026-01-10", 100.0)

    def test_nearest_price_after_skips_weekend(self):
        prices = {"2026-01-12": 102.0}  # only Monday available
        result = _nearest_price_after(prices, date(2026, 1, 10), max_gap=5)  # Sat
        assert result == ("2026-01-12", 102.0)

    def test_nearest_price_before_finds_exact(self):
        prices = {"2026-01-10": 100.0}
        result = _nearest_price_before(prices, date(2026, 1, 10))
        assert result == ("2026-01-10", 100.0)

    def test_nearest_price_after_returns_none_beyond_gap(self):
        prices = {"2026-01-20": 100.0}
        result = _nearest_price_after(prices, date(2026, 1, 10), max_gap=5)
        assert result is None

    def test_forward_return_positive(self):
        prices = _make_price_series(date(2026, 1, 1), [100, 100, 100, 100, 100, 110])
        r = _forward_return(prices, date(2026, 1, 1), 5)
        assert r == pytest.approx(0.10)

    def test_forward_return_negative(self):
        prices = _make_price_series(date(2026, 1, 1), [100, 100, 100, 100, 100, 90])
        r = _forward_return(prices, date(2026, 1, 1), 5)
        assert r == pytest.approx(-0.10)

    def test_forward_return_none_when_no_data(self):
        prices = {"2026-01-01": 100.0}  # no future prices
        r = _forward_return(prices, date(2026, 1, 1), 5)
        assert r is None


# ═══════════════════════════════════════════════════════════════════════════════
# _active_holdings
# ═══════════════════════════════════════════════════════════════════════════════

class TestActiveHoldings:
    def test_excludes_spaxx(self):
        raw = [{"symbol": "SPAXX", "market_value": "5000"}, {"symbol": "MSFT", "market_value": "10000"}]
        result = _active_holdings(raw)
        assert all(h["_symbol"] != "SPAXX" for h in result)
        assert any(h["_symbol"] == "MSFT" for h in result)

    def test_excludes_zero_mv(self):
        raw = [{"symbol": "ZERO", "market_value": "0"}, {"symbol": "REAL", "market_value": "5000"}]
        result = _active_holdings(raw)
        syms = [h["_symbol"] for h in result]
        assert "ZERO" not in syms
        assert "REAL" in syms

    def test_mv_parsed_correctly(self):
        raw = [{"symbol": "X", "market_value": "12345.67"}]
        result = _active_holdings(raw)
        assert result[0]["_mv"] == pytest.approx(12345.67)


# ═══════════════════════════════════════════════════════════════════════════════
# _compute_event_type_effectiveness
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventTypeEffectiveness:
    def _outcomes(self, etype: str, ret1s: List[float], ret5s: List[float]):
        return [
            {
                "event_type": etype,
                "portfolio_return_1d": r1,
                "portfolio_return_5d": r5,
                "surprise_factor": abs(r1),
            }
            for r1, r5 in zip(ret1s, ret5s)
        ]

    def test_computes_avg_returns(self):
        outcomes = self._outcomes("MONETARY_POLICY", [0.5, -0.5, 1.0], [1.0, -1.0, 2.0])
        results = _compute_event_type_effectiveness(outcomes)
        mp = next(r for r in results if r["event_type"] == "MONETARY_POLICY")
        assert mp["event_count"] == 3
        assert mp["avg_return_5d_pct"] == pytest.approx(2.0 / 3, abs=0.01)

    def test_importance_score_positive(self):
        outcomes = self._outcomes("INFLATION", [1.0, 2.0], [2.0, 3.0])
        results = _compute_event_type_effectiveness(outcomes)
        inf = next(r for r in results if r["event_type"] == "INFLATION")
        assert inf["importance_score"] > 0

    def test_sorted_by_importance_descending(self):
        outcomes = (
            self._outcomes("MONETARY_POLICY", [5.0] * 10, [5.0] * 10) +
            self._outcomes("HOUSING", [0.1], [0.1])
        )
        results = _compute_event_type_effectiveness(outcomes)
        scores = [r["importance_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_consistency_computed(self):
        # All move in same direction on 1d and 5d
        outcomes = self._outcomes("LABOR_MARKET", [1.0, 1.0, 1.0], [1.0, 1.0, 1.0])
        results = _compute_event_type_effectiveness(outcomes)
        lm = next(r for r in results if r["event_type"] == "LABOR_MARKET")
        assert lm["consistency_pct"] == pytest.approx(100.0)

    def test_empty_outcomes_returns_empty_list(self):
        assert _compute_event_type_effectiveness([]) == []


# ═══════════════════════════════════════════════════════════════════════════════
# End-to-end: mei_outcomes + mei_event_impact + mei_outcome_summary
# ═══════════════════════════════════════════════════════════════════════════════

class TestPublicAPI:
    def _setup(self, tmp_path: Path):
        """Set up a minimal repo with 2 past events and price data for 2 securities."""
        event_date = date(2026, 1, 15)
        prices_a = _make_price_series(event_date - timedelta(days=3), [100, 100, 100, 100, 105, 108, 107, 106, 109, 110, 112])
        prices_b = _make_price_series(event_date - timedelta(days=3), [50, 50, 50, 50, 48, 47, 46, 45, 46, 47, 46])

        _write_prices(tmp_path, "AAAA", prices_a)
        _write_prices(tmp_path, "BBBB", prices_b)
        _write_holdings(tmp_path, [
            {"symbol": "AAAA", "market_value": "10000", "percent_of_portfolio": "5.0"},
            {"symbol": "BBBB", "market_value": "10000", "percent_of_portfolio": "5.0"},
        ])
        events = [
            _make_event("FOMC-TEST-001", "MONETARY_POLICY", event_date.isoformat()),
            _make_event("CPI-TEST-001", "INFLATION", (event_date + timedelta(days=3)).isoformat()),
        ]
        _write_historical_events(tmp_path, events)

    def test_mei_outcomes_returns_structure(self, tmp_path):
        self._setup(tmp_path)
        result = mei_outcomes(repo_root=tmp_path)
        assert "outcomes" in result
        assert "effectiveness" in result
        assert "event_count" in result
        assert result["event_count"] >= 1

    def test_outcomes_have_portfolio_returns(self, tmp_path):
        self._setup(tmp_path)
        result = mei_outcomes(repo_root=tmp_path)
        attributed = [o for o in result["outcomes"] if o.get("portfolio_return_5d") is not None]
        assert len(attributed) >= 1

    def test_outcomes_have_winners_losers(self, tmp_path):
        self._setup(tmp_path)
        result = mei_outcomes(repo_root=tmp_path)
        attributed = [o for o in result["outcomes"] if o.get("portfolio_return_5d") is not None]
        if attributed:
            o = attributed[0]
            assert "top_winners" in o
            assert "top_losers" in o
            assert isinstance(o["top_winners"], list)

    def test_security_returns_stripped_from_outcomes_list(self, tmp_path):
        """mei_outcomes() must not include security_returns in the outcomes list."""
        self._setup(tmp_path)
        result = mei_outcomes(repo_root=tmp_path)
        for o in result["outcomes"]:
            assert "security_returns" not in o

    def test_effectiveness_contains_event_types(self, tmp_path):
        self._setup(tmp_path)
        result = mei_outcomes(repo_root=tmp_path)
        types = {r["event_type"] for r in result.get("effectiveness", [])}
        # At least one of our seeded types should appear
        assert len(types) >= 1

    def test_mei_event_impact_returns_effectiveness(self, tmp_path):
        self._setup(tmp_path)
        result = mei_event_impact(repo_root=tmp_path)
        assert "effectiveness" in result
        assert isinstance(result["effectiveness"], list)

    def test_mei_outcome_summary_keys(self, tmp_path):
        self._setup(tmp_path)
        result = mei_outcome_summary(repo_root=tmp_path)
        for key in ["event_count", "attributed_count", "most_impactful",
                    "top_event_types", "governance_note"]:
            assert key in result

    def test_governance_note_present(self, tmp_path):
        self._setup(tmp_path)
        result = mei_outcome_summary(repo_root=tmp_path)
        note = result.get("governance_note", "")
        assert len(note) > 20
        assert "informational" in note.lower() or "no" in note.lower()

    def test_refresh_writes_file(self, tmp_path):
        self._setup(tmp_path)
        meta = refresh_event_outcomes(repo_root=tmp_path)
        assert meta.get("ok") is True
        assert (tmp_path / "data" / "mei" / "event_outcomes.json").exists()

    def test_cache_reused_on_second_call(self, tmp_path):
        self._setup(tmp_path)
        r1 = mei_outcomes(repo_root=tmp_path)
        r2 = mei_outcomes(repo_root=tmp_path)
        assert r1["event_count"] == r2["event_count"]

    def test_empty_holdings_handled_gracefully(self, tmp_path):
        """No holdings → coverage 0%, no crash."""
        event_date = date(2026, 1, 15)
        _write_historical_events(tmp_path, [_make_event("X", "INFLATION", event_date.isoformat())])
        # No holdings file
        result = mei_outcomes(repo_root=tmp_path)
        assert "outcomes" in result

    def test_no_events_returns_gracefully(self, tmp_path):
        _write_historical_events(tmp_path, [])
        result = mei_outcomes(repo_root=tmp_path)
        assert result["event_count"] == 0
        assert result["outcomes"] == []

    def test_no_action_keys_in_output(self, tmp_path):
        self._setup(tmp_path)
        result = mei_outcomes(repo_root=tmp_path)
        forbidden = {"execute", "trade", "buy_signal", "action_type"}
        assert not (forbidden & set(result.keys()))
        for o in result.get("outcomes", []):
            assert not (forbidden & set(o.keys()))


# ═══════════════════════════════════════════════════════════════════════════════
# Governance Q5–Q8
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceMEI002:
    """Q5: No recommendations modified. Q6: No CW-DAS changes. Q8: Informational."""

    def test_module_writes_only_to_mei_dir(self, tmp_path):
        """refresh_event_outcomes must only write to data/mei/ — not portfolio_ingestion."""
        event_date = date(2026, 1, 15)
        prices = _make_price_series(event_date - timedelta(days=2), [100, 100, 100, 105, 108])
        for sym in ["AAAA"]:
            _write_prices(tmp_path, sym, prices)
        _write_holdings(tmp_path, [{"symbol": "AAAA", "market_value": "5000", "percent_of_portfolio": "2"}])
        _write_historical_events(tmp_path, [_make_event("E1", "INFLATION", event_date.isoformat())])

        refresh_event_outcomes(tmp_path)

        # Only event_outcomes.json should be written in data/mei/
        written = list((tmp_path / "data" / "mei").rglob("*.json"))
        names = {f.name for f in written}
        assert "event_outcomes.json" in names
        # No files should be in portfolio_ingestion
        par_writes = list((tmp_path / "data" / "portfolio_ingestion").rglob("*.json")) if \
            (tmp_path / "data" / "portfolio_ingestion").exists() else []
        # Only the holdings.csv we wrote in setup; no new json from MEI-002
        par_json = [p for p in par_writes if p.name != "run_metadata.json"]
        assert len(par_json) == 0
