# Pipeline Observability

## Manifest-Driven Observability

Pipeline execution is described by manifests that capture stage outcomes,
artifacts, warnings, errors, and validation summaries.
Manifests document execution history. They do not orchestrate execution.

## Historical Run Lineage

- Every run is identified by run_id and snapshot_date.
- Run manifests capture ordered stage results for replayable lineage.
- Stage manifests provide per-stage historical evidence.

## Future UI and Chat Integration Philosophy

- Execution summaries are deterministic text for terminal and chat rendering.
- Manifest structure is intentionally stable for future visual adapters.
- Summary payloads avoid hidden logic and remain human-reviewable.

## Explicit Failure Visibility

- Stage errors are emitted in stage and run manifests.
- Overall run status is derived from explicit stage outcomes.
- Failures are fail-closed and never silently corrected.

## Artifact Traceability

- Every produced artifact is recorded with path, producing stage, and lineage.
- Artifact records provide immutable evidence of run outputs.
- Traceability enables deterministic audit and future reproducibility checks.

## Sequential Deterministic Execution Philosophy

- Stages run in explicit sequential order.
- No retries, worker pools, or async fan-out in this waypoint.
- Deterministic run order preserves observability clarity.

## Execution vs Orchestration Separation

- Execution contracts define what happened in a run.
- Orchestration decides what to run and when.
- This project currently implements execution observability only.

## Preventing Orchestration Complexity Explosion

- No DAG schedulers.
- No recursive workflow governance.
- No distributed control plane.
- No autonomous runtime agents.
- Keep status semantics flat, explicit, and human-readable.