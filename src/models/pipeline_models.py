"""Deterministic pipeline observability models.

These models describe execution results and lineage artifacts.
They do not orchestrate or schedule execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Mapping, Sequence


class PipelineStatus(str, Enum):
    """Flat, deterministic pipeline status values."""

    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    WARNING = "WARNING"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


PIPELINE_STATUS_VALUES: tuple[str, ...] = tuple(item.value for item in PipelineStatus)


def validate_pipeline_status(status: str) -> str:
    """Validate a pipeline status value and return the normalized string."""

    if status not in PIPELINE_STATUS_VALUES:
        allowed = ", ".join(PIPELINE_STATUS_VALUES)
        raise ValueError(f"Invalid pipeline status {status!r}. Allowed values: {allowed}")
    return status


@dataclass(frozen=True)
class ArtifactRecord:
    """Immutable record of a produced artifact for run-level lineage."""

    artifact_name: str
    artifact_path: str
    artifact_type: str
    created_at: datetime
    producing_stage: str
    checksum_placeholder: str
    lineage_notes: str


@dataclass(frozen=True)
class PipelineStageResult:
    """Deterministic stage execution result for manifest tracking."""

    stage_name: str
    status: str
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    warnings: Sequence[str] = field(default_factory=tuple)
    errors: Sequence[str] = field(default_factory=tuple)
    artifacts_created: Sequence[ArtifactRecord] = field(default_factory=tuple)
    validation_summary: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_pipeline_status(self.status)
        if self.duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must be greater than or equal to started_at")


@dataclass(frozen=True)
class RunManifest:
    """Canonical run manifest describing deterministic execution outcomes."""

    run_id: str
    snapshot_date: date
    overall_status: str
    started_at: datetime
    completed_at: datetime
    stages: Sequence[PipelineStageResult] = field(default_factory=tuple)
    artifacts: Sequence[ArtifactRecord] = field(default_factory=tuple)
    warnings: Sequence[str] = field(default_factory=tuple)
    errors: Sequence[str] = field(default_factory=tuple)
    validation_summary: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_pipeline_status(self.overall_status)
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must be greater than or equal to started_at")


def _serialize_manifest_value(value: Any) -> Any:
    """Serialize nested dataclass values to deterministic JSON-friendly values."""

    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _serialize_manifest_value(inner) for key, inner in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_manifest_value(item) for item in value]
    return value


def stage_result_to_dict(stage_result: PipelineStageResult) -> dict[str, Any]:
    """Convert stage result dataclass into a deterministic dictionary."""

    return _serialize_manifest_value(asdict(stage_result))


def run_manifest_to_dict(manifest: RunManifest) -> dict[str, Any]:
    """Convert run manifest dataclass into a deterministic dictionary."""

    return _serialize_manifest_value(asdict(manifest))
