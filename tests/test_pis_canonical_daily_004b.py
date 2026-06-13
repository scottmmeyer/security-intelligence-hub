from __future__ import annotations

import csv
from pathlib import Path

from src.pis.canonical_daily import (
    canonical_selected_index_rows,
    pis_canonical_history,
    pis_canonical_latest,
    pis_canonical_summary,
    refresh_canonical_daily,
)


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _index_headers() -> list[str]:
    return [
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
    ]


def _pass_account() -> str:
    return "General Brokerage, Joint WROS - TOD, Individual - TOD"


def _rejected_account() -> str:
    return "General Brokerage, Joint WROS - TOD, Individual - TOD, FIS 401(K) PLAN, BrokerageLink"


def test_pass_preferred_over_warning(tmp_path: Path) -> None:
    index_path = tmp_path / "pis_snapshot_index.csv"
    output = tmp_path / "canonical" / "canonical_daily_snapshots.csv"
    _write_csv(
        index_path,
        _index_headers(),
        [
            {
                "snapshot_id": "W1",
                "snapshot_date": "2026-06-11",
                "account_id": "PORTFOLIO",
                "account_name": _pass_account(),
                "source_file": "upload.csv",
                "source_run_id": "PAR-W",
                "source_format": "FIDELITY_CSV",
                "partition_path": "x",
                "snapshot_path": "x",
                "positions_path": "x",
                "position_count": "10",
                "portfolio_value": "470000",
                "cash_value": "20000",
                "equity_value": "450000",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-11T12:05:00+00:00",
            },
            {
                "snapshot_id": "P1",
                "snapshot_date": "2026-06-11",
                "account_id": "PORTFOLIO",
                "account_name": _pass_account(),
                "source_file": "fidelity.csv",
                "source_run_id": "PAR-P",
                "source_format": "FIDELITY_CSV",
                "partition_path": "x",
                "snapshot_path": "x",
                "positions_path": "x",
                "position_count": "11",
                "portfolio_value": "468000",
                "cash_value": "19000",
                "equity_value": "449000",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-11T12:00:00+00:00",
            },
        ],
    )

    rows = refresh_canonical_daily(index_path=index_path, output_path=output)
    assert rows[0]["canonical_snapshot_id"] == "P1"
    assert rows[0]["governance_status"] == "PASS"


def test_reject_excluded_and_warning_selected_when_no_pass(tmp_path: Path) -> None:
    index_path = tmp_path / "pis_snapshot_index.csv"
    output = tmp_path / "canonical" / "canonical_daily_snapshots.csv"
    _write_csv(
        index_path,
        _index_headers(),
        [
            {
                "snapshot_id": "R1",
                "snapshot_date": "2026-06-10",
                "account_id": "PORTFOLIO",
                "account_name": _rejected_account(),
                "source_file": "fidelity.csv",
                "source_run_id": "PAR-R",
                "source_format": "FIDELITY_CSV",
                "partition_path": "x",
                "snapshot_path": "x",
                "positions_path": "x",
                "position_count": "10",
                "portfolio_value": "2000000",
                "cash_value": "10000",
                "equity_value": "1990000",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-10T12:00:00+00:00",
            },
            {
                "snapshot_id": "W1",
                "snapshot_date": "2026-06-10",
                "account_id": "PORTFOLIO",
                "account_name": _pass_account(),
                "source_file": "audit_test.csv",
                "source_run_id": "PAR-W",
                "source_format": "FIDELITY_CSV",
                "partition_path": "x",
                "snapshot_path": "x",
                "positions_path": "x",
                "position_count": "10",
                "portfolio_value": "470000",
                "cash_value": "20000",
                "equity_value": "450000",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-10T12:05:00+00:00",
            },
        ],
    )

    rows = refresh_canonical_daily(index_path=index_path, output_path=output)
    assert rows[0]["canonical_snapshot_id"] == "W1"
    assert rows[0]["governance_status"] == "WARNING"


def test_latest_pass_selected_and_tiebreak_is_lexical(tmp_path: Path) -> None:
    index_path = tmp_path / "pis_snapshot_index.csv"
    output = tmp_path / "canonical" / "canonical_daily_snapshots.csv"
    _write_csv(
        index_path,
        _index_headers(),
        [
            {
                "snapshot_id": "PSNAP-A",
                "snapshot_date": "2026-06-09",
                "account_id": "PORTFOLIO",
                "account_name": _pass_account(),
                "source_file": "fidelity.csv",
                "source_run_id": "PAR-A",
                "source_format": "FIDELITY_CSV",
                "partition_path": "x",
                "snapshot_path": "x",
                "positions_path": "x",
                "position_count": "9",
                "portfolio_value": "468000",
                "cash_value": "18000",
                "equity_value": "450000",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-09T12:00:00+00:00",
            },
            {
                "snapshot_id": "PSNAP-B",
                "snapshot_date": "2026-06-09",
                "account_id": "PORTFOLIO",
                "account_name": _pass_account(),
                "source_file": "fidelity.csv",
                "source_run_id": "PAR-B",
                "source_format": "FIDELITY_CSV",
                "partition_path": "x",
                "snapshot_path": "x",
                "positions_path": "x",
                "position_count": "10",
                "portfolio_value": "470000",
                "cash_value": "20000",
                "equity_value": "450000",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-09T12:00:00+00:00",
            },
            {
                "snapshot_id": "PSNAP-C",
                "snapshot_date": "2026-06-09",
                "account_id": "PORTFOLIO",
                "account_name": _pass_account(),
                "source_file": "fidelity.csv",
                "source_run_id": "PAR-C",
                "source_format": "FIDELITY_CSV",
                "partition_path": "x",
                "snapshot_path": "x",
                "positions_path": "x",
                "position_count": "11",
                "portfolio_value": "472000",
                "cash_value": "22000",
                "equity_value": "450000",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-09T12:01:00+00:00",
            },
        ],
    )

    rows = refresh_canonical_daily(index_path=index_path, output_path=output)
    assert rows[0]["canonical_snapshot_id"] == "PSNAP-C"

    # Tie by timestamp should pick lexical max snapshot id.
    _write_csv(
        index_path,
        _index_headers(),
        [
            {
                "snapshot_id": "PSNAP-A",
                "snapshot_date": "2026-06-09",
                "account_id": "PORTFOLIO",
                "account_name": _pass_account(),
                "source_file": "fidelity.csv",
                "source_run_id": "PAR-A",
                "source_format": "FIDELITY_CSV",
                "partition_path": "x",
                "snapshot_path": "x",
                "positions_path": "x",
                "position_count": "9",
                "portfolio_value": "468000",
                "cash_value": "18000",
                "equity_value": "450000",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-09T12:00:00+00:00",
            },
            {
                "snapshot_id": "PSNAP-B",
                "snapshot_date": "2026-06-09",
                "account_id": "PORTFOLIO",
                "account_name": _pass_account(),
                "source_file": "fidelity.csv",
                "source_run_id": "PAR-B",
                "source_format": "FIDELITY_CSV",
                "partition_path": "x",
                "snapshot_path": "x",
                "positions_path": "x",
                "position_count": "10",
                "portfolio_value": "470000",
                "cash_value": "20000",
                "equity_value": "450000",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-09T12:00:00+00:00",
            },
        ],
    )
    tie_rows = refresh_canonical_daily(index_path=index_path, output_path=output)
    assert tie_rows[0]["canonical_snapshot_id"] == "PSNAP-B"


def test_canonical_persistence_and_api_payloads(tmp_path: Path) -> None:
    index_path = tmp_path / "pis_snapshot_index.csv"
    output = tmp_path / "canonical" / "canonical_daily_snapshots.csv"
    _write_csv(
        index_path,
        _index_headers(),
        [
            {
                "snapshot_id": "PSNAP-1",
                "snapshot_date": "2026-06-11",
                "account_id": "PORTFOLIO",
                "account_name": _pass_account(),
                "source_file": "fidelity.csv",
                "source_run_id": "PAR-1",
                "source_format": "FIDELITY_CSV",
                "partition_path": "x",
                "snapshot_path": "x",
                "positions_path": "x",
                "position_count": "10",
                "portfolio_value": "470000",
                "cash_value": "20000",
                "equity_value": "450000",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-11T12:00:00+00:00",
            }
        ],
    )

    history = pis_canonical_history(index_path=index_path, output_path=output)
    latest = pis_canonical_latest(index_path=index_path, output_path=output)
    summary = pis_canonical_summary(index_path=index_path, output_path=output)
    selected_rows = canonical_selected_index_rows(index_path=index_path, output_path=output)

    assert output.exists()
    assert set(history.keys()) == {"generated_at_utc", "history"}
    assert set(latest.keys()) == {"generated_at_utc", "latest"}
    assert set(summary.keys()) == {
        "generated_at_utc",
        "total_dates",
        "selected_dates",
        "unselected_dates",
        "selected_status_counts",
    }
    assert len(selected_rows) == 1
