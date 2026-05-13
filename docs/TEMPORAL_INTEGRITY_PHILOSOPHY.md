# Temporal Integrity Philosophy

## Purpose

Preserve point-in-time intelligence validity across snapshots, benchmark-relative analytics, and future outcome modeling.

## Point-In-Time Truth Requirements

- Every published record must be interpretable at its snapshot_date.
- Historical truth must remain append-only and immutable after publication.
- No retroactive mutation is allowed for published records.

## Future Information Leakage Prevention

- Validation and normalization must not use data from future timestamps.
- Outcome labels must remain temporally downstream from signal snapshots.
- Backfilled data must be appended as new records, never rewritten into prior states.

## Snapshot-Time Classification Requirements

- Security classification context must reflect snapshot_date semantics.
- Market-cap and coverage context must be tied to the snapshot event time.
- Classification changes over time must be represented as append-only transitions.

## Benchmark-Time Consistency Requirements

- Benchmark-relative interpretation must use benchmark context valid at snapshot_date.
- Outcome windows must align with benchmark definitions at evaluation time.
- Cross-time benchmark drift must be explicit, not silently absorbed.

## Historical Replayability Requirements

- Identical inputs and configs must produce deterministic replays.
- Run manifests and stage manifests must preserve temporal lineage evidence.
- Replay outputs must remain consistent with immutable publication rules.

## ML Feature Integrity Requirements

- Feature sets must only include information available at prediction-time boundaries.
- Training labels must be derived from later outcome windows, never contemporaneous leakage.
- Temporal drift invalidates benchmark-relative model evaluation.

## Why Temporal Drift Invalidates Analytics

- Drift mixes unavailable future information into prior decision contexts.
- Drift destroys causal interpretability and historical comparability.
- Drift undermines confidence in benchmark-relative effectiveness measures.

## Snapshots, Outcomes, And Benchmarks Relationship

- Snapshot is the point-in-time intelligence state.
- Outcome window is the future measurement horizon from that state.
- Benchmark-relative comparison is the evaluation frame connecting snapshot to outcome.
