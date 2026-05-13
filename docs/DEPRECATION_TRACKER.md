# Deprecation Tracker

## Purpose

Track approved deprecations and deterministic replacement paths while preserving
lineage integrity during transition.

## Deprecated Artifacts

| Artifact | Status | Rationale | Replacement Authoritative Path | Planned Removal Timing |
|---|---|---|---|---|
| data/history/signals/signal_snapshot_history.csv | DEPRECATED | Legacy flat-history contract replaced by immutable run partitions | data/history/signals/snapshot_date=<date>/run_id=<run_id>/signal_snapshots.csv and data/history/signal_index.csv | Remove from compatibility documentation after WP-04 readiness sign-off |
| data/history/signals/signal_snapshots.csv | DEPRECATED | Legacy global append file replaced by partitioned immutable storage | data/history/signals/snapshot_date=<date>/run_id=<run_id>/signal_snapshots.csv | Remove from compatibility documentation after WP-04 readiness sign-off |
| data/history/signals/signal_lineage_registry.csv | DEPRECATED | Legacy flat lineage registry replaced by run-scoped lineage partitions | data/history/signals/snapshot_date=<date>/run_id=<run_id>/signal_lineage_registry.csv | Remove from compatibility documentation after WP-04 readiness sign-off |
| run_pipeline.py | DEPRECATED | Untrusted ad hoc entrypoint not aligned with authoritative runner contracts | src/pipeline/pipeline_runner.py via governed invocation flow | Immediate operational deprecation; do not reintroduce without governance review |
| run_pipeline_ess.py | DEPRECATED | Untrusted ad hoc wrapper with non-authoritative execution pathing | src/pipeline/pipeline_runner.py via governed invocation flow | Immediate operational deprecation; do not reintroduce without governance review |

## Cleanup Artifacts

| Artifact | Action | Notes |
|---|---|---|
| data/.DS_Store | DELETE | Hygiene artifact removed |
| incoming/ess/.DS_Store | DELETE | Hygiene artifact removed |
| src/.DS_Store | DELETE | Hygiene artifact removed |
| status_output.txt | DELETE | Debug artifact removed |
| .DS_Store | DELETE | Root hygiene artifact removed when present |

## Transitional Compatibility Notes

- Partitioned history under data/history/signals and data/history/universe is now
  authoritative for immutable evidence retention.
- Index artifacts (data/history/signal_index.csv and
  data/history/universe_index.csv) are the retrieval bridge for run-scoped
  partition discovery.
- data/derived/base_universe remains KEEP TEMPORARILY and is not removed in this
  cleanup unit.

## Final Helper Drift Resolution Status

- Legacy root-level helper drift was resolved in the final pre-WP-04 hygiene
  pass.
- Reusable read-only diagnostics were formalized under scripts/diagnostics.
- Non-deterministic scratch helpers were removed.
