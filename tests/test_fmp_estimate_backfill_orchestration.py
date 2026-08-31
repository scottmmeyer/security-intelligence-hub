from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.history import fmp_estimate_backfill as feb
from src.history.pit_observation_manager import query_pit_observations


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
        [{"symbol": s, "company_name": s, "market_cap_bucket": "MID"} for s in symbols],
    )


def _success_rows(symbol: str, today: str, period: str = "annual") -> list[dict[str, str]]:
    return [
        {
            "symbol": symbol,
            "sourced_date": today,
            "fetch_status": "SUCCESS",
            "failure_type": "",
            "failure_reason": "",
            "request_period": period,
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
        },
        {
            "symbol": symbol,
            "sourced_date": today,
            "fetch_status": "SUCCESS",
            "failure_type": "",
            "failure_reason": "",
            "request_period": period,
            "period_date": "2030-01-31",
            "period_label": "",
            "fiscal_period": "2030-01-31",
            "forecast_horizon": "ANNUAL",
            "estimated_revenue_avg": "95",
            "estimated_revenue_high": "102",
            "estimated_revenue_low": "88",
            "estimated_eps_avg": "1.9",
            "estimated_eps_high": "2.1",
            "estimated_eps_low": "1.7",
            "analyst_count_revenue": "9",
            "analyst_count_eps": "7",
        },
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


def _failed_rows(symbol: str, today: str, failure_type: str = "NETWORK_ERROR") -> list[dict[str, str]]:
    return [
        {
            "symbol": symbol,
            "sourced_date": today,
            "fetch_status": "FETCH_FAILED",
            "failure_type": failure_type,
            "failure_reason": "simulated",
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


def _duplicate_period_rows(
    symbol: str,
    today: str,
    *,
    conflicting: bool = False,
) -> list[dict[str, str]]:
    rows = _success_rows(symbol, today, period="annual")
    duplicate = dict(rows[0])
    if conflicting:
        duplicate["estimated_eps_avg"] = "9.9"
    rows.append(duplicate)
    return rows


def _fetch_factory(
    *,
    behavior: dict[str, str],
    call_log: list[str],
    retries_by_symbol: dict[str, int] | None = None,
    rate_limit_by_symbol: dict[str, int] | None = None,
):
    retries_by_symbol = retries_by_symbol or {}
    rate_limit_by_symbol = rate_limit_by_symbol or {}

    def _fake(symbol: str, api_key: str, today: str, *, period: str, page: int = 0, limit: int = 8):
        call_log.append(symbol)
        state = behavior.get(symbol, "success")
        if state == "success":
            rows = _success_rows(symbol, today, period=period)
        elif state == "no_coverage":
            rows = _no_coverage_rows(symbol, today)
        elif state == "rate_limit":
            rows = _failed_rows(symbol, today, failure_type="RATE_LIMIT")
        elif state == "plan_limit":
            rows = _failed_rows(symbol, today, failure_type="PLAN_LIMIT")
        else:
            rows = _failed_rows(symbol, today, failure_type="NETWORK_ERROR")
        return rows, {
            "status": 200 if state in {"success", "no_coverage"} else 0,
            "error": "",
            "retries_performed": int(retries_by_symbol.get(symbol, 0)),
            "rate_limit_events": int(rate_limit_by_symbol.get(symbol, 0)),
            "period": period,
            "request_url": "stub",
        }

    return _fake


def test_FMP_BACKFILL_BATCH_PARTITION_TEST() -> None:
    symbols = [f"S{i:03d}" for i in range(123)]
    batches = feb._partition_symbols(symbols, 50)
    sizes = [len(batch) for batch in batches]
    assert sizes == [50, 50, 23]


def test_FMP_BACKFILL_CHECKPOINT_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    symbols = [f"S{i:03d}" for i in range(8)]
    _seed_base_universe(repo, symbols)

    calls: list[str] = []
    monkeypatch.setattr(feb, "_get_api_key", lambda: "TEST")
    monkeypatch.setattr(
        feb,
        "fetch_analyst_estimates_with_meta",
        _fetch_factory(behavior={s: "success" for s in symbols}, call_log=calls),
    )

    checkpoint_path = repo / "runtime" / "fmp_checkpoint.json"
    result = feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=5,
        checkpoint_path=checkpoint_path,
        max_batches=1,
        delay_seconds=0.0,
    )

    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert result["status"] == "IN_PROGRESS"
    assert checkpoint["current_batch"] == 1
    assert checkpoint["batch_size"] == 5
    assert checkpoint["requested_periods"] == ["annual"]
    assert checkpoint["universe_count"] == 8
    assert len(checkpoint["completed_symbols"]) == 5
    assert checkpoint["estimate_rows_fetched"] > 0


def test_FMP_BACKFILL_RESUME_SKIP_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    symbols = [f"S{i:03d}" for i in range(10)]
    _seed_base_universe(repo, symbols)

    calls: list[str] = []
    monkeypatch.setattr(feb, "_get_api_key", lambda: "TEST")
    monkeypatch.setattr(
        feb,
        "fetch_analyst_estimates_with_meta",
        _fetch_factory(behavior={s: "success" for s in symbols}, call_log=calls),
    )

    checkpoint_path = repo / "runtime" / "resume_checkpoint.json"
    first = feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=5,
        checkpoint_path=checkpoint_path,
        max_batches=1,
        delay_seconds=0.0,
    )
    first_calls = len(calls)
    assert first_calls == 5

    second = feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=5,
        checkpoint_path=checkpoint_path,
        resume=True,
        delay_seconds=0.0,
    )
    second_calls = len(calls) - first_calls
    assert first["completed_count"] == 5
    assert second_calls == 5
    assert second["status"] == "COMPLETE"
    assert second["completed_count"] == 10


def test_FMP_BACKFILL_NO_COVERAGE_TERMINAL_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    symbols = ["AAA", "BBB", "CCC"]
    _seed_base_universe(repo, symbols)

    calls: list[str] = []
    monkeypatch.setattr(feb, "_get_api_key", lambda: "TEST")
    monkeypatch.setattr(
        feb,
        "fetch_analyst_estimates_with_meta",
        _fetch_factory(
            behavior={"AAA": "no_coverage", "BBB": "success", "CCC": "success"},
            call_log=calls,
        ),
    )

    checkpoint_path = repo / "runtime" / "no_cov_checkpoint.json"
    feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=2,
        checkpoint_path=checkpoint_path,
        max_batches=1,
        delay_seconds=0.0,
    )
    first_calls = len(calls)

    resumed = feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=2,
        checkpoint_path=checkpoint_path,
        resume=True,
        delay_seconds=0.0,
    )
    second_calls = len(calls) - first_calls
    assert second_calls <= 1
    assert "AAA" in resumed["no_coverage_symbols"]


def test_FMP_BACKFILL_TRANSIENT_RETRY_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    symbols = ["AAA", "BBB"]
    _seed_base_universe(repo, symbols)

    calls: list[str] = []
    state = {"AAA": 0, "BBB": 0}

    def _fake(symbol: str, api_key: str, today: str, *, period: str, page: int = 0, limit: int = 8):
        calls.append(symbol)
        state[symbol] += 1
        if symbol == "AAA" and state[symbol] == 1:
            return _failed_rows(symbol, today, failure_type="NETWORK_ERROR"), {
                "status": 0,
                "error": "boom",
                "retries_performed": 1,
                "rate_limit_events": 0,
                "period": period,
                "request_url": "stub",
            }
        return _success_rows(symbol, today, period=period), {
            "status": 200,
            "error": "",
            "retries_performed": 0,
            "rate_limit_events": 0,
            "period": period,
            "request_url": "stub",
        }

    monkeypatch.setattr(feb, "_get_api_key", lambda: "TEST")
    monkeypatch.setattr(feb, "fetch_analyst_estimates_with_meta", _fake)

    checkpoint_path = repo / "runtime" / "retry_checkpoint.json"
    first = feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=2,
        checkpoint_path=checkpoint_path,
        max_batches=1,
        delay_seconds=0.0,
    )
    assert first["failed_count"] == 1

    second = feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=2,
        checkpoint_path=checkpoint_path,
        resume=True,
        delay_seconds=0.0,
    )
    assert second["failed_count"] == 0
    assert second["status"] == "COMPLETE"
    assert calls.count("AAA") == 2


def test_FMP_BACKFILL_SCOPE_MISMATCH_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    _seed_base_universe(repo, ["AAA", "BBB"])

    calls: list[str] = []
    monkeypatch.setattr(feb, "_get_api_key", lambda: "TEST")
    monkeypatch.setattr(
        feb,
        "fetch_analyst_estimates_with_meta",
        _fetch_factory(behavior={"AAA": "success", "BBB": "success"}, call_log=calls),
    )

    checkpoint_path = repo / "runtime" / "scope_checkpoint.json"
    feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=1,
        checkpoint_path=checkpoint_path,
        max_batches=1,
        delay_seconds=0.0,
    )

    _seed_base_universe(repo, ["AAA", "BBB", "CCC"])
    with pytest.raises(ValueError, match="universe_(count|hash)"):
        feb.run_fmp_estimate_backfill(
            repo_root=repo,
            research_universe=True,
            requested_periods=["annual"],
            batch_size=1,
            checkpoint_path=checkpoint_path,
            resume=True,
            delay_seconds=0.0,
        )


def test_FMP_BACKFILL_PERIOD_MISMATCH_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    _seed_base_universe(repo, ["AAA", "BBB"])

    calls: list[str] = []
    monkeypatch.setattr(feb, "_get_api_key", lambda: "TEST")
    monkeypatch.setattr(
        feb,
        "fetch_analyst_estimates_with_meta",
        _fetch_factory(behavior={"AAA": "success", "BBB": "success"}, call_log=calls),
    )

    checkpoint_path = repo / "runtime" / "period_checkpoint.json"
    feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=1,
        checkpoint_path=checkpoint_path,
        max_batches=1,
        delay_seconds=0.0,
    )

    with pytest.raises(ValueError, match="requested_periods"):
        feb.run_fmp_estimate_backfill(
            repo_root=repo,
            research_universe=True,
            requested_periods=["annual", "quarter"],
            batch_size=1,
            checkpoint_path=checkpoint_path,
            resume=True,
            delay_seconds=0.0,
        )


def test_FMP_BACKFILL_PIT_RESUME_IDEMPOTENCE_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    _seed_base_universe(repo, ["AAA", "BBB"])

    calls: list[str] = []
    monkeypatch.setattr(feb, "_get_api_key", lambda: "TEST")
    monkeypatch.setattr(
        feb,
        "fetch_analyst_estimates_with_meta",
        _fetch_factory(behavior={"AAA": "success", "BBB": "success"}, call_log=calls),
    )

    real_write_checkpoint = feb._write_json_atomic
    checkpoint_writes = {"count": 0}

    def _flaky_checkpoint(path: Path, payload: dict[str, object]) -> None:
        checkpoint_writes["count"] += 1
        # Fail once after first symbol checkpoint has been written.
        if checkpoint_writes["count"] == 2:
            raise RuntimeError("simulated crash")
        real_write_checkpoint(path, payload)

    monkeypatch.setattr(feb, "_write_json_atomic", _flaky_checkpoint)

    checkpoint_path = repo / "runtime" / "pit_idem_checkpoint.json"
    with pytest.raises(RuntimeError, match="simulated crash"):
        feb.run_fmp_estimate_backfill(
            repo_root=repo,
            research_universe=True,
            requested_periods=["annual"],
            batch_size=2,
            checkpoint_path=checkpoint_path,
            delay_seconds=0.0,
        )

    monkeypatch.setattr(feb, "_write_json_atomic", real_write_checkpoint)
    resumed = feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=2,
        checkpoint_path=checkpoint_path,
        resume=True,
        delay_seconds=0.0,
    )

    assert resumed["status"] == "COMPLETE"
    assert resumed["pit_duplicates_skipped"] > 0
    rows = query_pit_observations(
        symbol="BBB",
        cutoff_retrieved_at_utc="9999-12-31T23:59:59+00:00",
        provider="FMP",
        history_root=repo / "data/history/pit_observations",
    )
    assert rows


def test_FMP_BACKFILL_DRY_RUN_TEST(tmp_path: Path) -> None:
    repo = tmp_path
    _seed_base_universe(repo, ["AAA", "BBB", "CCC"])

    result = feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=2,
        checkpoint_path=repo / "runtime" / "dry_run_checkpoint.json",
        dry_run=True,
    )

    assert result["provider_calls"] == 0
    assert result["pit_writes"] == 0
    assert result["fmp_writes"] == 0


def test_FMP_BACKFILL_FINAL_LATEST_ARTIFACT_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    symbols = [f"S{i:03d}" for i in range(12)]
    _seed_base_universe(repo, symbols)

    calls: list[str] = []
    monkeypatch.setattr(feb, "_get_api_key", lambda: "TEST")
    monkeypatch.setattr(
        feb,
        "fetch_analyst_estimates_with_meta",
        _fetch_factory(behavior={s: "success" for s in symbols}, call_log=calls),
    )

    result = feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=5,
        checkpoint_path=repo / "runtime" / "latest_checkpoint.json",
        delay_seconds=0.0,
    )

    latest_path = Path(result["latest_artifact_path"])
    rows = list(csv.DictReader(latest_path.open("r", encoding="utf-8", newline="")))
    symbols_in_latest = {str(row.get("symbol") or "").strip().upper() for row in rows}
    assert symbols_in_latest == set(symbols)


def test_FMP_BACKFILL_INTERRUPT_RESUME_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    symbols = [f"S{i:03d}" for i in range(15)]
    _seed_base_universe(repo, symbols)

    calls: list[str] = []
    monkeypatch.setattr(feb, "_get_api_key", lambda: "TEST")
    monkeypatch.setattr(
        feb,
        "fetch_analyst_estimates_with_meta",
        _fetch_factory(behavior={s: "success" for s in symbols}, call_log=calls),
    )

    checkpoint_path = repo / "runtime" / "interrupt_checkpoint.json"
    first = feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=5,
        checkpoint_path=checkpoint_path,
        max_batches=2,
        delay_seconds=0.0,
    )
    assert first["status"] == "IN_PROGRESS"

    resumed = feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=5,
        checkpoint_path=checkpoint_path,
        resume=True,
        delay_seconds=0.0,
    )
    assert resumed["status"] == "COMPLETE"
    assert resumed["completed_count"] == 15


def test_FMP_EXACT_DUPLICATE_COLLAPSE_TEST() -> None:
    rows = _duplicate_period_rows("CAE", "2026-08-30", conflicting=False)
    canonical, meta = feb._canonicalize_rows_for_publication(rows)

    assert len(canonical) == 2
    assert meta["provider_duplicate_rows_detected"] == 2
    assert meta["provider_duplicate_rows_collapsed"] == 1
    assert meta["provider_duplicate_conflict_key_count"] == 0


def test_FMP_DUPLICATE_CONFLICT_TEST() -> None:
    rows = _duplicate_period_rows("CAE", "2026-08-30", conflicting=True)
    canonical, meta = feb._canonicalize_rows_for_publication(rows)
    conflict_rows = [r for r in canonical if str(r.get("failure_type") or "") == feb.CONFLICT_FAILURE_TYPE]

    assert len(canonical) == 2
    assert len(conflict_rows) == 1
    assert meta["provider_duplicate_rows_detected"] == 2
    assert meta["provider_duplicate_rows_collapsed"] == 0
    assert meta["provider_duplicate_conflict_key_count"] == 1


def test_FMP_DISTINCT_PERIOD_RETENTION_TEST() -> None:
    rows = _success_rows("CAE", "2026-08-30", period="annual")
    canonical, meta = feb._canonicalize_rows_for_publication(rows)

    assert len(canonical) == 2
    assert meta["provider_duplicate_rows_detected"] == 0


def test_FMP_DISTINCT_SYMBOL_RETENTION_TEST() -> None:
    rows = _success_rows("AAA", "2026-08-30", period="annual")[:1] + _success_rows("BBB", "2026-08-30", period="annual")[:1]
    canonical, meta = feb._canonicalize_rows_for_publication(rows)
    symbols = {str(r.get("symbol") or "") for r in canonical}

    assert len(canonical) == 2
    assert symbols == {"AAA", "BBB"}
    assert meta["provider_duplicate_rows_detected"] == 0


def test_FMP_FINAL_LATEST_UNIQUENESS_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    symbols = ["CAE", "MSFT"]
    _seed_base_universe(repo, symbols)

    def _fake(symbol: str, api_key: str, today: str, *, period: str, page: int = 0, limit: int = 8):
        if symbol == "CAE":
            rows = _duplicate_period_rows(symbol, today, conflicting=False)
        else:
            rows = _success_rows(symbol, today, period=period)
        return rows, {
            "status": 200,
            "error": "",
            "retries_performed": 0,
            "rate_limit_events": 0,
            "period": period,
            "request_url": "stub",
        }

    monkeypatch.setattr(feb, "_get_api_key", lambda: "TEST")
    monkeypatch.setattr(feb, "fetch_analyst_estimates_with_meta", _fake)

    result = feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=2,
        checkpoint_path=repo / "runtime" / "final_unique_checkpoint.json",
        delay_seconds=0.0,
    )

    latest_path = Path(result["latest_artifact_path"])
    rows = list(csv.DictReader(latest_path.open("r", encoding="utf-8", newline="")))
    keys = {
        (
            str(r.get("symbol") or "").strip().upper(),
            str(r.get("request_period") or "").strip().lower(),
            str(r.get("period_date") or "").strip(),
        )
        for r in rows
    }

    assert len(rows) == len(keys)
    assert result["provider_duplicate_rows_detected"] == 2
    assert result["provider_duplicate_rows_collapsed"] == 1


def test_FMP_DUPLICATE_PIT_BEHAVIOR_TEST(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    _seed_base_universe(repo, ["CAE"])

    def _fake(symbol: str, api_key: str, today: str, *, period: str, page: int = 0, limit: int = 8):
        rows = _duplicate_period_rows(symbol, today, conflicting=False)
        return rows, {
            "status": 200,
            "error": "",
            "retries_performed": 0,
            "rate_limit_events": 0,
            "period": period,
            "request_url": "stub",
        }

    monkeypatch.setattr(feb, "_get_api_key", lambda: "TEST")
    monkeypatch.setattr(feb, "fetch_analyst_estimates_with_meta", _fake)

    result = feb.run_fmp_estimate_backfill(
        repo_root=repo,
        research_universe=True,
        requested_periods=["annual"],
        batch_size=1,
        checkpoint_path=repo / "runtime" / "pit_dup_behavior_checkpoint.json",
        delay_seconds=0.0,
    )

    assert result["status"] == "COMPLETE"
    assert result["pit_observations_written"] == 16

    pit_rows = query_pit_observations(
        symbol="CAE",
        cutoff_retrieved_at_utc="9999-12-31T23:59:59+00:00",
        provider="FMP",
        history_root=repo / "data/history/pit_observations",
    )
    assert len(pit_rows) == 16
