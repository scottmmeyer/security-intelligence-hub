"""Lightweight sequential pipeline runner for observability foundation.

This runner executes stages in deterministic order and emits manifests.
It intentionally avoids orchestration features such as DAGs, retries, and
distributed scheduling.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Sequence

from src.models.pipeline_models import (
    ArtifactRecord,
    PipelineStageResult,
    PipelineStatus,
    RunManifest,
    run_manifest_to_dict,
    stage_result_to_dict,
)
from src.pipeline.stage_registry import (
    StageContext,
    StageDefinition,
    StageExecutionOutput,
    default_stage_registry,
)


def utcnow() -> datetime:
    """Return timezone-aware UTC now timestamp."""

    return datetime.now(timezone.utc)


class PipelineRunner:
    """Deterministic sequential pipeline runner for manifest generation."""

    def __init__(
        self,
        runs_root: str | Path = "runs",
        stages: Sequence[StageDefinition] | None = None,
    ) -> None:
        self.runs_root = Path(runs_root)
        self.stages = tuple(stages or default_stage_registry())
        self.manifest_dir = self.runs_root / "manifests"
        self.stage_manifest_dir = self.runs_root / "stage_manifests"
        self.log_dir = self.runs_root / "logs"

    def _ensure_run_dirs(self) -> None:
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.stage_manifest_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _placeholder_output(self, stage: StageDefinition) -> StageExecutionOutput:
        return StageExecutionOutput(
            status=PipelineStatus.COMPLETE.value,
            warnings=(
                f"Placeholder stage: {stage.stage_name} has no business logic implementation yet.",
            ),
            validation_summary={"contract_status": "REGISTERED_PLACEHOLDER"},
        )

    def run(self, run_id: str, snapshot_date: date) -> RunManifest:
        """Execute all registered stages in deterministic order and return manifest."""

        self._ensure_run_dirs()
        run_started_at = utcnow()
        stage_results: list[PipelineStageResult] = []
        all_artifacts: list[ArtifactRecord] = []
        run_warnings: list[str] = []
        run_errors: list[str] = []
        run_validation_summary: dict[str, str] = {}
        overall_status = PipelineStatus.COMPLETE.value

        for stage in self.stages:
            stage_started_at = utcnow()
            stage_timer_start = perf_counter()

            try:
                context = StageContext(run_id=run_id, snapshot_date=snapshot_date)
                output = stage.executor(context) if stage.executor else self._placeholder_output(stage)
                stage_completed_at = utcnow()
                duration_seconds = round(perf_counter() - stage_timer_start, 6)

                stage_result = PipelineStageResult(
                    stage_name=stage.stage_name,
                    status=output.status,
                    started_at=stage_started_at,
                    completed_at=stage_completed_at,
                    duration_seconds=duration_seconds,
                    warnings=tuple(output.warnings),
                    errors=tuple(output.errors),
                    artifacts_created=tuple(output.artifacts_created),
                    validation_summary=dict(output.validation_summary),
                )
            except Exception as exc:
                stage_completed_at = utcnow()
                duration_seconds = round(perf_counter() - stage_timer_start, 6)
                stage_result = PipelineStageResult(
                    stage_name=stage.stage_name,
                    status=PipelineStatus.FAILED.value,
                    started_at=stage_started_at,
                    completed_at=stage_completed_at,
                    duration_seconds=duration_seconds,
                    errors=(f"Unhandled stage exception: {exc}",),
                    validation_summary={"stage_execution": "FAILED_EXCEPTION"},
                )

            stage_results.append(stage_result)
            all_artifacts.extend(stage_result.artifacts_created)
            run_warnings.extend(stage_result.warnings)
            run_errors.extend(stage_result.errors)

            for key, value in stage_result.validation_summary.items():
                run_validation_summary[f"{stage.stage_name}.{key}"] = value

            if stage_result.status == PipelineStatus.WARNING.value and overall_status == PipelineStatus.COMPLETE.value:
                overall_status = PipelineStatus.WARNING.value

            if stage_result.status in {PipelineStatus.FAILED.value, PipelineStatus.BLOCKED.value}:
                overall_status = stage_result.status
                break

        run_completed_at = utcnow()
        manifest = RunManifest(
            run_id=run_id,
            snapshot_date=snapshot_date,
            overall_status=overall_status,
            started_at=run_started_at,
            completed_at=run_completed_at,
            stages=tuple(stage_results),
            artifacts=tuple(all_artifacts),
            warnings=tuple(run_warnings),
            errors=tuple(run_errors),
            validation_summary=run_validation_summary,
        )

        self.write_run_manifest(manifest)
        self.write_stage_manifests(manifest)
        self.write_run_log(manifest)
        return manifest

    def write_run_manifest(self, manifest: RunManifest) -> Path:
        """Write run manifest JSON artifact."""

        output_path = self.manifest_dir / f"{manifest.run_id}_manifest.json"
        output_path.write_text(
            json.dumps(run_manifest_to_dict(manifest), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return output_path

    def write_stage_manifests(self, manifest: RunManifest) -> list[Path]:
        """Write per-stage manifest JSON files."""

        output_paths: list[Path] = []
        for stage in manifest.stages:
            output_path = self.stage_manifest_dir / f"{manifest.run_id}_{stage.stage_name}.json"
            payload = {
                "run_id": manifest.run_id,
                "snapshot_date": manifest.snapshot_date.isoformat(),
                "stage": stage_result_to_dict(stage),
            }
            output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            output_paths.append(output_path)
        return output_paths

    def write_run_log(self, manifest: RunManifest) -> Path:
        """Write simple deterministic run log summary."""

        output_path = self.log_dir / f"{manifest.run_id}.log"
        lines = [
            f"run_id={manifest.run_id}",
            f"snapshot_date={manifest.snapshot_date.isoformat()}",
            f"overall_status={manifest.overall_status}",
            f"stage_count={len(manifest.stages)}",
            f"artifact_count={len(manifest.artifacts)}",
            f"warning_count={len(manifest.warnings)}",
            f"error_count={len(manifest.errors)}",
        ]
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return output_path
