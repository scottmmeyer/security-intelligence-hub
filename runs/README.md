# Runs Contract

## Run Folder Philosophy

The runs directory stores deterministic execution evidence.
Run artifacts describe what happened during execution and preserve lineage.

## Directory Structure

- manifests/: run-level manifest JSON artifacts
- stage_manifests/: per-stage manifest JSON artifacts
- logs/: run summary logs for operator visibility

## Manifest Structure

- run manifests capture overall status, stage outcomes, artifacts, warnings,
  errors, and validation summaries.
- stage manifests capture deterministic outcomes for one stage in one run.

## Lineage Structure

- run_id is the primary run lineage key.
- snapshot_date anchors point-in-time context.
- artifact records include producing stage and lineage notes.

## Artifact Traceability

- each artifact must be represented by an artifact record.
- records should include path, type, and producing stage.
- immutable records support audit and future ML traceability.

## Important Constraint

Manifests describe execution history. They do not orchestrate execution.