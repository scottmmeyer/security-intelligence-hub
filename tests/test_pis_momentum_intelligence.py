from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

from src.pis.momentum_intelligence import (
    MomentumSeries,
    _build_horizon_payload,
    _classify_absolute_momentum_state,
    _classify_breadth_state,
    _classify_confirmation_state,
    _classify_extension_state,
    _classify_fundamental_momentum,
    _classify_security_leadership_state,
    _relative_momentum_change,
    _relative_strength_level,
    _series_confidence,
    pis_momentum_summary,
)


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


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
