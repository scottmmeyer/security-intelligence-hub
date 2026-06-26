"""Tests for ROTATION-RISK-01 display-only rotation monitor."""

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


def _seed_manifest_and_holdings(tmp_path: Path, holdings_rows: list[dict]) -> None:
    run_id = "PAR-TEST-0001"
    manifest_path = tmp_path / "data" / "portfolio_ingestion" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "portfolios": [
                    {
                        "run_id": run_id,
                        "snapshot_date": "2026-06-26",
                        "created_at_utc": "2026-06-26T12:00:00+00:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    _write_csv(
        tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / run_id / "holdings.csv",
        [
            "symbol",
            "industry",
            "market_value",
            "percent_of_portfolio",
        ],
        holdings_rows,
    )


def _seed_signal_snapshot(tmp_path: Path, rows: list[dict]) -> None:
    _write_csv(
        tmp_path / "data" / "current" / "signal_snapshot.csv",
        [
            "snapshot_date",
            "symbol",
            "starmine_ess_numeric",
        ],
        rows,
    )


def _seed_replay_inputs(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "data" / "current" / "replay_inputs.csv",
        [
            "replay_id",
            "start_date",
            "end_date",
            "filter_market_cap_bucket",
            "filter_geography",
            "filter_industry",
            "filter_analytical_subtier",
            "selection_method",
            "top_n",
            "selected_symbols",
            "composite_score_snapshot_date",
            "replay_mode",
        ],
        [
            {
                "replay_id": "RID-TECH-LARGE",
                "start_date": "2025-05-01",
                "end_date": "2026-05-01",
                "filter_market_cap_bucket": "LARGE",
                "filter_geography": "US",
                "filter_industry": "TECHNOLOGY",
                "filter_analytical_subtier": "",
                "selection_method": "TOP_N_COMPOSITE_AT_START",
                "top_n": "20",
                "selected_symbols": "AAPL|MSFT",
                "composite_score_snapshot_date": "2025-05-01",
                "replay_mode": "HISTORICAL_VALIDATION",
            },
            {
                "replay_id": "RID-ENERGY-LARGE",
                "start_date": "2025-05-01",
                "end_date": "2026-05-01",
                "filter_market_cap_bucket": "LARGE",
                "filter_geography": "US",
                "filter_industry": "ENERGY",
                "filter_analytical_subtier": "",
                "selection_method": "TOP_N_COMPOSITE_AT_START",
                "top_n": "20",
                "selected_symbols": "XOM|CVX",
                "composite_score_snapshot_date": "2025-05-01",
                "replay_mode": "HISTORICAL_VALIDATION",
            },
            {
                "replay_id": "RID-MATERIALS-LARGE",
                "start_date": "2025-05-01",
                "end_date": "2026-05-01",
                "filter_market_cap_bucket": "LARGE",
                "filter_geography": "US",
                "filter_industry": "BASIC MATERIALS",
                "filter_analytical_subtier": "",
                "selection_method": "TOP_N_COMPOSITE_AT_START",
                "top_n": "20",
                "selected_symbols": "NUE|LIN",
                "composite_score_snapshot_date": "2025-05-01",
                "replay_mode": "HISTORICAL_VALIDATION",
            },
            {
                "replay_id": "RID-INDUS-LARGE",
                "start_date": "2025-05-01",
                "end_date": "2026-05-01",
                "filter_market_cap_bucket": "LARGE",
                "filter_geography": "US",
                "filter_industry": "INDUSTRIALS",
                "filter_analytical_subtier": "",
                "selection_method": "TOP_N_COMPOSITE_AT_START",
                "top_n": "20",
                "selected_symbols": "CAT|DE",
                "composite_score_snapshot_date": "2025-05-01",
                "replay_mode": "HISTORICAL_VALIDATION",
            },
        ],
    )


def _seed_replay_perf(tmp_path: Path) -> None:
    rows = []

    # Build 80 points so 5d/20d/60d windows are all available.
    dates: list[str] = []
    start = date(2026, 1, 1)
    for i in range(80):
        dates.append((start + timedelta(days=i)).isoformat())

    # tech underperforms while hard-assets trend stronger
    tech = [100.0 + (i * 0.05) for i in range(80)]
    energy = [100.0 + (i * 0.18) for i in range(80)]
    mats = [100.0 + (i * 0.16) for i in range(80)]
    indus = [100.0 + (i * 0.14) for i in range(80)]

    def add_series(replay_id: str, vals: list[float]) -> None:
        for d, v in zip(dates, vals):
            rows.append(
                {
                    "series_id": f"{replay_id}:BENCHMARK",
                    "replay_id": replay_id,
                    "series_type": "BENCHMARK",
                    "date": d,
                    "value": str(v),
                    "cumulative_return": "0",
                    "source": "benchmark_history_provider",
                    "coverage_status": "AVAILABLE",
                }
            )

    add_series("RID-TECH-LARGE", tech)
    add_series("RID-ENERGY-LARGE", energy)
    add_series("RID-MATERIALS-LARGE", mats)
    add_series("RID-INDUS-LARGE", indus)

    _write_csv(
        tmp_path / "data" / "current" / "replay_performance_series.csv",
        [
            "series_id",
            "replay_id",
            "series_type",
            "date",
            "value",
            "cumulative_return",
            "source",
            "coverage_status",
        ],
        rows,
    )


def test_rotation_monitor_elevated_when_hard_assets_lead_and_confirmation(tmp_path: Path):
    _seed_manifest_and_holdings(
        tmp_path,
        [
            {"symbol": "AAPL", "industry": "TECHNOLOGY", "market_value": "30000", "percent_of_portfolio": "30"},
            {"symbol": "MSFT", "industry": "TECHNOLOGY", "market_value": "20000", "percent_of_portfolio": "20"},
            {"symbol": "NVDA", "industry": "TECHNOLOGY", "market_value": "10000", "percent_of_portfolio": "10"},
            {"symbol": "XOM", "industry": "ENERGY", "market_value": "12000", "percent_of_portfolio": "12"},
            {"symbol": "CVX", "industry": "ENERGY", "market_value": "10000", "percent_of_portfolio": "10"},
            {"symbol": "NUE", "industry": "BASIC MATERIALS", "market_value": "9000", "percent_of_portfolio": "9"},
            {"symbol": "CAT", "industry": "INDUSTRIALS", "market_value": "9000", "percent_of_portfolio": "9"},
        ],
    )
    _seed_signal_snapshot(
        tmp_path,
        [
            {"snapshot_date": "2026-06-26", "symbol": "AAPL", "starmine_ess_numeric": "2"},
            {"snapshot_date": "2026-06-26", "symbol": "MSFT", "starmine_ess_numeric": "2"},
            {"snapshot_date": "2026-06-26", "symbol": "NVDA", "starmine_ess_numeric": "3"},
            {"snapshot_date": "2026-06-26", "symbol": "XOM", "starmine_ess_numeric": "4"},
            {"snapshot_date": "2026-06-26", "symbol": "CVX", "starmine_ess_numeric": "5"},
            {"snapshot_date": "2026-06-26", "symbol": "NUE", "starmine_ess_numeric": "4"},
            {"snapshot_date": "2026-06-26", "symbol": "CAT", "starmine_ess_numeric": "4"},
        ],
    )
    _seed_replay_inputs(tmp_path)
    _seed_replay_perf(tmp_path)

    result = rotation_risk_summary(tmp_path)

    assert result["status"] == "OK"
    assert result["signal"] in {"ELEVATED_ROTATION_RISK", "WATCHLIST_ROTATION"}
    assert result["proxy_returns"]["selected_cap_bucket"] == "LARGE"
    assert result["proxy_returns"]["rotation_spread_pct"]["20d"] is not None
    assert result["portfolio_exposure"]["tech_pct"] > 0
    assert result["portfolio_exposure"]["hard_assets_pct"] > 0


def test_rotation_monitor_data_unavailable_when_replay_missing(tmp_path: Path):
    _seed_manifest_and_holdings(
        tmp_path,
        [
            {"symbol": "AAPL", "industry": "TECHNOLOGY", "market_value": "1000", "percent_of_portfolio": "50"},
            {"symbol": "XOM", "industry": "ENERGY", "market_value": "1000", "percent_of_portfolio": "50"},
        ],
    )
    _seed_signal_snapshot(
        tmp_path,
        [
            {"snapshot_date": "2026-06-26", "symbol": "AAPL", "starmine_ess_numeric": "3"},
            {"snapshot_date": "2026-06-26", "symbol": "XOM", "starmine_ess_numeric": "3"},
        ],
    )

    result = rotation_risk_summary(tmp_path)

    assert result["status"] == "DATA_UNAVAILABLE"
    assert result["signal"] == "DATA_UNAVAILABLE"
    assert len(result["data_quality"]["missing_inputs"]) >= 1
