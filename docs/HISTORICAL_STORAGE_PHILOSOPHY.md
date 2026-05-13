# Historical Storage Philosophy (WP-03.4)

## Overview

WP-03.4 separates **latest operational outputs** from **immutable historical evidence**.

- Latest outputs are written to `data/current` and are intentionally overwritten by each successful run.
- Historical outputs are written to run-partitioned directories under `data/history` and are immutable once created.

This model preserves fast access for downstream consumers while maintaining deterministic, auditable lineage for every run.

## Current vs Historical

Current layer:

- `data/current/signal_snapshot.csv`
- `data/current/base_equity_universe.csv`

Historical layer:

- `data/history/signals/snapshot_date=YYYY-MM-DD/run_id=RUN-.../signal_snapshots.csv`
- `data/history/signals/snapshot_date=YYYY-MM-DD/run_id=RUN-.../signal_lineage_registry.csv`
- `data/history/universe/snapshot_date=YYYY-MM-DD/run_id=RUN-.../base_equity_universe.csv`
- `data/history/universe/snapshot_date=YYYY-MM-DD/run_id=RUN-.../universe_lineage_registry.csv`

Index layer:

- `data/history/signal_index.csv`
- `data/history/universe_index.csv`

Index files are append-only and provide deterministic discovery of partition paths, row counts, and creation metadata.

## Partition Strategy

Partition key:

- `snapshot_date`
- `run_id`

Each successful run creates exactly one partition directory per domain (signals and universe), with full CSV outputs and lineage registry files scoped to that run.

Design goals:

- deterministic file discovery
- no accidental cross-run mutation
- explicit run-level lineage and row accounting

## Immutability and Fail-Closed Behavior

Writes are fail-closed for historical partitions:

- If a target partition directory already exists for the same `run_id`, write is rejected.
- If index already contains the same `run_id`, append is rejected.

This enforces run immutability and prevents duplicate or conflicting historical evidence.

Latest/current files are the only mutable outputs and are replaced atomically by each accepted run.

## Recovery and Scalability Rationale

Operational recovery:

- Pipelines can reconstruct run outcomes directly from index entries and partitioned artifacts.
- Partition isolation simplifies triage and rollback analysis to a single run scope.

Scalability:

- Historical volume scales by partition, not by repeated appends to single giant files.
- Run-scoped files reduce contention and avoid brittle global append semantics.
- Storage contracts are backend-agnostic at the partition/index level, enabling future migration to Parquet object layouts or database-backed partition catalogs without changing run-scoped immutability rules.

Auditability:

- Per-run lineage registries preserve source, provider, normalization, and creation metadata.
- Index metadata links manifests to concrete storage locations.

## Why Single Growing CSV Is Insufficient Long Term

- A single append-only history file creates hot-spot write contention and slower validation as the file grows.
- Recovery and incident triage become coarse-grained because one large file mixes many runs instead of isolating evidence per run.
- Late-stage corruption risk is amplified because header/row shape issues in one segment can degrade readability for the full history file.
- Operational replay requires run-level segmentation; flat history requires scanning and filtering large files to reconstruct one run.
- Partitioned storage preserves deterministic run-level isolation while keeping current/latest outputs simple for downstream consumers.

## Legacy Note

`LEGACY_PROOF_OF_PERSISTENCE`: prior WP-03.3 and earlier behavior used single flat append files such as `signal_snapshot_history.csv` and `base_equity_universe_history.csv`. Those artifacts are retained only as legacy proof points and are no longer the primary persistence contract for WP-03.4 and later.
