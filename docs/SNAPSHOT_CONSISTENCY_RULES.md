# Snapshot Consistency Rules

## Purpose

Define deterministic publication rules for signal snapshots and related lineage artifacts.

## Rule SC-001 Snapshot Date Required

- snapshot_date is required in every published signal snapshot record.
- snapshot_date must be non-empty, parseable, and point-in-time meaningful.

## Rule SC-002 Run Id Propagation Required

- run_id must propagate from run manifest into all published snapshot records.
- run_id must remain stable for all records produced by the same run.

## Rule SC-003 Provider Propagation Required

- provider is required for each normalized record.
- provider values must remain traceable to provider-native source semantics.

## Rule SC-004 Source File Propagation Required

- source_file is required for each normalized record.
- source_file must identify the ingest artifact used to produce the record.

## Rule SC-005 Coverage-Domain Consistency Required

- coverage_domain must be present and valid for each record.
- coverage_domain must match the active coverage universe contract.

## Rule SC-006 Benchmark-Context Consistency Required

- benchmark context used for interpretation must align with snapshot_date semantics.
- benchmark-relative analytics must not cross unresolved benchmark-time boundaries.

## Rule SC-007 Append-Only Publication

- published snapshots are append-only.
- no in-place edits are permitted for previously published historical records.

## Rule SC-008 Immutable Publication

- immutable publication is mandatory after successful validation.
- corrections must be represented as new appended records with lineage references.

## Rule SC-009 Fail-Closed Validation Gate

- fail-closed validation is required before any snapshot append operation.
- malformed records block publication and must be surfaced in manifests.
