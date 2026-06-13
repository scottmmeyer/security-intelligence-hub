from __future__ import annotations

import csv
from pathlib import Path

from src.pis.governance import (
    SnapshotGovernanceConfig,
    build_snapshot_governance_rows,
    evaluate_snapshot_governance,
    pis_governance_latest,
    pis_governance_summary,
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


def test_expected_scope_pass() -> None:
    row = {
        "account_name": "General Brokerage, Joint WROS - TOD, Individual - TOD",
        "portfolio_value": "472000.12",
        "source_file": "fidelity_may30.csv",
    }

    result = evaluate_snapshot_governance(row)
    assert result["status"] == "PASS"
    assert result["scope_valid"] is True
    assert result["value_valid"] is True
    assert result["source_valid"] is True
    assert result["reasons"] == []


def test_contaminated_scope_reject() -> None:
    row = {
        "account_name": "General Brokerage, Joint WROS - TOD, Individual - TOD, FIS 401(K) PLAN, BrokerageLink",
        "portfolio_value": "472000.12",
        "source_file": "fidelity_may30.csv",
    }

    result = evaluate_snapshot_governance(row)
    assert result["status"] == "REJECT"
    assert result["scope_valid"] is False
    assert "SCOPE_DISALLOWED_ACCOUNT_CLASS" in result["reasons"]


def test_value_warning_band() -> None:
    row = {
        "account_name": "General Brokerage, Joint WROS - TOD, Individual - TOD",
        "portfolio_value": "700000",
        "source_file": "fidelity_may30.csv",
    }

    result = evaluate_snapshot_governance(row)
    assert result["status"] == "WARNING"
    assert result["value_valid"] is True
    assert "VALUE_IN_WARNING_BAND" in result["reasons"]


def test_value_reject_band() -> None:
    row = {
        "account_name": "General Brokerage, Joint WROS - TOD, Individual - TOD",
        "portfolio_value": "750000.01",
        "source_file": "fidelity_may30.csv",
    }

    result = evaluate_snapshot_governance(row)
    assert result["status"] == "REJECT"
    assert result["value_valid"] is False
    assert "VALUE_EXCEEDS_REJECT_THRESHOLD" in result["reasons"]


def test_source_artifact_warning() -> None:
    row = {
        "account_name": "General Brokerage, Joint WROS - TOD, Individual - TOD",
        "portfolio_value": "472000.12",
        "source_file": "audit_test.csv",
    }

    result = evaluate_snapshot_governance(row)
    assert result["status"] == "WARNING"
    assert result["source_valid"] is False
    assert "SOURCE_TEST_OR_BACKFILL_ARTIFACT" in result["reasons"]


def test_combined_rule_evaluation_reject_precedence() -> None:
    row = {
        "account_name": "General Brokerage, Joint WROS - TOD, Individual - TOD, BrokerageLink Roth",
        "portfolio_value": "2000000",
        "source_file": "test.csv",
    }

    result = evaluate_snapshot_governance(row)
    assert result["status"] == "REJECT"
    assert "SCOPE_DISALLOWED_ACCOUNT_CLASS" in result["reasons"]
    assert "VALUE_EXCEEDS_REJECT_THRESHOLD" in result["reasons"]
    assert "SOURCE_TEST_OR_BACKFILL_ARTIFACT" in result["reasons"]


def test_configurable_thresholds() -> None:
    config = SnapshotGovernanceConfig(value_pass_max=500000, value_reject_gt=650000)
    row = {
        "account_name": "General Brokerage, Joint WROS - TOD, Individual - TOD",
        "portfolio_value": "640000",
        "source_file": "fidelity_may30.csv",
    }

    result = evaluate_snapshot_governance(row, config=config)
    assert result["status"] == "WARNING"


def test_api_payload_validation_and_persistence(tmp_path: Path) -> None:
    index_path = tmp_path / "pis_snapshot_index.csv"
    governance_path = tmp_path / "governance" / "snapshot_governance.csv"
    _write_csv(
        index_path,
        _index_headers(),
        [
            {
                "snapshot_id": "PSNAP-1",
                "snapshot_date": "2026-06-11",
                "account_id": "PORTFOLIO",
                "account_name": "General Brokerage, Joint WROS - TOD, Individual - TOD",
                "source_file": "fidelity.csv",
                "source_run_id": "PAR-1",
                "source_format": "FIDELITY_CSV",
                "partition_path": "x",
                "snapshot_path": "x",
                "positions_path": "x",
                "position_count": "12",
                "portfolio_value": "470000",
                "cash_value": "20000",
                "equity_value": "450000",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-11T12:00:00+00:00",
            },
            {
                "snapshot_id": "PSNAP-2",
                "snapshot_date": "2026-06-11",
                "account_id": "PORTFOLIO",
                "account_name": "General Brokerage, Joint WROS - TOD, Individual - TOD",
                "source_file": "upload.csv",
                "source_run_id": "PAR-2",
                "source_format": "FIDELITY_CSV",
                "partition_path": "x",
                "snapshot_path": "x",
                "positions_path": "x",
                "position_count": "12",
                "portfolio_value": "700000",
                "cash_value": "20000",
                "equity_value": "680000",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-11T12:05:00+00:00",
            },
            {
                "snapshot_id": "PSNAP-3",
                "snapshot_date": "2026-06-10",
                "account_id": "PORTFOLIO",
                "account_name": "General Brokerage, Joint WROS - TOD, Individual - TOD, FIS 401(K) PLAN, BrokerageLink",
                "source_file": "fidelity.csv",
                "source_run_id": "PAR-3",
                "source_format": "FIDELITY_CSV",
                "partition_path": "x",
                "snapshot_path": "x",
                "positions_path": "x",
                "position_count": "12",
                "portfolio_value": "1900000",
                "cash_value": "20000",
                "equity_value": "1880000",
                "ingestion_status": "PARTIAL",
                "created_at_utc": "2026-06-10T12:00:00+00:00",
            },
        ],
    )

    latest = pis_governance_latest(index_path=index_path, output_path=governance_path)
    summary = pis_governance_summary(index_path=index_path, output_path=governance_path)

    assert set(latest.keys()) == {"generated_at_utc", "latest_snapshot_date", "status_counts", "snapshots"}
    assert set(summary.keys()) == {"generated_at_utc", "total_snapshots", "status_counts", "daily"}
    assert summary["total_snapshots"] == 3
    assert summary["status_counts"] == {"PASS": 1, "WARNING": 1, "REJECT": 1}

    rows = build_snapshot_governance_rows(index_path=index_path)
    assert len(rows) == 3
    assert governance_path.exists()
