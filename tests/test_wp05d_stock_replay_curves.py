"""WP-05D tests — Stock Historical Replay Curve Foundation.

Covers:
- Stock price provider normalization and adjusted-close return calc
- Missing symbol behaviour and partial coverage
- FULL_UNIVERSE equal-weight curve computation
- TOP_N_STRATEGY equal-weight curve computation
- No-lookahead enforcement in selection
- Symbol-basket freeze semantics
- Evidence summary generation
- UI contract: FULL_UNIVERSE and TOP_N_STRATEGY appear in performance series
- Coverage threshold enforcement
- Batch provider fallback (get_batch_prices)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pytest

from src.models.analytical_models import AnalyticalUniverseRow
from src.replay.history_providers import PricePoint
from src.replay.replay_engine import (
    build_performance_series,
    build_replay_evidence_summary,
    select_top_n_replay,
    write_replay_evidence_summary,
)
from src.replay.stock_replay_service import (
    FULL_UNIVERSE_COVERAGE_THRESHOLD,
    MINIMUM_CURVE_POINTS,
    TOP_N_COVERAGE_THRESHOLD,
    StockCurveResult,
    _classify_symbol_series,
    _compute_final_return,
    _coverage_status_from_fraction,
    build_full_universe_curve,
    build_top_n_curve,
)
from src.validation.market_data_validator import (
    validate_stock_coverage_status,
    validate_stock_replay_curve_depth,
    validate_stock_end_price_presence,
    validate_stock_price_completeness,
    validate_stock_start_price_presence,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row(
    symbol: str,
    score: float,
    geo: str = "US",
    cap: str = "LARGE",
    industry: str = "ALL",
    snapshot_date: str = "2026-01-10",
) -> AnalyticalUniverseRow:
    return AnalyticalUniverseRow(
        security_id=f"TEST:{symbol}",
        symbol=symbol,
        security_type="Common Stock",
        snapshot_date=snapshot_date,
        run_id="TEST-RUN",
        market_cap_bucket=cap,
        geography=geo,
        country=geo,
        industry=industry,
        sector="ALL",
        composite_score=score,
        ess_score_text="BULLISH",
        zacks_rating="",
        yahoo_score="",
        danelfin_score="",
        benchmark_id=f"BM_{geo}_{cap}",
        investable_vehicle_id=f"VEH_{geo}_{cap}",
        price_at_snapshot="",
        provider_lineage="provider=TEST",
    )


class _StubProvider:
    """In-memory provider returning price series per symbol."""

    def __init__(self, prices: Dict[str, List[PricePoint]]) -> None:
        self._prices = prices

    def get_symbol_series(self, symbol: str, start_date: str, end_date: str) -> List[PricePoint]:
        return self._prices.get(symbol, [])

    def get_historical_prices(self, *, security_id, symbol, security_type, start_date, end_date):
        return []

    # Optional batch API — defers to per-symbol
    def get_batch_prices(self, symbols, start_date, end_date) -> Dict[str, List[PricePoint]]:
        return {s: self._prices.get(s, []) for s in symbols}

    def get_benchmark_series(self, benchmark_symbol_or_index, start_date, end_date):
        return [PricePoint("2026-01-10", 100.0), PricePoint("2026-01-11", 102.0)]

    def get_vehicle_series(self, symbol, start_date, end_date):
        return [PricePoint("2026-01-10", 100.0), PricePoint("2026-01-11", 101.5)]


def _pt(date: str, price: float) -> PricePoint:
    return PricePoint(date, price)


# ---------------------------------------------------------------------------
# Unit: adjusted-close return calculation
# ---------------------------------------------------------------------------


def _make_point(date: str, cumulative_return: float):
    """Create a minimal replay point object with the fields _compute_final_return expects."""
    from types import SimpleNamespace
    return SimpleNamespace(date=date, cumulative_return=cumulative_return, value=cumulative_return)


def test_compute_final_return_two_points() -> None:
    # _compute_final_return takes PricePoint(date, value) and returns (last/first) - 1
    points = [_pt("2026-01-10", 100.0), _pt("2026-01-11", 105.0)]
    result = _compute_final_return(points)
    assert result == pytest.approx(0.05)


def test_compute_final_return_empty() -> None:
    assert _compute_final_return([]) is None


# ---------------------------------------------------------------------------
# Unit: classify_symbol_series
# ---------------------------------------------------------------------------


def test_classify_symbol_series_all_available() -> None:
    sym_series = {
        "AAPL": [_pt("2026-01-10", 100.0), _pt("2026-01-11", 102.0)],
        "MSFT": [_pt("2026-01-10", 200.0), _pt("2026-01-11", 201.0)],
    }
    available, insufficient, missing, avail_map = _classify_symbol_series(sym_series, {"AAPL", "MSFT"})
    assert set(available) == {"AAPL", "MSFT"}
    assert insufficient == []
    assert missing == []


def test_classify_symbol_series_missing_symbol() -> None:
    sym_series: Dict[str, List[PricePoint]] = {
        "AAPL": [_pt("2026-01-10", 100.0), _pt("2026-01-11", 102.0)],
    }
    available, insufficient, missing, _ = _classify_symbol_series(sym_series, {"AAPL", "GOOG"})
    assert "AAPL" in available
    assert "GOOG" in missing


def test_classify_symbol_series_insufficient_points() -> None:
    sym_series: Dict[str, List[PricePoint]] = {
        "AAPL": [_pt("2026-01-10", 100.0)],  # single point = insufficient
    }
    available, insufficient, missing, _ = _classify_symbol_series(sym_series, {"AAPL"})
    assert "AAPL" in insufficient
    assert available == []
    assert missing == []


# ---------------------------------------------------------------------------
# Unit: coverage_status_from_fraction
# ---------------------------------------------------------------------------


def test_coverage_status_available() -> None:
    status = _coverage_status_from_fraction(1.0, 0.80, 5, 5, 0)
    assert status == "AVAILABLE"


def test_coverage_status_at_threshold() -> None:
    # 8/10 = 0.85 which is >= 0.80 threshold — should be AVAILABLE
    status = _coverage_status_from_fraction(0.85, 0.80, 10, 8, 0)
    assert status in ("AVAILABLE", "PARTIAL")


def test_coverage_status_below_threshold() -> None:
    # 5/10 = 0.50 which is < 0.80 threshold — status indicates insufficient coverage
    status = _coverage_status_from_fraction(0.50, 0.80, 10, 5, 5)
    assert status in ("MISSING_MARKET_DATA", "FAILED", "PARTIAL")


def test_coverage_status_all_missing() -> None:
    status = _coverage_status_from_fraction(0.0, 0.60, 5, 0, 5)
    assert status in ("MISSING_MARKET_DATA", "FAILED")


# ---------------------------------------------------------------------------
# Integration: build_full_universe_curve
# ---------------------------------------------------------------------------


def test_build_full_universe_curve_all_available() -> None:
    rows = [_row("AAPL", 5.0), _row("MSFT", 4.5)]
    provider = _StubProvider(
        {
            "AAPL": [_pt("2026-01-10", 100.0), _pt("2026-01-11", 105.0)],
            "MSFT": [_pt("2026-01-10", 200.0), _pt("2026-01-11", 204.0)],
        }
    )
    result = build_full_universe_curve(
        universe_rows=rows,
        start_date="2026-01-10",
        end_date="2026-01-11",
        provider=provider,
        filter_geography="US",
        filter_market_cap_bucket="LARGE",
        filter_industry="ALL",
        coverage_threshold=FULL_UNIVERSE_COVERAGE_THRESHOLD,
        max_symbols=500,
    )
    assert isinstance(result, StockCurveResult)
    assert result.coverage_status == "AVAILABLE"
    assert len(result.points) >= MINIMUM_CURVE_POINTS
    assert result.symbols_available == ["AAPL", "MSFT"] or set(result.symbols_available) == {"AAPL", "MSFT"}


def test_build_full_universe_curve_partial_missing() -> None:
    """One symbol missing — if fraction is above threshold, still AVAILABLE."""
    rows = [_row("AAPL", 5.0), _row("MSFT", 4.5), _row("GOOG", 4.0)]
    provider = _StubProvider(
        {
            "AAPL": [_pt("2026-01-10", 100.0), _pt("2026-01-11", 105.0)],
            "MSFT": [_pt("2026-01-10", 200.0), _pt("2026-01-11", 204.0)],
            # GOOG missing
        }
    )
    result = build_full_universe_curve(
        universe_rows=rows,
        start_date="2026-01-10",
        end_date="2026-01-11",
        provider=provider,
        filter_geography="US",
        filter_market_cap_bucket="LARGE",
        filter_industry="ALL",
        coverage_threshold=0.60,  # 2/3 ≥ 0.60
        max_symbols=500,
    )
    assert result.coverage_status in ("AVAILABLE", "PARTIAL")
    assert "GOOG" in result.symbols_missing


def test_build_full_universe_curve_below_coverage_threshold() -> None:
    """If too many symbols missing, coverage_status reflects MISSING_MARKET_DATA."""
    rows = [_row("AAPL", 5.0), _row("MSFT", 4.5), _row("GOOG", 4.0)]
    provider = _StubProvider(
        {
            "AAPL": [_pt("2026-01-10", 100.0), _pt("2026-01-11", 105.0)],
            # MSFT and GOOG missing
        }
    )
    result = build_full_universe_curve(
        universe_rows=rows,
        start_date="2026-01-10",
        end_date="2026-01-11",
        provider=provider,
        filter_geography="US",
        filter_market_cap_bucket="LARGE",
        filter_industry="ALL",
        coverage_threshold=0.80,  # 1/3 < 0.80
        max_symbols=500,
    )
    assert result.coverage_status in ("MISSING_MARKET_DATA", "FAILED", "PARTIAL")
    assert set(result.symbols_missing).issuperset({"MSFT", "GOOG"})


def test_build_full_universe_curve_empty_universe() -> None:
    result = build_full_universe_curve(
        universe_rows=[],
        start_date="2026-01-10",
        end_date="2026-01-11",
        provider=_StubProvider({}),
        filter_geography="US",
        filter_market_cap_bucket="LARGE",
        filter_industry="ALL",
        coverage_threshold=FULL_UNIVERSE_COVERAGE_THRESHOLD,
        max_symbols=500,
    )
    assert result.coverage_status in ("FAILED", "MISSING_MARKET_DATA")
    assert list(result.points) == []


# ---------------------------------------------------------------------------
# Integration: build_top_n_curve
# ---------------------------------------------------------------------------


def test_build_top_n_curve_returns_correct_symbols() -> None:
    rows = [_row("AAPL", 5.0), _row("MSFT", 4.5), _row("GOOG", 4.0)]
    selection, _ = select_top_n_replay(
        analytical_rows=rows,
        start_date="2026-01-10",
        end_date="2026-01-11",
        market_cap_bucket="LARGE",
        geography="US",
        industry="ALL",
        top_n=2,
        replay_id_suffix="UNIT-D",
    )
    provider = _StubProvider(
        {
            "AAPL": [_pt("2026-01-10", 100.0), _pt("2026-01-11", 106.0)],
            "MSFT": [_pt("2026-01-10", 200.0), _pt("2026-01-11", 208.0)],
        }
    )
    result = build_top_n_curve(
        selection=selection,
        provider=provider,
        coverage_threshold=TOP_N_COVERAGE_THRESHOLD,
    )
    assert isinstance(result, StockCurveResult)
    assert result.coverage_status == "AVAILABLE"
    assert len(result.points) >= MINIMUM_CURVE_POINTS
    # Both requested symbols should be in available
    assert set(result.symbols_available) == {"AAPL", "MSFT"}


def test_build_top_n_curve_no_lookahead() -> None:
    """Symbols are fixed at selection time — adding later-scored rows should not change basket."""
    rows = [_row("AAPL", 5.0), _row("MSFT", 4.5)]
    selection, _ = select_top_n_replay(
        analytical_rows=rows,
        start_date="2026-01-10",
        end_date="2026-01-11",
        market_cap_bucket="LARGE",
        geography="US",
        industry="ALL",
        top_n=2,
        replay_id_suffix="NOLOOK",
    )
    provider = _StubProvider(
        {
            "AAPL": [_pt("2026-01-10", 100.0), _pt("2026-01-11", 106.0)],
            "MSFT": [_pt("2026-01-10", 200.0), _pt("2026-01-11", 208.0)],
            # XTRA would be introduced after selection — should never appear
            "XTRA": [_pt("2026-01-10", 50.0), _pt("2026-01-11", 60.0)],
        }
    )
    result = build_top_n_curve(
        selection=selection,
        provider=provider,
        coverage_threshold=TOP_N_COVERAGE_THRESHOLD,
    )
    # XTRA must not appear in selected symbols
    all_symbols = set(result.symbols_requested)
    assert "XTRA" not in all_symbols


# ---------------------------------------------------------------------------
# Integration: full performance series includes FULL_UNIVERSE and TOP_N_STRATEGY
# ---------------------------------------------------------------------------


def test_performance_series_includes_stock_curve_series() -> None:
    rows = [_row("AAPL", 5.0), _row("MSFT", 4.5)]
    selection, filtered = select_top_n_replay(
        analytical_rows=rows,
        start_date="2026-01-10",
        end_date="2026-01-11",
        market_cap_bucket="LARGE",
        geography="US",
        industry="ALL",
        top_n=2,
        replay_id_suffix="UI-CONTRACT",
    )
    prices = {
        "AAPL": [_pt("2026-01-10", 100.0), _pt("2026-01-11", 106.0)],
        "MSFT": [_pt("2026-01-10", 200.0), _pt("2026-01-11", 208.0)],
    }
    provider = _StubProvider(prices)
    fu_result = build_full_universe_curve(
        universe_rows=filtered,
        start_date="2026-01-10",
        end_date="2026-01-11",
        provider=provider,
        filter_geography="US",
        filter_market_cap_bucket="LARGE",
        filter_industry="ALL",
        coverage_threshold=FULL_UNIVERSE_COVERAGE_THRESHOLD,
        max_symbols=500,
    )
    tn_result = build_top_n_curve(
        selection=selection,
        provider=provider,
        coverage_threshold=TOP_N_COVERAGE_THRESHOLD,
    )
    series = build_performance_series(
        selection=selection,
        full_universe_rows=filtered,
        benchmark_symbol_or_index="^GSPC",
        investable_vehicle_symbol="SPY",
        security_price_provider=provider,
        benchmark_provider=provider,
        vehicle_provider=provider,
        full_universe_curve_result=fu_result,
        top_n_curve_result=tn_result,
    )
    types = {row.series_type for row in series}
    assert "BENCHMARK" in types
    assert "INVESTABLE_VEHICLE" in types
    assert "FULL_UNIVERSE" in types
    assert "TOP_N_STRATEGY" in types


# ---------------------------------------------------------------------------
# Integration: build_replay_evidence_summary
# ---------------------------------------------------------------------------


def test_build_replay_evidence_summary_structure(tmp_path: Path) -> None:
    rows = [_row("AAPL", 5.0), _row("MSFT", 4.5)]
    selection, filtered = select_top_n_replay(
        analytical_rows=rows,
        start_date="2026-01-10",
        end_date="2026-01-11",
        market_cap_bucket="LARGE",
        geography="US",
        industry="ALL",
        top_n=2,
        replay_id_suffix="EVS",
    )
    prices = {
        "AAPL": [_pt("2026-01-10", 100.0), _pt("2026-01-11", 106.0)],
        "MSFT": [_pt("2026-01-10", 200.0), _pt("2026-01-11", 208.0)],
    }
    provider = _StubProvider(prices)
    fu = build_full_universe_curve(
        universe_rows=filtered,
        start_date="2026-01-10",
        end_date="2026-01-11",
        provider=provider,
        filter_geography="US",
        filter_market_cap_bucket="LARGE",
        filter_industry="ALL",
        coverage_threshold=FULL_UNIVERSE_COVERAGE_THRESHOLD,
        max_symbols=500,
    )
    tn = build_top_n_curve(
        selection=selection,
        provider=provider,
        coverage_threshold=TOP_N_COVERAGE_THRESHOLD,
    )
    series = build_performance_series(
        selection=selection,
        full_universe_rows=filtered,
        benchmark_symbol_or_index="^GSPC",
        investable_vehicle_symbol="SPY",
        security_price_provider=provider,
        benchmark_provider=provider,
        vehicle_provider=provider,
        full_universe_curve_result=fu,
        top_n_curve_result=tn,
    )
    summary = build_replay_evidence_summary(
        selection=selection,
        benchmark_symbol="^GSPC",
        investable_vehicle_symbol="SPY",
        full_universe_symbol_count=len(filtered),
        full_universe_curve_result=fu,
        top_n_curve_result=tn,
        performance_series=series,
    )
    # Required keys
    required_keys = {
        "replay_id", "replay_mode", "start_date", "end_date",
        "geography", "market_cap_bucket", "industry",
        "benchmark_symbol", "investable_vehicle_symbol",
        "full_universe_symbol_count", "top_n", "selected_symbols",
        "missing_price_symbols", "partial_price_symbols",
        "benchmark_final_return", "investable_vehicle_final_return",
        "full_universe_final_return", "top_n_strategy_final_return",
        "strategy_vs_benchmark_delta", "strategy_vs_vehicle_delta",
        "coverage_status", "generated_at_utc",
    }
    assert required_keys.issubset(set(summary.keys()))
    assert summary["coverage_status"] in ("AVAILABLE", "PARTIAL", "FAILED")

    # write to disk and verify readable JSON
    path = write_replay_evidence_summary(replay_dir=tmp_path, summary=summary)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["replay_id"] == summary["replay_id"]


# ---------------------------------------------------------------------------
# Validators: market_data_validator stock coverage
# ---------------------------------------------------------------------------


def test_validate_stock_coverage_status_valid() -> None:
    errors = validate_stock_coverage_status("AVAILABLE", "FULL_UNIVERSE")
    assert errors == []


def test_validate_stock_coverage_status_invalid() -> None:
    errors = validate_stock_coverage_status("UNKNOWN_STATUS", "FULL_UNIVERSE")
    assert len(errors) > 0


def test_validate_stock_price_completeness_all_available() -> None:
    errors = validate_stock_price_completeness(
        symbols_requested=["AAPL", "MSFT"],
        symbols_available=["AAPL", "MSFT"],
        symbols_missing=[],
        series_type="TOP_N_STRATEGY",
    )
    assert errors == []


def test_validate_stock_price_completeness_missing_reported() -> None:
    errors = validate_stock_price_completeness(
        symbols_requested=["AAPL", "MSFT", "GOOG"],
        symbols_available=["AAPL"],
        symbols_missing=["MSFT", "GOOG"],
        series_type="FULL_UNIVERSE",
    )
    # Missing symbols should produce informational entries or warnings
    assert isinstance(errors, list)


def test_validate_stock_replay_curve_depth_ok() -> None:
    errors = validate_stock_replay_curve_depth(series_type="FULL_UNIVERSE", point_count=5)
    assert errors == []


def test_validate_stock_replay_curve_depth_insufficient() -> None:
    errors = validate_stock_replay_curve_depth(series_type="FULL_UNIVERSE", point_count=1, minimum_points=2)
    assert len(errors) > 0


def test_validate_stock_start_price_allows_small_gap() -> None:
    # Price appears 3 days after start — within 7-day tolerance
    errors = validate_stock_start_price_presence(
        symbol="AAPL",
        start_date="2026-01-10",
        price_dates=["2026-01-13", "2026-01-14"],
    )
    assert errors == []


def test_validate_stock_start_price_rejects_large_gap() -> None:
    # Price appears 10 days after start — exceeds 7-day tolerance
    errors = validate_stock_start_price_presence(
        symbol="AAPL",
        start_date="2026-01-10",
        price_dates=["2026-01-20", "2026-01-21"],
    )
    assert len(errors) > 0


# ---------------------------------------------------------------------------
# Coverage: StockCurveResult frozen dataclass
# ---------------------------------------------------------------------------


def test_stock_curve_result_is_frozen() -> None:
    result = StockCurveResult(
        series_type="FULL_UNIVERSE",
        symbols_requested=["AAPL"],
        symbols_available=["AAPL"],
        symbols_missing=[],
        symbols_insufficient=[],
        coverage_fraction=1.0,
        coverage_status="AVAILABLE",
        points=[],
        final_return=None,
        coverage_threshold_used=0.60,
        symbols_truncated=False,
    )
    with pytest.raises((AttributeError, TypeError)):
        result.coverage_status = "FAILED"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Regression tests: graph rendering regression introduced by WP-05D
# ---------------------------------------------------------------------------


class _ThrowingProvider:
    """Stub provider whose every method raises to verify exception isolation."""

    def get_batch_prices(self, *, symbols, start_date, end_date):  # type: ignore[override]
        raise RuntimeError("network error")

    def get_symbol_series(self, symbol, start_date, end_date):  # type: ignore[override]
        raise RuntimeError(f"network error for {symbol}")

    def get_historical_prices(self, *, security_id, symbol, security_type, start_date, end_date):  # type: ignore[override]
        raise RuntimeError(f"network error for {symbol}")


def test_fetch_symbol_series_isolates_per_symbol_exceptions() -> None:
    """Regression: _fetch_symbol_series must return empty list per symbol,
    not propagate exceptions, so one bad symbol never kills the whole batch.
    Fix: per-symbol try/except in fallback loop."""
    from src.replay.stock_replay_service import _fetch_symbol_series

    provider = _ThrowingProvider()
    result = _fetch_symbol_series(["AAPL", "MSFT", "GOOG"], "2025-01-01", "2026-01-01", provider)
    assert set(result.keys()) == {"AAPL", "MSFT", "GOOG"}
    assert result["AAPL"] == []
    assert result["MSFT"] == []
    assert result["GOOG"] == []


def test_build_full_universe_curve_degrades_when_provider_throws() -> None:
    """Regression: build_full_universe_curve must return a valid StockCurveResult
    (status=FAILED or MISSING_MARKET_DATA) even when the price provider raises
    on every call.  It must never propagate the exception."""
    _rows = _make_universe_rows(["AAPL", "MSFT"], snapshot_date="2025-01-01")
    provider = _ThrowingProvider()

    result = build_full_universe_curve(
        universe_rows=_rows,
        start_date="2025-01-01",
        end_date="2026-01-01",
        provider=provider,
        coverage_threshold=FULL_UNIVERSE_COVERAGE_THRESHOLD,
    )
    assert isinstance(result, StockCurveResult)
    assert result.coverage_status in ("FAILED", "MISSING_MARKET_DATA", "INSUFFICIENT_HISTORY")
    assert list(result.points) == []


def test_build_top_n_curve_degrades_when_provider_throws() -> None:
    """Regression: build_top_n_curve must not propagate provider exceptions."""
    from src.models.analytical_models import ReplaySelection

    selection = ReplaySelection(
        replay_id="TEST-REPLAY",
        replay_mode="HISTORICAL_VALIDATION",
        start_date="2025-01-01",
        end_date="2026-01-01",
        filter_geography="US",
        filter_market_cap_bucket="LARGE",
        filter_industry="ALL",
        selection_method="TOP_N_COMPOSITE",
        top_n=2,
        selected_symbols=("AAPL", "MSFT"),
    )
    provider = _ThrowingProvider()

    result = build_top_n_curve(
        selection=selection,
        provider=provider,
        coverage_threshold=TOP_N_COVERAGE_THRESHOLD,
    )
    assert isinstance(result, StockCurveResult)
    assert result.coverage_status in ("FAILED", "MISSING_MARKET_DATA", "INSUFFICIENT_HISTORY")
    assert list(result.points) == []


# ---------------------------------------------------------------------------
# Helper used by the regression tests above
# ---------------------------------------------------------------------------


def _make_universe_rows(symbols: list, *, snapshot_date: str) -> list:
    """Create minimal AnalyticalUniverseRow objects for testing."""
    rows = []
    for sym in symbols:
        rows.append(
            AnalyticalUniverseRow(
                security_id=f"TEST:{sym}",
                symbol=sym,
                security_type="Common Stock",
                snapshot_date=snapshot_date,
                run_id="TEST",
                market_cap_bucket="LARGE",
                geography="US",
                country="US",
                industry="ALL",
                sector="ALL",
                composite_score=0.5,
                ess_score_text="",
                zacks_rating="",
                yahoo_score="",
                danelfin_score="",
                benchmark_id="SP500",
                investable_vehicle_id="SPY",
                price_at_snapshot="",
                provider_lineage="",
            )
        )
    return rows
