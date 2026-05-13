# Architecture Consistency Checklist

Use this checklist for deterministic cross-document architecture hardening reviews.

## Terminology Consistency

- [ ] Canonical terminology definitions are present and non-overlapping.
- [ ] Coverage domain and coverage universe language is consistent.
- [ ] Authoritative, derived, and estimated value terminology is consistent.

## Snapshot And Immutability Consistency

- [ ] Immutable and append-only snapshot language is consistent.
- [ ] No document implies retroactive mutation of published records.
- [ ] run_id, provider, source_file, and snapshot_date propagation is consistent.

## Benchmark-Relative Consistency

- [ ] Benchmark-relative interpretation language is consistent across docs.
- [ ] Snapshot and benchmark time-alignment language is consistent.
- [ ] Outcome window references preserve temporal ordering.

## Provider Lineage Consistency

- [ ] Provider-native truth preservation language is consistent.
- [ ] Normalization boundary language is deterministic and explicit.
- [ ] Provider disagreement and conflict handling language is traceable.

## Temporal Integrity Consistency

- [ ] Point-in-time intelligence language is consistent.
- [ ] Future information leakage prevention is explicit.
- [ ] Historical replayability requirements are explicit.

## Validation And Control Discipline

- [ ] Fail-closed terminology is consistent in philosophy and rule docs.
- [ ] Deterministic validation boundary language is preserved.
- [ ] No document introduces orchestration or runtime autonomy drift.

## Persistence Verification Consistency

- [ ] Persistence verification philosophy is present and references fail-closed behavior.
- [ ] Manifest-to-physical row reconciliation language is explicit.
- [ ] Partition run-isolation and index integrity expectations are documented.
