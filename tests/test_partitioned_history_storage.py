from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.history.base_universe_manager import append_base_universe_rows, build_base_universe_storage_paths
from src.history.signal_snapshot_manager import append_signal_snapshots, build_signal_storage_paths


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _signal_record(symbol: str) -> dict[str, object]:
    return {
        "snapshot_date": "2026-05-13",
        "provider": "FIDELITY",
        "source_file": "fixture.csv",
        "symbol": symbol,
        "coverage_domain": "STARMINE_COVERED",
        "signal_coverage_status": "COVERED",
        "starmine_ess_text": "BULLISH",
        "starmine_ess_numeric": 4.0,
        "starmine_ess_numeric_estimated": True,
        "starmine_ess_source_type": "TEXT_MAPPED",
    }


def _base_row(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "company_name": f"{symbol} Corp",
        "security_type": "Common Stock",
        "geography": "UNKNOWN",
        "market_cap_raw_usd": 123456789,
        "market_cap_bucket": "LARGE",
        "coverage_domain": "STARMINE_COVERED",
        "starmine_ess_text": "BULLISH",
        "provider": "FIDELITY",
        "source_file": "fixture.csv",
        "snapshot_date": "2026-05-13",
        "provider_schema_version": "Fidelity.v1",
        "provider_column_lineage": {"symbol": "Symbol"},
        "unmapped_provider_columns": [],
    }


def test_partition_path_generation_for_signal_and_base() -> None:
    signal_paths = build_signal_storage_paths(
        snapshot_date="2026-05-13",
        run_id="RUN-UNIT-001",
        current_root="data/current",
        history_root="data/history/signals",
        index_path="data/history/signal_index.csv",
    )
    assert str(signal_paths.current_signal_snapshot_path) == "data/current/signal_snapshot.csv"
    assert str(signal_paths.partition_dir) == "data/history/signals/snapshot_date=2026-05-13/run_id=RUN-UNIT-001"
    assert str(signal_paths.partition_signal_snapshots_path).endswith("signal_snapshots.csv")
    assert str(signal_paths.partition_signal_lineage_path).endswith("signal_lineage_registry.csv")
    assert str(signal_paths.index_path) == "data/history/signal_index.csv"

    base_paths = build_base_universe_storage_paths(
        snapshot_date="2026-05-13",
        run_id="RUN-UNIT-001",
        current_root="data/current",
        history_root="data/history/universe",
        index_path="data/history/universe_index.csv",
    )
    assert str(base_paths.current_base_universe_path) == "data/current/base_equity_universe.csv"
    assert str(base_paths.partition_dir) == "data/history/universe/snapshot_date=2026-05-13/run_id=RUN-UNIT-001"
    assert str(base_paths.partition_base_universe_path).endswith("base_equity_universe.csv")
    assert str(base_paths.partition_lineage_registry_path).endswith("universe_lineage_registry.csv")
    assert str(base_paths.index_path) == "data/history/universe_index.csv"


def test_signal_partition_is_immutable_and_current_is_overwritable(tmp_path: Path) -> None:
    current_root = tmp_path / "data" / "current"
    signal_history_root = tmp_path / "data" / "history" / "signals"
    signal_index_path = tmp_path / "data" / "history" / "signal_index.csv"

    append_signal_snapshots(
        normalized_records=[_signal_record("AAA")],
        run_id="RUN-SIGNAL-001",
        current_root=current_root,
        history_root=signal_history_root,
        index_path=signal_index_path,
    )

    with pytest.raises(ValueError, match="Immutable signal partition protection"):
        append_signal_snapshots(
            normalized_records=[_signal_record("AAA")],
            run_id="RUN-SIGNAL-001",
            current_root=current_root,
            history_root=signal_history_root,
            index_path=signal_index_path,
        )

    append_signal_snapshots(
        normalized_records=[_signal_record("BBB")],
        run_id="RUN-SIGNAL-002",
        current_root=current_root,
        history_root=signal_history_root,
        index_path=signal_index_path,
    )

    current_rows = _read_csv_rows(current_root / "signal_snapshot.csv")
    assert len(current_rows) == 1
    assert current_rows[0]["run_id"] == "RUN-SIGNAL-002"
    assert current_rows[0]["symbol"] == "BBB"

    run1_partition_rows = _read_csv_rows(
        signal_history_root / "snapshot_date=2026-05-13" / "run_id=RUN-SIGNAL-001" / "signal_snapshots.csv"
    )
    assert len(run1_partition_rows) == 1
    assert run1_partition_rows[0]["symbol"] == "AAA"

    run2_partition_rows = _read_csv_rows(
        signal_history_root / "snapshot_date=2026-05-13" / "run_id=RUN-SIGNAL-002" / "signal_snapshots.csv"
    )
    assert len(run2_partition_rows) == 1
    assert run2_partition_rows[0]["symbol"] == "BBB"

    signal_index_rows = _read_csv_rows(signal_index_path)
    assert len(signal_index_rows) == 2


def test_base_universe_partition_is_immutable_and_current_is_overwritable(tmp_path: Path) -> None:
    current_root = tmp_path / "data" / "current"
    universe_history_root = tmp_path / "data" / "history" / "universe"
    universe_index_path = tmp_path / "data" / "history" / "universe_index.csv"

    append_base_universe_rows(
        base_rows=[_base_row("AAA")],
        run_id="RUN-BASE-001",
        current_root=current_root,
        history_root=universe_history_root,
        index_path=universe_index_path,
    )

    with pytest.raises(ValueError, match="Immutable base-universe partition protection"):
        append_base_universe_rows(
            base_rows=[_base_row("AAA")],
            run_id="RUN-BASE-001",
            current_root=current_root,
            history_root=universe_history_root,
            index_path=universe_index_path,
        )

    append_base_universe_rows(
        base_rows=[_base_row("BBB")],
        run_id="RUN-BASE-002",
        current_root=current_root,
        history_root=universe_history_root,
        index_path=universe_index_path,
    )

    current_rows = _read_csv_rows(current_root / "base_equity_universe.csv")
    assert len(current_rows) == 1
    assert current_rows[0]["run_id"] == "RUN-BASE-002"
    assert current_rows[0]["symbol"] == "BBB"

    run1_partition_rows = _read_csv_rows(
        universe_history_root / "snapshot_date=2026-05-13" / "run_id=RUN-BASE-001" / "base_equity_universe.csv"
    )
    assert len(run1_partition_rows) == 1
    assert run1_partition_rows[0]["symbol"] == "AAA"

    run2_partition_rows = _read_csv_rows(
        universe_history_root / "snapshot_date=2026-05-13" / "run_id=RUN-BASE-002" / "base_equity_universe.csv"
    )
    assert len(run2_partition_rows) == 1
    assert run2_partition_rows[0]["symbol"] == "BBB"

    universe_index_rows = _read_csv_rows(universe_index_path)
    assert len(universe_index_rows) == 2
