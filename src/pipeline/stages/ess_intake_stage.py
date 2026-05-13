"""ESS intake stage scaffolding for sequential pipeline execution."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml

from src.history.signal_snapshot_manager import append_signal_snapshots, ensure_signal_history_contracts
from src.models.pipeline_models import ArtifactRecord, PipelineStatus
from src.normalize.ess_normalizer import normalize_ess_rows
from src.pipeline.stage_registry import StageContext, StageExecutionOutput
from src.validation.ess_validator import EssValidationError, assert_valid_ess_file


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


def execute_ess_intake_stage(context: StageContext) -> StageExecutionOutput:
    """Execute deterministic ESS intake scaffold and append immutable snapshots."""

    ensure_signal_history_contracts()
    coverage_config = _load_coverage_config()
    allowed_domains = list(coverage_config.get("coverage_domains", []))
    allowed_source_types = list(coverage_config.get("starmine_ess_source_types", []))
    universe_mapping = dict(coverage_config.get("universe_to_domain", {}))

    discovered: Dict[str, List[Path]] = {
        "starmine": _discover_csv_files("incoming/ess/starmine"),
        "non_starmine_zacks": _discover_csv_files("incoming/ess/non_starmine_zacks"),
    }

    if not discovered["starmine"] and not discovered["non_starmine_zacks"]:
        return StageExecutionOutput(
            status=PipelineStatus.WARNING.value,
            warnings=("No ESS input CSV files found in configured intake folders.",),
            validation_summary={"ess_files_discovered": "0", "ess_rows_appended": "0"},
        )

    normalized_records: List[Dict[str, object]] = []
    artifact_specs: List[Dict[str, str]] = []
    warnings: List[str] = []

    try:
        for universe, files in discovered.items():
            for file_path in files:
                rows = assert_valid_ess_file(
                    file_path=file_path,
                    universe=universe,
                    allowed_coverage_domains=allowed_domains,
                    allowed_source_types=allowed_source_types,
                )
                normalized = normalize_ess_rows(
                    rows=rows,
                    universe=universe,
                    coverage_mapping=universe_mapping,
                    derive_numeric=True,
                )
                normalized_records.extend(normalized)

                artifact_specs.append(
                    {
                        "artifact_name": file_path.name,
                        "artifact_path": str(file_path),
                        "artifact_type": "ESS_INPUT_CSV",
                        "lineage_notes": f"Validated and normalized from universe={universe}",
                    }
                )

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
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

        appended_count = append_signal_snapshots(
            normalized_records=normalized_records,
            run_id=context.run_id,
            history_root="data/history/signals",
        )

        finalized_artifacts.extend(
            [
                ArtifactRecord(
                    artifact_name="signal_snapshots.csv",
                    artifact_path="data/history/signals/signal_snapshots.csv",
                    artifact_type="HISTORY_CSV",
                    created_at=now,
                    producing_stage="ess_intake",
                    checksum_placeholder="TODO",
                    lineage_notes="Immutable signal snapshots appended.",
                ),
                ArtifactRecord(
                    artifact_name="signal_snapshot_history.csv",
                    artifact_path="data/history/signals/signal_snapshot_history.csv",
                    artifact_type="HISTORY_CSV",
                    created_at=now,
                    producing_stage="ess_intake",
                    checksum_placeholder="TODO",
                    lineage_notes="Signal append event history updated.",
                ),
                ArtifactRecord(
                    artifact_name="signal_lineage_registry.csv",
                    artifact_path="data/history/signals/signal_lineage_registry.csv",
                    artifact_type="HISTORY_CSV",
                    created_at=now,
                    producing_stage="ess_intake",
                    checksum_placeholder="TODO",
                    lineage_notes="Signal lineage registry updated.",
                ),
            ]
        )

        return StageExecutionOutput(
            status=PipelineStatus.COMPLETE.value,
            warnings=tuple(warnings),
            artifacts_created=tuple(finalized_artifacts),
            validation_summary={
                "ess_files_discovered": str(sum(len(items) for items in discovered.values())),
                "ess_rows_normalized": str(len(normalized_records)),
                "ess_rows_appended": str(appended_count),
            },
        )
    except EssValidationError as exc:
        return StageExecutionOutput(
            status=PipelineStatus.FAILED.value,
            errors=tuple(exc.errors),
            validation_summary={"ess_validation": "FAILED"},
        )
    except Exception as exc:
        return StageExecutionOutput(
            status=PipelineStatus.FAILED.value,
            errors=(f"Unhandled ESS intake error: {exc}",),
            validation_summary={"ess_execution": "FAILED_EXCEPTION"},
        )
