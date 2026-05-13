# Snapshot Lineage Philosophy

## Immutable Snapshot Philosophy

Historical snapshots are immutable records. Published snapshots are never
overwritten in place. Corrections are represented as new records with explicit
lineage references.

## Historical Truth Preservation

- Point-in-time records must reflect what was known at publication time.
- Backfilling cannot alter prior published values.
- Historical datasets remain append-oriented for audit and reproducibility.

## Point-in-Time Intelligence

- Every snapshot is keyed by benchmark symbol and snapshot date.
- Benchmark-relative outcomes must be computed using snapshots that were valid
  at the corresponding point in time.
- Derived analytics cannot depend on future information leakage.

## Run Lineage Requirements

- Every published snapshot must include a deterministic run_id.
- Lineage metadata must capture source_provider and source_file.
- Processing status must indicate run completion before publication.

## Snapshot Reproducibility

- Identical input artifacts and configuration must yield identical snapshots.
- Validation is fail-closed: malformed or conflicting records stop publication.
- Run metadata and snapshot data are retained together for replayability.

## Future ML Integrity Requirements

- ML training datasets must be built only from immutable, lineage-backed data.
- Benchmark and outcome features must remain time-consistent.
- Any data correction must create a new versioned snapshot path.

## Absolute Rule

Historical snapshots must never be overwritten.