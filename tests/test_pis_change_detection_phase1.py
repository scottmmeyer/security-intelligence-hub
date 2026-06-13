from __future__ import annotations

import csv
from pathlib import Path

from src.pis.change_detection import (
    compute_all_snapshot_changes,
    pis_change_summary,
    pis_changes_for_snapshot,
    pis_changes_latest,
)


_PASS_ACCOUNT_NAME = "General Brokerage, Joint WROS - TOD, Individual - TOD"


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _write_positions(path: Path, rows: list[dict]) -> None:
    headers = [
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
    ]
    _write_csv(path, headers, rows)


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


def _build_pair_dataset(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path
    index_path = root / "history" / "pis" / "pis_snapshot_index.csv"
    changes_root = root / "history" / "pis" / "changes"

    prior_positions_path = root / "history" / "pis" / "snapshot_date=2026-06-10" / "account_id=PORTFOLIO" / "snapshot_id=S1" / "position_snapshots.csv"
    curr_positions_path = root / "history" / "pis" / "snapshot_date=2026-06-11" / "account_id=PORTFOLIO" / "snapshot_id=S2" / "position_snapshots.csv"

    _write_positions(
        prior_positions_path,
        [
            {"snapshot_id": "S1", "snapshot_date": "2026-06-10", "account_id": "PORTFOLIO", "account_name": _PASS_ACCOUNT_NAME, "symbol": "AAPL", "description": "A", "quantity": "10", "market_value": "1000", "percent_of_account": "50", "source_percent_of_account": "50", "cost_basis_total": "900", "security_type": "Common", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "false", "source_file": "x", "created_at_utc": "2026-06-10T12:00:00+00:00"},
            {"snapshot_id": "S1", "snapshot_date": "2026-06-10", "account_id": "PORTFOLIO", "account_name": _PASS_ACCOUNT_NAME, "symbol": "MSFT", "description": "M", "quantity": "5", "market_value": "500", "percent_of_account": "25", "source_percent_of_account": "25", "cost_basis_total": "450", "security_type": "Common", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "false", "source_file": "x", "created_at_utc": "2026-06-10T12:00:00+00:00"},
            {"snapshot_id": "S1", "snapshot_date": "2026-06-10", "account_id": "PORTFOLIO", "account_name": _PASS_ACCOUNT_NAME, "symbol": "SPAXX", "description": "Cash", "quantity": "1", "market_value": "200", "percent_of_account": "10", "source_percent_of_account": "10", "cost_basis_total": "200", "security_type": "Cash", "operational_state": "CASH_EQUIVALENT", "is_cash_equivalent": "true", "source_file": "x", "created_at_utc": "2026-06-10T12:00:00+00:00"},
        ],
    )

    _write_positions(
        curr_positions_path,
        [
            {"snapshot_id": "S2", "snapshot_date": "2026-06-11", "account_id": "PORTFOLIO", "account_name": _PASS_ACCOUNT_NAME, "symbol": "AAPL", "description": "A", "quantity": "12", "market_value": "1320", "percent_of_account": "55", "source_percent_of_account": "55", "cost_basis_total": "1000", "security_type": "Common", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "false", "source_file": "x", "created_at_utc": "2026-06-11T12:00:00+00:00"},
            {"snapshot_id": "S2", "snapshot_date": "2026-06-11", "account_id": "PORTFOLIO", "account_name": _PASS_ACCOUNT_NAME, "symbol": "GOOG", "description": "G", "quantity": "4", "market_value": "800", "percent_of_account": "33", "source_percent_of_account": "33", "cost_basis_total": "700", "security_type": "Common", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "false", "source_file": "x", "created_at_utc": "2026-06-11T12:00:00+00:00"},
            {"snapshot_id": "S2", "snapshot_date": "2026-06-11", "account_id": "PORTFOLIO", "account_name": _PASS_ACCOUNT_NAME, "symbol": "SPAXX", "description": "Cash", "quantity": "1", "market_value": "120", "percent_of_account": "5", "source_percent_of_account": "5", "cost_basis_total": "120", "security_type": "Cash", "operational_state": "CASH_EQUIVALENT", "is_cash_equivalent": "true", "source_file": "x", "created_at_utc": "2026-06-11T12:00:00+00:00"},
        ],
    )

    _write_csv(
        index_path,
        _index_headers(),
        [
            {
                "snapshot_id": "S1",
                "snapshot_date": "2026-06-10",
                "account_id": "PORTFOLIO",
                "account_name": _PASS_ACCOUNT_NAME,
                "source_file": "x",
                "source_run_id": "PAR1",
                "source_format": "FIDELITY_CSV",
                "partition_path": str(prior_positions_path.parent),
                "snapshot_path": str(prior_positions_path.parent / "portfolio_snapshot.csv"),
                "positions_path": str(prior_positions_path),
                "position_count": "3",
                "portfolio_value": "1700",
                "cash_value": "200",
                "equity_value": "1500",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-10T12:00:00+00:00",
            },
            {
                "snapshot_id": "S2",
                "snapshot_date": "2026-06-11",
                "account_id": "PORTFOLIO",
                "account_name": _PASS_ACCOUNT_NAME,
                "source_file": "x",
                "source_run_id": "PAR2",
                "source_format": "FIDELITY_CSV",
                "partition_path": str(curr_positions_path.parent),
                "snapshot_path": str(curr_positions_path.parent / "portfolio_snapshot.csv"),
                "positions_path": str(curr_positions_path),
                "position_count": "3",
                "portfolio_value": "2240",
                "cash_value": "120",
                "equity_value": "2120",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-11T12:00:00+00:00",
            },
        ],
    )

    return index_path, changes_root, root


def test_new_exit_increase_reduction_no_change_and_cash_change(tmp_path: Path) -> None:
    index_path, changes_root, root = _build_pair_dataset(tmp_path)

    compute_all_snapshot_changes(index_path=index_path, changes_root=changes_root, repo_root=root)
    latest = pis_changes_latest(index_path=index_path, changes_root=changes_root, repo_root=root)

    assert latest["summary"] is not None
    assert latest["summary"]["new_holdings_count"] == 1
    assert latest["summary"]["exited_holdings_count"] == 1
    assert latest["summary"]["increased_holdings_count"] == 1
    assert latest["summary"]["reduced_holdings_count"] == 0
    assert latest["summary"]["unchanged_holdings_count"] == 1
    assert latest["summary"]["cash_change"] == -80.0

    assert [row["symbol"] for row in latest["new_positions"]] == ["GOOG"]
    assert [row["symbol"] for row in latest["exited_positions"]] == ["MSFT"]
    assert [row["symbol"] for row in latest["increased_positions"]] == ["AAPL"]
    assert latest["reduced_positions"] == []
    assert [row["symbol"] for row in latest["unchanged_positions"]] == ["SPAXX"]


def test_no_change_detection(tmp_path: Path) -> None:
    index_path, changes_root, root = _build_pair_dataset(tmp_path)

    # add unchanged symbol in both snapshots
    p1 = tmp_path / "history" / "pis" / "snapshot_date=2026-06-10" / "account_id=PORTFOLIO" / "snapshot_id=S1" / "position_snapshots.csv"
    p2 = tmp_path / "history" / "pis" / "snapshot_date=2026-06-11" / "account_id=PORTFOLIO" / "snapshot_id=S2" / "position_snapshots.csv"
    for path in (p1, p2):
        rows = list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))
        rows.append({"snapshot_id": rows[0]["snapshot_id"], "snapshot_date": rows[0]["snapshot_date"], "account_id": "PORTFOLIO", "account_name": _PASS_ACCOUNT_NAME, "symbol": "QQQ", "description": "Q", "quantity": "2", "market_value": "200", "percent_of_account": "5", "source_percent_of_account": "5", "cost_basis_total": "180", "security_type": "ETF", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "false", "source_file": "x", "created_at_utc": rows[0]["created_at_utc"]})
        _write_positions(path, rows)

    compute_all_snapshot_changes(index_path=index_path, changes_root=changes_root, repo_root=root)
    latest = pis_changes_latest(index_path=index_path, changes_root=changes_root, repo_root=root)
    assert latest["summary"]["unchanged_holdings_count"] == 2
    assert "QQQ" in [row["symbol"] for row in latest["unchanged_positions"]]


def test_canonical_daily_prefers_latest_ingestion_snapshot(tmp_path: Path) -> None:
    index_path, changes_root, root = _build_pair_dataset(tmp_path)

    # add second account rows for both dates
    p1b = tmp_path / "history" / "pis" / "snapshot_date=2026-06-10" / "account_id=IRA" / "snapshot_id=S1B" / "position_snapshots.csv"
    p2b = tmp_path / "history" / "pis" / "snapshot_date=2026-06-11" / "account_id=IRA" / "snapshot_id=S2B" / "position_snapshots.csv"

    _write_positions(p1b, [{"snapshot_id": "S1B", "snapshot_date": "2026-06-10", "account_id": "IRA", "account_name": _PASS_ACCOUNT_NAME, "symbol": "TSLA", "description": "T", "quantity": "1", "market_value": "300", "percent_of_account": "100", "source_percent_of_account": "100", "cost_basis_total": "250", "security_type": "Common", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "false", "source_file": "x", "created_at_utc": "2026-06-10T12:00:00+00:00"}])
    _write_positions(p2b, [{"snapshot_id": "S2B", "snapshot_date": "2026-06-11", "account_id": "IRA", "account_name": _PASS_ACCOUNT_NAME, "symbol": "TSLA", "description": "T", "quantity": "3", "market_value": "960", "percent_of_account": "100", "source_percent_of_account": "100", "cost_basis_total": "700", "security_type": "Common", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "false", "source_file": "x", "created_at_utc": "2026-06-11T12:00:00+00:00"}])

    rows = list(csv.DictReader(index_path.open("r", encoding="utf-8", newline="")))
    rows.extend(
        [
            {
                "snapshot_id": "S1B", "snapshot_date": "2026-06-10", "account_id": "IRA", "account_name": _PASS_ACCOUNT_NAME, "source_file": "x", "source_run_id": "PAR1B", "source_format": "FIDELITY_CSV", "partition_path": str(p1b.parent), "snapshot_path": str(p1b.parent / "portfolio_snapshot.csv"), "positions_path": str(p1b), "position_count": "1", "portfolio_value": "300", "cash_value": "0", "equity_value": "300", "ingestion_status": "PARTIAL", "created_at_utc": "2026-06-10T12:05:00+00:00",
            },
            {
                "snapshot_id": "S2B", "snapshot_date": "2026-06-11", "account_id": "IRA", "account_name": _PASS_ACCOUNT_NAME, "source_file": "x", "source_run_id": "PAR2B", "source_format": "FIDELITY_CSV", "partition_path": str(p2b.parent), "snapshot_path": str(p2b.parent / "portfolio_snapshot.csv"), "positions_path": str(p2b), "position_count": "1", "portfolio_value": "960", "cash_value": "0", "equity_value": "960", "ingestion_status": "PARTIAL", "created_at_utc": "2026-06-11T12:05:00+00:00",
            },
        ]
    )
    _write_csv(index_path, _index_headers(), rows)

    compute_all_snapshot_changes(index_path=index_path, changes_root=changes_root, repo_root=root)
    latest = pis_changes_latest(index_path=index_path, changes_root=changes_root, repo_root=root)

    assert latest["summary"]["increased_holdings_count"] == 1
    assert [row["symbol"] for row in latest["increased_positions"]] == ["TSLA"]


def test_snapshot_ordering_correctness(tmp_path: Path) -> None:
    index_path, changes_root, root = _build_pair_dataset(tmp_path)

    # add older date to ensure latest compares 06-11 vs 06-10
    old_positions = tmp_path / "history" / "pis" / "snapshot_date=2026-06-09" / "account_id=PORTFOLIO" / "snapshot_id=S0" / "position_snapshots.csv"
    _write_positions(old_positions, [{"snapshot_id": "S0", "snapshot_date": "2026-06-09", "account_id": "PORTFOLIO", "account_name": _PASS_ACCOUNT_NAME, "symbol": "AAPL", "description": "A", "quantity": "9", "market_value": "900", "percent_of_account": "100", "source_percent_of_account": "100", "cost_basis_total": "850", "security_type": "Common", "operational_state": "ACTIVE_POSITION", "is_cash_equivalent": "false", "source_file": "x", "created_at_utc": "2026-06-09T12:00:00+00:00"}])

    rows = list(csv.DictReader(index_path.open("r", encoding="utf-8", newline="")))
    rows.append({"snapshot_id": "S0", "snapshot_date": "2026-06-09", "account_id": "PORTFOLIO", "account_name": _PASS_ACCOUNT_NAME, "source_file": "x", "source_run_id": "PAR0", "source_format": "FIDELITY_CSV", "partition_path": str(old_positions.parent), "snapshot_path": str(old_positions.parent / "portfolio_snapshot.csv"), "positions_path": str(old_positions), "position_count": "1", "portfolio_value": "900", "cash_value": "0", "equity_value": "900", "ingestion_status": "PARTIAL", "created_at_utc": "2026-06-09T12:00:00+00:00"})
    # shuffle order intentionally
    rows = [rows[2], rows[0], rows[1]]
    _write_csv(index_path, _index_headers(), rows)

    compute_all_snapshot_changes(index_path=index_path, changes_root=changes_root, repo_root=root)
    latest = pis_changes_latest(index_path=index_path, changes_root=changes_root, repo_root=root)
    assert latest["summary"]["snapshot_date"] == "2026-06-11"
    assert latest["summary"]["prior_snapshot_date"] == "2026-06-10"


def test_api_payload_shapes_and_empty_history_behavior(tmp_path: Path) -> None:
    index_path = tmp_path / "history" / "pis" / "pis_snapshot_index.csv"
    _write_csv(index_path, _index_headers(), [])
    changes_root = tmp_path / "history" / "pis" / "changes"

    latest_empty = pis_changes_latest(index_path=index_path, changes_root=changes_root, repo_root=tmp_path)
    summary_empty = pis_change_summary(index_path=index_path, changes_root=changes_root, repo_root=tmp_path)
    assert latest_empty["summary"] is None
    assert summary_empty["summary"] == []

    # now populate and assert endpoint-like payload fields exist
    index_path, changes_root, root = _build_pair_dataset(tmp_path / "filled")
    compute_all_snapshot_changes(index_path=index_path, changes_root=changes_root, repo_root=root)

    summary = pis_change_summary(index_path=index_path, changes_root=changes_root, repo_root=root)
    assert len(summary["summary"]) == 1
    snapshot_id = summary["summary"][0]["snapshot_id"]
    detail = pis_changes_for_snapshot(snapshot_id, index_path=index_path, changes_root=changes_root, repo_root=root)

    assert "summary" in detail
    assert "new_positions" in detail
    assert "exited_positions" in detail
    assert "increased_positions" in detail
    assert "reduced_positions" in detail


def test_run_outcome_ui_contains_change_api_routes() -> None:
    root = Path(__file__).resolve().parents[1]
    server_py = (root / "scripts" / "run_outcome_ui.py").read_text(encoding="utf-8")

    assert "/api/pis/changes/latest" in server_py
    assert "/api/pis/changes/" in server_py
    assert "/api/pis/change-summary" in server_py
