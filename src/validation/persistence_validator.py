"""Deterministic physical persistence validation for partitioned ESS outputs."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from src.history.base_universe_manager import build_base_universe_storage_paths
from src.history.signal_snapshot_manager import build_signal_storage_paths

PERSISTED_REQUIRED_FIELDS: tuple[str, ...] = (
    "run_id",
    "snapshot_date",
    "created_at_utc",
    "provider",
    "source_file",
)


@dataclass(frozen=True)
class ArtifactPersistenceCheck:
    """Physical persistence check result for a single artifact."""

    artifact_name: str
    artifact_path: str
    exists: bool
    physical_row_count: int
    run_row_count: int
    manifest_count: int
    match: bool


@dataclass(frozen=True)
class PersistenceValidationResult:
    """Aggregated persistence validation result across ESS artifacts."""

    checks: List[ArtifactPersistenceCheck]
    errors: List[str]
    warnings: List[str]
    signal_rows_persisted: int
    base_universe_rows_persisted: int


@dataclass(frozen=True)
class _ArtifactSpec:
    artifact_name: str
    artifact_path: Path
    expected_manifest_count: int
    require_partition_run_isolation: bool
    enforce_manifest_count_match: bool = True


def _read_csv_rows(path: Path) -> tuple[List[Dict[str, str]], int]:
    malformed_rows = 0
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if None in row:
                malformed_rows += 1
            rows.append(dict(row))
    return rows, malformed_rows


def _assert_required_fields(
    *,
    artifact_name: str,
    run_rows: Iterable[Dict[str, str]],
    expected_snapshot_date: str,
) -> List[str]:
    errors: List[str] = []
    for row_number, row in enumerate(run_rows, start=1):
        missing = [field for field in PERSISTED_REQUIRED_FIELDS if not str(row.get(field, "")).strip()]
        if missing:
            errors.append(
                f"{artifact_name}: missing required lineage fields at run-row {row_number}: {', '.join(sorted(missing))}."
            )
        row_snapshot = str(row.get("snapshot_date", "")).strip()
        if row_snapshot and row_snapshot != expected_snapshot_date:
            errors.append(
                f"{artifact_name}: snapshot_date mismatch at run-row {row_number}: "
                f"expected {expected_snapshot_date}, observed {row_snapshot}."
            )
    return errors


def _assert_append_integrity(*, artifact_name: str, run_rows: Iterable[Dict[str, str]]) -> List[str]:
    errors: List[str] = []
    rows = [dict(row) for row in run_rows]
    if not rows:
        return errors

    if "lineage_id" in rows[0]:
        seen_lineage_ids: set[str] = set()
        for row in rows:
            lineage_id = str(row.get("lineage_id", ""))
            if lineage_id in seen_lineage_ids:
                errors.append(
                    f"{artifact_name}: append integrity failure, duplicate lineage_id={lineage_id}."
                )
            seen_lineage_ids.add(lineage_id)

    required_snapshot_key_fields = {
        "run_id",
        "snapshot_date",
        "provider",
        "source_file",
        "symbol",
        "coverage_domain",
    }
    if required_snapshot_key_fields.issubset(set(rows[0].keys())):
        seen_snapshot_keys: set[tuple[str, str, str, str, str, str]] = set()
        for row in rows:
            snapshot_key = (
                str(row.get("run_id", "")),
                str(row.get("snapshot_date", "")),
                str(row.get("provider", "")),
                str(row.get("source_file", "")),
                str(row.get("symbol", "")),
                str(row.get("coverage_domain", "")),
            )
            if snapshot_key in seen_snapshot_keys:
                errors.append(
                    f"{artifact_name}: append integrity failure, duplicate run-scoped snapshot key for "
                    f"symbol={snapshot_key[4]} coverage_domain={snapshot_key[5]}."
                )
            seen_snapshot_keys.add(snapshot_key)

    return errors


def _validate_index_row(
    *,
    index_name: str,
    index_path: Path,
    run_id: str,
    snapshot_date: str,
    expected_count: int,
    required_path_fields: tuple[str, ...],
) -> List[str]:
    errors: List[str] = []

    if not index_path.exists():
        return [f"{index_name}: required index file does not exist at {index_path}."]

    rows, malformed_rows = _read_csv_rows(index_path)
    if malformed_rows:
        errors.append(
            f"{index_name}: malformed index rows detected (count={malformed_rows}); overflow columns found."
        )

    run_rows = [row for row in rows if str(row.get("run_id", "")) == run_id]
    if not run_rows:
        errors.append(f"{index_name}: missing index row for run_id={run_id}.")
        return errors

    if len(run_rows) > 1:
        errors.append(f"{index_name}: duplicate index rows for run_id={run_id} (count={len(run_rows)}).")

    row = run_rows[0]
    if str(row.get("snapshot_date", "")) != snapshot_date:
        errors.append(
            f"{index_name}: snapshot_date mismatch for run_id={run_id}: "
            f"expected {snapshot_date}, observed {row.get('snapshot_date', '')}."
        )

    if not str(row.get("created_at_utc", "")).strip():
        errors.append(f"{index_name}: created_at_utc is required for run_id={run_id}.")

    observed_count_raw = str(row.get("row_count", "")).strip()
    try:
        observed_count = int(observed_count_raw)
    except ValueError:
        errors.append(f"{index_name}: row_count must be integer for run_id={run_id}; observed={observed_count_raw}.")
        observed_count = -1

    if observed_count != expected_count:
        errors.append(
            f"{index_name}: row_count mismatch for run_id={run_id}: "
            f"expected {expected_count}, observed {observed_count}."
        )

    for field in required_path_fields:
        candidate = Path(str(row.get(field, "")).strip())
        if not candidate:
            errors.append(f"{index_name}: required field {field} is empty for run_id={run_id}.")
            continue
        if not candidate.exists():
            errors.append(
                f"{index_name}: referenced path in field {field} does not exist for run_id={run_id}: {candidate}."
            )

    return errors


def validate_ess_stage_persistence(
    *,
    run_id: str,
    snapshot_date: str,
    expected_signal_rows: int,
    expected_base_universe_rows: int,
    current_root: str | Path = "data/current",
    signal_history_root: str | Path = "data/history/signals",
    universe_history_root: str | Path = "data/history/universe",
    signal_index_path: str | Path = "data/history/signal_index.csv",
    universe_index_path: str | Path = "data/history/universe_index.csv",
) -> PersistenceValidationResult:
    """Validate partitioned persistence, counts, lineage fields, and index entries."""

    signal_paths = build_signal_storage_paths(
        snapshot_date=snapshot_date,
        run_id=run_id,
        current_root=current_root,
        history_root=signal_history_root,
        index_path=signal_index_path,
    )
    universe_paths = build_base_universe_storage_paths(
        snapshot_date=snapshot_date,
        run_id=run_id,
        current_root=current_root,
        history_root=universe_history_root,
        index_path=universe_index_path,
    )

    specs = [
        _ArtifactSpec(
            artifact_name="current/signal_snapshot.csv",
            artifact_path=signal_paths.current_signal_snapshot_path,
            expected_manifest_count=expected_signal_rows,
            require_partition_run_isolation=False,
            enforce_manifest_count_match=False,
        ),
        _ArtifactSpec(
            artifact_name="current/base_equity_universe.csv",
            artifact_path=universe_paths.current_base_universe_path,
            expected_manifest_count=expected_base_universe_rows,
            require_partition_run_isolation=False,
        ),
        _ArtifactSpec(
            artifact_name="partition/signal_snapshots.csv",
            artifact_path=signal_paths.partition_signal_snapshots_path,
            expected_manifest_count=expected_signal_rows,
            require_partition_run_isolation=True,
        ),
        _ArtifactSpec(
            artifact_name="partition/signal_lineage_registry.csv",
            artifact_path=signal_paths.partition_signal_lineage_path,
            expected_manifest_count=expected_signal_rows,
            require_partition_run_isolation=True,
        ),
        _ArtifactSpec(
            artifact_name="partition/base_equity_universe.csv",
            artifact_path=universe_paths.partition_base_universe_path,
            expected_manifest_count=expected_base_universe_rows,
            require_partition_run_isolation=True,
        ),
        _ArtifactSpec(
            artifact_name="partition/universe_lineage_registry.csv",
            artifact_path=universe_paths.partition_lineage_registry_path,
            expected_manifest_count=expected_base_universe_rows,
            require_partition_run_isolation=True,
        ),
    ]

    checks: List[ArtifactPersistenceCheck] = []
    errors: List[str] = []
    warnings: List[str] = []
    signal_rows_persisted = 0
    base_rows_persisted = 0

    for spec in specs:
        exists = spec.artifact_path.exists()
        rows: List[Dict[str, str]] = []
        malformed_rows = 0

        if not exists:
            errors.append(f"{spec.artifact_name}: required artifact file does not exist at {spec.artifact_path}.")
        else:
            rows, malformed_rows = _read_csv_rows(spec.artifact_path)

        run_rows = [row for row in rows if str(row.get("run_id", "")) == run_id]
        physical_row_count = len(rows)
        run_row_count = len(run_rows)

        if malformed_rows:
            errors.append(
                f"{spec.artifact_name}: malformed CSV rows detected (count={malformed_rows}); overflow columns found."
            )

        if spec.enforce_manifest_count_match:
            match = (
                exists
                and physical_row_count == spec.expected_manifest_count
                and run_row_count == spec.expected_manifest_count
            )
        else:
            match = exists and run_row_count > 0

        checks.append(
            ArtifactPersistenceCheck(
                artifact_name=spec.artifact_name,
                artifact_path=str(spec.artifact_path),
                exists=exists,
                physical_row_count=physical_row_count,
                run_row_count=run_row_count,
                manifest_count=spec.expected_manifest_count,
                match=match,
            )
        )

        if spec.artifact_name == "partition/signal_snapshots.csv":
            signal_rows_persisted = run_row_count
        if spec.artifact_name == "partition/base_equity_universe.csv":
            base_rows_persisted = run_row_count

        if exists and spec.enforce_manifest_count_match and physical_row_count != spec.expected_manifest_count:
            errors.append(
                f"{spec.artifact_name}: persisted physical-row count mismatch: "
                f"manifest={spec.expected_manifest_count}, persisted={physical_row_count}."
            )

        if exists and spec.enforce_manifest_count_match and run_row_count != spec.expected_manifest_count:
            errors.append(
                f"{spec.artifact_name}: persisted run-row count mismatch: "
                f"manifest={spec.expected_manifest_count}, persisted={run_row_count}."
            )

        if exists and spec.require_partition_run_isolation and physical_row_count != run_row_count:
            errors.append(
                f"{spec.artifact_name}: partition run isolation failed; observed rows from other run_ids "
                f"(physical={physical_row_count}, run_scoped={run_row_count})."
            )

        if exists:
            errors.extend(
                _assert_required_fields(
                    artifact_name=spec.artifact_name,
                    run_rows=run_rows,
                    expected_snapshot_date=snapshot_date,
                )
            )
            errors.extend(
                _assert_append_integrity(
                    artifact_name=spec.artifact_name,
                    run_rows=run_rows,
                )
            )

    errors.extend(
        _validate_index_row(
            index_name="signal_index.csv",
            index_path=signal_paths.index_path,
            run_id=run_id,
            snapshot_date=snapshot_date,
            expected_count=expected_signal_rows,
            required_path_fields=("partition_path", "signal_snapshots_path", "signal_lineage_registry_path"),
        )
    )
    errors.extend(
        _validate_index_row(
            index_name="universe_index.csv",
            index_path=universe_paths.index_path,
            run_id=run_id,
            snapshot_date=snapshot_date,
            expected_count=expected_base_universe_rows,
            required_path_fields=(
                "partition_path",
                "base_equity_universe_path",
                "universe_lineage_registry_path",
            ),
        )
    )

    return PersistenceValidationResult(
        checks=checks,
        errors=errors,
        warnings=warnings,
        signal_rows_persisted=signal_rows_persisted,
        base_universe_rows_persisted=base_rows_persisted,
    )
