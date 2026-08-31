from __future__ import annotations

import csv
import fcntl
import json
from pathlib import Path

import pytest

from src.history import fmp_estimate_backfill as feb
from src.history.fmp_annual_snapshot import discover_recent_captures, run_daily_fmp_annual_snapshot
from src.history.pit_observation_manager import query_pit_observations


def _checkpoint_path(repo: Path, snapshot_date: str) -> Path:
    return repo / "data/runtime/checkpoints" / f"fmp_annual_estimate_{snapshot_date}.json"


def _report_path(repo: Path, snapshot_date: str) -> Path:
    return repo / "data/runtime/reports" / f"fmp_annual_estimate_{snapshot_date}.json"


def _lock_path(repo: Path, snapshot_date: str) -> Path:
    return repo / "data/runtime/locks" / f"fmp_annual_estimate_{snapshot_date}.lock"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in headers})


def _seed_base_universe(repo: Path, symbols: list[str]) -> None:
    _write_csv(
        repo / "data/current/base_equity_universe.csv",
        ["symbol", "company_name", "market_cap_bucket"],
        [{"symbol": symbol, "company_name": symbol, "market_cap_bucket": "MID"} for symbol in symbols],
    )


def _success_rows(symbol: str, today: str) -> list[dict[str, str]]:
    return [
        {
            "symbol": symbol,
            "sourced_date": today,
            "fetch_status": "SUCCESS",
            "failure_type": "",
            "failure_reason": "",
            "request_period": "annual",
            "period_date": "2031-01-31",
            "period_label": "",
            "fiscal_period": "2031-01-31",
            "forecast_horizon": "ANNUAL",
            "estimated_revenue_avg": "100",
            "estimated_revenue_high": "110",
            "estimated_revenue_low": "90",
            "estimated_eps_avg": "2.0",
            "estimated_eps_high": "2.2",
            "estimated_eps_low": "1.8",
            "analyst_count_revenue": "10",
            "analyst_count_eps": "8",
        }
    ]


def _no_coverage_rows(symbol: str, today: str) -> list[dict[str, str]]:
    return [
        {
            "symbol": symbol,
            "sourced_date": today,
            "fetch_status": "PROVIDER_NO_DATA",
            "failure_type": "",
            "failure_reason": "",
            "request_period": "annual",
            "period_date": "",
            "period_label": "",
            "fiscal_period": "",
            "forecast_horizon": "ANNUAL",
            "estimated_revenue_avg": "",
            "estimated_revenue_high": "",
            "estimated_revenue_low": "",
            "estimated_eps_avg": "",
            "estimated_eps_high": "",
            "estimated_eps_low": "",
            "analyst_count_revenue": "",
            "analyst_count_eps": "",
        }
    ]


def _duplicate_rows(symbol: str, today: str) -> list[dict[str, str]]:
    row = _success_rows(symbol, today)[0]
    return [dict(row), dict(row)]


def test_FMP_DAILY_START_NEW_TEST(tmp_path: Path) -> None:
    repo = tmp_path
    calls: list[dict[str, object]] = []

    def _fake_backfill(**kwargs):
        calls.append(kwargs)
        return {
            "run_id": "run-a",
            "status": "COMPLETE",
            "requested_periods": ["annual"],
            "universe_count": 3,
            "universe_hash": "u1",
            "symbols_with_data_count": 2,
            "no_coverage_count": 1,
            "failed_count": 0,
            "total_batches": 1,
            "current_batch": 1,
            "estimate_rows_fetched": 4,
            "pit_observations_written": 8,
            "pit_duplicates_skipped": 0,
            "provider_duplicate_rows_detected": 0,
            "provider_duplicate_rows_collapsed": 0,
            "provider_duplicate_conflict_key_count": 0,
            "rate_limit_events": 0,
            "retries_performed": 0,
            "started_at_utc": "2026-08-31T10:00:00+00:00",
            "completed_at_utc": "2026-08-31T10:01:00+00:00",
        }

    result = run_daily_fmp_annual_snapshot(
        repo_root=repo,
        snapshot_date="2026-08-31",
        symbols=["CAE", "CRM", "MSFT"],
        run_backfill=_fake_backfill,
    )

    assert result["action"] == "START_NEW"
    assert result["status"] == "COMPLETE"
    assert result["requested_periods"] == ["annual"]
    assert "2026-08-31" in str(result["checkpoint_path"])
    assert "2026-08-31" in str(result["report_path"])
    assert len(calls) == 1
    assert calls[0]["resume"] is False
    assert calls[0]["requested_periods"] == ["annual"]


def test_FMP_DAILY_RESUME_INCOMPLETE_TEST(tmp_path: Path) -> None:
    repo = tmp_path
    snapshot_date = "2026-08-31"
    _write_json(
        _checkpoint_path(repo, snapshot_date),
        {
            "run_id": "run-resume",
            "status": "RUNNING",
            "requested_periods": ["annual"],
            "completed_symbols": ["CAE"],
            "failed_symbols": [],
            "symbols_with_data": ["CAE"],
            "no_coverage_symbols": [],
        },
    )

    calls: list[dict[str, object]] = []

    def _fake_backfill(**kwargs):
        calls.append(kwargs)
        return {
            "run_id": "run-resume",
            "status": "IN_PROGRESS",
            "requested_periods": ["annual"],
            "universe_count": 3,
            "universe_hash": "u1",
            "symbols_with_data_count": 1,
            "no_coverage_count": 0,
            "failed_count": 0,
            "total_batches": 2,
            "current_batch": 1,
            "estimate_rows_fetched": 2,
            "pit_observations_written": 4,
            "pit_duplicates_skipped": 0,
            "provider_duplicate_rows_detected": 0,
            "provider_duplicate_rows_collapsed": 0,
            "provider_duplicate_conflict_key_count": 0,
            "rate_limit_events": 0,
            "retries_performed": 0,
            "started_at_utc": "2026-08-31T10:00:00+00:00",
            "completed_at_utc": "",
        }

    result = run_daily_fmp_annual_snapshot(
        repo_root=repo,
        snapshot_date=snapshot_date,
        symbols=["CAE", "CRM", "MSFT"],
        run_backfill=_fake_backfill,
    )

    assert result["action"] == "RESUME"
    assert result["status"] == "IN_PROGRESS"
    assert len(calls) == 1
    assert calls[0]["resume"] is True


def test_FMP_DAILY_ALREADY_COMPLETE_SKIP_TEST(tmp_path: Path) -> None:
    repo = tmp_path
    snapshot_date = "2026-08-31"
    _write_json(
        _report_path(repo, snapshot_date),
        {
            "snapshot_date": snapshot_date,
            "status": "COMPLETE",
            "run_id": "run-complete",
            "requested_periods": ["annual"],
            "universe_count": 3,
            "symbols_with_data": 2,
            "symbols_no_coverage": 1,
            "symbols_failed": 0,
            "total_accounted": 3,
            "unaccounted_symbols": 0,
        },
    )

    called = {"value": False}

    def _never_call(**kwargs):
        called["value"] = True
        return {}

    result = run_daily_fmp_annual_snapshot(
        repo_root=repo,
        snapshot_date=snapshot_date,
        symbols=["CAE", "CRM", "MSFT"],
        run_backfill=_never_call,
    )

    assert result["action"] == "SKIP_ALREADY_COMPLETE"
    assert result["status"] == "ALREADY_COMPLETE"
    assert called["value"] is False


def test_FMP_DAILY_PARALLEL_BLOCK_TEST(tmp_path: Path) -> None:
    repo = tmp_path
    snapshot_date = "2026-08-31"
    lock_path = _lock_path(repo, snapshot_date)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        result = run_daily_fmp_annual_snapshot(
            repo_root=repo,
            snapshot_date=snapshot_date,
            symbols=["CAE", "CRM"],
        )

    assert result["status"] == "BLOCKED_ACTIVE_RUN"
    assert result["action"] == "BLOCKED_ACTIVE_RUN"


def test_FMP_DAILY_WEEKEND_SKIP_TEST(tmp_path: Path) -> None:
    repo = tmp_path

    called = {"value": False}

    def _never_call(**kwargs):
        called["value"] = True
        return {}

    result = run_daily_fmp_annual_snapshot(
        repo_root=repo,
        snapshot_date="2026-08-30",
        symbols=["CAE"],
        run_backfill=_never_call,
    )

    assert result["status"] == "SKIPPED_NON_TRADING_DAY"
    assert result["action"] == "SKIP_NON_TRADING_DAY"
    assert called["value"] is False


def test_FMP_DAILY_HEALTH_ACCOUNTING_AND_DUPLICATES_TEST(tmp_path: Path) -> None:
    repo = tmp_path

    def _fake_backfill(**kwargs):
        return {
            "run_id": "run-health",
            "status": "COMPLETE",
            "requested_periods": ["annual"],
            "universe_count": 4,
            "universe_hash": "u4",
            "symbols_with_data_count": 2,
            "no_coverage_count": 1,
            "failed_count": 1,
            "total_batches": 2,
            "current_batch": 2,
            "estimate_rows_fetched": 5,
            "pit_observations_written": 10,
            "pit_duplicates_skipped": 1,
            "provider_duplicate_rows_detected": 2,
            "provider_duplicate_rows_collapsed": 1,
            "provider_duplicate_conflict_key_count": 0,
            "rate_limit_events": 0,
            "retries_performed": 1,
            "started_at_utc": "2026-08-31T10:00:00+00:00",
            "completed_at_utc": "2026-08-31T10:01:00+00:00",
        }

    result = run_daily_fmp_annual_snapshot(
        repo_root=repo,
        snapshot_date="2026-08-31",
        symbols=["CAE", "CRM", "MSFT", "NVDA"],
        run_backfill=_fake_backfill,
    )

    assert result["status"] == "COMPLETE"
    assert result["symbols_no_coverage"] == 1
    assert result["symbols_failed"] == 1
    assert result["total_accounted"] == 4
    assert result["unaccounted_symbols"] == 0
    assert result["provider_duplicate_rows_detected"] == 2
    assert result["provider_duplicate_rows_collapsed"] == 1


def test_FMP_DAILY_DISCOVERY_TWO_DATE_TEST(tmp_path: Path) -> None:
    repo = tmp_path
    calls: list[dict[str, object]] = []

    def _fake_backfill(**kwargs):
        calls.append(kwargs)
        checkpoint_name = Path(str(kwargs["checkpoint_path"])).name
        run_id = checkpoint_name.replace("fmp_annual_estimate_", "run-").replace(".json", "")
        return {
            "run_id": run_id,
            "status": "COMPLETE",
            "requested_periods": ["annual"],
            "universe_count": 2,
            "universe_hash": "u2",
            "symbols_with_data_count": 2,
            "no_coverage_count": 0,
            "failed_count": 0,
            "total_batches": 1,
            "current_batch": 1,
            "estimate_rows_fetched": 4,
            "pit_observations_written": 8,
            "pit_duplicates_skipped": 0,
            "provider_duplicate_rows_detected": 0,
            "provider_duplicate_rows_collapsed": 0,
            "provider_duplicate_conflict_key_count": 0,
            "rate_limit_events": 0,
            "retries_performed": 0,
            "started_at_utc": "2026-08-31T10:00:00+00:00",
            "completed_at_utc": "2026-08-31T10:01:00+00:00",
        }

    first = run_daily_fmp_annual_snapshot(
        repo_root=repo,
        snapshot_date="2026-08-29",
        symbols=["CRM", "MSFT"],
        allow_non_trading_day=True,
        run_backfill=_fake_backfill,
    )
    second = run_daily_fmp_annual_snapshot(
        repo_root=repo,
        snapshot_date="2026-08-30",
        symbols=["CRM", "MSFT"],
        allow_non_trading_day=True,
        run_backfill=_fake_backfill,
    )

    assert first["run_id"] != second["run_id"]
    assert "2026-08-29" in str(calls[0]["checkpoint_path"])
    assert "2026-08-30" in str(calls[1]["checkpoint_path"])

    index = discover_recent_captures(repo_root=repo, limit=10)
    captures = list(index["captures"])
    assert len(captures) == 2
    assert captures[0]["snapshot_date"] == "2026-08-30"
    assert captures[1]["snapshot_date"] == "2026-08-29"


def test_FMP_DAILY_NO_COVERAGE_TERMINAL_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    snapshot_date = "2026-08-31"
    _seed_base_universe(repo, ["AAA"])

    calls: list[str] = []

    def _fake_fetch(symbol: str, api_key: str, today: str, *, period: str, page: int = 0, limit: int = 8):
        calls.append(symbol)
        return _no_coverage_rows(symbol, today), {
            "status": 200,
            "error": "",
            "retries_performed": 0,
            "rate_limit_events": 0,
            "period": period,
            "request_url": "stub",
        }

    monkeypatch.setattr(feb, "_get_api_key", lambda: "TEST")
    monkeypatch.setattr(feb, "fetch_analyst_estimates_with_meta", _fake_fetch)

    first = run_daily_fmp_annual_snapshot(
        repo_root=repo,
        snapshot_date=snapshot_date,
        allow_non_trading_day=True,
    )
    second = run_daily_fmp_annual_snapshot(
        repo_root=repo,
        snapshot_date=snapshot_date,
        allow_non_trading_day=True,
    )

    assert first["status"] == "COMPLETE"
    assert first["symbols_no_coverage"] == 1
    assert first["symbols_failed"] == 0
    assert first["total_accounted"] == 1
    assert second["action"] == "SKIP_ALREADY_COMPLETE"
    assert second["status"] == "ALREADY_COMPLETE"
    assert len(calls) == 1


def test_FMP_DAILY_PROVIDER_DUPLICATE_CANONICALIZATION_TEST(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path
    snapshot_date = "2026-08-31"

    def _fake_fetch(symbol: str, api_key: str, today: str, *, period: str, page: int = 0, limit: int = 8):
        return _duplicate_rows(symbol, today), {
            "status": 200,
            "error": "",
            "retries_performed": 0,
            "rate_limit_events": 0,
            "period": period,
            "request_url": "stub",
        }

    monkeypatch.setattr(feb, "_get_api_key", lambda: "TEST")
    monkeypatch.setattr(feb, "fetch_analyst_estimates_with_meta", _fake_fetch)

    result = run_daily_fmp_annual_snapshot(
        repo_root=repo,
        snapshot_date=snapshot_date,
        symbols=["CAE"],
        allow_non_trading_day=True,
    )

    run_id = str(result["run_id"])
    raw_symbol_path = repo / "data/runtime/fmp_estimate_backfill" / f"run_id={run_id}" / "symbol_rows" / "CAE.csv"
    latest_path = repo / "data/signals/fmp/latest/latest_fmp_analyst_estimates.csv"

    raw_rows = list(csv.DictReader(raw_symbol_path.open("r", encoding="utf-8", newline="")))
    canonical_rows = [
        row
        for row in csv.DictReader(latest_path.open("r", encoding="utf-8", newline=""))
        if str(row.get("symbol") or "").strip().upper() == "CAE"
    ]

    assert result["status"] == "COMPLETE"
    assert len(raw_rows) == 2
    assert len(canonical_rows) == 1
    assert result["provider_duplicate_rows_detected"] == 2
    assert result["provider_duplicate_rows_collapsed"] == 1
    assert result["provider_duplicate_conflict_key_count"] == 0


def test_FMP_DAILY_UNCHANGED_VALUE_RETENTION_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    snapshot_a = "2026-08-31"
    snapshot_b = "2026-09-01"

    def _fake_fetch(symbol: str, api_key: str, today: str, *, period: str, page: int = 0, limit: int = 8):
        return _success_rows(symbol, today), {
            "status": 200,
            "error": "",
            "retries_performed": 0,
            "rate_limit_events": 0,
            "period": period,
            "request_url": "stub",
        }

    monkeypatch.setattr(feb, "_get_api_key", lambda: "TEST")
    monkeypatch.setattr(feb, "fetch_analyst_estimates_with_meta", _fake_fetch)

    first = run_daily_fmp_annual_snapshot(
        repo_root=repo,
        snapshot_date=snapshot_a,
        symbols=["CRM"],
        allow_non_trading_day=True,
    )
    second = run_daily_fmp_annual_snapshot(
        repo_root=repo,
        snapshot_date=snapshot_b,
        symbols=["CRM"],
        allow_non_trading_day=True,
    )

    rows = query_pit_observations(
        symbol="CRM",
        cutoff_retrieved_at_utc="9999-12-31T23:59:59+00:00",
        provider="FMP",
        history_root=repo / "data/history/pit_observations",
    )
    matched = [
        row
        for row in rows
        if str(row.get("metric") or "") == "eps_estimate_avg"
        and str(row.get("forecast_horizon") or "") == "ANNUAL"
        and str(row.get("fiscal_period") or "") == "2031-01-31"
        and str(row.get("value") or "") == "2.0"
    ]

    run_ids = {str(row.get("run_id") or "") for row in matched}
    retrievals = {str(row.get("retrieved_at_utc") or "") for row in matched}

    assert first["status"] == "COMPLETE"
    assert second["status"] == "COMPLETE"
    assert str(first["run_id"]) != str(second["run_id"])
    assert len(matched) >= 2
    assert len(run_ids) == 2
    assert len(retrievals) == 2