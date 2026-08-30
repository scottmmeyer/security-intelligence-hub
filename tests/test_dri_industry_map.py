from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

from src.pis.dislocation_recovery_intelligence import pis_dri_industry_map

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _price_rows(
    *,
    symbol: str,
    start: date,
    days: int,
    base: float,
    step: float,
    future_spike_start: date | None = None,
    future_spike_value: float | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    price = base
    for i in range(days):
        d = start + timedelta(days=i)
        if future_spike_start is not None and future_spike_value is not None and d >= future_spike_start:
            price = future_spike_value
        else:
            price = price + step
        rows.append(
            {
                "security_id": f"{symbol}-ID",
                "symbol": symbol,
                "security_type": "EQUITY",
                "date": d.isoformat(),
                "open": round(price, 4),
                "high": round(price, 4),
                "low": round(price, 4),
                "close": round(price, 4),
                "adjusted_close": round(price, 4),
                "volume": 100000,
                "dividend": 0,
                "split_ratio": 1,
                "source_provider": "TEST",
                "created_at_utc": "2026-01-01T00:00:00+00:00",
            }
        )
    return rows


def _price_rows_from_values(
    *,
    symbol: str,
    start: date,
    values: list[float],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for i, price in enumerate(values):
        d = start + timedelta(days=i)
        rows.append(
            {
                "security_id": f"{symbol}-ID",
                "symbol": symbol,
                "security_type": "EQUITY",
                "date": d.isoformat(),
                "open": round(price, 4),
                "high": round(price, 4),
                "low": round(price, 4),
                "close": round(price, 4),
                "adjusted_close": round(price, 4),
                "volume": 100000,
                "dividend": 0,
                "split_ratio": 1,
                "source_provider": "TEST",
                "created_at_utc": "2026-01-01T00:00:00+00:00",
            }
        )
    return rows


def _rewrite_universe(tmp_path: Path, rows: list[dict[str, object]]) -> None:
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
        rows,
    )


def _rewrite_positions(tmp_path: Path, snapshot_date: str, symbols: list[str]) -> None:
    rows = []
    for i, symbol in enumerate(symbols, start=1):
        rows.append(
            {
                "snapshot_id": "S1",
                "snapshot_date": snapshot_date,
                "account_id": "A1",
                "account_name": "TEST",
                "symbol": symbol,
                "description": symbol,
                "quantity": 100,
                "market_value": 10000,
                "percent_of_account": round(100.0 / max(len(symbols), 1), 4),
                "source_percent_of_account": round(100.0 / max(len(symbols), 1), 4),
                "cost_basis_total": 9000,
                "security_type": "EQUITY",
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": f"seed-{i}",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        )
    _write_csv(
        tmp_path / f"data/history/pis/snapshot_date={snapshot_date}/positions.csv",
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
        rows,
    )


def _rewrite_snapshot_index(tmp_path: Path, snapshot_date: str) -> None:
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
                "snapshot_date": snapshot_date,
                "account_id": "A1",
                "account_name": "TEST",
                "source_file": "x",
                "source_run_id": "R1",
                "source_format": "csv",
                "partition_path": "",
                "snapshot_path": "",
                "positions_path": f"data/history/pis/snapshot_date={snapshot_date}/positions.csv",
                "position_count": 3,
                "portfolio_value": 100000,
                "cash_value": 0,
                "equity_value": 100000,
                "ingestion_status": "PASS",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )


def _rewrite_benchmark_values(tmp_path: Path, start: date, values: list[float]) -> None:
    _write_csv(
        tmp_path / "data/current/benchmark_returns.csv",
        ["benchmark_id", "symbol_or_index", "date", "adjusted_close", "cumulative_return", "source_provider"],
        [
            {
                "benchmark_id": "BM",
                "symbol_or_index": "^GSPC",
                "date": (start + timedelta(days=i)).isoformat(),
                "adjusted_close": round(values[i], 4),
                "cumulative_return": 0,
                "source_provider": "TEST",
            }
            for i in range(len(values))
        ],
    )


def _rewrite_symbol_prices(tmp_path: Path, symbol: str, start: date, values: list[float]) -> None:
    _write_csv(
        tmp_path / f"data/history/prices/symbol={symbol}/prices.csv",
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
        _price_rows_from_values(symbol=symbol, start=start, values=values),
    )


def _seed_minimal_dri_fixture(tmp_path: Path) -> None:
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
                "security_id": "CRM1",
                "symbol": "CRM",
                "security_type": "EQUITY",
                "snapshot_date": "2026-08-19",
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "SOFTWARE_INFRASTRUCTURE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "MSFT1",
                "symbol": "MSFT",
                "security_type": "EQUITY",
                "snapshot_date": "2026-08-19",
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "SOFTWARE_INFRASTRUCTURE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "XOM1",
                "symbol": "XOM",
                "security_type": "EQUITY",
                "snapshot_date": "2026-08-19",
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "INTEGRATED_OIL",
                "sector": "ENERGY",
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
                "position_count": 3,
                "portfolio_value": 100000,
                "cash_value": 0,
                "equity_value": 100000,
                "ingestion_status": "PASS",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            },
            {
                "snapshot_id": "S2",
                "snapshot_date": "2026-10-01",
                "account_id": "A1",
                "account_name": "TEST",
                "source_file": "x",
                "source_run_id": "R2",
                "source_format": "csv",
                "partition_path": "",
                "snapshot_path": "",
                "positions_path": "data/history/pis/snapshot_date=2026-10-01/positions.csv",
                "position_count": 3,
                "portfolio_value": 100000,
                "cash_value": 0,
                "equity_value": 100000,
                "ingestion_status": "PASS",
                "created_at_utc": "2026-10-01T00:00:00+00:00",
            },
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
                "symbol": "CRM",
                "description": "CRM",
                "quantity": 100,
                "market_value": 45000,
                "percent_of_account": 45,
                "source_percent_of_account": 45,
                "cost_basis_total": 40000,
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
                "symbol": "MSFT",
                "description": "MSFT",
                "quantity": 100,
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
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-08-19",
                "account_id": "A1",
                "account_name": "TEST",
                "symbol": "XOM",
                "description": "XOM",
                "quantity": 100,
                "market_value": 15000,
                "percent_of_account": 15,
                "source_percent_of_account": 15,
                "cost_basis_total": 15000,
                "security_type": "EQUITY",
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": "x",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            },
        ],
    )

    _write_csv(
        tmp_path / "data/history/pis/snapshot_date=2026-10-01/positions.csv",
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
                "snapshot_id": "S2",
                "snapshot_date": "2026-10-01",
                "account_id": "A1",
                "account_name": "TEST",
                "symbol": "CRM",
                "description": "CRM",
                "quantity": 100,
                "market_value": 45000,
                "percent_of_account": 45,
                "source_percent_of_account": 45,
                "cost_basis_total": 40000,
                "security_type": "EQUITY",
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": "x",
                "created_at_utc": "2026-10-01T00:00:00+00:00",
            },
            {
                "snapshot_id": "S2",
                "snapshot_date": "2026-10-01",
                "account_id": "A1",
                "account_name": "TEST",
                "symbol": "MSFT",
                "description": "MSFT",
                "quantity": 100,
                "market_value": 40000,
                "percent_of_account": 40,
                "source_percent_of_account": 40,
                "cost_basis_total": 35000,
                "security_type": "EQUITY",
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": "x",
                "created_at_utc": "2026-10-01T00:00:00+00:00",
            },
            {
                "snapshot_id": "S2",
                "snapshot_date": "2026-10-01",
                "account_id": "A1",
                "account_name": "TEST",
                "symbol": "XOM",
                "description": "XOM",
                "quantity": 100,
                "market_value": 15000,
                "percent_of_account": 15,
                "source_percent_of_account": 15,
                "cost_basis_total": 15000,
                "security_type": "EQUITY",
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": "x",
                "created_at_utc": "2026-10-01T00:00:00+00:00",
            },
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
                "adjusted_close": 100 + i * 0.15,
                "cumulative_return": 0,
                "source_provider": "TEST",
            }
            for i in range(300)
        ],
    )

    _write_csv(
        tmp_path / "data/history/prices/symbol=CRM/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(
            symbol="CRM",
            start=date(2026, 1, 1),
            days=300,
            base=100.0,
            step=0.35,
            future_spike_start=date(2026, 8, 20),
            future_spike_value=1000.0,
        ),
    )

    _write_csv(
        tmp_path / "data/history/prices/symbol=MSFT/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(symbol="MSFT", start=date(2026, 1, 1), days=300, base=80.0, step=0.22),
    )

    _write_csv(
        tmp_path / "data/history/prices/symbol=XOM/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(symbol="XOM", start=date(2026, 1, 1), days=300, base=120.0, step=-0.05),
    )

    signal_rows = []
    for i in range(40):
        d = (date(2026, 7, 1) + timedelta(days=i)).isoformat()
        signal_rows.append(
            {
                "snapshot_date": d,
                "symbol": "CRM",
                "starmine_ess_numeric": 6.0 + i * 0.02,
            }
        )
        signal_rows.append(
            {
                "snapshot_date": d,
                "symbol": "MSFT",
                "starmine_ess_numeric": 5.0 + i * 0.01,
            }
        )
    _write_csv(
        tmp_path / "data/history/signals/snapshot_date=2026-08-19/run_id=R1/signal_snapshots.csv",
        ["snapshot_date", "symbol", "starmine_ess_numeric"],
        signal_rows,
    )


def test_dri_industry_map_reports_raw_industry_metrics_and_coverage(tmp_path: Path) -> None:
    _seed_minimal_dri_fixture(tmp_path)

    payload = pis_dri_industry_map(repo_root=tmp_path, as_of_date="2026-08-19")

    assert payload["reporting_only"] is True
    assert payload["as_of_date"] == "2026-08-19"
    assert "coverage_summary" in payload
    assert payload["coverage_summary"]["industry_count"] == 2

    software = next(row for row in payload["industries"] if row["industry"] == "SOFTWARE_INFRASTRUCTURE")
    oil = next(row for row in payload["industries"] if row["industry"] == "INTEGRATED_OIL")

    assert "CRM" in software["members"]
    assert software["member_count"] == 2
    assert software["history_coverage"]["parent_available"] is True
    assert software["returns"]["return_3m_pct"] is not None
    assert software["returns"]["return_3m_vs_market_pct"] is not None
    assert software["breadth"]["above_50dma"]["denominator"] >= 1
    assert software["breadth"]["above_50dma"]["numerator"] >= 0
    assert software["breadth"]["above_50dma_share_change_20d_pp"] is not None
    assert software["trend_medians"]["price_vs_sma50_pct"] is not None
    assert software["momentum_context"]["relative_strength_level"] in {"HIGH", "MEDIUM", "NEUTRAL", "LOW", "WEAK", "UNAVAILABLE"}
    assert software["fundamental_context"]["ess_observations"] >= 1

    assert oil["member_count"] == 1
    assert oil["history_coverage"]["parent_available"] is False
    assert oil["returns"]["return_3m_pct"] is None
    assert oil["returns"]["return_3m_vs_market_pct"] is None
    assert oil["drawdown"]["from_available_history_high_pct"] is None


def test_dri_industry_map_as_of_filter_prevents_lookahead_from_future_price_spike(tmp_path: Path) -> None:
    _seed_minimal_dri_fixture(tmp_path)

    as_of_payload = pis_dri_industry_map(repo_root=tmp_path, as_of_date="2026-08-19")
    future_payload = pis_dri_industry_map(repo_root=tmp_path, as_of_date="2026-10-01")

    as_of_software = next(row for row in as_of_payload["industries"] if row["industry"] == "SOFTWARE_INFRASTRUCTURE")
    future_software = next(row for row in future_payload["industries"] if row["industry"] == "SOFTWARE_INFRASTRUCTURE")

    as_of_ret_1m = as_of_software["returns"]["return_1m_pct"]
    future_ret_1m = future_software["returns"]["return_1m_pct"]

    # Remove the future spike and recompute the same as-of date; the value should
    # remain identical if the as-of evaluator is correctly no-lookahead.
    _write_csv(
        tmp_path / "data/history/prices/symbol=CRM/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(symbol="CRM", start=date(2026, 1, 1), days=300, base=100.0, step=0.35),
    )
    control_as_of_payload = pis_dri_industry_map(repo_root=tmp_path, as_of_date="2026-08-19")
    control_as_of_software = next(row for row in control_as_of_payload["industries"] if row["industry"] == "SOFTWARE_INFRASTRUCTURE")
    control_as_of_ret_1m = control_as_of_software["returns"]["return_1m_pct"]

    assert isinstance(as_of_ret_1m, float)
    assert isinstance(control_as_of_ret_1m, float)
    assert as_of_ret_1m == control_as_of_ret_1m
    assert isinstance(future_ret_1m, float)
    assert future_ret_1m != as_of_ret_1m



def test_dri_runtime_route_and_ui_contracts_present() -> None:
    server_py = (REPO_ROOT / "scripts" / "run_outcome_ui.py").read_text(encoding="utf-8")
    dri_html = (REPO_ROOT / "ui" / "dislocation_recovery_intelligence" / "index.html").read_text(encoding="utf-8")
    dri_app = (REPO_ROOT / "ui" / "dislocation_recovery_intelligence" / "app.js").read_text(encoding="utf-8")

    assert "/api/pis/dri/industry-map" in server_py
    assert "pis_dri_industry_map" in server_py

    assert "Reporting-only visibility" in dri_html
    assert "Most Dislocated" in dri_html
    assert "Improving Internals" in dri_html
    assert "Current Leadership" in dri_html
    assert "sortMode" in dri_html
    assert "industryFilter" in dri_html

    assert "fetchJson(\"/api/pis/dri/industry-map\"" in dri_app
    assert "renderMostDislocated" in dri_app
    assert "renderImprovingInternals" in dri_app
    assert "renderCurrentLeadership" in dri_app


def test_non_held_research_symbol_and_industry_are_included_in_dri(tmp_path: Path) -> None:
    _seed_minimal_dri_fixture(tmp_path)

    # Add a non-held research-universe symbol in a new industry with valid history.
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
                "security_id": "CRM1",
                "symbol": "CRM",
                "security_type": "EQUITY",
                "snapshot_date": "2026-08-19",
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "SOFTWARE_INFRASTRUCTURE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "MSFT1",
                "symbol": "MSFT",
                "security_type": "EQUITY",
                "snapshot_date": "2026-08-19",
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "SOFTWARE_INFRASTRUCTURE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "XOM1",
                "symbol": "XOM",
                "security_type": "EQUITY",
                "snapshot_date": "2026-08-19",
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "INTEGRATED_OIL",
                "sector": "ENERGY",
            },
            {
                "security_id": "SNOW1",
                "symbol": "SNOW",
                "security_type": "EQUITY",
                "snapshot_date": "2026-08-19",
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "TEAM1",
                "symbol": "TEAM",
                "security_type": "EQUITY",
                "snapshot_date": "2026-08-19",
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
        ],
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=SNOW/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(symbol="SNOW", start=date(2026, 1, 1), days=300, base=50.0, step=0.11),
    )
    _write_csv(
        tmp_path / "data/history/prices/symbol=TEAM/prices.csv",
        ["security_id", "symbol", "security_type", "date", "open", "high", "low", "close", "adjusted_close", "volume", "dividend", "split_ratio", "source_provider", "created_at_utc"],
        _price_rows(symbol="TEAM", start=date(2026, 1, 1), days=300, base=45.0, step=0.09),
    )

    payload = pis_dri_industry_map(repo_root=tmp_path, as_of_date="2026-08-19")
    app_sw = next(row for row in payload["industries"] if row["industry"] == "APPLICATION_SOFTWARE")

    assert "SNOW" in app_sw["members"]
    assert "TEAM" in app_sw["members"]
    assert app_sw["portfolio_context"]["portfolio_member_count"] == 0


def test_dri_discovery_universe_is_independent_of_portfolio_membership(tmp_path: Path) -> None:
    _seed_minimal_dri_fixture(tmp_path)

    baseline = pis_dri_industry_map(repo_root=tmp_path, as_of_date="2026-08-19")
    baseline_members = {
        row["industry"]: tuple(row["members"])
        for row in baseline["industries"]
    }

    # Replace holdings composition entirely; DRI members should remain research-universe based.
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
                "symbol": "XOM",
                "description": "XOM",
                "quantity": 100,
                "market_value": 100000,
                "percent_of_account": 100,
                "source_percent_of_account": 100,
                "cost_basis_total": 100000,
                "security_type": "EQUITY",
                "operational_state": "ACTIVE_POSITION",
                "is_cash_equivalent": "False",
                "source_file": "x",
                "created_at_utc": "2026-08-19T00:00:00+00:00",
            }
        ],
    )

    shifted = pis_dri_industry_map(repo_root=tmp_path, as_of_date="2026-08-19")
    shifted_members = {
        row["industry"]: tuple(row["members"])
        for row in shifted["industries"]
    }

    assert shifted_members == baseline_members


def test_dri_share_price_scale_invariance_for_fixed_cohort_returns(tmp_path: Path) -> None:
    _seed_minimal_dri_fixture(tmp_path)

    start = date(2026, 1, 1)
    as_of = "2026-10-27"
    n = 300
    split_idx = 236  # 63 trading periods before final point in 300-row synthetic calendar

    def _series(start_px: float, end_px: float) -> list[float]:
        vals: list[float] = []
        for i in range(n):
            if i <= split_idx:
                vals.append(start_px)
            else:
                step = (end_px - start_px) / float(n - 1 - split_idx)
                vals.append(start_px + step * float(i - split_idx))
        return vals

    _rewrite_snapshot_index(tmp_path, "2026-10-27")
    _rewrite_positions(tmp_path, "2026-10-27", ["CRM", "MSFT"])
    _rewrite_universe(
        tmp_path,
        [
            {
                "security_id": "CRM1",
                "symbol": "CRM",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "SOFTWARE_INFRASTRUCTURE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "MSFT1",
                "symbol": "MSFT",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "SOFTWARE_INFRASTRUCTURE",
                "sector": "TECHNOLOGY",
            },
        ],
    )
    _rewrite_benchmark_values(tmp_path, start, _series(100.0, 110.0))
    _rewrite_symbol_prices(tmp_path, "CRM", start, _series(10.0, 11.0))
    _rewrite_symbol_prices(tmp_path, "MSFT", start, _series(1000.0, 1100.0))

    baseline = pis_dri_industry_map(repo_root=tmp_path, as_of_date=as_of)
    software = next(row for row in baseline["industries"] if row["industry"] == "SOFTWARE_INFRASTRUCTURE")
    baseline_ret = software["returns"]["return_3m_pct"]
    assert baseline_ret == 10.0

    _rewrite_symbol_prices(tmp_path, "MSFT", start, _series(10000.0, 11000.0))
    rescaled = pis_dri_industry_map(repo_root=tmp_path, as_of_date=as_of)
    software_rescaled = next(row for row in rescaled["industries"] if row["industry"] == "SOFTWARE_INFRASTRUCTURE")

    assert software_rescaled["returns"]["return_3m_pct"] == 10.0
    assert software_rescaled["returns"]["return_3m_pct"] == baseline_ret


def test_dri_fixed_cohort_excludes_member_missing_end_and_prevents_distortion(tmp_path: Path) -> None:
    _seed_minimal_dri_fixture(tmp_path)

    start = date(2026, 1, 1)
    as_of = "2026-10-27"
    n = 300
    split_idx = 236

    def _series(start_px: float, end_px: float) -> list[float]:
        vals: list[float] = []
        for i in range(n):
            if i <= split_idx:
                vals.append(start_px)
            else:
                step = (end_px - start_px) / float(n - 1 - split_idx)
                vals.append(start_px + step * float(i - split_idx))
        return vals

    _rewrite_snapshot_index(tmp_path, "2026-10-27")
    _rewrite_positions(tmp_path, "2026-10-27", ["CRM", "MSFT", "SNOW"])
    _rewrite_universe(
        tmp_path,
        [
            {
                "security_id": "CRM1",
                "symbol": "CRM",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "MSFT1",
                "symbol": "MSFT",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "SNOW1",
                "symbol": "SNOW",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
        ],
    )

    _rewrite_benchmark_values(tmp_path, start, _series(100.0, 105.0))
    _rewrite_symbol_prices(tmp_path, "CRM", start, _series(100.0, 110.0))
    _rewrite_symbol_prices(tmp_path, "MSFT", start, _series(200.0, 180.0))

    snow = _series(10.0, 30.0)
    snow[-1] = snow[-2]  # keep shape stable before dropping endpoint row
    snow_rows = _price_rows_from_values(symbol="SNOW", start=start, values=snow[:-1])
    _write_csv(
        tmp_path / "data/history/prices/symbol=SNOW/prices.csv",
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
        snow_rows,
    )

    payload = pis_dri_industry_map(repo_root=tmp_path, as_of_date=as_of)
    app_sw = next(row for row in payload["industries"] if row["industry"] == "APPLICATION_SOFTWARE")
    coverage = app_sw["returns"]["coverage"]["3M"]

    assert coverage["industry_member_count"] == 3
    assert coverage["eligible_return_member_count"] == 2
    assert coverage["excluded_missing_end_count"] == 1
    assert app_sw["returns"]["return_3m_pct"] == 0.0

    _rewrite_symbol_prices(tmp_path, "SNOW", start, _series(10000.0, 30000.0)[:-1])
    payload_shifted = pis_dri_industry_map(repo_root=tmp_path, as_of_date=as_of)
    app_sw_shifted = next(row for row in payload_shifted["industries"] if row["industry"] == "APPLICATION_SOFTWARE")
    assert app_sw_shifted["returns"]["return_3m_pct"] == 0.0


def test_dri_blocks_single_constituent_industry_return(tmp_path: Path) -> None:
    _seed_minimal_dri_fixture(tmp_path)

    start = date(2026, 1, 1)
    as_of = "2026-10-27"
    n = 300
    split_idx = 236

    def _series(start_px: float, end_px: float) -> list[float]:
        vals: list[float] = []
        for i in range(n):
            if i <= split_idx:
                vals.append(start_px)
            else:
                step = (end_px - start_px) / float(n - 1 - split_idx)
                vals.append(start_px + step * float(i - split_idx))
        return vals

    _rewrite_snapshot_index(tmp_path, "2026-10-27")
    _rewrite_positions(tmp_path, "2026-10-27", ["CRM", "MSFT", "SNOW"])
    _rewrite_universe(
        tmp_path,
        [
            {
                "security_id": "CRM1",
                "symbol": "CRM",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "MSFT1",
                "symbol": "MSFT",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "SNOW1",
                "symbol": "SNOW",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
        ],
    )
    _rewrite_benchmark_values(tmp_path, start, _series(100.0, 105.0))
    _rewrite_symbol_prices(tmp_path, "CRM", start, _series(100.0, 110.0))

    msft_values = _series(200.0, 220.0)
    msft_rows = []
    for i, row in enumerate(_price_rows_from_values(symbol="MSFT", start=start, values=msft_values)):
        if i == split_idx:
            continue
        msft_rows.append(row)
    _write_csv(
        tmp_path / "data/history/prices/symbol=MSFT/prices.csv",
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
        msft_rows,
    )
    snow_rows = _price_rows_from_values(symbol="SNOW", start=start, values=_series(50.0, 60.0)[:-1])
    _write_csv(
        tmp_path / "data/history/prices/symbol=SNOW/prices.csv",
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
        snow_rows,
    )

    payload = pis_dri_industry_map(repo_root=tmp_path, as_of_date=as_of)
    app_sw = next(row for row in payload["industries"] if row["industry"] == "APPLICATION_SOFTWARE")
    coverage = app_sw["returns"]["coverage"]["3M"]

    assert coverage["eligible_return_member_count"] == 1
    assert coverage["single_member_blocked"] is True
    assert app_sw["returns"]["return_3m_pct"] is None


def test_dri_uses_exact_benchmark_window_for_industry_and_relative_returns(tmp_path: Path) -> None:
    _seed_minimal_dri_fixture(tmp_path)

    start = date(2026, 1, 1)
    as_of = "2026-10-01"
    n_bench = 260
    split_idx = n_bench - 64

    def _series(days: int, start_px: float, end_px: float, anchor_idx: int) -> list[float]:
        vals: list[float] = []
        for i in range(days):
            if i <= anchor_idx:
                vals.append(start_px)
            else:
                step = (end_px - start_px) / float(days - 1 - anchor_idx)
                vals.append(start_px + step * float(i - anchor_idx))
        return vals

    _rewrite_snapshot_index(tmp_path, "2026-10-01")
    _rewrite_positions(tmp_path, "2026-10-01", ["CRM", "MSFT"])
    _rewrite_universe(
        tmp_path,
        [
            {
                "security_id": "CRM1",
                "symbol": "CRM",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "SOFTWARE_INFRASTRUCTURE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "MSFT1",
                "symbol": "MSFT",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "SOFTWARE_INFRASTRUCTURE",
                "sector": "TECHNOLOGY",
            },
        ],
    )

    bench_values = _series(n_bench, 100.0, 104.0, split_idx)
    _rewrite_benchmark_values(tmp_path, start, bench_values)

    # Security history extends beyond benchmark end; DRI returns must still anchor to benchmark dates.
    _rewrite_symbol_prices(tmp_path, "CRM", start, _series(300, 50.0, 75.0, 236))
    _rewrite_symbol_prices(tmp_path, "MSFT", start, _series(300, 40.0, 60.0, 236))

    payload = pis_dri_industry_map(repo_root=tmp_path, as_of_date=as_of)
    software = next(row for row in payload["industries"] if row["industry"] == "SOFTWARE_INFRASTRUCTURE")
    window_3m = software["returns"]["windows"]["3M"]

    assert window_3m["return_end_date"] == window_3m["benchmark_end_date"]
    assert window_3m["return_start_date"] == window_3m["benchmark_start_date"]
    assert window_3m["benchmark_window_aligned"] is True
    assert software["returns"]["return_3m_pct"] is not None
    assert software["returns"]["return_3m_vs_market_pct"] is not None


def test_dri_serializes_12m_payload_presence(tmp_path: Path) -> None:
    _seed_minimal_dri_fixture(tmp_path)

    start = date(2026, 1, 1)
    as_of = "2026-10-27"
    n = 300
    split_idx = 47  # 252 lookback periods => required_points=253 => start index 47 in 300 rows

    def _series(start_px: float, end_px: float) -> list[float]:
        vals: list[float] = []
        for i in range(n):
            if i <= split_idx:
                vals.append(start_px)
            else:
                step = (end_px - start_px) / float(n - 1 - split_idx)
                vals.append(start_px + step * float(i - split_idx))
        return vals

    _rewrite_snapshot_index(tmp_path, as_of)
    _rewrite_positions(tmp_path, as_of, ["CRM", "MSFT"])
    _rewrite_universe(
        tmp_path,
        [
            {
                "security_id": "CRM1",
                "symbol": "CRM",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "SOFTWARE_INFRASTRUCTURE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "MSFT1",
                "symbol": "MSFT",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "SOFTWARE_INFRASTRUCTURE",
                "sector": "TECHNOLOGY",
            },
        ],
    )

    _rewrite_benchmark_values(tmp_path, start, _series(100.0, 110.0))
    _rewrite_symbol_prices(tmp_path, "CRM", start, _series(10.0, 12.0))
    _rewrite_symbol_prices(tmp_path, "MSFT", start, _series(20.0, 24.0))

    payload = pis_dri_industry_map(repo_root=tmp_path, as_of_date=as_of)
    software = next(row for row in payload["industries"] if row["industry"] == "SOFTWARE_INFRASTRUCTURE")
    returns = software["returns"]

    assert "return_12m_pct" in returns
    assert "12M" in returns["coverage"]
    assert "12M" in returns["windows"]
    assert returns["windows"]["12M"]["benchmark_window_aligned"] is True


def test_dri_12m_fixed_cohort_eligibility_and_coverage(tmp_path: Path) -> None:
    _seed_minimal_dri_fixture(tmp_path)

    start = date(2026, 1, 1)
    as_of = "2026-10-27"
    n = 300
    split_idx = 47

    def _series(start_px: float, end_px: float) -> list[float]:
        vals: list[float] = []
        for i in range(n):
            if i <= split_idx:
                vals.append(start_px)
            else:
                step = (end_px - start_px) / float(n - 1 - split_idx)
                vals.append(start_px + step * float(i - split_idx))
        return vals

    _rewrite_snapshot_index(tmp_path, as_of)
    _rewrite_positions(tmp_path, as_of, ["CRM", "MSFT", "SNOW"])
    _rewrite_universe(
        tmp_path,
        [
            {
                "security_id": "CRM1",
                "symbol": "CRM",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "MSFT1",
                "symbol": "MSFT",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "SNOW1",
                "symbol": "SNOW",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
        ],
    )

    _rewrite_benchmark_values(tmp_path, start, _series(100.0, 112.0))
    _rewrite_symbol_prices(tmp_path, "CRM", start, _series(10.0, 14.0))
    _rewrite_symbol_prices(tmp_path, "MSFT", start, _series(20.0, 28.0))
    _rewrite_symbol_prices(tmp_path, "SNOW", start, _series(30.0, 42.0))

    payload = pis_dri_industry_map(repo_root=tmp_path, as_of_date=as_of)
    app_sw = next(row for row in payload["industries"] if row["industry"] == "APPLICATION_SOFTWARE")
    coverage = app_sw["returns"]["coverage"]["12M"]

    assert coverage["eligible_return_member_count"] == 3
    assert coverage["return_coverage_pct"] == 100.0
    assert app_sw["returns"]["return_12m_pct"] is not None


def test_dri_12m_single_member_gate_blocks_return(tmp_path: Path) -> None:
    _seed_minimal_dri_fixture(tmp_path)

    start = date(2026, 1, 1)
    as_of = "2026-10-27"
    n = 300
    split_idx = 47

    def _series(start_px: float, end_px: float) -> list[float]:
        vals: list[float] = []
        for i in range(n):
            if i <= split_idx:
                vals.append(start_px)
            else:
                step = (end_px - start_px) / float(n - 1 - split_idx)
                vals.append(start_px + step * float(i - split_idx))
        return vals

    _rewrite_snapshot_index(tmp_path, as_of)
    _rewrite_positions(tmp_path, as_of, ["CRM", "MSFT"])
    _rewrite_universe(
        tmp_path,
        [
            {
                "security_id": "CRM1",
                "symbol": "CRM",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "MSFT1",
                "symbol": "MSFT",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
        ],
    )

    _rewrite_benchmark_values(tmp_path, start, _series(100.0, 112.0))
    _rewrite_symbol_prices(tmp_path, "CRM", start, _series(10.0, 14.0))
    # MSFT starts far after the benchmark 12M start, so only CRM is eligible.
    _rewrite_symbol_prices(tmp_path, "MSFT", start + timedelta(days=120), _series(20.0, 28.0)[120:])

    payload = pis_dri_industry_map(repo_root=tmp_path, as_of_date=as_of)
    app_sw = next(row for row in payload["industries"] if row["industry"] == "APPLICATION_SOFTWARE")
    coverage = app_sw["returns"]["coverage"]["12M"]

    assert coverage["eligible_return_member_count"] == 1
    assert coverage["single_member_blocked"] is True
    assert app_sw["returns"]["return_12m_pct"] is None


def test_dri_12m_excludes_missing_endpoint_without_shortened_window(tmp_path: Path) -> None:
    _seed_minimal_dri_fixture(tmp_path)

    start = date(2026, 1, 1)
    as_of = "2026-10-27"
    n = 300
    split_idx = 47

    def _series(start_px: float, end_px: float) -> list[float]:
        vals: list[float] = []
        for i in range(n):
            if i <= split_idx:
                vals.append(start_px)
            else:
                step = (end_px - start_px) / float(n - 1 - split_idx)
                vals.append(start_px + step * float(i - split_idx))
        return vals

    _rewrite_snapshot_index(tmp_path, as_of)
    _rewrite_positions(tmp_path, as_of, ["CRM", "MSFT", "SNOW"])
    _rewrite_universe(
        tmp_path,
        [
            {
                "security_id": "CRM1",
                "symbol": "CRM",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "MSFT1",
                "symbol": "MSFT",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "SNOW1",
                "symbol": "SNOW",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "APPLICATION_SOFTWARE",
                "sector": "TECHNOLOGY",
            },
        ],
    )

    _rewrite_benchmark_values(tmp_path, start, _series(100.0, 112.0))
    _rewrite_symbol_prices(tmp_path, "CRM", start, _series(10.0, 14.0))
    _rewrite_symbol_prices(tmp_path, "MSFT", start, _series(20.0, 28.0))
    # SNOW has deep history but missing exact benchmark end date.
    _rewrite_symbol_prices(tmp_path, "SNOW", start, _series(30.0, 42.0)[:-1])

    payload = pis_dri_industry_map(repo_root=tmp_path, as_of_date=as_of)
    app_sw = next(row for row in payload["industries"] if row["industry"] == "APPLICATION_SOFTWARE")
    coverage = app_sw["returns"]["coverage"]["12M"]

    assert coverage["eligible_return_member_count"] == 2
    assert coverage["excluded_missing_end_count"] == 1
    assert app_sw["returns"]["return_12m_pct"] is not None


def test_dri_serialization_parity_for_6m_and_12m(tmp_path: Path) -> None:
    _seed_minimal_dri_fixture(tmp_path)

    start = date(2026, 1, 1)
    as_of = "2026-10-27"
    n = 300
    split_idx = 47

    def _series(start_px: float, end_px: float) -> list[float]:
        vals: list[float] = []
        for i in range(n):
            if i <= split_idx:
                vals.append(start_px)
            else:
                step = (end_px - start_px) / float(n - 1 - split_idx)
                vals.append(start_px + step * float(i - split_idx))
        return vals

    _rewrite_snapshot_index(tmp_path, as_of)
    _rewrite_positions(tmp_path, as_of, ["CRM", "MSFT"])
    _rewrite_universe(
        tmp_path,
        [
            {
                "security_id": "CRM1",
                "symbol": "CRM",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "SOFTWARE_INFRASTRUCTURE",
                "sector": "TECHNOLOGY",
            },
            {
                "security_id": "MSFT1",
                "symbol": "MSFT",
                "security_type": "EQUITY",
                "snapshot_date": as_of,
                "run_id": "R1",
                "market_cap_bucket": "LARGE",
                "geography": "US",
                "country": "US",
                "industry": "SOFTWARE_INFRASTRUCTURE",
                "sector": "TECHNOLOGY",
            },
        ],
    )

    _rewrite_benchmark_values(tmp_path, start, _series(100.0, 110.0))
    _rewrite_symbol_prices(tmp_path, "CRM", start, _series(10.0, 12.0))
    _rewrite_symbol_prices(tmp_path, "MSFT", start, _series(20.0, 24.0))

    payload = pis_dri_industry_map(repo_root=tmp_path, as_of_date=as_of)
    software = next(row for row in payload["industries"] if row["industry"] == "SOFTWARE_INFRASTRUCTURE")
    coverage = software["returns"]["coverage"]
    windows = software["returns"]["windows"]

    assert "6M" in coverage
    assert "12M" in coverage
    assert "6M" in windows
    assert "12M" in windows
