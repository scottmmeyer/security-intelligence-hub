from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from src.history.base_universe_manager import append_base_universe_rows
from src.history.signal_snapshot_manager import append_signal_snapshots
from src.validation.persistence_validator import validate_ess_stage_persistence


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    headers = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _sample_signal_record() -> dict[str, object]:
    return {
        "snapshot_date": "2026-05-13",
        "provider": "FIDELITY",
        "source_file": "sample.csv",
        "symbol": "AAPL",
        "coverage_domain": "STARMINE_COVERED",
        "signal_coverage_status": "COVERED",
        "starmine_ess_text": "VERY_BULLISH",
        "starmine_ess_numeric": 5.0,
        "starmine_ess_numeric_estimated": True,
        "starmine_ess_source_type": "TEXT_MAPPED",
    }


def _sample_base_universe_row(run_id: str) -> dict[str, object]:
    return {
        "symbol": "AAPL",
        "company_name": "Apple Inc",
        "security_type": "Common Stock",
        "geography": "UNKNOWN",
        "market_cap_raw_usd": 3000000000000,
        "market_cap_bucket": "MEGA",
        "coverage_domain": "STARMINE_COVERED",
        "starmine_ess_text": "VERY_BULLISH",
        "provider": "FIDELITY",
        "source_file": "sample.csv",
        "snapshot_date": "2026-05-13",
        "run_id": run_id,
        "provider_schema_version": "Fidelity.v1",
        "provider_column_lineage": {"symbol": "Symbol"},
        "unmapped_provider_columns": [],
    }


def test_persistence_validator_passes_with_matching_partitioned_counts(tmp_path: Path) -> None:
    current_root = tmp_path / "data" / "current"
    signal_history_root = tmp_path / "data" / "history" / "signals"
    universe_history_root = tmp_path / "data" / "history" / "universe"
    signal_index_path = tmp_path / "data" / "history" / "signal_index.csv"
    universe_index_path = tmp_path / "data" / "history" / "universe_index.csv"
    run_id = "RUN-PERSIST-001"

    append_signal_snapshots(
        normalized_records=[_sample_signal_record()],
        run_id=run_id,
        current_root=current_root,
        history_root=signal_history_root,
        index_path=signal_index_path,
    )
    append_base_universe_rows(
        base_rows=[_sample_base_universe_row(run_id)],
        run_id=run_id,
        current_root=current_root,
        history_root=universe_history_root,
        index_path=universe_index_path,
    )

    result = validate_ess_stage_persistence(
        run_id=run_id,
        snapshot_date=date(2026, 5, 13).isoformat(),
        expected_signal_rows=1,
        expected_base_universe_rows=1,
        current_root=current_root,
        signal_history_root=signal_history_root,
        universe_history_root=universe_history_root,
        signal_index_path=signal_index_path,
        universe_index_path=universe_index_path,
    )

    assert result.errors == []
    assert result.signal_rows_persisted == 1
    assert result.base_universe_rows_persisted == 1
    assert all(check.match for check in result.checks)


def test_persistence_validator_detects_row_count_mismatch(tmp_path: Path) -> None:
    current_root = tmp_path / "data" / "current"
    signal_history_root = tmp_path / "data" / "history" / "signals"
    universe_history_root = tmp_path / "data" / "history" / "universe"
    signal_index_path = tmp_path / "data" / "history" / "signal_index.csv"
    universe_index_path = tmp_path / "data" / "history" / "universe_index.csv"
    run_id = "RUN-PERSIST-002"

    append_signal_snapshots(
        normalized_records=[_sample_signal_record()],
        run_id=run_id,
        current_root=current_root,
        history_root=signal_history_root,
        index_path=signal_index_path,
    )
    append_base_universe_rows(
        base_rows=[_sample_base_universe_row(run_id)],
        run_id=run_id,
        current_root=current_root,
        history_root=universe_history_root,
        index_path=universe_index_path,
    )

    result = validate_ess_stage_persistence(
        run_id=run_id,
        snapshot_date=date(2026, 5, 13).isoformat(),
        expected_signal_rows=2,
        expected_base_universe_rows=1,
        current_root=current_root,
        signal_history_root=signal_history_root,
        universe_history_root=universe_history_root,
        signal_index_path=signal_index_path,
        universe_index_path=universe_index_path,
    )

    assert any("partition/signal_snapshots.csv: persisted run-row count mismatch" in err for err in result.errors)


def test_persistence_validator_detects_missing_index_entry(tmp_path: Path) -> None:
    current_root = tmp_path / "data" / "current"
    signal_history_root = tmp_path / "data" / "history" / "signals"
    universe_history_root = tmp_path / "data" / "history" / "universe"
    signal_index_path = tmp_path / "data" / "history" / "signal_index.csv"
    universe_index_path = tmp_path / "data" / "history" / "universe_index.csv"
    run_id = "RUN-PERSIST-003"

    append_signal_snapshots(
        normalized_records=[_sample_signal_record()],
        run_id=run_id,
        current_root=current_root,
        history_root=signal_history_root,
        index_path=signal_index_path,
    )
    append_base_universe_rows(
        base_rows=[_sample_base_universe_row(run_id)],
        run_id=run_id,
        current_root=current_root,
        history_root=universe_history_root,
        index_path=universe_index_path,
    )

    signal_index_path.unlink()

    result = validate_ess_stage_persistence(
        run_id=run_id,
        snapshot_date=date(2026, 5, 13).isoformat(),
        expected_signal_rows=1,
        expected_base_universe_rows=1,
        current_root=current_root,
        signal_history_root=signal_history_root,
        universe_history_root=universe_history_root,
        signal_index_path=signal_index_path,
        universe_index_path=universe_index_path,
    )

    assert any("signal_index.csv: required index file does not exist" in err for err in result.errors)


def test_persistence_validator_detects_missing_lineage_fields(tmp_path: Path) -> None:
    current_root = tmp_path / "data" / "current"
    signal_history_root = tmp_path / "data" / "history" / "signals"
    universe_history_root = tmp_path / "data" / "history" / "universe"
    signal_index_path = tmp_path / "data" / "history" / "signal_index.csv"
    universe_index_path = tmp_path / "data" / "history" / "universe_index.csv"
    run_id = "RUN-PERSIST-004"

    append_signal_snapshots(
        normalized_records=[_sample_signal_record()],
        run_id=run_id,
        current_root=current_root,
        history_root=signal_history_root,
        index_path=signal_index_path,
    )
    append_base_universe_rows(
        base_rows=[_sample_base_universe_row(run_id)],
        run_id=run_id,
        current_root=current_root,
        history_root=universe_history_root,
        index_path=universe_index_path,
    )

    signal_partition_path = (
        signal_history_root / "snapshot_date=2026-05-13" / "run_id=RUN-PERSIST-004" / "signal_snapshots.csv"
    )
    rows = _read_rows(signal_partition_path)
    rows[0]["provider"] = ""
    _write_rows(signal_partition_path, rows)

    result = validate_ess_stage_persistence(
        run_id=run_id,
        snapshot_date=date(2026, 5, 13).isoformat(),
        expected_signal_rows=1,
        expected_base_universe_rows=1,
        current_root=current_root,
        signal_history_root=signal_history_root,
        universe_history_root=universe_history_root,
        signal_index_path=signal_index_path,
        universe_index_path=universe_index_path,
    )

    assert any("missing required lineage fields" in err for err in result.errors)


def test_persistence_validator_allows_merged_current_signal_row_count(tmp_path: Path) -> None:
    current_root = tmp_path / "data" / "current"
    signal_history_root = tmp_path / "data" / "history" / "signals"
    universe_history_root = tmp_path / "data" / "history" / "universe"
    signal_index_path = tmp_path / "data" / "history" / "signal_index.csv"
    universe_index_path = tmp_path / "data" / "history" / "universe_index.csv"
    run_id = "RUN-PERSIST-MERGE-001"

    # Same symbol appears in two coverage domains; partition row count is 2,
    # but current merged snapshot keeps only the preferred STARMINE_COVERED row.
    records = [
        _sample_signal_record(),
        {
            **_sample_signal_record(),
            "coverage_domain": "NON_STARMINE_ANALYST",
            "signal_coverage_status": "NON_COVERED",
            "starmine_ess_text": "",
            "starmine_ess_numeric": "",
            "starmine_ess_numeric_estimated": False,
            "starmine_ess_source_type": "UNKNOWN",
        },
    ]

    append_signal_snapshots(
        normalized_records=records,
        run_id=run_id,
        current_root=current_root,
        history_root=signal_history_root,
        index_path=signal_index_path,
    )
    append_base_universe_rows(
        base_rows=[
            _sample_base_universe_row(run_id),
            {
                **_sample_base_universe_row(run_id),
                "coverage_domain": "NON_STARMINE_ANALYST",
            },
        ],
        run_id=run_id,
        current_root=current_root,
        history_root=universe_history_root,
        index_path=universe_index_path,
    )

    result = validate_ess_stage_persistence(
        run_id=run_id,
        snapshot_date=date(2026, 5, 13).isoformat(),
        expected_signal_rows=2,
        expected_base_universe_rows=2,
        current_root=current_root,
        signal_history_root=signal_history_root,
        universe_history_root=universe_history_root,
        signal_index_path=signal_index_path,
        universe_index_path=universe_index_path,
    )

    assert result.errors == []
    assert result.signal_rows_persisted == 2
