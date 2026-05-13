"""Deterministic execution summary rendering for manifests."""

from __future__ import annotations

from src.models.pipeline_models import RunManifest


def _status_marker(status: str) -> str:
    markers = {
        "NOT_STARTED": "[ ]",
        "RUNNING": "[>]",
        "COMPLETE": "[OK]",
        "WARNING": "[WARN]",
        "FAILED": "[FAIL]",
        "BLOCKED": "[BLOCKED]",
    }
    return markers.get(status, f"[{status}]")


def _stage_label(stage_name: str) -> str:
    return stage_name.replace("_", " ").title()


def render_execution_summary(manifest: RunManifest) -> str:
    """Render a concise deterministic execution summary."""

    lines: list[str] = []
    lines.append(f"RUN STATUS: {manifest.overall_status}")
    lines.append(f"RUN ID: {manifest.run_id}")
    lines.append(f"SNAPSHOT DATE: {manifest.snapshot_date.isoformat()}")
    lines.append("")
    lines.append("Stages:")

    for stage in manifest.stages:
        marker = _status_marker(stage.status)
        lines.append(f"- {marker} {_stage_label(stage.stage_name)} ({stage.duration_seconds:.3f}s)")

    lines.append("")
    lines.append("Artifacts:")
    if manifest.artifacts:
        for artifact in manifest.artifacts:
            lines.append(f"- {artifact.artifact_name} ({artifact.artifact_type})")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("Validation:")
    if manifest.validation_summary:
        for key in sorted(manifest.validation_summary):
            lines.append(f"- {key}: {manifest.validation_summary[key]}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append(f"Warnings: {len(manifest.warnings)}")
    lines.append(f"Errors: {len(manifest.errors)}")
    return "\n".join(lines)
