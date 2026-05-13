"""Pipeline stage registration contracts.

This module declares stage order and execution interfaces only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Mapping, Optional, Sequence

from src.models.pipeline_models import ArtifactRecord


@dataclass(frozen=True)
class StageContext:
    """Context passed to stage executors."""

    run_id: str
    snapshot_date: date


@dataclass(frozen=True)
class StageExecutionOutput:
    """Deterministic output contract returned by a stage executor."""

    status: str
    warnings: Sequence[str] = field(default_factory=tuple)
    errors: Sequence[str] = field(default_factory=tuple)
    artifacts_created: Sequence[ArtifactRecord] = field(default_factory=tuple)
    validation_summary: Mapping[str, str] = field(default_factory=dict)


StageExecutor = Callable[[StageContext], StageExecutionOutput]


@dataclass(frozen=True)
class StageDefinition:
    """Sequential stage definition with optional executor implementation."""

    stage_name: str
    description: str
    executor: Optional[StageExecutor] = None


def default_stage_registry() -> tuple[StageDefinition, ...]:
    """Return default sequential stage registration for the pipeline."""

    # Lazy import avoids cyclical loading between stage contracts and stage implementations.
    from src.pipeline.stages.ess_intake_stage import execute_ess_intake_stage

    return (
        StageDefinition(
            stage_name="benchmark_validation",
            description="Validate benchmark registry and category mappings.",
        ),
        StageDefinition(
            stage_name="benchmark_snapshot_ingestion",
            description="Ingest benchmark snapshots into immutable history contracts.",
        ),
        StageDefinition(
            stage_name="ess_intake",
            description="Ingest ESS intake lane payloads into run-scoped staging.",
            executor=execute_ess_intake_stage,
        ),
        StageDefinition(
            stage_name="normalization",
            description="Normalize provider payloads into canonical intelligence contracts.",
        ),
        StageDefinition(
            stage_name="snapshot_export",
            description="Export run-ready snapshot artifacts for downstream consumers.",
        ),
    )
