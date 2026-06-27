"""ROTATION-PROXY-AUDIT-01: Tests for proxy series identity validation and FULL_UNIVERSE selection."""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

from src.sih.rotation_risk_monitor import rotation_risk_summary


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def _seed_manifest(tmp_path: Path, run_id: str = "PAR-PROXY-TEST") -> str:
    manifest_path = tmp_path / "data" / "portfolio_ingestion" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({
            "version": 1,
            "portfolios": [{
                "run_id": run_id,
                "snapshot_date": "2026-06-27",
                "created_at_utc": "2026-06-27T00:00:00+00:00",
            }]
        }),
        encoding="utf-8",
    )
    return run_id


def _seed_holdings(tmp_path: Path, run_id: str) -> None:
    _write_csv(
        tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / run_id / "holdings.csv",
        ["symbol", "industry", "market_value", "percent_of_portfolio"],
        [
            {"symbol": "AAPL", "industry": "TECHNOLOGY", "market_value": "30000", "percent_of_portfolio": "30"},
            {"symbol": "XOM",  "industry": "ENERGY",     "market_value": "20000", "percent_of_portfolio": "20"},
            {"symbol": "NUE",  "industry": "BASIC MATERIALS", "market_value": "15000", "percent_of_portfolio": "15"},
            {"symbol": "CAT",  "industry": "INDUSTRIALS", "market_value": "10000", "percent_of_portfolio": "10"},
        ],
    )


def _seed_signal_snapshot(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "data" / "current" / "signal_snapshot.csv",
        ["snapshot_date", "symbol", "starmine_ess_numeric"],
        [
            {"snapshot_date": "2026-06-27", "symbol": "AAPL", "starmine_ess_numeric": "2"},
            {"snapshot_date": "2026-06-27", "symbol": "XOM",  "starmine_ess_numeric": "4"},
            {"snapshot_date": "2026-06-27", "symbol": "NUE",  "starmine_ess_numeric": "4"},
            {"snapshot_date": "2026-06-27", "symbol": "CAT",  "starmine_ess_numeric": "4"},
        ],
    )


def _seed_replay_inputs(tmp_path: Path) -> None:
    """Seed replay_inputs with distinct replay_ids per industry."""
    _write_csv(
        tmp_path / "data" / "current" / "replay_inputs.csv",
        ["replay_id", "start_date", "end_date", "filter_market_cap_bucket",
         "filter_geography", "filter_industry", "filter_analytical_subtier",
         "selection_method", "top_n", "selected_symbols",
         "composite_score_snapshot_date", "replay_mode"],
        [
            {"replay_id": "RID-TECH-LARGE",   "start_date": "2025-01-01", "end_date": "2026-01-01",
             "filter_market_cap_bucket": "LARGE", "filter_geography": "US", "filter_industry": "TECHNOLOGY",
             "filter_analytical_subtier": "", "selection_method": "TOP_N_COMPOSITE_AT_START",
             "top_n": "20", "selected_symbols": "AAPL|MSFT", "composite_score_snapshot_date": "2025-01-01",
             "replay_mode": "HISTORICAL_VALIDATION"},
            {"replay_id": "RID-ENERGY-LARGE", "start_date": "2025-01-01", "end_date": "2026-01-01",
             "filter_market_cap_bucket": "LARGE", "filter_geography": "US", "filter_industry": "ENERGY",
             "filter_analytical_subtier": "", "selection_method": "TOP_N_COMPOSITE_AT_START",
             "top_n": "20", "selected_symbols": "XOM|CVX", "composite_score_snapshot_date": "2025-01-01",
             "replay_mode": "HISTORICAL_VALIDATION"},
            {"replay_id": "RID-BMAT-LARGE",   "start_date": "2025-01-01", "end_date": "2026-01-01",
             "filter_market_cap_bucket": "LARGE", "filter_geography": "US", "filter_industry": "BASIC MATERIALS",
             "filter_analytical_subtier": "", "selection_method": "TOP_N_COMPOSITE_AT_START",
             "top_n": "20", "selected_symbols": "NUE|LIN", "composite_score_snapshot_date": "2025-01-01",
             "replay_mode": "HISTORICAL_VALIDATION"},
            {"replay_id": "RID-INDUS-LARGE",  "start_date": "2025-01-01", "end_date": "2026-01-01",
             "filter_market_cap_bucket": "LARGE", "filter_geography": "US", "filter_industry": "INDUSTRIALS",
             "filter_analytical_subtier": "", "selection_method": "TOP_N_COMPOSITE_AT_START",
             "top_n": "20", "selected_symbols": "CAT|DE", "composite_score_snapshot_date": "2025-01-01",
             "replay_mode": "HISTORICAL_VALIDATION"},
        ],
    )


def _build_perf_rows(
    replay_id: str,
    series_type: str,
    start_val: float,
    daily_gain: float,
    n_days: int = 80,
) -> list[dict]:
    rows = []
    start = date(2025, 6, 1)
    val = start_val
    for i in range(n_days):
        d = (start + timedelta(days=i)).isoformat()
        rows.append({
            "series_id": f"{replay_id}:{series_type}",
            "replay_id": replay_id,
            "series_type": series_type,
            "date": d,
            "value": str(round(val, 6)),
            "cumulative_return": "0",
            "source": "test",
            "coverage_status": "AVAILABLE",
        })
        val *= (1 + daily_gain)
    return rows


_PERF_HEADERS = ["series_id", "replay_id", "series_type", "date", "value",
                 "cumulative_return", "source", "coverage_status"]


def _seed_distinct_perf(tmp_path: Path) -> None:
    """Tech outperforms hard assets on FULL_UNIVERSE series — gives a real spread."""
    rows = []
    # BENCHMARK identical across all (should be ignored)
    benchmark_val = 5000.0
    for rid in ("RID-TECH-LARGE", "RID-ENERGY-LARGE", "RID-BMAT-LARGE", "RID-INDUS-LARGE"):
        rows.extend(_build_perf_rows(rid, "BENCHMARK", benchmark_val, 0.0008))

    # FULL_UNIVERSE — distinct per industry
    rows.extend(_build_perf_rows("RID-TECH-LARGE",   "FULL_UNIVERSE", 100.0, 0.0030))  # tech strong
    rows.extend(_build_perf_rows("RID-ENERGY-LARGE", "FULL_UNIVERSE", 100.0, 0.0005))  # energy weak
    rows.extend(_build_perf_rows("RID-BMAT-LARGE",   "FULL_UNIVERSE", 100.0, 0.0006))
    rows.extend(_build_perf_rows("RID-INDUS-LARGE",  "FULL_UNIVERSE", 100.0, 0.0007))

    _write_csv(tmp_path / "data" / "current" / "replay_performance_series.csv", _PERF_HEADERS, rows)


def _seed_identical_perf(tmp_path: Path) -> None:
    """All industries use identical FULL_UNIVERSE values to test fail-closed behavior."""
    rows = []
    identical_val = 100.0
    for rid in ("RID-TECH-LARGE", "RID-ENERGY-LARGE", "RID-BMAT-LARGE", "RID-INDUS-LARGE"):
        rows.extend(_build_perf_rows(rid, "FULL_UNIVERSE", identical_val, 0.0010))
    _write_csv(tmp_path / "data" / "current" / "replay_performance_series.csv", _PERF_HEADERS, rows)


def _seed_only_benchmark_perf(tmp_path: Path) -> None:
    """Only BENCHMARK series exist — no FULL_UNIVERSE data — should produce DATA_UNAVAILABLE."""
    rows = []
    for rid in ("RID-TECH-LARGE", "RID-ENERGY-LARGE", "RID-BMAT-LARGE", "RID-INDUS-LARGE"):
        rows.extend(_build_perf_rows(rid, "BENCHMARK", 5000.0, 0.0008))
    _write_csv(tmp_path / "data" / "current" / "replay_performance_series.csv", _PERF_HEADERS, rows)


def _seed_no_hard_asset_perf(tmp_path: Path) -> None:
    """Only tech FULL_UNIVERSE, no hard-asset series."""
    rows = _build_perf_rows("RID-TECH-LARGE", "FULL_UNIVERSE", 100.0, 0.0030)
    _write_csv(tmp_path / "data" / "current" / "replay_performance_series.csv", _PERF_HEADERS, rows)


def _seed_common(tmp_path: Path, perf_mode: str) -> str:
    run_id = _seed_manifest(tmp_path)
    _seed_holdings(tmp_path, run_id)
    _seed_signal_snapshot(tmp_path)
    _seed_replay_inputs(tmp_path)
    if perf_mode == "distinct":
        _seed_distinct_perf(tmp_path)
    elif perf_mode == "identical":
        _seed_identical_perf(tmp_path)
    elif perf_mode == "benchmark_only":
        _seed_only_benchmark_perf(tmp_path)
    elif perf_mode == "no_hard_asset":
        _seed_no_hard_asset_perf(tmp_path)
    return run_id


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_distinct_full_universe_series_produces_real_spread(tmp_path: Path) -> None:
    """Tech strong, hard assets weak => FULL_UNIVERSE gives a non-zero spread."""
    _seed_common(tmp_path, "distinct")
    result = rotation_risk_summary(tmp_path)

    assert result["status"] == "OK"
    assert result["signal"] != "DATA_UNAVAILABLE"
    pd = result.get("proxy_diagnostics", {})
    ic = pd.get("series_identity_check", {})
    assert not ic.get("identical_returns_all_windows"), "Distinct series should not be identical"
    assert not ic.get("warning"), f"No warning expected, got: {ic.get('warning')}"
    # Spread should be non-zero in at least one window
    spreads = (result.get("proxy_returns") or {}).get("rotation_spread_pct") or {}
    assert any(v is not None and abs(v) > 0.001 for v in spreads.values()), \
        f"Expected non-zero spread, got: {spreads}"


def test_identical_returns_triggers_data_unavailable(tmp_path: Path) -> None:
    """If FULL_UNIVERSE returns are identical across all windows, signal must be DATA_UNAVAILABLE."""
    _seed_common(tmp_path, "identical")
    result = rotation_risk_summary(tmp_path)

    assert result["status"] == "DATA_UNAVAILABLE"
    assert result["signal"] == "DATA_UNAVAILABLE"
    assert result["risk_score"] == 0
    pd = result.get("proxy_diagnostics", {})
    ic = pd.get("series_identity_check", {})
    assert ic.get("identical_returns_all_windows") is True
    assert ic.get("warning") == "tech_and_hard_asset_proxy_returns_identical_all_windows"
    assert "proxy" in result["headline"].lower()


def test_benchmark_only_series_produces_data_unavailable(tmp_path: Path) -> None:
    """If only BENCHMARK series exist (no FULL_UNIVERSE / TOP_N_STRATEGY), result is DATA_UNAVAILABLE."""
    _seed_common(tmp_path, "benchmark_only")
    result = rotation_risk_summary(tmp_path)

    # No FULL_UNIVERSE data means no points pass filter, tech_series = None
    assert result["status"] == "DATA_UNAVAILABLE"
    assert result["signal"] == "DATA_UNAVAILABLE"


def test_missing_hard_asset_proxy_produces_data_unavailable(tmp_path: Path) -> None:
    """Hard-asset proxy absent → DATA_UNAVAILABLE, not NO_CLEAR_SIGNAL."""
    _seed_common(tmp_path, "no_hard_asset")
    result = rotation_risk_summary(tmp_path)

    assert result["status"] == "DATA_UNAVAILABLE"
    assert result["signal"] == "DATA_UNAVAILABLE"
    # must not pretend rotation is clear
    assert result["signal"] != "NO_CLEAR_SIGNAL"


def test_tech_and_hard_asset_cannot_share_replay_id(tmp_path: Path) -> None:
    """If tech and a hard-asset cohort resolve to the same replay_id, flag it."""
    # Seed replay_inputs with ENERGY pointing to the same replay_id as TECHNOLOGY
    run_id = _seed_manifest(tmp_path)
    _seed_holdings(tmp_path, run_id)
    _seed_signal_snapshot(tmp_path)

    shared_rid = "RID-SHARED"
    _write_csv(
        tmp_path / "data" / "current" / "replay_inputs.csv",
        ["replay_id", "start_date", "end_date", "filter_market_cap_bucket",
         "filter_geography", "filter_industry", "filter_analytical_subtier",
         "selection_method", "top_n", "selected_symbols",
         "composite_score_snapshot_date", "replay_mode"],
        [
            {"replay_id": shared_rid, "start_date": "2025-01-01", "end_date": "2026-01-01",
             "filter_market_cap_bucket": "LARGE", "filter_geography": "US", "filter_industry": "TECHNOLOGY",
             "filter_analytical_subtier": "", "selection_method": "TOP_N_COMPOSITE_AT_START",
             "top_n": "20", "selected_symbols": "AAPL", "composite_score_snapshot_date": "2025-01-01",
             "replay_mode": "HISTORICAL_VALIDATION"},
            {"replay_id": shared_rid, "start_date": "2025-01-01", "end_date": "2026-01-01",
             "filter_market_cap_bucket": "LARGE", "filter_geography": "US", "filter_industry": "ENERGY",
             "filter_analytical_subtier": "", "selection_method": "TOP_N_COMPOSITE_AT_START",
             "top_n": "20", "selected_symbols": "XOM", "composite_score_snapshot_date": "2025-01-01",
             "replay_mode": "HISTORICAL_VALIDATION"},
            {"replay_id": "RID-BMAT",  "start_date": "2025-01-01", "end_date": "2026-01-01",
             "filter_market_cap_bucket": "LARGE", "filter_geography": "US", "filter_industry": "BASIC MATERIALS",
             "filter_analytical_subtier": "", "selection_method": "TOP_N_COMPOSITE_AT_START",
             "top_n": "20", "selected_symbols": "NUE", "composite_score_snapshot_date": "2025-01-01",
             "replay_mode": "HISTORICAL_VALIDATION"},
            {"replay_id": "RID-INDUS", "start_date": "2025-01-01", "end_date": "2026-01-01",
             "filter_market_cap_bucket": "LARGE", "filter_geography": "US", "filter_industry": "INDUSTRIALS",
             "filter_analytical_subtier": "", "selection_method": "TOP_N_COMPOSITE_AT_START",
             "top_n": "20", "selected_symbols": "CAT", "composite_score_snapshot_date": "2025-01-01",
             "replay_mode": "HISTORICAL_VALIDATION"},
        ],
    )
    # Give the shared_rid distinct-looking returns so only replay_id check fires
    rows = (
        _build_perf_rows(shared_rid, "FULL_UNIVERSE", 100.0, 0.002)
        + _build_perf_rows("RID-BMAT",  "FULL_UNIVERSE", 100.0, 0.001)
        + _build_perf_rows("RID-INDUS", "FULL_UNIVERSE", 100.0, 0.0008)
    )
    _write_csv(tmp_path / "data" / "current" / "replay_performance_series.csv",
               _PERF_HEADERS, rows)

    result = rotation_risk_summary(tmp_path)
    pd = result.get("proxy_diagnostics", {})
    ic = pd.get("series_identity_check", {})
    assert ic.get("same_replay_id") is True
    assert ic.get("warning") == "tech_and_hard_asset_proxy_replay_ids_identical"
    assert result["signal"] == "DATA_UNAVAILABLE"


def test_proxy_diagnostics_present_in_valid_result(tmp_path: Path) -> None:
    """proxy_diagnostics key must be present even in valid OK results."""
    _seed_common(tmp_path, "distinct")
    result = rotation_risk_summary(tmp_path)

    assert "proxy_diagnostics" in result
    pd = result["proxy_diagnostics"]
    assert "tech_proxy" in pd
    assert "hard_assets_proxies" in pd
    assert "series_identity_check" in pd
    assert pd["tech_proxy"]["series_type_used"] in {"FULL_UNIVERSE", "TOP_N_STRATEGY"}


def test_commodity_fill_guard_survives_proxy_validation_failure(tmp_path: Path) -> None:
    """If proxy validation fails, commodity_fill_guard must still be present and safe."""
    from tests.test_commodity_fill_guard import (
        _seed_alignment, _seed_deployment_queue,
    )
    run_id = _seed_common(tmp_path, "identical")
    # Seed alignment + dq for guard computation
    _seed_alignment(
        tmp_path, run_id,
        commodities_actual=0.0, commodities_target=2.0,
        gold_actual=0.0, gold_target=1.0,
        energy_actual=0.0, energy_target=0.7,
        broad_actual=0.0, broad_target=0.3,
        ultra_mega_drift=5.0,
    )
    _seed_deployment_queue(tmp_path, run_id, deployable_cash=4702.0,
                           equity_symbols=["AAPL"], commodity_symbols=[])

    result = rotation_risk_summary(tmp_path)
    assert result["signal"] == "DATA_UNAVAILABLE"
    assert "commodity_fill_guard" in result
    assert result["commodity_fill_guard"]["status"] in {"NONE", "INFO", "ACTIVE_REVIEW"}


def test_no_deployment_queue_or_allocation_artifact_modified(tmp_path: Path) -> None:
    """Proxy validation must not write to or modify any deployment artifact."""
    from tests.test_commodity_fill_guard import _seed_alignment, _seed_deployment_queue
    run_id = _seed_common(tmp_path, "distinct")
    _seed_alignment(
        tmp_path, run_id,
        commodities_actual=0.0, commodities_target=2.0,
        gold_actual=0.0, gold_target=1.0,
        energy_actual=0.0, energy_target=0.7,
        broad_actual=0.0, broad_target=0.3,
        ultra_mega_drift=2.0,
    )
    dq_path = tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / run_id / "deployment_queue.json"
    _seed_deployment_queue(tmp_path, run_id, deployable_cash=4702.0,
                           equity_symbols=["AAPL", "MSFT"], commodity_symbols=[])
    before = dq_path.read_text(encoding="utf-8")
    rotation_risk_summary(tmp_path)
    after = dq_path.read_text(encoding="utf-8")
    assert before == after, "deployment_queue.json must not be modified by rotation_risk_summary"
