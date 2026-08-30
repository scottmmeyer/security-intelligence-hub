from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.models.market_data_models import HistoricalPriceRow
from src.pis import momentum_price_history as mph


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in headers})


def _seed_price_history(repo_root: Path, symbol: str, dates: list[str]) -> None:
    rows = []
    for value in dates:
        rows.append(
            {
                "security_id": f"YF:{symbol}",
                "symbol": symbol,
                "security_type": "EQUITY",
                "date": value,
                "open": "100",
                "high": "100",
                "low": "100",
                "close": "100",
                "adjusted_close": "100",
                "volume": "1000",
                "dividend": "0",
                "split_ratio": "1",
                "source_provider": "TEST",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
    _write_csv(
        repo_root / "data/history/prices" / f"symbol={symbol}" / "prices.csv",
        mph.SECURITY_PRICE_HEADERS if hasattr(mph, "SECURITY_PRICE_HEADERS") else [
            "security_id",
            "symbol",
            "security_type",
            "date",
            "open",
            "high",
            "low",
            "close",
            "adjusted_close",
            "volume",
            "dividend",
            "split_ratio",
            "source_provider",
            "created_at_utc",
        ],
        rows,
    )


def _seed_benchmark_history(repo_root: Path, dates: list[str]) -> None:
    rows = []
    for idx, value in enumerate(dates):
        rows.append(
            {
                "benchmark_id": "BM_US_LARGE_SP500",
                "symbol_or_index": "^GSPC",
                "date": value,
                "adjusted_close": str(100 + idx),
                "cumulative_return": str(idx / 100.0),
                "source_provider": "TEST",
            }
        )
    _write_csv(
        repo_root / "data/history/benchmarks/benchmark_id=BM_US_LARGE_SP500" / "benchmark_returns.csv",
        [
            "benchmark_id",
            "symbol_or_index",
            "date",
            "adjusted_close",
            "cumulative_return",
            "source_provider",
        ],
        rows,
    )


def _seed_research_universe(repo_root: Path, rows: list[dict[str, str]]) -> None:
    headers = ["symbol", "security_type", "industry", "sector", "market_cap_bucket"]
    _write_csv(repo_root / "data/current/analytical_universe.csv", headers, rows)


def _price_row(symbol: str, value_date: str, px: float = 100.0) -> HistoricalPriceRow:
    return HistoricalPriceRow(
        security_id=f"YF:{symbol}",
        symbol=symbol,
        security_type="EQUITY",
        date=value_date,
        open=px,
        high=px,
        low=px,
        close=px,
        adjusted_close=px,
        volume=1000,
        dividend=0.0,
        split_ratio=1.0,
        source_provider="TEST_PROVIDER",
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def test_explicit_symbol_backfill_and_date_propagation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    _seed_benchmark_history(repo, ["2021-01-04", "2026-08-27"])

    calls: list[dict[str, str]] = []

    class FakeProvider:
        def get_historical_prices(self, **kwargs):
            calls.append({k: str(v) for k, v in kwargs.items()})
            symbol = str(kwargs["symbol"])
            return [_price_row(symbol, "2021-01-04"), _price_row(symbol, "2026-08-27")]

    monkeypatch.setattr(mph, "YahooHistoricalPriceProvider", lambda: FakeProvider())

    result = mph.backfill_research_universe_price_history(
        repo_root=repo,
        symbols=["crm", "aapl"],
        start_date="2021-01-01",
        end_date="2026-08-29",
        batch_size=1,
        checkpoint_path=repo / "runtime" / "checkpoint.json",
        include_benchmark=False,
        dry_run=False,
    )

    assert result["mode"] == "explicit_symbols"
    assert {c["symbol"] for c in calls} == {"CRM", "AAPL"}
    assert all(c["start_date"] == "2021-01-01" for c in calls)
    assert all(c["end_date"] == "2026-08-29" for c in calls)
    assert all(r["status"] in {"SUCCESS", "ALREADY_COMPLETE"} for r in result["symbol_results"])


def test_research_universe_mode_independent_of_portfolio(tmp_path: Path) -> None:
    repo = tmp_path
    _seed_benchmark_history(repo, ["2021-01-04", "2026-08-27"])
    _seed_research_universe(
        repo,
        [
            {
                "symbol": "HELD",
                "security_type": "EQUITY",
                "industry": "TECH",
                "sector": "TECHNOLOGY",
                "market_cap_bucket": "LARGE",
            },
            {
                "symbol": "NONHELD",
                "security_type": "EQUITY",
                "industry": "TECH",
                "sector": "TECHNOLOGY",
                "market_cap_bucket": "SMALL",
            },
        ],
    )

    result = mph.backfill_research_universe_price_history(
        repo_root=repo,
        research_universe_mode=True,
        start_date="2021-01-01",
        end_date="2026-08-29",
        checkpoint_path=repo / "runtime" / "checkpoint.json",
        include_benchmark=False,
        dry_run=True,
    )

    assert result["research_universe_symbols_resolved"] == 2
    assert result["applicable_equities_resolved"] == 2
    assert result["sample_status_by_symbol"]["HELD"] == "FETCH_REQUIRED"
    assert result["sample_status_by_symbol"]["NONHELD"] == "FETCH_REQUIRED"


def test_already_complete_contract_checks_start_and_end(tmp_path: Path) -> None:
    repo = tmp_path
    _seed_benchmark_history(repo, ["2021-01-04", "2026-08-27"])

    _seed_price_history(repo, "AAA", ["2020-12-31", "2026-08-27"])
    _seed_price_history(repo, "BBB", ["2020-12-31", "2026-08-26"])
    _seed_price_history(repo, "CCC", ["2022-01-03", "2026-08-27"])
    _seed_price_history(repo, "DDD", ["2022-01-03", "2026-08-26"])

    result = mph.backfill_research_universe_price_history(
        repo_root=repo,
        symbols=["AAA", "BBB", "CCC", "DDD"],
        start_date="2021-01-01",
        end_date="2026-08-29",
        checkpoint_path=repo / "runtime" / "checkpoint.json",
        include_benchmark=False,
        dry_run=True,
    )

    assert result["already_complete_count"] == 1
    assert result["fetch_required_count"] == 3
    assert result["sample_status_by_symbol"]["AAA"] == "ALREADY_COMPLETE"
    assert result["sample_status_by_symbol"]["BBB"] == "FETCH_REQUIRED"
    assert result["sample_status_by_symbol"]["CCC"] == "FETCH_REQUIRED"
    assert result["sample_status_by_symbol"]["DDD"] == "FETCH_REQUIRED"


def test_no_truncation_and_idempotence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    _seed_benchmark_history(repo, ["2021-01-04", "2026-08-27"])
    _seed_price_history(repo, "AAA", ["2025-01-02", "2025-01-03", "2026-08-27"])

    class FakeProvider:
        def get_historical_prices(self, **kwargs):
            symbol = str(kwargs["symbol"])
            return [_price_row(symbol, "2024-12-30"), _price_row(symbol, "2025-01-03")]

    monkeypatch.setattr(mph, "YahooHistoricalPriceProvider", lambda: FakeProvider())

    run1 = mph.backfill_research_universe_price_history(
        repo_root=repo,
        symbols=["AAA"],
        start_date="2021-01-01",
        end_date="2026-08-29",
        checkpoint_path=repo / "runtime" / "checkpoint.json",
        include_benchmark=False,
        dry_run=False,
    )
    run2 = mph.backfill_research_universe_price_history(
        repo_root=repo,
        symbols=["AAA"],
        start_date="2021-01-01",
        end_date="2026-08-29",
        checkpoint_path=repo / "runtime" / "checkpoint2.json",
        include_benchmark=False,
        dry_run=False,
    )

    first_result = next(r for r in run1["symbol_results"] if r["symbol"] == "AAA")
    second_result = next(r for r in run2["symbol_results"] if r["symbol"] == "AAA")
    assert first_result["last_date_after"] == "2026-08-27"
    assert first_result["rows_after"] >= first_result["rows_before"]
    assert first_result["rows_added"] > 0
    assert second_result["status"] == "SUCCESS"
    assert second_result["rows_added"] == 0
    assert run2["rows_added_total"] == 0


def test_resume_skips_completed_symbols(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    _seed_benchmark_history(repo, ["2021-01-04", "2026-08-27"])

    calls: list[str] = []

    class FakeProvider:
        def get_historical_prices(self, **kwargs):
            symbol = str(kwargs["symbol"])
            calls.append(symbol)
            return [_price_row(symbol, "2021-01-04"), _price_row(symbol, "2026-08-27")]

    monkeypatch.setattr(mph, "YahooHistoricalPriceProvider", lambda: FakeProvider())

    checkpoint = {
        "run_id": "run-1",
        "mode": "explicit_symbols",
        "requested_start_date": "2021-01-01",
        "requested_end_date": "2026-08-29",
        "batch_size": 1,
        "resolved_symbols": ["AAA", "BBB", "CCC"],
        "resolved_symbol_count": 3,
        "completed_symbols": ["AAA"],
        "failed_symbols": [],
        "current_batch": 1,
        "last_completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    checkpoint_path = repo / "runtime" / "checkpoint.json"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

    mph.backfill_research_universe_price_history(
        repo_root=repo,
        symbols=["AAA", "BBB", "CCC"],
        start_date="2021-01-01",
        end_date="2026-08-29",
        batch_size=1,
        checkpoint_path=checkpoint_path,
        resume=True,
        include_benchmark=False,
        dry_run=False,
    )

    assert "AAA" not in calls
    assert set(calls) == {"BBB", "CCC"}


def test_dry_run_non_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    _seed_benchmark_history(repo, ["2021-01-04", "2026-08-27"])
    _seed_research_universe(
        repo,
        [
            {
                "symbol": "CRM",
                "security_type": "EQUITY",
                "industry": "TECH",
                "sector": "TECHNOLOGY",
                "market_cap_bucket": "LARGE",
            }
        ],
    )

    provider_calls = {"count": 0}
    persist_calls = {"prices": 0, "bench": 0}

    class FakeProvider:
        def __init__(self):
            provider_calls["count"] += 1

        def get_historical_prices(self, **kwargs):
            raise AssertionError("Dry run must not fetch provider data")

    def _prices_stub(**kwargs):
        persist_calls["prices"] += 1
        return {}

    def _bench_stub(**kwargs):
        persist_calls["bench"] += 1
        return {}

    monkeypatch.setattr(mph, "YahooHistoricalPriceProvider", lambda: FakeProvider())
    monkeypatch.setattr(mph, "persist_security_prices", _prices_stub)
    monkeypatch.setattr(mph, "persist_benchmark_returns", _bench_stub)

    result = mph.backfill_research_universe_price_history(
        repo_root=repo,
        research_universe_mode=True,
        start_date="2021-01-01",
        end_date="2026-08-29",
        checkpoint_path=repo / "runtime" / "checkpoint.json",
        include_benchmark=True,
        dry_run=True,
    )

    assert result["provider_calls"] == 0
    assert result["canonical_writes"] == 0
    assert result["data_mutated"] is False
    assert provider_calls["count"] == 0
    assert persist_calls["prices"] == 0
    assert persist_calls["bench"] == 0


def test_benchmark_backfill_routing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    _seed_benchmark_history(repo, ["2025-06-25", "2026-08-27"])

    calls: list[dict[str, str]] = []

    class FakeProvider:
        def get_historical_prices(self, **kwargs):
            calls.append({k: str(v) for k, v in kwargs.items()})
            symbol = str(kwargs["symbol"])
            if symbol == "^GSPC":
                return [_price_row("^GSPC", "2021-01-04"), _price_row("^GSPC", "2026-08-27")]
            return [_price_row(symbol, "2021-01-04"), _price_row(symbol, "2026-08-27")]

    monkeypatch.setattr(mph, "YahooHistoricalPriceProvider", lambda: FakeProvider())

    result = mph.backfill_research_universe_price_history(
        repo_root=repo,
        symbols=["AAA"],
        start_date="2021-01-01",
        end_date="2026-08-29",
        checkpoint_path=repo / "runtime" / "checkpoint.json",
        include_benchmark=True,
        dry_run=False,
    )

    benchmark_call = next(c for c in calls if c["symbol"] == "^GSPC")
    assert benchmark_call["security_id"] == "BENCH:BM_US_LARGE_SP500"
    assert benchmark_call["security_type"] == "BENCHMARK_INDEX"
    assert benchmark_call["start_date"] == "2021-01-01"
    assert benchmark_call["end_date"] == "2026-08-29"
    assert result["benchmark"]["status"] == "SUCCESS"
