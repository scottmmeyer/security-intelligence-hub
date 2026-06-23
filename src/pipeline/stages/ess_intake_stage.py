"""ESS intake stage scaffolding for sequential pipeline execution."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import yaml

from src.history.base_universe_manager import (
    append_base_universe_rows,
    build_base_universe_storage_paths,
    ensure_base_universe_contracts,
)
from src.history.signal_snapshot_manager import (
    append_signal_snapshots,
    build_signal_storage_paths,
    ensure_signal_history_contracts,
)
from src.models.pipeline_models import ArtifactRecord, PipelineStatus
from src.normalize.provider_normalizer import normalize_fidelity_ess_file
from src.portfolio.ess_coverage import build_ess_coverage_gap_warning, write_ess_coverage_warning
from src.portfolio.fidelity_signal import load_fidelity_signals
from src.pipeline.stage_registry import StageContext, StageExecutionOutput
from src.validation.intake_readiness_validator import (
    INTAKE_OPERATOR_GUIDANCE,
    validate_intake_readiness,
)
from src.validation.persistence_validator import validate_ess_stage_persistence


def _load_coverage_config(config_path: str | Path = "config/coverage_domains.yaml") -> Dict[str, object]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("coverage_domains.yaml must contain a mapping root.")
    return config


def _discover_csv_files(base_path: str | Path) -> List[Path]:
    path = Path(base_path)
    if not path.exists():
        return []
    return sorted(p for p in path.glob("*.csv") if p.is_file())


def _cleanup_processed_intake_files(
    discovered: Dict[str, List[Path]],
) -> tuple[List[str], List[str]]:
    """Delete successfully processed intake files. Returns (cleaned_paths, failed_paths)."""
    cleaned: List[str] = []
    failed: List[str] = []
    for files in discovered.values():
        for file_path in files:
            try:
                file_path.unlink()
                cleaned.append(str(file_path))
            except Exception as exc:
                failed.append(f"{file_path}: {exc}")
    return cleaned, failed


def _base_row_accounting() -> Dict[str, int]:
    return {
        "raw_rows_discovered": 0,
        "raw_rows_parsed": 0,
        "rows_validated": 0,
        "rows_normalized": 0,
        "rows_rejected": 0,
        "duplicate_symbols": 0,
        "malformed_values": 0,
    }


def _to_validation_summary(
    *,
    discovered_files: int,
    accounting: Dict[str, int],
    rows_appended: int,
    base_universe_rows_appended: int,
    unmapped_columns: List[str],
) -> Dict[str, str]:
    summary = {
        "ess_files_discovered": str(discovered_files),
        "raw_rows_discovered": str(accounting["raw_rows_discovered"]),
        "raw_rows_parsed": str(accounting["raw_rows_parsed"]),
        "rows_validated": str(accounting["rows_validated"]),
        "rows_normalized": str(accounting["rows_normalized"]),
        "rows_rejected": str(accounting["rows_rejected"]),
        "rows_appended": str(rows_appended),
        "base_universe_rows_appended": str(base_universe_rows_appended),
        "duplicate_symbols": str(accounting["duplicate_symbols"]),
        "unmapped_columns": str(len(unmapped_columns)),
        "malformed_values": str(accounting["malformed_values"]),
    }
    if unmapped_columns:
        summary["unmapped_column_list"] = "|".join(unmapped_columns)
    return summary


def execute_ess_intake_stage(context: StageContext) -> StageExecutionOutput:
    """Execute deterministic Fidelity provider intake and append immutable outputs."""

    ensure_signal_history_contracts()
    ensure_base_universe_contracts()

    coverage_config = _load_coverage_config()
    universe_mapping = dict(coverage_config.get("universe_to_domain", {}))

    intake_readiness = validate_intake_readiness()
    discovered = intake_readiness.discovered_files
    discovered_files = intake_readiness.eligible_file_count

    if not intake_readiness.is_ready:
        empty_accounting = _base_row_accounting()
        blocked_summary = _to_validation_summary(
            discovered_files=0,
            accounting=empty_accounting,
            rows_appended=0,
            base_universe_rows_appended=0,
            unmapped_columns=[],
        )
        blocked_summary.update(intake_readiness.to_validation_summary())

        return StageExecutionOutput(
            status=PipelineStatus.BLOCKED.value,
            errors=(
                "Intake readiness gate blocked: no eligible ESS intake files were discovered.",
                INTAKE_OPERATOR_GUIDANCE,
            ),
            validation_summary=blocked_summary,
        )

    normalized_signal_records: List[Dict[str, object]] = []
    base_universe_rows: List[Dict[str, object]] = []
    artifact_specs: List[Dict[str, str]] = []
    warnings: List[str] = []
    errors: List[str] = []
    accounting = _base_row_accounting()
    unmapped_columns_set: set[str] = set()

    for universe, files in discovered.items():
        for file_path in files:
            normalized_result = normalize_fidelity_ess_file(
                file_path=file_path,
                universe=universe,
                snapshot_date=context.snapshot_date,
                run_id=context.run_id,
                coverage_mapping=universe_mapping,
            )

            accounting["raw_rows_discovered"] += normalized_result.raw_rows_discovered
            accounting["raw_rows_parsed"] += normalized_result.raw_rows_parsed
            accounting["rows_validated"] += normalized_result.rows_validated
            accounting["rows_normalized"] += normalized_result.rows_normalized
            accounting["rows_rejected"] += normalized_result.rows_rejected
            accounting["duplicate_symbols"] += normalized_result.duplicate_symbols
            accounting["malformed_values"] += normalized_result.malformed_values
            unmapped_columns_set.update(normalized_result.unmapped_columns)

            normalized_signal_records.extend(normalized_result.normalized_signal_rows)
            base_universe_rows.extend(normalized_result.base_universe_rows)

            if normalized_result.warnings:
                warnings.extend(
                    f"{Path(file_path).name}: {warning}" for warning in normalized_result.warnings
                )

            if normalized_result.errors:
                errors.extend(f"{Path(file_path).name}: {error}" for error in normalized_result.errors)

            artifact_specs.append(
                {
                    "artifact_name": file_path.name,
                    "artifact_path": str(file_path),
                    "artifact_type": "ESS_INPUT_CSV",
                    "lineage_notes": f"Provider-native Fidelity export discovered for universe={universe}",
                }
            )

    sorted_unmapped = sorted(unmapped_columns_set)

    if unmapped_columns_set:
        warnings.append("Unmapped provider columns observed: " + ", ".join(sorted_unmapped))

    if errors:
        # Row-level validation errors (e.g. missing ESS text for a single
        # security) are demoted to warnings.  The rejected rows are already
        # excluded from normalized_signal_records and counted in
        # accounting["rows_rejected"].  Hard-failing the entire batch for a
        # single incomplete row discards all other valid data, which is
        # disproportionate.  Promote to warnings so the batch continues.
        warnings.extend(
            f"[ROW_REJECTED] {error}" for error in errors
        )
        errors = []

    now = datetime.now(timezone.utc)
    pre_merge_signal_path = Path("data/current/signal_snapshot.csv")
    pre_merge_signals = (
        load_fidelity_signals(pre_merge_signal_path)
        if pre_merge_signal_path.exists()
        else {}
    )
    finalized_artifacts = [
        ArtifactRecord(
            artifact_name=item["artifact_name"],
            artifact_path=item["artifact_path"],
            artifact_type=item["artifact_type"],
            created_at=now,
            producing_stage="ess_intake",
            checksum_placeholder="TODO",
            lineage_notes=item["lineage_notes"],
        )
        for item in artifact_specs
    ]

    try:
        appended_signal_count = append_signal_snapshots(
            normalized_records=normalized_signal_records,
            run_id=context.run_id,
            current_root="data/current",
            history_root="data/history/signals",
            index_path="data/history/signal_index.csv",
        )

        appended_universe_count = append_base_universe_rows(
            base_rows=base_universe_rows,
            run_id=context.run_id,
            current_root="data/current",
            history_root="data/history/universe",
            index_path="data/history/universe_index.csv",
        )

        signal_storage_paths = build_signal_storage_paths(
            snapshot_date=context.snapshot_date.isoformat(),
            run_id=context.run_id,
            current_root="data/current",
            history_root="data/history/signals",
            index_path="data/history/signal_index.csv",
        )
        universe_storage_paths = build_base_universe_storage_paths(
            snapshot_date=context.snapshot_date.isoformat(),
            run_id=context.run_id,
            current_root="data/current",
            history_root="data/history/universe",
            index_path="data/history/universe_index.csv",
        )

        # Regenerate warning from merged current signal state immediately after append.
        # This keeps warning freshness coupled to merge completion even if
        # persistence validation later reports errors.
        ess_warning = build_ess_coverage_gap_warning(
            snapshot_date=context.snapshot_date,
            signal_snapshot_path=Path("data/current/signal_snapshot.csv"),
            analysis_runs_root=Path("data/portfolio_ingestion/analysis_runs"),
            base_universe_csv=Path("data/current/base_equity_universe.csv"),
            prior_signals=pre_merge_signals,
        )
        ess_warning_path = Path("data/current/ess_coverage_warning.json")
        write_ess_coverage_warning(
            output_path=ess_warning_path,
            snapshot_date=context.snapshot_date,
            warning=ess_warning,
        )
        if ess_warning is not None:
            warnings.append(ess_warning.summary_message)
        finalized_artifacts.append(
            ArtifactRecord(
                artifact_name="ess_coverage_warning.json",
                artifact_path=str(ess_warning_path),
                artifact_type="DERIVED_JSON",
                created_at=now,
                producing_stage="ess_intake",
                checksum_placeholder="TODO",
                lineage_notes=(
                    "Structured ESS coverage-drop warning artifact for held positions. "
                    f"count={ess_warning.warning_count if ess_warning else 0}"
                ),
            )
        )

        persistence_result = validate_ess_stage_persistence(
            run_id=context.run_id,
            snapshot_date=context.snapshot_date.isoformat(),
            expected_signal_rows=appended_signal_count,
            expected_base_universe_rows=appended_universe_count,
            current_root="data/current",
            signal_history_root="data/history/signals",
            universe_history_root="data/history/universe",
            signal_index_path="data/history/signal_index.csv",
            universe_index_path="data/history/universe_index.csv",
        )
        warnings.extend(persistence_result.warnings)

        if persistence_result.errors:
            failure_summary = _to_validation_summary(
                discovered_files=discovered_files,
                accounting=accounting,
                rows_appended=persistence_result.signal_rows_persisted,
                base_universe_rows_appended=persistence_result.base_universe_rows_persisted,
                unmapped_columns=sorted_unmapped,
            )
            failure_summary.update(
                {
                    "persistence_verification": "FAILED",
                    "ess_coverage_gap_count": str(ess_warning.warning_count if ess_warning else 0),
                    "ess_coverage_gap_examples": "|".join(ess_warning.example_symbols) if ess_warning else "",
                    "ess_coverage_true_missing_count": str(ess_warning.true_missing_count if ess_warning else 0),
                    "ess_coverage_stale_count": str(ess_warning.stale_coverage_count if ess_warning else 0),
                    "ess_coverage_no_fresh_starmine_count": str(ess_warning.no_fresh_starmine_count if ess_warning else 0),
                    "persisted_signal_rows": str(persistence_result.signal_rows_persisted),
                    "persisted_base_universe_rows": str(persistence_result.base_universe_rows_persisted),
                    "artifact.current_signal_snapshot.path": str(
                        signal_storage_paths.current_signal_snapshot_path
                    ),
                    "artifact.current_base_equity_universe.path": str(
                        universe_storage_paths.current_base_universe_path
                    ),
                    "artifact.partition_signal_snapshot.path": str(
                        signal_storage_paths.partition_signal_snapshots_path
                    ),
                    "artifact.partition_signal_lineage.path": str(
                        signal_storage_paths.partition_signal_lineage_path
                    ),
                    "artifact.partition_base_equity_universe.path": str(
                        universe_storage_paths.partition_base_universe_path
                    ),
                    "artifact.partition_universe_lineage.path": str(
                        universe_storage_paths.partition_lineage_registry_path
                    ),
                    "artifact.signal_index.path": str(signal_storage_paths.index_path),
                    "artifact.universe_index.path": str(universe_storage_paths.index_path),
                    "artifact.ess_coverage_warning.path": str(ess_warning_path),
                    "artifact.current_signal_snapshot.rows": str(
                        persistence_result.signal_rows_persisted
                    ),
                    "artifact.current_base_equity_universe.rows": str(
                        persistence_result.base_universe_rows_persisted
                    ),
                    "artifact.partition_signal_snapshot.rows": str(
                        persistence_result.signal_rows_persisted
                    ),
                    "artifact.partition_signal_lineage.rows": str(
                        persistence_result.signal_rows_persisted
                    ),
                    "artifact.partition_base_equity_universe.rows": str(
                        persistence_result.base_universe_rows_persisted
                    ),
                    "artifact.partition_universe_lineage.rows": str(
                        persistence_result.base_universe_rows_persisted
                    ),
                }
            )
            return StageExecutionOutput(
                status=PipelineStatus.FAILED.value,
                warnings=tuple(warnings),
                errors=tuple(persistence_result.errors),
                artifacts_created=tuple(finalized_artifacts),
                validation_summary=failure_summary,
            )

        finalized_artifacts.extend(
            [
                ArtifactRecord(
                    artifact_name="signal_snapshot.csv",
                    artifact_path=str(signal_storage_paths.current_signal_snapshot_path),
                    artifact_type="HISTORY_CSV",
                    created_at=now,
                    producing_stage="ess_intake",
                    checksum_placeholder="TODO",
                    lineage_notes=(
                        "Current/latest signal snapshot output overwritten by latest successful run. "
                        f"rows={persistence_result.signal_rows_persisted}"
                    ),
                ),
                ArtifactRecord(
                    artifact_name="signal_snapshots.csv",
                    artifact_path=str(signal_storage_paths.partition_signal_snapshots_path),
                    artifact_type="HISTORY_CSV",
                    created_at=now,
                    producing_stage="ess_intake",
                    checksum_placeholder="TODO",
                    lineage_notes=(
                        "Immutable run-scoped partitioned signal snapshot output created. "
                        f"rows={persistence_result.signal_rows_persisted}"
                    ),
                ),
                ArtifactRecord(
                    artifact_name="signal_lineage_registry.csv",
                    artifact_path=str(signal_storage_paths.partition_signal_lineage_path),
                    artifact_type="HISTORY_CSV",
                    created_at=now,
                    producing_stage="ess_intake",
                    checksum_placeholder="TODO",
                    lineage_notes=(
                        "Immutable run-scoped partitioned signal lineage registry created. "
                        f"rows={persistence_result.signal_rows_persisted}"
                    ),
                ),
                ArtifactRecord(
                    artifact_name="base_equity_universe.csv",
                    artifact_path=str(universe_storage_paths.current_base_universe_path),
                    artifact_type="DERIVED_CSV",
                    created_at=now,
                    producing_stage="ess_intake",
                    checksum_placeholder="TODO",
                    lineage_notes=(
                        "Current/latest base-universe output overwritten by latest successful run. "
                        f"rows={persistence_result.base_universe_rows_persisted}"
                    ),
                ),
                ArtifactRecord(
                    artifact_name="base_equity_universe.csv",
                    artifact_path=str(universe_storage_paths.partition_base_universe_path),
                    artifact_type="DERIVED_CSV",
                    created_at=now,
                    producing_stage="ess_intake",
                    checksum_placeholder="TODO",
                    lineage_notes=(
                        "Immutable run-scoped partitioned base-universe output created. "
                        f"rows={persistence_result.base_universe_rows_persisted}"
                    ),
                ),
                ArtifactRecord(
                    artifact_name="universe_lineage_registry.csv",
                    artifact_path=str(universe_storage_paths.partition_lineage_registry_path),
                    artifact_type="DERIVED_CSV",
                    created_at=now,
                    producing_stage="ess_intake",
                    checksum_placeholder="TODO",
                    lineage_notes=(
                        "Immutable run-scoped partitioned base-universe lineage registry created. "
                        f"rows={persistence_result.base_universe_rows_persisted}"
                    ),
                ),
                ArtifactRecord(
                    artifact_name="signal_index.csv",
                    artifact_path=str(signal_storage_paths.index_path),
                    artifact_type="HISTORY_CSV",
                    created_at=now,
                    producing_stage="ess_intake",
                    checksum_placeholder="TODO",
                    lineage_notes="Append-only signal index updated with run partition pointer.",
                ),
                ArtifactRecord(
                    artifact_name="universe_index.csv",
                    artifact_path=str(universe_storage_paths.index_path),
                    artifact_type="HISTORY_CSV",
                    created_at=now,
                    producing_stage="ess_intake",
                    checksum_placeholder="TODO",
                    lineage_notes="Append-only universe index updated with run partition pointer.",
                ),
            ]
        )

        cleaned_files, failed_cleanups = _cleanup_processed_intake_files(discovered)
        if failed_cleanups:
            warnings.extend(
                f"Intake cleanup failed (file not deleted): {msg}" for msg in failed_cleanups
            )

        return StageExecutionOutput(
            status=PipelineStatus.COMPLETE.value,
            warnings=tuple(warnings),
            artifacts_created=tuple(finalized_artifacts),
            validation_summary={
                **_to_validation_summary(
                    discovered_files=discovered_files,
                    accounting=accounting,
                    rows_appended=persistence_result.signal_rows_persisted,
                    base_universe_rows_appended=persistence_result.base_universe_rows_persisted,
                    unmapped_columns=sorted_unmapped,
                ),
                **{
                    "persistence_verification": "PASSED",
                    "ess_coverage_gap_count": str(ess_warning.warning_count if ess_warning else 0),
                    "ess_coverage_gap_examples": "|".join(ess_warning.example_symbols) if ess_warning else "",
                    "ess_coverage_true_missing_count": str(ess_warning.true_missing_count if ess_warning else 0),
                    "ess_coverage_stale_count": str(ess_warning.stale_coverage_count if ess_warning else 0),
                    "ess_coverage_no_fresh_starmine_count": str(ess_warning.no_fresh_starmine_count if ess_warning else 0),
                    "intake_files_cleaned": str(len(cleaned_files)),
                    "intake_files_cleanup_failed": str(len(failed_cleanups)),
                    "persisted_signal_rows": str(persistence_result.signal_rows_persisted),
                    "persisted_base_universe_rows": str(persistence_result.base_universe_rows_persisted),
                    "artifact.current_signal_snapshot.path": str(
                        signal_storage_paths.current_signal_snapshot_path
                    ),
                    "artifact.current_base_equity_universe.path": str(
                        universe_storage_paths.current_base_universe_path
                    ),
                    "artifact.partition_signal_snapshot.path": str(
                        signal_storage_paths.partition_signal_snapshots_path
                    ),
                    "artifact.partition_signal_lineage.path": str(
                        signal_storage_paths.partition_signal_lineage_path
                    ),
                    "artifact.partition_base_equity_universe.path": str(
                        universe_storage_paths.partition_base_universe_path
                    ),
                    "artifact.partition_universe_lineage.path": str(
                        universe_storage_paths.partition_lineage_registry_path
                    ),
                    "artifact.signal_index.path": str(signal_storage_paths.index_path),
                    "artifact.universe_index.path": str(universe_storage_paths.index_path),
                    "artifact.ess_coverage_warning.path": str(ess_warning_path),
                    "artifact.current_signal_snapshot.rows": str(
                        persistence_result.signal_rows_persisted
                    ),
                    "artifact.current_base_equity_universe.rows": str(
                        persistence_result.base_universe_rows_persisted
                    ),
                    "artifact.partition_signal_snapshot.rows": str(
                        persistence_result.signal_rows_persisted
                    ),
                    "artifact.partition_signal_lineage.rows": str(
                        persistence_result.signal_rows_persisted
                    ),
                    "artifact.partition_base_equity_universe.rows": str(
                        persistence_result.base_universe_rows_persisted
                    ),
                    "artifact.partition_universe_lineage.rows": str(
                        persistence_result.base_universe_rows_persisted
                    ),
                },
            },
        )
    except Exception as exc:
        return StageExecutionOutput(
            status=PipelineStatus.FAILED.value,
            warnings=tuple(warnings),
            errors=(f"Unhandled ESS intake append error: {exc}",),
            validation_summary=_to_validation_summary(
                discovered_files=discovered_files,
                accounting=accounting,
                rows_appended=0,
                base_universe_rows_appended=0,
                unmapped_columns=sorted_unmapped,
            ),
        )
