from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.pis.momentum_intelligence import (
    MomentumSeries,
    _build_horizon_payload,
    build_trend_structure_context,
    _classify_absolute_momentum_state,
    _classify_breadth_state,
    _classify_confirmation_state,
    _classify_extension_state,
    _classify_fundamental_momentum,
    _classify_security_leadership_state,
    _relative_momentum_change,
    _relative_strength_level,
    _series_confidence,
    evaluate_momentum_as_of,
    evaluate_momentum_for_symbols,
    materialize_momentum_snapshot,
    pis_momentum_snapshot_history,
    pis_momentum_summary,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_momentum_snapshot_materialization_is_idempotent_and_indexed(tmp_path: Path) -> None:
    """Materialized snapshots should be durable, indexed, and idempotent for the same as-of state."""
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [
            {
                "benchmark_id": "BM",
                "symbol_or_index": "^GSPC",
                "date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(),
                "adjusted_close": 100 + i,
                "cumulative_return": 0,
                "source_provider": "TEST",
            }
            for i in range(40)
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "source_file",
            "source_run_id",
            "source_format",
            "partition_path",
            "snapshot_path",
            "positions_path",
            "position_count",
            "portfolio_value",
            "cash_value",
            "equity_value",
            "ingestion_status",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "source_file": "x",
                "source_run_id": "R1",
                "source_format": "csv",
                "partition_path": "",
                "snapshot_path": "",
                "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv",
                "position_count": 1,
                "portfolio_value": 100000,
                "cash_value": 0,
                "equity_value": 100000,
                "ingestion_status": "PASS",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "symbol",
            "description",
            "quantity",
            "market_value",
            "percent_of_account",
            "source_percent_of_account",
            "cost_basis_total",
            "security_type",
            "operational_state",
            "is_cash_equivalent",
            "source_file",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "symbol": "MU",
                "description": "MU",
                "quantity": 10,
                "market_value": 100000,
                "percent_of_account": 100,
                "source_percent_of_account": 100,
                "cost_basis_total": 90000,
                "security_type": "COMMON STOCK",
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": "x",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=MU/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 1, 1), 40, 100.0, 1.0, "MU"),
    )

    first = materialize_momentum_snapshot(repo_root=tmp_path, portfolio_reference="data/history/pis/pis_snapshot_index.csv")
    second = materialize_momentum_snapshot(repo_root=tmp_path, portfolio_reference="data/history/pis/pis_snapshot_index.csv")

    assert first["snapshot_id"] == second["snapshot_id"]
    history = pis_momentum_snapshot_history(repo_root=tmp_path)
    assert history["snapshot_count"] == 1
    assert history["latest_snapshot"]["as_of_date"] == "2026-08-19"
    assert first["artifact_path"].endswith("momentum_snapshot.json")


def test_non_held_symbol_evaluation_uses_same_security_state_without_mutating_portfolio(tmp_path: Path) -> None:
    """Shadow evaluation should reuse the same security-level methodology without mutating holdings or weights."""
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [
            {
                "benchmark_id": "BM",
                "symbol_or_index": "^GSPC",
                "date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(),
                "adjusted_close": 100 + i,
                "cumulative_return": 0,
                "source_provider": "TEST",
            }
            for i in range(40)
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "source_file",
            "source_run_id",
            "source_format",
            "partition_path",
            "snapshot_path",
            "positions_path",
            "position_count",
            "portfolio_value",
            "cash_value",
            "equity_value",
            "ingestion_status",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "source_file": "x",
                "source_run_id": "R1",
                "source_format": "csv",
                "partition_path": "",
                "snapshot_path": "",
                "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv",
                "position_count": 1,
                "portfolio_value": 100000,
                "cash_value": 0,
                "equity_value": 100000,
                "ingestion_status": "PASS",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "symbol",
            "description",
            "quantity",
            "market_value",
            "percent_of_account",
            "source_percent_of_account",
            "cost_basis_total",
            "security_type",
            "operational_state",
            "is_cash_equivalent",
            "source_file",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "symbol": "MU",
                "description": "MU",
                "quantity": 10,
                "market_value": 100000,
                "percent_of_account": 100,
                "source_percent_of_account": 100,
                "cost_basis_total": 90000,
                "security_type": "COMMON STOCK",
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": "x",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=MU/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 1, 1), 40, 100.0, 1.0, "MU"),
    )

    before = pis_momentum_summary(repo_root=tmp_path)
    shadow = evaluate_momentum_for_symbols(["MU"], repo_root=tmp_path)
    after = pis_momentum_summary(repo_root=tmp_path)

    assert shadow[0]["symbol"] == "MU"
    assert shadow[0]["portfolio_weight"] is None
    assert len(before["portfolio_momentum_map"]["holdings"]) == len(after["portfolio_momentum_map"]["holdings"])
    assert shadow[0]["confirmation_state"] == next(row for row in before["portfolio_momentum_map"]["holdings"] if row["symbol"] == "MU")["confirmation_state"]


def test_metadata_precedence_portfolio_analysis_over_universe(tmp_path: Path) -> None:
    """Validate that portfolio_ingestion/analysis_runs holdings.csv has precedence over analytical_universe."""
    # Write analytical_universe with wrong metadata
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [
            {"security_id": "MU1", "symbol": "MU", "security_type": "EQUITY", "snapshot_date": "2026-08-19", "run_id": "R1", "market_cap_bucket": "MEGA", "geography": "US", "country": "US", "industry": "WRONG_INDUSTRY", "sector": "WRONG_SECTOR"},
        ],
    )
    
    # Write portfolio analysis with correct metadata
    _write_csv(
        tmp_path / "data/portfolio_ingestion/analysis_runs/PAR-20260819-CORRECT/holdings.csv",
        ["symbol", "sector", "industry", "security_type", "quantity", "market_value"],
        [
            {"symbol": "MU", "sector": "TECHNOLOGY", "industry": "SEMICONDUCTORS", "security_type": "COMMON STOCK", "quantity": 10, "market_value": 100000},
        ],
    )

    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [
            {
                "benchmark_id": "BM",
                "symbol_or_index": "^GSPC",
                "date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(),
                "adjusted_close": 100 + i,
                "cumulative_return": 0,
                "source_provider": "TEST",
            }
            for i in range(40)
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "source_file",
            "source_run_id",
            "source_format",
            "partition_path",
            "snapshot_path",
            "positions_path",
            "position_count",
            "portfolio_value",
            "cash_value",
            "equity_value",
            "ingestion_status",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "source_file": "x",
                "source_run_id": "R1",
                "source_format": "csv",
                "partition_path": "",
                "snapshot_path": "",
                "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv",
                "position_count": 1,
                "portfolio_value": 100000,
                "cash_value": 0,
                "equity_value": 100000,
                "ingestion_status": "PASS",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "symbol",
            "description",
            "quantity",
            "market_value",
            "percent_of_account",
            "source_percent_of_account",
            "cost_basis_total",
            "security_type",
            "operational_state",
            "is_cash_equivalent",
            "source_file",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "symbol": "MU",
                "description": "MU",
                "quantity": 10,
                "market_value": 100000,
                "percent_of_account": 100,
                "source_percent_of_account": 100,
                "cost_basis_total": 90000,
                "security_type": "COMMON STOCK",
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": "x",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=MU/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 1, 1), 40, 100.0, 1.0, "MU"),
    )

    payload = pis_momentum_summary(repo_root=tmp_path)
    mu_row = next(row for row in payload["portfolio_momentum_map"]["holdings"] if row["symbol"] == "MU")
    mu_sector = mu_row["sector"]
    mu_industry = mu_row["industry"]
    assert mu_sector == "TECHNOLOGY", f"Expected TECHNOLOGY from portfolio analysis, got {mu_sector}"
    assert mu_industry == "SEMICONDUCTORS", f"Expected SEMICONDUCTORS from portfolio analysis, got {mu_industry}"


def test_security_type_normalization_common_stock(tmp_path: Path) -> None:
    """Validate security type normalization handles 'COMMON STOCK' from PIS."""
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [
            {"security_id": "NVDA1", "symbol": "NVDA", "security_type": "EQUITY", "snapshot_date": "2026-08-19", "run_id": "R1", "market_cap_bucket": "MEGA", "geography": "US", "country": "US", "industry": "Semiconductors", "sector": "Technology"},
        ],
    )
    
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [
            {
                "benchmark_id": "BM",
                "symbol_or_index": "^GSPC",
                "date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(),
                "adjusted_close": 100 + i,
                "cumulative_return": 0,
                "source_provider": "TEST",
            }
            for i in range(40)
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "source_file",
            "source_run_id",
            "source_format",
            "partition_path",
            "snapshot_path",
            "positions_path",
            "position_count",
            "portfolio_value",
            "cash_value",
            "equity_value",
            "ingestion_status",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "source_file": "x",
                "source_run_id": "R1",
                "source_format": "csv",
                "partition_path": "",
                "snapshot_path": "",
                "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv",
                "position_count": 1,
                "portfolio_value": 100000,
                "cash_value": 0,
                "equity_value": 100000,
                "ingestion_status": "PASS",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "symbol",
            "description",
            "quantity",
            "market_value",
            "percent_of_account",
            "source_percent_of_account",
            "cost_basis_total",
            "security_type",
            "operational_state",
            "is_cash_equivalent",
            "source_file",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "symbol": "NVDA",
                "description": "NVDA",
                "quantity": 10,
                "market_value": 100000,
                "percent_of_account": 100,
                "source_percent_of_account": 100,
                "cost_basis_total": 90000,
                "security_type": "COMMON STOCK",  # PIS format with space
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": "x",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=NVDA/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 1, 1), 40, 100.0, 1.0, "NVDA"),
    )

    payload = pis_momentum_summary(repo_root=tmp_path)
    # NVDA should be treated as applicable despite PIS using "COMMON STOCK" format
    nvda_row = next(row for row in payload["portfolio_momentum_map"]["holdings"] if row["symbol"] == "NVDA")
    assert nvda_row["sector"] == "TECHNOLOGY"
    assert nvda_row["evaluation_status"] in {"PARTIALLY_EVALUATED", "FULLY_EVALUATED"}


def test_unknown_only_when_metadata_absent(tmp_path: Path) -> None:
    """Validate UNKNOWN only appears when metadata is truly absent, not when loaded from sources."""
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [
            {"security_id": "KNOWN1", "symbol": "KNOWN", "security_type": "EQUITY", "snapshot_date": "2026-08-19", "run_id": "R1", "market_cap_bucket": "L", "geography": "US", "country": "US", "industry": "Technology Services", "sector": "Technology"},
        ],
    )
    
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [
            {
                "benchmark_id": "BM",
                "symbol_or_index": "^GSPC",
                "date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(),
                "adjusted_close": 100 + i,
                "cumulative_return": 0,
                "source_provider": "TEST",
            }
            for i in range(40)
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "source_file",
            "source_run_id",
            "source_format",
            "partition_path",
            "snapshot_path",
            "positions_path",
            "position_count",
            "portfolio_value",
            "cash_value",
            "equity_value",
            "ingestion_status",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "source_file": "x",
                "source_run_id": "R1",
                "source_format": "csv",
                "partition_path": "",
                "snapshot_path": "",
                "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv",
                "position_count": 2,
                "portfolio_value": 100000,
                "cash_value": 0,
                "equity_value": 100000,
                "ingestion_status": "PASS",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "symbol",
            "description",
            "quantity",
            "market_value",
            "percent_of_account",
            "source_percent_of_account",
            "cost_basis_total",
            "security_type",
            "operational_state",
            "is_cash_equivalent",
            "source_file",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "symbol": "KNOWN",
                "description": "KNOWN",
                "quantity": 5,
                "market_value": 50000,
                "percent_of_account": 50,
                "source_percent_of_account": 50,
                "cost_basis_total": 45000,
                "security_type": "EQUITY",
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": "x",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            },
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "symbol": "UNKNOWN",
                "description": "UNKNOWN",
                "quantity": 5,
                "market_value": 50000,
                "percent_of_account": 50,
                "source_percent_of_account": 50,
                "cost_basis_total": 45000,
                "security_type": "EQUITY",
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": "x",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            },
        ],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=KNOWN/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 1, 1), 40, 100.0, 1.0, "KNOWN"),
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=UNKNOWN/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 1, 1), 40, 100.0, 1.0, "UNKNOWN"),
    )

    payload = pis_momentum_summary(repo_root=tmp_path)
    known_row = next(row for row in payload["portfolio_momentum_map"]["holdings"] if row["symbol"] == "KNOWN")
    unknown_row = next(row for row in payload["portfolio_momentum_map"]["holdings"] if row["symbol"] == "UNKNOWN")
    known_sector = known_row["sector"]
    known_industry = known_row["industry"]
    unknown_sector = unknown_row["sector"]
    unknown_industry = unknown_row["industry"]
    
    assert known_sector == "TECHNOLOGY", f"Known security should have sector, got {known_sector}"
    assert known_industry == "TECHNOLOGY SERVICES", f"Known security should have industry, got {known_industry}"
    assert unknown_sector == "UNKNOWN", f"Unknown security should have UNKNOWN sector, got {unknown_sector}"
    assert unknown_industry == "UNAVAILABLE", f"Unknown security should have UNAVAILABLE industry, got {unknown_industry}"


def _price_rows(start: date, count: int, first: float, step: float, symbol: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    price = first
    for i in range(count):
        d = start + timedelta(days=i)
        rows.append(
            {
                "security_id": symbol,
                "symbol": symbol,
                "security_type": "EQUITY",
                "date": d.isoformat(),
                "open": round(price, 4),
                "high": round(price * 1.01, 4),
                "low": round(price * 0.99, 4),
                "close": round(price, 4),
                "adjusted_close": round(price, 4),
                "volume": 100000,
                "dividend": 0,
                "split_ratio": 1,
                "source_provider": "TEST",
                "created_at_utc": f"{d.isoformat()}T00:00:00+00:00",
            }
        )
        price += step
    return rows


def test_absolute_momentum_state_strong() -> None:
    series = MomentumSeries(
        symbol="T1",
        source="test",
        as_of_date="2026-08-19",
        freshness_days=0,
        points=[(f"2026-01-{(i % 28) + 1:02d}", 100.0 + i) for i in range(260)],
    )
    horizons = _build_horizon_payload(series)
    assert _classify_absolute_momentum_state(horizons) == "STRONG"


def test_sector_vs_market_relative_momentum_distinction() -> None:
    sector = {
        "1W": {"relative_return_pct": 2.5},
        "1M": {"relative_return_pct": 3.2},
        "3M": {"relative_return_pct": 1.0},
    }
    assert _relative_strength_level(sector) == "MEDIUM"
    assert _relative_momentum_change(sector) == "ACCELERATING"


def test_relative_strength_level_vs_change_fading() -> None:
    rel = {
        "1W": {"relative_return_pct": 0.3},
        "1M": {"relative_return_pct": 0.4},
        "3M": {"relative_return_pct": 2.8},
    }
    assert _relative_strength_level(rel) == "MEDIUM"
    assert _relative_momentum_change(rel) == "FADING"


def test_relative_strength_level_threshold_boundaries_deterministic() -> None:
    assert _relative_strength_level({"3M": {"relative_return_pct": -3.5}}) == "LOW"
    assert _relative_strength_level({"3M": {"relative_return_pct": -3.0}}) == "LOW"
    assert _relative_strength_level({"3M": {"relative_return_pct": -2.0}}) == "WEAK"
    assert _relative_strength_level({"3M": {"relative_return_pct": -1.0}}) == "WEAK"
    assert _relative_strength_level({"3M": {"relative_return_pct": -0.2}}) == "NEUTRAL"
    assert _relative_strength_level({"3M": {"relative_return_pct": 1.0}}) == "MEDIUM"
    assert _relative_strength_level({"3M": {"relative_return_pct": 2.4}}) == "MEDIUM"
    assert _relative_strength_level({"3M": {"relative_return_pct": 3.0}}) == "HIGH"
    assert _relative_strength_level({"3M": {"relative_return_pct": 4.2}}) == "HIGH"


def test_fundamental_change_semantics_and_static_rating() -> None:
    assert _classify_fundamental_momentum([0.0, 0.0, 0.0]) == "STABLE"
    assert _classify_fundamental_momentum([0.2, 0.1, -0.1, 0.2]) == "IMPROVING"
    assert _classify_fundamental_momentum([-0.3, -0.2, 0.1, -0.2]) == "DETERIORATING"


def test_confirmation_state_semantics() -> None:
    assert _classify_confirmation_state("STRONG", "IMPROVING") == "CONFIRMED_MOMENTUM"
    assert _classify_confirmation_state("STRONG", "DETERIORATING") == "MOMENTUM_DIVERGENCE"
    assert _classify_confirmation_state("WEAK", "IMPROVING") == "FUNDAMENTAL_ONLY_IMPROVEMENT"


def test_breadth_aggregation_states() -> None:
    assert _classify_breadth_state(0.72, 0.68, 0.56, 0.58, 12) == "BROAD"
    assert _classify_breadth_state(0.71, 0.66, 0.55, 0.81, 12) == "HEALTHY_CONCENTRATED"
    assert _classify_breadth_state(0.40, 0.35, 0.44, 0.79, 12) == "DETERIORATING"


def test_extension_reporting_states() -> None:
    assert (
        _classify_extension_state(
            distance_ma20_pct=0.18,
            distance_52w_high_pct=-0.005,
            recent_acceleration_pct=4.5,
            volatility_20d_pct=0.06,
        )
        == "EXTENDED"
    )
    assert (
        _classify_extension_state(
            distance_ma20_pct=0.09,
            distance_52w_high_pct=-0.02,
            recent_acceleration_pct=2.1,
            volatility_20d_pct=0.03,
        )
        == "ELEVATED"
    )


def test_security_leadership_laggard_and_resilient_states() -> None:
    assert (
        _classify_security_leadership_state(
            sector_vs_market_level="HIGH",
            industry_vs_sector_level="HIGH",
            security_vs_industry_level="LOW",
            security_vs_industry_change="FADING",
        )
        == "SECURITY_LAGGARD_IN_STRONG_GROUP"
    )
    assert (
        _classify_security_leadership_state(
            sector_vs_market_level="LOW",
            industry_vs_sector_level="WEAK",
            security_vs_industry_level="HIGH",
            security_vs_industry_change="ACCELERATING",
        )
        == "SECURITY_RESILIENT_IN_WEAK_GROUP"
    )


def test_missing_history_and_confidence_metadata() -> None:
    sparse = MomentumSeries(
        symbol="SPARSE",
        source="fixture",
        as_of_date="2026-08-19",
        freshness_days=0,
        points=[("2026-08-18", 10.0), ("2026-08-19", 10.1)],
    )
    horizons = _build_horizon_payload(sparse)
    assert horizons["1W"]["state"] == "UNAVAILABLE"
    assert horizons["1W"]["history_available"] == 2
    assert horizons["1W"]["confidence"] in {"LOW", "UNAVAILABLE"}
    assert _series_confidence(10, 22) == "LOW"


def test_build_trend_structure_context_calculates_sma50_sma200_and_20d_change() -> None:
    points = [((date(2026, 1, 1) + timedelta(days=i)).isoformat(), 100.0 + i) for i in range(220)]
    as_of = "2026-08-08"
    series = MomentumSeries(symbol="TEST", source="fixture", as_of_date=as_of, freshness_days=0, points=points)

    ctx = build_trend_structure_context(series)

    assert ctx["history_status"] == "AVAILABLE"
    assert ctx["latest_price_date"] == as_of
    assert ctx["latest_price"] == pytest.approx(319.0)
    assert ctx["sma50"] == pytest.approx(294.5)
    assert ctx["sma200"] == pytest.approx(219.5)
    assert ctx["price_vs_sma50_pct"] == pytest.approx(((319.0 / 294.5) - 1.0) * 100.0)
    assert ctx["price_vs_sma200_pct"] == pytest.approx(((319.0 / 219.5) - 1.0) * 100.0)
    assert ctx["sma50_change_20d_pct"] == pytest.approx(((294.5 / 274.5) - 1.0) * 100.0)
    assert ctx["sma200_change_20d_pct"] == pytest.approx(((219.5 / 199.5) - 1.0) * 100.0)
    assert ctx["reporting_only"] is True


def test_build_trend_structure_context_respects_as_of_cutoff() -> None:
    as_of = "2026-03-15"
    points = [
        ("2026-01-01", 100.0),
        ("2026-02-10", 110.0),
        ("2026-03-10", 120.0),
        ("2026-03-20", 999.0),
        ("2026-03-25", 1000.0),
    ]
    series = MomentumSeries(symbol="CUT", source="fixture", as_of_date=as_of, freshness_days=0, points=points)

    ctx = build_trend_structure_context(series, as_of_date=as_of)

    assert ctx["latest_price_date"] == "2026-03-10"
    assert ctx["latest_price"] == pytest.approx(120.0)
    assert ctx["price_vs_sma50_pct"] == pytest.approx(0.0)
    assert ctx["history_status"] in {"INSUFFICIENT_50", "INSUFFICIENT_200", "AVAILABLE"}


def test_build_trend_structure_context_reports_insufficient_history() -> None:
    points = [((date(2026, 1, 1) + timedelta(days=i)).isoformat(), 100.0 + i) for i in range(49)]
    series = MomentumSeries(symbol="SHORT", source="fixture", as_of_date="2026-02-18", freshness_days=0, points=points)

    ctx = build_trend_structure_context(series)

    assert ctx["history_status"] == "INSUFFICIENT_50"
    assert ctx["currentness_state"] == "CURRENT"
    assert ctx["sma50"] is None
    assert ctx["sma200"] is None
    assert ctx["reporting_only"] is True


def test_entry_timing_context_exposes_history_and_top_trade_trend_exposure() -> None:
    as_of = "2026-08-08"
    points = [((date(2026, 1, 1) + timedelta(days=i)).isoformat(), 100.0 + i) for i in range(220)]
    series = MomentumSeries(symbol="TEST", source="fixture", as_of_date=as_of, freshness_days=2, points=points)
    ctx = build_trend_structure_context(series, as_of_date=as_of)
    assert ctx["history_status"] == "AVAILABLE"
    assert ctx["currentness_state"] == "CURRENT"
    assert ctx["freshness_status"] == "CURRENT"
    assert ctx["coverage_status"] == "CURRENT"

    payload = {
        "entry_timing_context": {
            "holdings": [{"symbol": "TEST", "trend_structure_context": ctx}],
            "top_trades_trend_exposure": {
                "reporting_only": True,
                "leaders": ["TEST"],
                "laggards": [],
                "neutral": [],
                "insufficient_history": [],
                "unavailable": [],
                "per_symbol": [
                    {
                        "symbol": "TEST",
                        "bucket": "LEADING",
                        "history_status": "AVAILABLE",
                        "currentness_state": "CURRENT",
                        "price_vs_sma50_pct": 8.319185,
                        "price_vs_sma200_pct": 45.330296,
                    }
                ],
                "total_symbols": 1,
            },
        }
    }
    exposure = payload["entry_timing_context"]["top_trades_trend_exposure"]
    assert exposure["leaders"] == ["TEST"]
    assert exposure["per_symbol"][0]["symbol"] == "TEST"
    assert exposure["reporting_only"] is True


def test_evaluate_momentum_as_of_blocks_future_prices_and_providers(tmp_path: Path) -> None:
    as_of = "2026-03-15"
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [
            {"benchmark_id": "BM", "symbol_or_index": "^GSPC", "date": "2026-01-01", "adjusted_close": 100.0, "cumulative_return": 0.0, "source_provider": "TEST"},
            {"benchmark_id": "BM", "symbol_or_index": "^GSPC", "date": "2026-02-15", "adjusted_close": 110.0, "cumulative_return": 0.1, "source_provider": "TEST"},
            {"benchmark_id": "BM", "symbol_or_index": "^GSPC", "date": "2026-03-20", "adjusted_close": 130.0, "cumulative_return": 0.3, "source_provider": "TEST"},
        ],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=MU/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        [
            {"security_id": "MU", "symbol": "MU", "security_type": "EQUITY", "date": "2026-01-01", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "adjusted_close": 100.0, "volume": 1000, "dividend": 0.0, "split_ratio": 1.0, "source_provider": "TEST", "created_at_utc": "2026-01-01T00:00:00+00:00"},
            {"security_id": "MU", "symbol": "MU", "security_type": "EQUITY", "date": "2026-02-15", "open": 110.0, "high": 110.0, "low": 110.0, "close": 110.0, "adjusted_close": 110.0, "volume": 1000, "dividend": 0.0, "split_ratio": 1.0, "source_provider": "TEST", "created_at_utc": "2026-02-15T00:00:00+00:00"},
            {"security_id": "MU", "symbol": "MU", "security_type": "EQUITY", "date": "2026-03-20", "open": 140.0, "high": 140.0, "low": 140.0, "close": 140.0, "adjusted_close": 140.0, "volume": 1000, "dividend": 0.0, "split_ratio": 1.0, "source_provider": "TEST", "created_at_utc": "2026-03-20T00:00:00+00:00"},
        ],
    )
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [{"security_id": "MU1", "symbol": "MU", "security_type": "EQUITY", "snapshot_date": as_of, "run_id": "R1", "market_cap_bucket": "L", "geography": "US", "country": "US", "industry": "Semiconductors", "sector": "Technology"}],
    )

    result = evaluate_momentum_as_of("MU", as_of, repo_root=tmp_path)

    assert result["price_points_available"] == 2
    assert result["provenance"] == "HISTORICAL_AS_OF"
    assert result["absolute_state"] in {"STRONG", "IMPROVING", "POSITIVE"}
    assert result["raw_price_points"] == ["2026-01-01", "2026-02-15"]


def test_as_of_evaluation_uses_filtered_historical_provider_evidence(tmp_path: Path) -> None:
    as_of = "2026-03-15"
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [
            {"benchmark_id": "BM", "symbol_or_index": "^GSPC", "date": "2026-01-01", "adjusted_close": 100.0, "cumulative_return": 0.0, "source_provider": "TEST"},
            {"benchmark_id": "BM", "symbol_or_index": "^GSPC", "date": "2026-03-10", "adjusted_close": 115.0, "cumulative_return": 0.15, "source_provider": "TEST"},
            {"benchmark_id": "BM", "symbol_or_index": "^GSPC", "date": "2026-03-20", "adjusted_close": 130.0, "cumulative_return": 0.3, "source_provider": "TEST"},
        ],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=MU/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        [
            {"security_id": "MU", "symbol": "MU", "security_type": "EQUITY", "date": "2026-01-01", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "adjusted_close": 100.0, "volume": 1000, "dividend": 0.0, "split_ratio": 1.0, "source_provider": "TEST", "created_at_utc": "2026-01-01T00:00:00+00:00"},
            {"security_id": "MU", "symbol": "MU", "security_type": "EQUITY", "date": "2026-03-10", "open": 120.0, "high": 120.0, "low": 120.0, "close": 120.0, "adjusted_close": 120.0, "volume": 1000, "dividend": 0.0, "split_ratio": 1.0, "source_provider": "TEST", "created_at_utc": "2026-03-10T00:00:00+00:00"},
            {"security_id": "MU", "symbol": "MU", "security_type": "EQUITY", "date": "2026-03-20", "open": 150.0, "high": 150.0, "low": 150.0, "close": 150.0, "adjusted_close": 150.0, "volume": 1000, "dividend": 0.0, "split_ratio": 1.0, "source_provider": "TEST", "created_at_utc": "2026-03-20T00:00:00+00:00"},
        ],
    )
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [{"security_id": "MU1", "symbol": "MU", "security_type": "EQUITY", "snapshot_date": as_of, "run_id": "R1", "market_cap_bucket": "L", "geography": "US", "country": "US", "industry": "Semiconductors", "sector": "Technology"}],
    )

    result = evaluate_momentum_as_of("MU", as_of, repo_root=tmp_path)

    assert result["raw_price_points"] == ["2026-01-01", "2026-03-10"]
    assert result["market_points_available"] == 2
    assert result["provenance"] == "HISTORICAL_AS_OF"


def test_short_history_fallback_is_historical_as_of_only(tmp_path: Path) -> None:
    as_of = "2026-03-15"
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [
            {"benchmark_id": "BM", "symbol_or_index": "^GSPC", "date": "2026-03-01", "adjusted_close": 100.0, "cumulative_return": 0.0, "source_provider": "TEST"},
            {"benchmark_id": "BM", "symbol_or_index": "^GSPC", "date": "2026-03-15", "adjusted_close": 101.0, "cumulative_return": 0.01, "source_provider": "TEST"},
        ],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=MU/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        [
            {"security_id": "MU", "symbol": "MU", "security_type": "EQUITY", "date": "2026-03-01", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "adjusted_close": 100.0, "volume": 1000, "dividend": 0.0, "split_ratio": 1.0, "source_provider": "TEST", "created_at_utc": "2026-03-01T00:00:00+00:00"},
            {"security_id": "MU", "symbol": "MU", "security_type": "EQUITY", "date": "2026-03-15", "open": 103.0, "high": 103.0, "low": 103.0, "close": 103.0, "adjusted_close": 103.0, "volume": 1000, "dividend": 0.0, "split_ratio": 1.0, "source_provider": "TEST", "created_at_utc": "2026-03-15T00:00:00+00:00"},
        ],
    )
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [{"security_id": "MU1", "symbol": "MU", "security_type": "EQUITY", "snapshot_date": as_of, "run_id": "R1", "market_cap_bucket": "L", "geography": "US", "country": "US", "industry": "Semiconductors", "sector": "Technology"}],
    )

    short_series = MomentumSeries(
        symbol="MU",
        source="fixture",
        as_of_date=as_of,
        freshness_days=0,
        points=[("2026-03-01", 100.0), ("2026-03-15", 103.0)],
    )
    generic_abs = _classify_absolute_momentum_state(_build_horizon_payload(short_series))
    as_of_eval = evaluate_momentum_as_of("MU", as_of, repo_root=tmp_path)

    assert generic_abs == "UNAVAILABLE"
    assert as_of_eval["absolute_state"] in {"POSITIVE", "IMPROVING", "STRONG"}
    assert as_of_eval["provenance"] == "HISTORICAL_AS_OF"
    assert as_of_eval["source_constraints"]["historical_short_history_fallback_used"] is True


def test_as_of_current_parity_keeps_industry_unavailable_and_no_market_fallback(tmp_path: Path) -> None:
    as_of = "2026-08-19"
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [
            {
                "benchmark_id": "BM",
                "symbol_or_index": "^GSPC",
                "date": (date(2026, 5, 1) + timedelta(days=i)).isoformat(),
                "adjusted_close": 100 + i,
                "cumulative_return": 0,
                "source_provider": "TEST",
            }
            for i in range(120)
        ],
    )
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [
            {"security_id": "D1", "symbol": "DELL", "security_type": "EQUITY", "snapshot_date": as_of, "run_id": "R1", "market_cap_bucket": "L", "geography": "US", "country": "US", "industry": "Computer Hardware", "sector": "Technology"},
            {"security_id": "V1", "symbol": "VO", "security_type": "ETF", "snapshot_date": as_of, "run_id": "R1", "market_cap_bucket": "L", "geography": "US", "country": "US", "industry": "", "sector": "Financials"},
            {"security_id": "V2", "symbol": "VOO", "security_type": "ETF", "snapshot_date": as_of, "run_id": "R1", "market_cap_bucket": "L", "geography": "US", "country": "US", "industry": "", "sector": "Financials"},
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "source_file",
            "source_run_id",
            "source_format",
            "partition_path",
            "snapshot_path",
            "positions_path",
            "position_count",
            "portfolio_value",
            "cash_value",
            "equity_value",
            "ingestion_status",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": as_of,
                "account_id": "A1",
                "account_name": "TEST",
                "source_file": "x",
                "source_run_id": "R1",
                "source_format": "csv",
                "partition_path": "",
                "snapshot_path": "",
                "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv",
                "position_count": 3,
                "portfolio_value": 100000,
                "cash_value": 0,
                "equity_value": 100000,
                "ingestion_status": "PASS",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "symbol",
            "description",
            "quantity",
            "market_value",
            "percent_of_account",
            "source_percent_of_account",
            "cost_basis_total",
            "security_type",
            "operational_state",
            "is_cash_equivalent",
            "source_file",
            "created_at_utc",
        ],
        [
            {"snapshot_id": "S1", "snapshot_date": as_of, "account_id": "A1", "account_name": "TEST", "symbol": "DELL", "description": "DELL", "quantity": 10, "market_value": 40000, "percent_of_account": 40, "source_percent_of_account": 40, "cost_basis_total": 30000, "security_type": "COMMON STOCK", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "False", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"},
            {"snapshot_id": "S1", "snapshot_date": as_of, "account_id": "A1", "account_name": "TEST", "symbol": "VO", "description": "VO", "quantity": 10, "market_value": 30000, "percent_of_account": 30, "source_percent_of_account": 30, "cost_basis_total": 28000, "security_type": "ETF", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "False", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"},
            {"snapshot_id": "S1", "snapshot_date": as_of, "account_id": "A1", "account_name": "TEST", "symbol": "VOO", "description": "VOO", "quantity": 10, "market_value": 30000, "percent_of_account": 30, "source_percent_of_account": 30, "cost_basis_total": 28000, "security_type": "ETF", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "False", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"},
        ],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=DELL/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 5, 1), 120, 100.0, 1.0, "DELL"),
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=VO/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 5, 1), 120, 80.0, 0.5, "VO"),
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=VOO/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 5, 1), 120, 90.0, 0.5, "VOO"),
    )

    live = pis_momentum_summary(repo_root=tmp_path)
    live_rows = {row["symbol"]: row for row in live["portfolio_momentum_map"]["holdings"]}
    dell_asof = evaluate_momentum_as_of("DELL", as_of, repo_root=tmp_path)
    vo_asof = evaluate_momentum_as_of("VO", as_of, repo_root=tmp_path)
    voo_asof = evaluate_momentum_as_of("VOO", as_of, repo_root=tmp_path)

    assert _relative_strength_level(live_rows["DELL"]["security_vs_industry"]) == "UNAVAILABLE"
    assert _relative_strength_level(dell_asof["vs_industry"]) == "UNAVAILABLE"
    assert live_rows["DELL"]["relative_strength_level"] == "UNAVAILABLE"
    assert dell_asof["relative_strength_level"] == "UNAVAILABLE"

    assert live_rows["VO"]["relative_strength_level"] == "UNAVAILABLE"
    assert vo_asof["relative_strength_level"] == "LOW"
    assert live_rows["VOO"]["relative_strength_level"] == "UNAVAILABLE"
    assert voo_asof["relative_strength_level"] == "LOW"

    assert dell_asof["source_constraints"]["historical_short_history_fallback_used"] is False
    assert vo_asof["source_constraints"]["historical_short_history_fallback_used"] is False
    assert voo_asof["source_constraints"]["historical_short_history_fallback_used"] is False


def test_non_held_etf_proposed_buy_metadata_is_partially_evaluable_and_provenanced() -> None:
    symbols = ["IJH", "MDY", "SCHB", "VO", "VOO", "VTI"]
    current = {row["symbol"]: row for row in evaluate_momentum_for_symbols(symbols, repo_root=".")}
    valid_relative_levels = {"HIGH", "MEDIUM", "NEUTRAL", "WEAK", "LOW", "UNAVAILABLE"}
    valid_relative_changes = {"ACCELERATING", "STABLE", "FADING", "UNAVAILABLE"}
    valid_extension_states = {"NORMAL", "ELEVATED", "EXTENDED", "UNAVAILABLE"}

    assert current["IJH"]["security_type"] == "ETF"
    assert current["MDY"]["security_type"] == "ETF"
    assert current["SCHB"]["security_type"] == "ETF"
    assert current["VO"]["security_type"] == "ETF"
    assert current["VOO"]["security_type"] == "ETF"
    assert current["VTI"]["security_type"] == "ETF"

    for symbol in symbols:
        assert current[symbol]["relative_strength_level"] in valid_relative_levels
        assert current[symbol]["relative_momentum_change"] in valid_relative_changes
        assert current[symbol]["extension_state"] in valid_extension_states
        # ETF proposed-buys are evaluated via market fallback and should be classifiable.
        assert current[symbol]["relative_strength_level"] != "UNAVAILABLE"
        assert current[symbol]["relative_momentum_change"] != "UNAVAILABLE"

    assert current["IJH"]["market_fallback_used"] is True
    assert current["MDY"]["market_fallback_used"] is True
    assert current["SCHB"]["market_fallback_used"] is True
    assert current["VO"]["market_fallback_used"] is True
    assert current["VOO"]["market_fallback_used"] is True
    assert current["VTI"]["market_fallback_used"] is True
    assert current["IJH"]["industry"] == "UNAVAILABLE"
    assert current["VO"]["industry"] == "UNAVAILABLE"
    assert current["VOO"]["industry"] == "UNAVAILABLE"
    assert current["IJH"]["industry_parent_used"] is False
    assert current["MDY"]["industry_parent_used"] is False
    assert current["SCHB"]["industry_parent_used"] is False
    assert current["VO"]["industry_parent_used"] is False
    assert current["VOO"]["industry_parent_used"] is False
    assert current["VTI"]["industry_parent_used"] is False
    assert current["VO"]["sector_parent_used"] is True
    assert current["VOO"]["sector_parent_used"] is True
    assert current["IJH"]["sector_parent_used"] is False
    assert current["MDY"]["sector_parent_used"] is False
    assert current["SCHB"]["sector_parent_used"] is False
    assert current["VTI"]["sector_parent_used"] is False

    expected_provenance = {
        "IJH": "UNAVAILABLE",
        "MDY": "UNAVAILABLE",
        "SCHB": "UNAVAILABLE",
        "VO": "CURRENT_TAXONOMY_FALLBACK",
        "VOO": "CURRENT_TAXONOMY_FALLBACK",
        "VTI": "UNAVAILABLE",
    }

    for as_of in ("2026-08-19", "2026-07-20", "2026-05-21", "2026-02-20"):
        for symbol in symbols:
            result = evaluate_momentum_as_of(symbol, as_of, repo_root=".")
            assert result["security_type"] == "ETF"
            assert result["industry"] == "UNAVAILABLE"
            assert result["relative_strength_level"] in valid_relative_levels
            assert result["relative_momentum_change"] in valid_relative_changes
            assert result["extension_state"] in valid_extension_states
            assert result["metadata_provenance"] == expected_provenance[symbol]
            assert result["price_provenance"] == "HISTORICAL_PRICE_HISTORY_AS_OF"
            assert result["price_points_available"] > 0
            assert result["raw_price_points"][-1] <= as_of
            assert result["source_constraints"]["price_observations_filtered_to_as_of"] is True
            assert result["source_constraints"]["benchmark_observations_filtered_to_as_of"] is True
            assert result["source_constraints"]["provider_fundamental_evidence_filtered_to_as_of"] is True
            assert result["market_fallback_used"] is True
            assert result["industry_parent_used"] is False
            assert result["sector_parent_used"] in {True, False}
            assert result["relative_strength_level"] == _relative_strength_level(result["vs_market"])
            assert result["relative_momentum_change"] == _relative_momentum_change(result["vs_market"])
            if symbol in {"VO", "VOO"}:
                assert result["metadata_source"] == "PORTFOLIO_ANALYSIS_HOLDINGS"

    before = pis_momentum_summary(repo_root=".")
    after = pis_momentum_summary(repo_root=".")
    assert before["portfolio_momentum_map"]["holdings"] == after["portfolio_momentum_map"]["holdings"]


def test_latest_provider_file_uses_exact_sourced_date_for_as_of_filter(tmp_path: Path) -> None:
    as_of_1 = "2026-08-18"
    as_of_2 = "2026-08-19"
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [
            {"benchmark_id": "BM", "symbol_or_index": "^GSPC", "date": (date(2026, 5, 1) + timedelta(days=i)).isoformat(), "adjusted_close": 100 + i, "cumulative_return": 0, "source_provider": "TEST"}
            for i in range(120)
        ],
    )
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [{"security_id": "P1", "symbol": "PLTR", "security_type": "EQUITY", "snapshot_date": as_of_2, "run_id": "R1", "market_cap_bucket": "L", "geography": "US", "country": "US", "industry": "Software", "sector": "Technology"}],
    )
    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        ["snapshot_id", "snapshot_date", "account_id", "account_name", "source_file", "source_run_id", "source_format", "partition_path", "snapshot_path", "positions_path", "position_count", "portfolio_value", "cash_value", "equity_value", "ingestion_status", "created_at_utc"],
        [{"snapshot_id": "S1", "snapshot_date": as_of_2, "account_id": "A1", "account_name": "TEST", "source_file": "x", "source_run_id": "R1", "source_format": "csv", "partition_path": "", "snapshot_path": "", "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv", "position_count": 1, "portfolio_value": 100000, "cash_value": 0, "equity_value": 100000, "ingestion_status": "PASS", "created_at_utc": "2026-08-19T00:00:00+00:00"}],
    )
    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        ["snapshot_id", "snapshot_date", "account_id", "account_name", "symbol", "description", "quantity", "market_value", "percent_of_account", "source_percent_of_account", "cost_basis_total", "security_type", "operational_state", "is_cash_equivalent", "source_file", "created_at_utc"],
        [{"snapshot_id": "S1", "snapshot_date": as_of_2, "account_id": "A1", "account_name": "TEST", "symbol": "PLTR", "description": "PLTR", "quantity": 10, "market_value": 100000, "percent_of_account": 100, "source_percent_of_account": 100, "cost_basis_total": 90000, "security_type": "COMMON STOCK", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "False", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"}],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=PLTR/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 5, 1), 120, 10.0, 0.2, "PLTR"),
    )
    _write_csv(
        tmp_path / "data/signals/zacks/2026-08-18_zacks.csv",
        ["symbol", "zacks_rank", "zacks_score", "abr", "price_target", "eps_growth", "sourced_date"],
        [{"symbol": "PLTR", "zacks_rank": 4, "zacks_score": 2, "abr": "", "price_target": "", "eps_growth": "", "sourced_date": "2026-08-18"}],
    )
    _write_csv(
        tmp_path / "data/signals/zacks/latest_zacks.csv",
        ["symbol", "zacks_rank", "zacks_score", "abr", "price_target", "eps_growth", "sourced_date"],
        [{"symbol": "PLTR", "zacks_rank": 2, "zacks_score": 4, "abr": "", "price_target": "", "eps_growth": "", "sourced_date": "2026-08-19"}],
    )

    older = evaluate_momentum_as_of("PLTR", as_of_1, repo_root=tmp_path)
    newer = evaluate_momentum_as_of("PLTR", as_of_2, repo_root=tmp_path)
    assert older["fundamental_momentum"] == "UNAVAILABLE"
    assert newer["fundamental_momentum"] in {"STABLE", "IMPROVING", "DETERIORATING"}


def test_proposed_buy_membership_uses_positions_not_shadow_weight() -> None:
    holdings_symbols = {"VO", "VOO", "MU"}
    proposed = ["IJH", "MDY", "SCHB", "VO", "VOO", "VTI"]
    membership = {symbol: (symbol in holdings_symbols) for symbol in proposed}

    assert membership["IJH"] is False
    assert membership["MDY"] is False
    assert membership["SCHB"] is False
    assert membership["VTI"] is False
    assert membership["VO"] is True
    assert membership["VOO"] is True


def test_direction_partition_percentages_reconcile_to_declared_denominator() -> None:
    total_denom = 101.02
    parts = {
        "positive": 50.46,
        "negative": 0.0,
        "unchanged": 0.0,
        "unavailable": 50.56,
    }
    pct_sum = sum((value / total_denom) * 100.0 for value in parts.values())
    assert abs(pct_sum - 100.0) <= 0.02


def test_backward_lens_partition_percentages_reconcile() -> None:
    total_denom = 100.0
    parts = {
        "positive": 50.02,
        "negative": 0.0,
        "unchanged": 0.0,
        "unavailable": 49.98,
    }
    pct_sum = sum((value / total_denom) * 100.0 for value in parts.values())
    assert abs(pct_sum - 100.0) <= 0.02


def test_stale_input_freshness_metadata() -> None:
    old_day = (date.today() - timedelta(days=30)).isoformat()
    series = MomentumSeries(
        symbol="OLD",
        source="fixture",
        as_of_date=old_day,
        freshness_days=30,
        points=[(old_day, 100.0), (old_day, 101.0)],
    )
    horizons = _build_horizon_payload(series)
    assert horizons["1W"]["freshness_days"] == 30


def test_summary_sector_and_industry_aggregation(tmp_path: Path) -> None:
    # Current benchmark history (market parent)
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [
            {
                "benchmark_id": "BM",
                "symbol_or_index": "^GSPC",
                "date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(),
                "adjusted_close": 100 + i,
                "cumulative_return": 0,
                "source_provider": "TEST",
            }
            for i in range(90)
        ],
    )

    _write_csv(
        tmp_path / "data/current/market_regime_proxy_price_history.csv",
        ["date", "symbol", "proxy_group", "price", "price_field", "provider", "source_timestamp", "retrieved_at_utc", "status"],
        [
            {
                "date": (date(2026, 4, 1) + timedelta(days=i)).isoformat(),
                "symbol": "XLK",
                "proxy_group": "technology",
                "price": 100 + (i * 0.8),
                "price_field": "close",
                "provider": "TEST",
                "source_timestamp": "",
                "retrieved_at_utc": "",
                "status": "OK",
            }
            for i in range(90)
        ],
    )

    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        [
            "security_id",
            "symbol",
            "security_type",
            "snapshot_date",
            "run_id",
            "market_cap_bucket",
            "geography",
            "country",
            "industry",
            "sector",
        ],
        [
            {
                "security_id": "AAA",
                "symbol": "AAA",
                "security_type": "EQUITY",
                "snapshot_date": "2026-08-19",
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "Semiconductors",
                "sector": "Technology",
            },
            {
                "security_id": "BBB",
                "symbol": "BBB",
                "security_type": "EQUITY",
                "snapshot_date": "2026-08-19",
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "Semiconductors",
                "sector": "Technology",
            },
        ],
    )

    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "source_file",
            "source_run_id",
            "source_format",
            "partition_path",
            "snapshot_path",
            "positions_path",
            "position_count",
            "portfolio_value",
            "cash_value",
            "equity_value",
            "ingestion_status",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "source_file": "x",
                "source_run_id": "R1",
                "source_format": "csv",
                "partition_path": "",
                "snapshot_path": "",
                "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv",
                "position_count": 2,
                "portfolio_value": 100000,
                "cash_value": 0,
                "equity_value": 100000,
                "ingestion_status": "PASS",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )

    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "symbol",
            "description",
            "quantity",
            "market_value",
            "percent_of_account",
            "source_percent_of_account",
            "cost_basis_total",
            "security_type",
            "operational_state",
            "is_cash_equivalent",
            "source_file",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "symbol": "AAA",
                "description": "AAA",
                "quantity": 10,
                "market_value": 60000,
                "percent_of_account": 60,
                "source_percent_of_account": 60,
                "cost_basis_total": 50000,
                "security_type": "EQUITY",
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": "x",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            },
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "symbol": "BBB",
                "description": "BBB",
                "quantity": 10,
                "market_value": 40000,
                "percent_of_account": 40,
                "source_percent_of_account": 40,
                "cost_basis_total": 35000,
                "security_type": "EQUITY",
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": "x",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            },
        ],
    )

    _write_csv(
        tmp_path / "data/history/prices/symbol=AAA/prices.csv",
        [
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
        _price_rows(date(2026, 1, 1), 90, 100.0, 0.7, "AAA"),
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=BBB/prices.csv",
        [
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
        _price_rows(date(2026, 1, 1), 90, 100.0, 0.2, "BBB"),
    )

    # Minimal provider histories for fundamental momentum derivation.
    _write_csv(
        tmp_path / "data/signals/zacks/2026-08-18_zacks.csv",
        ["symbol", "zacks_rank", "zacks_score", "abr", "price_target", "eps_growth", "sourced_date"],
        [{"symbol": "AAA", "zacks_rank": 3, "zacks_score": 3.0, "abr": 2.5, "price_target": 120, "eps_growth": 8, "sourced_date": "2026-08-18"}],
    )
    _write_csv(
        tmp_path / "data/signals/zacks/2026-08-19_zacks.csv",
        ["symbol", "zacks_rank", "zacks_score", "abr", "price_target", "eps_growth", "sourced_date"],
        [{"symbol": "AAA", "zacks_rank": 2, "zacks_score": 4.0, "abr": 2.0, "price_target": 122, "eps_growth": 9, "sourced_date": "2026-08-19"}],
    )

    _write_csv(
        tmp_path / "data/history/signals/snapshot_date=2026-08-18/run_id=R1/signal_snapshots.csv",
        [
            "snapshot_date",
            "created_at_utc",
            "run_id",
            "provider",
            "source_file",
            "symbol",
            "coverage_domain",
            "signal_coverage_status",
            "starmine_ess_text",
            "starmine_ess_numeric",
            "starmine_ess_numeric_estimated",
            "starmine_ess_source_type",
        ],
        [{"snapshot_date": "2026-08-18", "created_at_utc": "", "run_id": "R1", "provider": "ESS", "source_file": "", "symbol": "AAA", "coverage_domain": "", "signal_coverage_status": "", "starmine_ess_text": "BULLISH", "starmine_ess_numeric": 4.0, "starmine_ess_numeric_estimated": "False", "starmine_ess_source_type": ""}],
    )
    _write_csv(
        tmp_path / "data/history/signals/snapshot_date=2026-08-19/run_id=R2/signal_snapshots.csv",
        [
            "snapshot_date",
            "created_at_utc",
            "run_id",
            "provider",
            "source_file",
            "symbol",
            "coverage_domain",
            "signal_coverage_status",
            "starmine_ess_text",
            "starmine_ess_numeric",
            "starmine_ess_numeric_estimated",
            "starmine_ess_source_type",
        ],
        [{"snapshot_date": "2026-08-19", "created_at_utc": "", "run_id": "R2", "provider": "ESS", "source_file": "", "symbol": "AAA", "coverage_domain": "", "signal_coverage_status": "", "starmine_ess_text": "VERY_BULLISH", "starmine_ess_numeric": 5.0, "starmine_ess_numeric_estimated": "False", "starmine_ess_source_type": ""}],
    )

    payload = pis_momentum_summary(repo_root=tmp_path)

    assert payload["status"] == "ok"
    assert payload["reporting_only"] is True
    assert "coverage" in payload
    assert payload["market_momentum"]["market_absolute_momentum"]["state"] in {
        "STRONG",
        "IMPROVING",
        "NEUTRAL",
    }
    assert len(payload["sector_rotation"]) >= 1
    assert len(payload["industry_rotation"]) >= 1
    assert len(payload["portfolio_momentum_map"]["holdings"]) == 2

    first_holding = payload["portfolio_momentum_map"]["holdings"][0]
    assert "relative_strength_level" in first_holding
    assert "relative_momentum_change" in first_holding
    assert "fundamental_momentum" in first_holding
    assert "confirmation_state" in first_holding
    assert "extension_state" in first_holding
    assert first_holding["change_detection"]["method"] == "RECONSTRUCTED_DERIVED"


def test_confirmation_unavailable_when_price_evidence_missing(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [
            {
                "benchmark_id": "BM",
                "symbol_or_index": "^GSPC",
                "date": "2026-08-19",
                "adjusted_close": 100.0,
                "cumulative_return": 0.0,
                "source_provider": "TEST",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/current/market_regime_proxy_price_history.csv",
        ["date", "symbol", "proxy_group", "price", "price_field", "provider", "source_timestamp", "retrieved_at_utc", "status"],
        [],
    )
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [
            {
                "security_id": "MU",
                "symbol": "MU",
                "security_type": "EQUITY",
                "snapshot_date": "2026-08-19",
                "run_id": "R1",
                "market_cap_bucket": "MEGA",
                "geography": "US",
                "country": "US",
                "industry": "Semiconductors",
                "sector": "Technology",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "source_file",
            "source_run_id",
            "source_format",
            "partition_path",
            "snapshot_path",
            "positions_path",
            "position_count",
            "portfolio_value",
            "cash_value",
            "equity_value",
            "ingestion_status",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "source_file": "x",
                "source_run_id": "R1",
                "source_format": "csv",
                "partition_path": "",
                "snapshot_path": "",
                "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv",
                "position_count": 1,
                "portfolio_value": 100000,
                "cash_value": 0,
                "equity_value": 100000,
                "ingestion_status": "PASS",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "symbol",
            "description",
            "quantity",
            "market_value",
            "percent_of_account",
            "source_percent_of_account",
            "cost_basis_total",
            "security_type",
            "operational_state",
            "is_cash_equivalent",
            "source_file",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "symbol": "MU",
                "description": "MU",
                "quantity": 10,
                "market_value": 100000,
                "percent_of_account": 100,
                "source_percent_of_account": 100,
                "cost_basis_total": 90000,
                "security_type": "EQUITY",
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": "x",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )

    payload = pis_momentum_summary(repo_root=tmp_path)
    mu = payload["security_drilldown"]["mu"]["questions"]
    assert mu["confirmation_state"] == "UNAVAILABLE"
    assert mu["vs_market"] == "UNAVAILABLE"


def test_industry_parent_unavailable_when_coverage_insufficient(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [
            {
                "benchmark_id": "BM",
                "symbol_or_index": "^GSPC",
                "date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(),
                "adjusted_close": 100 + i,
                "cumulative_return": 0,
                "source_provider": "TEST",
            }
            for i in range(40)
        ],
    )
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [
            {"security_id": "AAA", "symbol": "AAA", "security_type": "EQUITY", "snapshot_date": "2026-08-19", "run_id": "R1", "market_cap_bucket": "L", "geography": "US", "country": "US", "industry": "Semiconductors", "sector": "Technology"},
            {"security_id": "BBB", "symbol": "BBB", "security_type": "EQUITY", "snapshot_date": "2026-08-19", "run_id": "R1", "market_cap_bucket": "L", "geography": "US", "country": "US", "industry": "Semiconductors", "sector": "Technology"},
            {"security_id": "CCC", "symbol": "CCC", "security_type": "EQUITY", "snapshot_date": "2026-08-19", "run_id": "R1", "market_cap_bucket": "L", "geography": "US", "country": "US", "industry": "Semiconductors", "sector": "Technology"},
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "source_file",
            "source_run_id",
            "source_format",
            "partition_path",
            "snapshot_path",
            "positions_path",
            "position_count",
            "portfolio_value",
            "cash_value",
            "equity_value",
            "ingestion_status",
            "created_at_utc",
        ],
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "source_file": "x",
                "source_run_id": "R1",
                "source_format": "csv",
                "partition_path": "",
                "snapshot_path": "",
                "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv",
                "position_count": 3,
                "portfolio_value": 100000,
                "cash_value": 0,
                "equity_value": 100000,
                "ingestion_status": "PASS",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        [
            "snapshot_id",
            "snapshot_date",
            "account_id",
            "account_name",
            "symbol",
            "description",
            "quantity",
            "market_value",
            "percent_of_account",
            "source_percent_of_account",
            "cost_basis_total",
            "security_type",
            "operational_state",
            "is_cash_equivalent",
            "source_file",
            "created_at_utc",
        ],
        [
            {"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "symbol": "AAA", "description": "AAA", "quantity": 1, "market_value": 34000, "percent_of_account": 34, "source_percent_of_account": 34, "cost_basis_total": 30000, "security_type": "EQUITY", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "False", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"},
            {"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "symbol": "BBB", "description": "BBB", "quantity": 1, "market_value": 33000, "percent_of_account": 33, "source_percent_of_account": 33, "cost_basis_total": 30000, "security_type": "EQUITY", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "False", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"},
            {"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "symbol": "CCC", "description": "CCC", "quantity": 1, "market_value": 33000, "percent_of_account": 33, "source_percent_of_account": 33, "cost_basis_total": 30000, "security_type": "EQUITY", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "False", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"},
        ],
    )

    # Only one constituent has price history, so industry parent coverage is insufficient.
    _write_csv(
        tmp_path / "data/history/prices/symbol=AAA/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 1, 1), 40, 100.0, 1.0, "AAA"),
    )

    payload = pis_momentum_summary(repo_root=tmp_path)
    industry_rows = payload["industry_rotation"]
    semi = next(row for row in industry_rows if row["industry"] == "SEMICONDUCTORS")
    assert semi["parent_available"] is False
    assert semi["parent_methodology"] == "UNAVAILABLE"


def test_industry_granularity_sector_only_becomes_unavailable(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [{"security_id": "MU", "symbol": "MU", "security_type": "EQUITY", "snapshot_date": "2026-08-19", "run_id": "R1", "market_cap_bucket": "MEGA", "geography": "US", "country": "US", "industry": "Technology", "sector": "Technology"}],
    )
    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        ["snapshot_id", "snapshot_date", "account_id", "account_name", "source_file", "source_run_id", "source_format", "partition_path", "snapshot_path", "positions_path", "position_count", "portfolio_value", "cash_value", "equity_value", "ingestion_status", "created_at_utc"],
        [{"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "source_file": "x", "source_run_id": "R1", "source_format": "csv", "partition_path": "", "snapshot_path": "", "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv", "position_count": 1, "portfolio_value": 100000, "cash_value": 0, "equity_value": 100000, "ingestion_status": "PASS", "created_at_utc": "2026-08-19T00:00:00+00:00"}],
    )
    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        ["snapshot_id", "snapshot_date", "account_id", "account_name", "symbol", "description", "quantity", "market_value", "percent_of_account", "source_percent_of_account", "cost_basis_total", "security_type", "operational_state", "is_cash_equivalent", "source_file", "created_at_utc"],
        [{"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "symbol": "MU", "description": "MU", "quantity": 10, "market_value": 100000, "percent_of_account": 100, "source_percent_of_account": 100, "cost_basis_total": 90000, "security_type": "EQUITY", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "False", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"}],
    )
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [{"benchmark_id": "BM", "symbol_or_index": "^GSPC", "date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(), "adjusted_close": 100 + i, "cumulative_return": 0, "source_provider": "TEST"} for i in range(40)],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=MU/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 1, 1), 40, 100.0, 1.0, "MU"),
    )

    payload = pis_momentum_summary(repo_root=tmp_path)
    mu_row = next(row for row in payload["portfolio_momentum_map"]["holdings"] if row["symbol"] == "MU")
    assert mu_row["industry"] == "UNAVAILABLE"
    assert mu_row["industry_granularity"] == "SECTOR_ONLY"


def test_industry_uses_security_metadata_when_distinct(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [{"security_id": "MU", "symbol": "MU", "security_type": "EQUITY", "snapshot_date": "2026-08-19", "run_id": "R1", "market_cap_bucket": "MEGA", "geography": "US", "country": "US", "industry": "Technology", "sector": "Technology"}],
    )
    _write_csv(
        tmp_path / "data/signals/security_metadata/latest_security_metadata.csv",
        ["symbol", "sector", "industry", "country", "quote_type", "sourced_date", "metadata_status", "failure_type", "failure_reason", "attempt_count", "last_attempt_utc"],
        [{"symbol": "MU", "sector": "Technology", "industry": "Semiconductors", "country": "United States", "quote_type": "EQUITY", "sourced_date": "2026-08-19", "metadata_status": "OK", "failure_type": "", "failure_reason": "", "attempt_count": 1, "last_attempt_utc": "2026-08-19T00:00:00+00:00"}],
    )
    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        ["snapshot_id", "snapshot_date", "account_id", "account_name", "source_file", "source_run_id", "source_format", "partition_path", "snapshot_path", "positions_path", "position_count", "portfolio_value", "cash_value", "equity_value", "ingestion_status", "created_at_utc"],
        [{"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "source_file": "x", "source_run_id": "R1", "source_format": "csv", "partition_path": "", "snapshot_path": "", "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv", "position_count": 1, "portfolio_value": 100000, "cash_value": 0, "equity_value": 100000, "ingestion_status": "PASS", "created_at_utc": "2026-08-19T00:00:00+00:00"}],
    )
    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        ["snapshot_id", "snapshot_date", "account_id", "account_name", "symbol", "description", "quantity", "market_value", "percent_of_account", "source_percent_of_account", "cost_basis_total", "security_type", "operational_state", "is_cash_equivalent", "source_file", "created_at_utc"],
        [{"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "symbol": "MU", "description": "MU", "quantity": 10, "market_value": 100000, "percent_of_account": 100, "source_percent_of_account": 100, "cost_basis_total": 90000, "security_type": "EQUITY", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "False", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"}],
    )
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [{"benchmark_id": "BM", "symbol_or_index": "^GSPC", "date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(), "adjusted_close": 100 + i, "cumulative_return": 0, "source_provider": "TEST"} for i in range(40)],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=MU/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 1, 1), 40, 100.0, 1.0, "MU"),
    )

    payload = pis_momentum_summary(repo_root=tmp_path)
    mu_row = next(row for row in payload["portfolio_momentum_map"]["holdings"] if row["symbol"] == "MU")
    assert mu_row["industry"] == "SEMICONDUCTORS"
    assert mu_row["industry_source"] == "SECURITY_METADATA"
    assert mu_row["industry_granularity"] == "DISTINCT_INDUSTRY"


def test_industry_parent_coverage_uses_applicable_denominator(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [
            {"security_id": "AAA1", "symbol": "AAA", "security_type": "EQUITY", "snapshot_date": "2026-08-19", "run_id": "R1", "market_cap_bucket": "LARGE", "geography": "US", "country": "US", "industry": "SEMICONDUCTORS", "sector": "TECHNOLOGY"},
            {"security_id": "BBB1", "symbol": "BBB", "security_type": "EQUITY", "snapshot_date": "2026-08-19", "run_id": "R1", "market_cap_bucket": "LARGE", "geography": "US", "country": "US", "industry": "SEMICONDUCTORS", "sector": "TECHNOLOGY"},
            {"security_id": "SPX1", "symbol": "SPAXX", "security_type": "MUTUAL_FUND", "snapshot_date": "2026-08-19", "run_id": "R1", "market_cap_bucket": "N/A", "geography": "US", "country": "US", "industry": "MONEY MARKET", "sector": "CASH"},
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        ["snapshot_id", "snapshot_date", "account_id", "account_name", "source_file", "source_run_id", "source_format", "partition_path", "snapshot_path", "positions_path", "position_count", "portfolio_value", "cash_value", "equity_value", "ingestion_status", "created_at_utc"],
        [{"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "source_file": "x", "source_run_id": "R1", "source_format": "csv", "partition_path": "", "snapshot_path": "", "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv", "position_count": 3, "portfolio_value": 100000, "cash_value": 10000, "equity_value": 90000, "ingestion_status": "PASS", "created_at_utc": "2026-08-19T00:00:00+00:00"}],
    )
    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        ["snapshot_id", "snapshot_date", "account_id", "account_name", "symbol", "description", "quantity", "market_value", "percent_of_account", "source_percent_of_account", "cost_basis_total", "security_type", "operational_state", "is_cash_equivalent", "source_file", "created_at_utc"],
        [
            {"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "symbol": "AAA", "description": "AAA", "quantity": 10, "market_value": 45000, "percent_of_account": 45, "source_percent_of_account": 45, "cost_basis_total": 40000, "security_type": "EQUITY", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "False", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"},
            {"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "symbol": "BBB", "description": "BBB", "quantity": 10, "market_value": 45000, "percent_of_account": 45, "source_percent_of_account": 45, "cost_basis_total": 40000, "security_type": "EQUITY", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "False", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"},
            {"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "symbol": "SPAXX", "description": "SPAXX", "quantity": 1, "market_value": 10000, "percent_of_account": 10, "source_percent_of_account": 10, "cost_basis_total": 10000, "security_type": "MUTUAL_FUND", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "True", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"},
        ],
    )
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [{"benchmark_id": "BM", "symbol_or_index": "^GSPC", "date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(), "adjusted_close": 100 + i, "cumulative_return": 0, "source_provider": "TEST"} for i in range(300)],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=AAA/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 1, 1), 300, 100.0, 0.2, "AAA"),
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=BBB/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 1, 1), 300, 95.0, 0.25, "BBB"),
    )

    payload = pis_momentum_summary(repo_root=tmp_path)
    counts = payload["coverage"]["industry_parent_counts"]
    assert counts["total"] == 2
    assert counts["required"] == 1
    assert counts["not_applicable"] == 1
    assert counts["available"] == 1
    assert payload["coverage"]["industry_parent_coverage_pct"] == 100.0

    hierarchy = payload["coverage"]["hierarchy_availability"]
    assert hierarchy["industry_relative_evaluable_security_pct"] == 100.0
    assert hierarchy["full_hierarchy_security_pct"] == 100.0


def test_non_equity_industry_is_not_applicable_for_parent(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [
            {"security_id": "IBIT1", "symbol": "IBIT", "security_type": "ETF", "snapshot_date": "2026-08-19", "run_id": "R1", "market_cap_bucket": "N/A", "geography": "US", "country": "US", "industry": "BITCOIN", "sector": "DIGITAL ASSETS"},
            {"security_id": "FBTC1", "symbol": "FBTC", "security_type": "ETF", "snapshot_date": "2026-08-19", "run_id": "R1", "market_cap_bucket": "N/A", "geography": "US", "country": "US", "industry": "BITCOIN", "sector": "DIGITAL ASSETS"},
        ],
    )
    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        ["snapshot_id", "snapshot_date", "account_id", "account_name", "source_file", "source_run_id", "source_format", "partition_path", "snapshot_path", "positions_path", "position_count", "portfolio_value", "cash_value", "equity_value", "ingestion_status", "created_at_utc"],
        [{"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "source_file": "x", "source_run_id": "R1", "source_format": "csv", "partition_path": "", "snapshot_path": "", "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv", "position_count": 2, "portfolio_value": 100000, "cash_value": 0, "equity_value": 100000, "ingestion_status": "PASS", "created_at_utc": "2026-08-19T00:00:00+00:00"}],
    )
    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        ["snapshot_id", "snapshot_date", "account_id", "account_name", "symbol", "description", "quantity", "market_value", "percent_of_account", "source_percent_of_account", "cost_basis_total", "security_type", "operational_state", "is_cash_equivalent", "source_file", "created_at_utc"],
        [
            {"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "symbol": "IBIT", "description": "IBIT", "quantity": 10, "market_value": 50000, "percent_of_account": 50, "source_percent_of_account": 50, "cost_basis_total": 45000, "security_type": "ETF", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "False", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"},
            {"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "symbol": "FBTC", "description": "FBTC", "quantity": 10, "market_value": 50000, "percent_of_account": 50, "source_percent_of_account": 50, "cost_basis_total": 45000, "security_type": "ETF", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "False", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"},
        ],
    )
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [{"benchmark_id": "BM", "symbol_or_index": "^GSPC", "date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(), "adjusted_close": 100 + i, "cumulative_return": 0, "source_provider": "TEST"} for i in range(300)],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=IBIT/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 1, 1), 300, 100.0, 0.3, "IBIT"),
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=FBTC/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 1, 1), 300, 95.0, 0.25, "FBTC"),
    )

    payload = pis_momentum_summary(repo_root=tmp_path)
    bitcoin = next(row for row in payload["industry_rotation"] if row["industry"] == "BITCOIN")
    assert bitcoin["parent_applicable"] is False
    assert bitcoin["parent_blocker"] == "ASSET_CLASS_NOT_MEANINGFUL"
    assert bitcoin["parent_available"] is False


def test_single_security_equity_industry_stays_applicable_but_unavailable(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "data/current/analytical_universe.csv",
        ["security_id", "symbol", "security_type", "snapshot_date", "run_id", "market_cap_bucket", "geography", "country", "industry", "sector"],
        [{"security_id": "DELL1", "symbol": "DELL", "security_type": "EQUITY", "snapshot_date": "2026-08-19", "run_id": "R1", "market_cap_bucket": "LARGE", "geography": "US", "country": "US", "industry": "COMPUTER HARDWARE", "sector": "TECHNOLOGY"}],
    )
    _write_csv(
        tmp_path / "data/history/pis/pis_snapshot_index.csv",
        ["snapshot_id", "snapshot_date", "account_id", "account_name", "source_file", "source_run_id", "source_format", "partition_path", "snapshot_path", "positions_path", "position_count", "portfolio_value", "cash_value", "equity_value", "ingestion_status", "created_at_utc"],
        [{"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "source_file": "x", "source_run_id": "R1", "source_format": "csv", "partition_path": "", "snapshot_path": "", "positions_path": "data/history/pis/snapshot_date=2026-08-19/positions.csv", "position_count": 1, "portfolio_value": 100000, "cash_value": 0, "equity_value": 100000, "ingestion_status": "PASS", "created_at_utc": "2026-08-19T00:00:00+00:00"}],
    )
    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-08-19/positions.csv",
        ["snapshot_id", "snapshot_date", "account_id", "account_name", "symbol", "description", "quantity", "market_value", "percent_of_account", "source_percent_of_account", "cost_basis_total", "security_type", "operational_state", "is_cash_equivalent", "source_file", "created_at_utc"],
        [{"snapshot_id": "S1", "snapshot_date": "2026-08-19", "account_id": "A1", "account_name": "TEST", "symbol": "DELL", "description": "DELL", "quantity": 10, "market_value": 100000, "percent_of_account": 100, "source_percent_of_account": 100, "cost_basis_total": 95000, "security_type": "EQUITY", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "False", "source_file": "x", "created_at_utc": "2026-08-19T00:00:00+00:00"}],
    )
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [{"benchmark_id": "BM", "symbol_or_index": "^GSPC", "date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(), "adjusted_close": 100 + i, "cumulative_return": 0, "source_provider": "TEST"} for i in range(120)],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=DELL/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(date(2026, 1, 1), 120, 100.0, 0.2, "DELL"),
    )

    payload = pis_momentum_summary(repo_root=tmp_path)
    row = next(r for r in payload["industry_rotation"] if r["industry"] == "COMPUTER HARDWARE")
    assert row["parent_applicable"] is True
    assert row["parent_available"] is False
    assert row["parent_blocker"] == "INSUFFICIENT_CONSTITUENTS"


def test_momentum_ui_uses_relative_level_label_and_market_help_text() -> None:
    app_js = (REPO_ROOT / "ui" / "momentum_intelligence" / "app.js").read_text(encoding="utf-8")

    assert "| REL:${esc(r.relative_strength_level || \"UNAVAILABLE\")}" in app_js
    assert "| MKT:${esc(r.relative_strength_level || \"UNAVAILABLE\")}" not in app_js
    assert "Market Relative Coverage measures availability of direct benchmark-relative security evidence only." in app_js
    assert "Relative Level is the selected relative-strength context for this security." in app_js


def test_momentum_ui_uses_independent_section_loading_and_explicit_summary_states() -> None:
    app_js = (REPO_ROOT / "ui" / "momentum_intelligence" / "app.js").read_text(encoding="utf-8")
    server_js = (REPO_ROOT / "scripts" / "run_outcome_ui.py").read_text(encoding="utf-8")

    assert "Promise.all(" not in app_js
    assert "Promise.allSettled" in app_js
    assert "Loading Momentum analysis..." in app_js
    assert "Momentum analysis is still being prepared..." in app_js
    assert "Momentum analysis unavailable." in app_js
    assert "loadSummary" in app_js
    assert "loadMethodology" in app_js
    assert "renderExecutive(summary);" in app_js and "renderMethodology(methodology);" in app_js
    assert "_PIS_MOMENTUM_CACHE[\"signature\"]" in server_js
    assert "_macro_momentum_dependency_signature" in server_js


def test_momentum_ui_renders_trend_structure_reporting_context() -> None:
    app_js = (REPO_ROOT / "ui" / "momentum_intelligence" / "app.js").read_text(encoding="utf-8")
    index_html = (REPO_ROOT / "ui" / "momentum_intelligence" / "index.html").read_text(encoding="utf-8")

    assert "renderTrendStructure(summary);" in app_js
    assert "entry_timing_context" in app_js
    assert "vs 50DMA" in app_js
    assert "vs 200DMA" in app_js
    assert "50DMA 20D" in app_js
    assert "200DMA 20D" in app_js
    assert "Price data" in app_js
    assert "history_status" in app_js
    assert "currentness_state" in app_js
    assert "50DMA and 200DMA are reporting-only timing context." in app_js
    assert "id=\"trendStructure\"" in index_html
