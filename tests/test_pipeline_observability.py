from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.models.pipeline_models import (
    ArtifactRecord,
    PipelineStageResult,
    PipelineStatus,
    RunManifest,
)
from src.pipeline.execution_summary import render_execution_summary
from src.pipeline.pipeline_runner import PipelineRunner
from src.pipeline.stage_registry import (
    StageContext,
    StageDefinition,
    StageExecutionOutput,
)


def test_manifest_initialization() -> None:
    now = datetime(2026, 5, 13, tzinfo=timezone.utc)
    stage = PipelineStageResult(
        stage_name="benchmark_validation",
        status=PipelineStatus.COMPLETE.value,
        started_at=now,
        completed_at=now,
        duration_seconds=0.0,
        validation_summary={"coverage": "100%"},
    )

    manifest = RunManifest(
        run_id="RUN-INIT-001",
        snapshot_date=date(2026, 5, 13),
        overall_status=PipelineStatus.COMPLETE.value,
        started_at=now,
        completed_at=now,
        stages=(stage,),
        validation_summary={"benchmark.coverage": "100%"},
    )

    assert manifest.run_id == "RUN-INIT-001"
    assert manifest.overall_status == PipelineStatus.COMPLETE.value
    assert len(manifest.stages) == 1


def test_stage_status_handling_promotes_overall_warning(tmp_path) -> None:
    def stage_ok(_: StageContext) -> StageExecutionOutput:
        return StageExecutionOutput(
            status=PipelineStatus.COMPLETE.value,
            validation_summary={"ok": "true"},
        )

    def stage_warn(_: StageContext) -> StageExecutionOutput:
        return StageExecutionOutput(
            status=PipelineStatus.WARNING.value,
            warnings=("Coverage below threshold",),
            validation_summary={"coverage": "97%"},
        )

    stages = (
        StageDefinition("benchmark_validation", "test stage", stage_ok),
        StageDefinition("normalization", "test stage", stage_warn),
    )
    runner = PipelineRunner(runs_root=tmp_path / "runs", stages=stages)
    manifest = runner.run(run_id="RUN-WARN-001", snapshot_date=date(2026, 5, 13))

    assert manifest.overall_status == PipelineStatus.WARNING.value
    assert any("Coverage below threshold" in warning for warning in manifest.warnings)


def test_invalid_status_detection() -> None:
    now = datetime(2026, 5, 13, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        PipelineStageResult(
            stage_name="invalid_stage",
            status="UNKNOWN",
            started_at=now,
            completed_at=now,
            duration_seconds=0.0,
        )


def test_artifact_registration(tmp_path) -> None:
    def create_artifact(_: StageContext) -> StageExecutionOutput:
        artifact = ArtifactRecord(
            artifact_name="benchmark_snapshots.csv",
            artifact_path="data/history/benchmarks/benchmark_snapshots.csv",
            artifact_type="CSV",
            created_at=datetime(2026, 5, 13, tzinfo=timezone.utc),
            producing_stage="benchmark_snapshot_ingestion",
            checksum_placeholder="TODO",
            lineage_notes="Created for deterministic contract test",
        )
        return StageExecutionOutput(
            status=PipelineStatus.COMPLETE.value,
            artifacts_created=(artifact,),
            validation_summary={"rows": "0"},
        )

    stages = (
        StageDefinition("benchmark_snapshot_ingestion", "test stage", create_artifact),
    )
    runner = PipelineRunner(runs_root=tmp_path / "runs", stages=stages)
    manifest = runner.run(run_id="RUN-ARTIFACT-001", snapshot_date=date(2026, 5, 13))

    assert len(manifest.artifacts) == 1
    assert manifest.artifacts[0].artifact_name == "benchmark_snapshots.csv"


def test_execution_summary_rendering() -> None:
    now = datetime(2026, 5, 13, tzinfo=timezone.utc)
    stage = PipelineStageResult(
        stage_name="benchmark_validation",
        status=PipelineStatus.COMPLETE.value,
        started_at=now,
        completed_at=now,
        duration_seconds=0.25,
        validation_summary={"coverage": "100%"},
    )
    manifest = RunManifest(
        run_id="RUN-SUMMARY-001",
        snapshot_date=date(2026, 5, 13),
        overall_status=PipelineStatus.COMPLETE.value,
        started_at=now,
        completed_at=now,
        stages=(stage,),
        validation_summary={"benchmark_validation.coverage": "100%"},
    )

    summary = render_execution_summary(manifest)
    assert "RUN STATUS: COMPLETE" in summary
    assert "Benchmark Validation" in summary
    assert "Validation:" in summary


def test_lineage_metadata_propagation(tmp_path) -> None:
    def lineage_stage(context: StageContext) -> StageExecutionOutput:
        artifact = ArtifactRecord(
            artifact_name="run_lineage_marker.txt",
            artifact_path="runs/lineage_marker.txt",
            artifact_type="TEXT",
            created_at=datetime(2026, 5, 13, tzinfo=timezone.utc),
            producing_stage="benchmark_validation",
            checksum_placeholder="TODO",
            lineage_notes=f"generated_by_run_id={context.run_id}",
        )
        return StageExecutionOutput(
            status=PipelineStatus.COMPLETE.value,
            artifacts_created=(artifact,),
            validation_summary={"lineage_context": context.run_id},
        )

    runner = PipelineRunner(
        runs_root=tmp_path / "runs",
        stages=(StageDefinition("benchmark_validation", "test stage", lineage_stage),),
    )
    manifest = runner.run(run_id="RUN-LINEAGE-001", snapshot_date=date(2026, 5, 13))

    assert manifest.run_id == "RUN-LINEAGE-001"
    assert manifest.artifacts[0].lineage_notes.endswith("RUN-LINEAGE-001")
    assert manifest.validation_summary["benchmark_validation.lineage_context"] == "RUN-LINEAGE-001"
