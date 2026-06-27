"""Display-only guardrail tests for COMMODITY-FILL-GUARD-01 and ROTATION-FRAGILITY-WATCH-01."""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

from src.sih.rotation_risk_monitor import rotation_risk_summary


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _seed_manifest(tmp_path: Path, run_id: str = "PAR-GUARD-0001") -> str:
    manifest_path = tmp_path / "data" / "portfolio_ingestion" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "portfolios": [
                    {
                        "run_id": run_id,
                        "snapshot_date": "2026-06-27",
                        "created_at_utc": "2026-06-27T13:59:00+00:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return run_id


def _seed_holdings(tmp_path: Path, run_id: str) -> None:
    _write_csv(
        tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / run_id / "holdings.csv",
        ["symbol", "industry", "market_value", "percent_of_portfolio"],
        [
            {"symbol": "AAPL", "industry": "TECHNOLOGY", "market_value": "20000", "percent_of_portfolio": "20"},
            {"symbol": "MSFT", "industry": "TECHNOLOGY", "market_value": "11000", "percent_of_portfolio": "11"},
            {"symbol": "XOM", "industry": "ENERGY", "market_value": "10000", "percent_of_portfolio": "10"},
            {"symbol": "NUE", "industry": "BASIC MATERIALS", "market_value": "9000", "percent_of_portfolio": "9"},
            {"symbol": "CAT", "industry": "INDUSTRIALS", "market_value": "7000", "percent_of_portfolio": "7"},
            {"symbol": "VOO", "industry": "MISC", "market_value": "43000", "percent_of_portfolio": "43"},
        ],
    )


def _seed_signal_snapshot(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "data" / "current" / "signal_snapshot.csv",
        ["snapshot_date", "symbol", "starmine_ess_numeric"],
        [
            {"snapshot_date": "2026-06-27", "symbol": "AAPL", "starmine_ess_numeric": "2"},
            {"snapshot_date": "2026-06-27", "symbol": "MSFT", "starmine_ess_numeric": "2"},
            {"snapshot_date": "2026-06-27", "symbol": "XOM", "starmine_ess_numeric": "4"},
            {"snapshot_date": "2026-06-27", "symbol": "NUE", "starmine_ess_numeric": "4"},
            {"snapshot_date": "2026-06-27", "symbol": "CAT", "starmine_ess_numeric": "4"},
        ],
    )


def _seed_alignment(
    tmp_path: Path,
    run_id: str,
    *,
    commodities_actual: float,
    commodities_target: float,
    gold_actual: float,
    gold_target: float,
    energy_actual: float,
    energy_target: float,
    broad_actual: float,
    broad_target: float,
    ultra_mega_drift: float,
) -> None:
    _write_csv(
        tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / run_id / "alignment.csv",
        [
            "analysis_run_id",
            "portfolio_snapshot_id",
            "node_key",
            "node_label",
            "dimension_type",
            "actual_pct",
            "target_pct",
            "tactical_target_pct",
            "drift_pct",
            "drift_direction",
            "severity",
            "concentration_risk",
            "alignment_score",
            "recommendation_priority",
            "created_at_utc",
        ],
        [
            {
                "analysis_run_id": run_id,
                "portfolio_snapshot_id": "PSNAP-TEST",
                "node_key": "COMMODITIES",
                "node_label": "COMMODITIES",
                "dimension_type": "ASSET_CLASS",
                "actual_pct": str(commodities_actual),
                "target_pct": str(commodities_target),
                "tactical_target_pct": str(commodities_target),
                "drift_pct": str(commodities_actual - commodities_target),
                "drift_direction": "UNDERWEIGHT",
                "severity": "LOW",
                "concentration_risk": "LOW",
                "alignment_score": "0.0",
                "recommendation_priority": "3",
                "created_at_utc": "2026-06-27T13:59:00+00:00",
            },
            {
                "analysis_run_id": run_id,
                "portfolio_snapshot_id": "PSNAP-TEST",
                "node_key": "COMMODITIES.GOLD",
                "node_label": "COMMODITIES.GOLD",
                "dimension_type": "GEOGRAPHY",
                "actual_pct": str(gold_actual),
                "target_pct": str(gold_target),
                "tactical_target_pct": str(gold_target),
                "drift_pct": str(gold_actual - gold_target),
                "drift_direction": "UNDERWEIGHT",
                "severity": "NONE",
                "concentration_risk": "LOW",
                "alignment_score": "0.0",
                "recommendation_priority": "4",
                "created_at_utc": "2026-06-27T13:59:00+00:00",
            },
            {
                "analysis_run_id": run_id,
                "portfolio_snapshot_id": "PSNAP-TEST",
                "node_key": "COMMODITIES.ENERGY",
                "node_label": "COMMODITIES.ENERGY",
                "dimension_type": "GEOGRAPHY",
                "actual_pct": str(energy_actual),
                "target_pct": str(energy_target),
                "tactical_target_pct": str(energy_target),
                "drift_pct": str(energy_actual - energy_target),
                "drift_direction": "UNDERWEIGHT",
                "severity": "NONE",
                "concentration_risk": "LOW",
                "alignment_score": "0.0",
                "recommendation_priority": "4",
                "created_at_utc": "2026-06-27T13:59:00+00:00",
            },
            {
                "analysis_run_id": run_id,
                "portfolio_snapshot_id": "PSNAP-TEST",
                "node_key": "COMMODITIES.BROAD_BASKET",
                "node_label": "COMMODITIES.BROAD_BASKET",
                "dimension_type": "GEOGRAPHY",
                "actual_pct": str(broad_actual),
                "target_pct": str(broad_target),
                "tactical_target_pct": str(broad_target),
                "drift_pct": str(broad_actual - broad_target),
                "drift_direction": "UNDERWEIGHT",
                "severity": "NONE",
                "concentration_risk": "LOW",
                "alignment_score": "0.0",
                "recommendation_priority": "4",
                "created_at_utc": "2026-06-27T13:59:00+00:00",
            },
            {
                "analysis_run_id": run_id,
                "portfolio_snapshot_id": "PSNAP-TEST",
                "node_key": "EQUITIES.US.MEGA.ULTRA_MEGA",
                "node_label": "EQUITIES.US.MEGA.ULTRA_MEGA",
                "dimension_type": "MEGA_SUBTIER",
                "actual_pct": "11.3",
                "target_pct": "6.3",
                "tactical_target_pct": "6.3",
                "drift_pct": str(ultra_mega_drift),
                "drift_direction": "OVERWEIGHT",
                "severity": "MODERATE",
                "concentration_risk": "LOW",
                "alignment_score": "0.2",
                "recommendation_priority": "2",
                "created_at_utc": "2026-06-27T13:59:00+00:00",
            },
        ],
    )


def _seed_deployment_queue(
    tmp_path: Path,
    run_id: str,
    *,
    deployable_cash: float,
    equity_symbols: list[str],
    commodity_symbols: list[str],
) -> None:
    queue = []
    rank = 1
    for sym in equity_symbols:
        queue.append(
            {
                "rank": rank,
                "symbol": sym,
                "allocation_node": "EQUITIES.US.LARGE",
                "deployment_score": 80.0,
            }
        )
        rank += 1
    for sym in commodity_symbols:
        queue.append(
            {
                "rank": rank,
                "symbol": sym,
                "allocation_node": "COMMODITIES.ENERGY",
                "deployment_score": 70.0,
            }
        )
        rank += 1

    payload = {
        "run_id": run_id,
        "queue_version": "CW-DAS-1.0",
        "candidate_count": len(queue),
        "cash_context": {
            "deployable_mv": deployable_cash,
            "adjusted_deployable_mv": deployable_cash,
        },
        "queue": queue,
    }
    path = tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / run_id / "deployment_queue.json"
    path.write_text(json.dumps(payload), encoding="utf-8")


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


def _seed_replay_perf(tmp_path: Path, mode: str) -> None:
    rows = []
    start = date(2026, 1, 1)
    dates = [(start + timedelta(days=i)).isoformat() for i in range(80)]

    if mode == "elevated":
        tech = [100.0 + (i * 0.05) for i in range(80)]
        energy = [100.0 + (i * 0.18) for i in range(80)]
        mats = [100.0 + (i * 0.16) for i in range(80)]
        indus = [100.0 + (i * 0.14) for i in range(80)]
    else:
        tech = [100.0 + (i * 0.10) for i in range(80)]
        energy = [100.0 + (i * 0.10) for i in range(80)]
        mats = [100.0 + (i * 0.10) for i in range(80)]
        indus = [100.0 + (i * 0.10) for i in range(80)]

    def _add_series(replay_id: str, vals: list[float]) -> None:
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

    _add_series("RID-TECH-LARGE", tech)
    _add_series("RID-ENERGY-LARGE", energy)
    _add_series("RID-MATERIALS-LARGE", mats)
    _add_series("RID-INDUS-LARGE", indus)

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


def _seed_mei_events(tmp_path: Path) -> None:
    today = date.today()
    events = [
        {
            "event_id": "PCE",
            "event_name": "PCE Price Index",
            "event_date": today.isoformat(),
            "impact_level": "HIGH",
            "sensitivity_tags": ["INFLATION"],
        },
        {
            "event_id": "NFP",
            "event_name": "Nonfarm Payrolls",
            "event_date": (today + timedelta(days=5)).isoformat(),
            "impact_level": "HIGH",
            "sensitivity_tags": ["LABOR"],
        },
    ]
    path = tmp_path / "data" / "mei" / "event_calendar.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(events), encoding="utf-8")


def _seed_prices(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "data" / "current" / "security_prices.csv",
        ["symbol", "date", "close"],
        [{"symbol": "AAPL", "date": "2026-06-27", "close": "100"}],
    )


def _seed_common(tmp_path: Path, *, replay_mode: str | None = "flat") -> tuple[str, Path]:
    run_id = _seed_manifest(tmp_path)
    _seed_holdings(tmp_path, run_id)
    _seed_signal_snapshot(tmp_path)
    _seed_mei_events(tmp_path)
    _seed_prices(tmp_path)
    if replay_mode is not None:
        _seed_replay_inputs(tmp_path)
        _seed_replay_perf(tmp_path, replay_mode)
    dq_path = tmp_path / "data" / "portfolio_ingestion" / "analysis_runs" / run_id / "deployment_queue.json"
    return run_id, dq_path


def test_guard_active_review_and_fragility_watch_when_no_clear_signal(tmp_path: Path):
    run_id, dq_path = _seed_common(tmp_path, replay_mode="flat")
    _seed_alignment(
        tmp_path,
        run_id,
        commodities_actual=0.0,
        commodities_target=2.0,
        gold_actual=0.0,
        gold_target=1.0,
        energy_actual=0.0,
        energy_target=0.7,
        broad_actual=0.0,
        broad_target=0.3,
        ultra_mega_drift=5.0,
    )
    _seed_deployment_queue(
        tmp_path,
        run_id,
        deployable_cash=4702.65,
        equity_symbols=["AAPL", "MSFT", "NUE"],
        commodity_symbols=[],
    )

    before = dq_path.read_text(encoding="utf-8")
    result = rotation_risk_summary(tmp_path)
    after = dq_path.read_text(encoding="utf-8")

    guard = result["commodity_fill_guard"]
    frag = result["rotation_fragility_watch"]

    assert result["signal"] == "NO_CLEAR_SIGNAL"
    assert guard["status"] == "ACTIVE_REVIEW"
    assert guard["commodities_actual_pct"] == 0.0
    assert guard["commodities_target_pct"] == 2.0
    assert guard["equity_deployment_count"] == 3
    assert frag["status"] in {"FRAGILITY_WATCH", "FRAGILITY_ELEVATED"}
    assert "not confirmed" in frag["message"].lower() or "incomplete" in frag["message"].lower()
    assert before == after


def test_guard_none_when_commodities_filled(tmp_path: Path):
    run_id, _ = _seed_common(tmp_path, replay_mode="flat")
    _seed_alignment(
        tmp_path,
        run_id,
        commodities_actual=2.0,
        commodities_target=2.0,
        gold_actual=1.0,
        gold_target=1.0,
        energy_actual=0.7,
        energy_target=0.7,
        broad_actual=0.3,
        broad_target=0.3,
        ultra_mega_drift=1.0,
    )
    _seed_deployment_queue(tmp_path, run_id, deployable_cash=4702.65, equity_symbols=["AAPL"], commodity_symbols=[])

    result = rotation_risk_summary(tmp_path)
    assert result["commodity_fill_guard"]["status"] == "NONE"


def test_guard_info_when_under_target_but_no_deployable_cash(tmp_path: Path):
    run_id, _ = _seed_common(tmp_path, replay_mode="flat")
    _seed_alignment(
        tmp_path,
        run_id,
        commodities_actual=0.0,
        commodities_target=2.0,
        gold_actual=0.0,
        gold_target=1.0,
        energy_actual=0.0,
        energy_target=0.7,
        broad_actual=0.0,
        broad_target=0.3,
        ultra_mega_drift=4.0,
    )
    _seed_deployment_queue(tmp_path, run_id, deployable_cash=0.0, equity_symbols=["AAPL"], commodity_symbols=[])

    result = rotation_risk_summary(tmp_path)
    assert result["commodity_fill_guard"]["status"] == "INFO"
    assert result["commodity_fill_guard"]["severity"] == "INFO"


def test_fragility_active_when_rotation_data_unavailable_and_hard_asset_unfilled(tmp_path: Path):
    run_id, _ = _seed_common(tmp_path, replay_mode=None)
    _seed_alignment(
        tmp_path,
        run_id,
        commodities_actual=0.0,
        commodities_target=2.0,
        gold_actual=0.0,
        gold_target=1.0,
        energy_actual=0.0,
        energy_target=0.7,
        broad_actual=0.0,
        broad_target=0.3,
        ultra_mega_drift=5.0,
    )
    _seed_deployment_queue(tmp_path, run_id, deployable_cash=4702.65, equity_symbols=["AAPL", "MSFT"], commodity_symbols=[])

    result = rotation_risk_summary(tmp_path)
    assert result["signal"] == "DATA_UNAVAILABLE"
    assert result["rotation_fragility_watch"]["status"] in {"FRAGILITY_WATCH", "FRAGILITY_ELEVATED"}


def test_fragility_severity_strengthens_when_rotation_elevated(tmp_path: Path):
    run_id, _ = _seed_common(tmp_path, replay_mode="elevated")
    _seed_alignment(
        tmp_path,
        run_id,
        commodities_actual=0.0,
        commodities_target=2.0,
        gold_actual=0.0,
        gold_target=1.0,
        energy_actual=0.0,
        energy_target=0.7,
        broad_actual=0.0,
        broad_target=0.3,
        ultra_mega_drift=5.0,
    )
    _seed_deployment_queue(tmp_path, run_id, deployable_cash=4702.65, equity_symbols=["AAPL", "MSFT", "NUE"], commodity_symbols=[])

    result = rotation_risk_summary(tmp_path)
    assert result["signal"] in {"WATCHLIST_ROTATION", "ELEVATED_ROTATION_RISK"}
    assert result["rotation_fragility_watch"]["severity"] in {"WATCH", "ELEVATED"}


def test_guard_none_when_commodities_target_is_zero(tmp_path: Path):
    run_id, _ = _seed_common(tmp_path, replay_mode="flat")
    _seed_alignment(
        tmp_path,
        run_id,
        commodities_actual=0.0,
        commodities_target=0.0,
        gold_actual=0.0,
        gold_target=0.0,
        energy_actual=0.0,
        energy_target=0.0,
        broad_actual=0.0,
        broad_target=0.0,
        ultra_mega_drift=0.0,
    )
    _seed_deployment_queue(tmp_path, run_id, deployable_cash=4702.65, equity_symbols=["AAPL"], commodity_symbols=[])

    result = rotation_risk_summary(tmp_path)
    assert result["commodity_fill_guard"]["status"] == "NONE"


def test_guard_reports_no_commodity_candidates_available(tmp_path: Path):
    run_id, _ = _seed_common(tmp_path, replay_mode="flat")
    _seed_alignment(
        tmp_path,
        run_id,
        commodities_actual=0.0,
        commodities_target=2.0,
        gold_actual=0.0,
        gold_target=1.0,
        energy_actual=0.0,
        energy_target=0.7,
        broad_actual=0.0,
        broad_target=0.3,
        ultra_mega_drift=5.0,
    )
    _seed_deployment_queue(tmp_path, run_id, deployable_cash=4702.65, equity_symbols=["AAPL", "MSFT"], commodity_symbols=[])

    result = rotation_risk_summary(tmp_path)
    guard = result["commodity_fill_guard"]
    assert guard["commodity_candidates_available"] is False
    assert guard["commodity_deployment_count"] == 0
