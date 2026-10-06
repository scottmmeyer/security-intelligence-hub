from __future__ import annotations

import csv
from pathlib import Path

from src.pis.momentum_intelligence import _load_holdings, _load_holdings_as_of


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _seed_snapshot(tmp_path: Path, snapshot_date: str, rows: list[dict[str, object]]) -> None:
    positions_rel = f"data/history/pis/snapshot_date={snapshot_date}/positions.csv"
    _write_csv(
        tmp_path / positions_rel,
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
                "source_file": "fixture.csv",
                "source_run_id": "R1",
                "source_format": "csv",
                "partition_path": "",
                "snapshot_path": "",
                "positions_path": positions_rel,
                "position_count": len(rows),
                "portfolio_value": 100000,
                "cash_value": 0,
                "equity_value": 100000,
                "ingestion_status": "PASS",
                "created_at_utc": "2026-10-05T00:00:00+00:00",
            }
        ],
    )


def _row(symbol: str, security_type: str, market_value: float, pct: float) -> dict[str, object]:
    return {
        "snapshot_id": "S1",
        "snapshot_date": "2026-10-05",
        "account_id": "A1",
        "account_name": "TEST",
        "symbol": symbol,
        "description": symbol,
        "quantity": 1,
        "market_value": market_value,
        "percent_of_account": pct,
        "source_percent_of_account": pct,
        "cost_basis_total": market_value,
        "security_type": security_type,
        "operational_state": "ACTIVE_POSITION",
        "is_cash_equivalent": "False",
        "source_file": "fixture.csv",
        "created_at_utc": "2026-10-05T00:00:00+00:00",
    }


def test_shared_holdings_boundary_excludes_pseudo_positions_and_preserves_valid_rows(tmp_path: Path) -> None:
    rows = [
        _row("AAPL", "Common Stock", 10000.0, 10.0),
        _row("ASML", "Depository Receipt", 9000.0, 9.0),
        _row("VOO", "ETF", 8000.0, 8.0),
        _row("SPAXX", "Cash", 7000.0, 7.0),
        _row("XYZQ", "Structured Note", 6000.0, 6.0),
        _row("PENDING", "Common Stock", 10.0, 0.01),
        _row("PENDING ACTIVITY", "Common Stock", 19.73, 0.0041),
        _row("CASH", "Cash", 500.0, 0.5),
    ]
    _seed_snapshot(tmp_path, "2026-10-05", rows)

    snapshot_date, holdings = _load_holdings(tmp_path)

    assert snapshot_date == "2026-10-05"
    symbols = {h["symbol"] for h in holdings}
    assert "PENDING" not in symbols
    assert "PENDING ACTIVITY" not in symbols
    assert "CASH" not in symbols

    # Preserve ordinary and non-standard but valid investable symbols.
    assert "AAPL" in symbols
    assert "ASML" in symbols
    assert "VOO" in symbols
    assert "SPAXX" in symbols
    assert "XYZQ" in symbols


def test_shared_holdings_boundary_applies_to_as_of_loader(tmp_path: Path) -> None:
    rows = [
        _row("AAPL", "Common Stock", 10000.0, 10.0),
        _row("PENDING ACTIVITY", "Common Stock", 19.73, 0.0041),
    ]
    _seed_snapshot(tmp_path, "2026-10-05", rows)

    as_of, holdings = _load_holdings_as_of(tmp_path, "2026-10-05")

    assert as_of == "2026-10-05"
    assert [h["symbol"] for h in holdings] == ["AAPL"]
