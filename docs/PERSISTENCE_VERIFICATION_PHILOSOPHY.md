# Persistence Verification Philosophy

## Purpose

Persistence verification ensures that manifest-level claims are reconciled with
physical CSV artifacts and run-scoped lineage evidence.

## Deterministic Verification Scope

Verification must fail closed for each ESS persistence artifact class:

- current/signal_snapshot.csv
- current/base_equity_universe.csv
- partition/signal_snapshots.csv
- partition/signal_lineage_registry.csv
- partition/base_equity_universe.csv
- partition/universe_lineage_registry.csv
- signal and universe index files

## Core Integrity Rules

- Physical row counts must match stage-manifest expected counts.
- Run-scoped row counts must match stage-manifest expected counts.
- Required lineage fields must be present for persisted run rows.
- Snapshot date must match the run snapshot date.
- Partition artifacts must remain run-isolated.
- Index rows must exist exactly once per run_id.
- Index path references must exist and resolve to published artifacts.

## Required Lineage Fields

Each persisted row must include:

- run_id
- snapshot_date
- created_at_utc
- provider
- source_file

## Append Integrity Rules

- Append-only artifacts must not silently overwrite prior historical rows.
- Duplicate lineage_id values within a run are validation failures.
- Duplicate run-scoped snapshot keys are validation failures.
- Malformed CSV overflow rows are validation failures.

## Failure Semantics

Persistence verification is fail closed:

- Any mismatch between manifest counts and physical persistence fails the stage.
- Any malformed row, missing lineage field, or index inconsistency fails the stage.
- Warnings may surface non-fatal observations, but integrity breaches are errors.

## Governance Outcome

Persistence verification is a release guardrail, not optional telemetry.
It protects immutable historical truth, run reproducibility, and downstream
consumer trust in published intelligence artifacts.
