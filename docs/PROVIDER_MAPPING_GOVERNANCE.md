# Provider Mapping Governance

## Provider-Native Truth Preservation

- Raw Fidelity exports remain authoritative provider-native records.
- Mapping layers must not mutate source files or rewrite provider-native
  structure.
- Canonical records are derived artifacts produced by explicit mapping rules.

## Deterministic Non-Data And Duplicate Handling

- Fidelity export footer and notice lines are treated as non-data rows when
  symbol tokens do not match ticker syntax and are excluded from canonical
  normalization.
- Duplicate symbols inside a single provider file are handled deterministically
  by keeping the first observed row and skipping subsequent duplicates.
- Skipped non-data and duplicate rows are surfaced explicitly in stage warnings
  and manifest row-accounting metrics.

## Canonical Mapping Philosophy

- Canonical normalization is a separate deterministic step.
- Provider-to-canonical mappings are versioned contracts, not ad hoc transforms.
- Mapping validation fails closed when required provider columns are missing.

## Unmapped Column Handling

- Unmapped provider columns must be surfaced explicitly in stage warnings and
  validation summaries.
- Unmapped columns are captured in lineage registry artifacts.
- Unmapped columns are never silently discarded in execution reporting.

## Schema Evolution Handling

- Provider-native schema contracts are versioned independently from canonical
  model contracts.
- New provider columns must be visible immediately as unknown/unmapped columns
  until mapping governance decisions are applied.
- Missing required provider-native columns are fail-closed validation errors.

## Future Provider Coexistence

- Provider adapters are first-class architecture modules.
- Each provider owns provider-native schema contracts and explicit
  provider-to-canonical mapping rules.
- Canonical records can coexist with provider-specific metadata and lineage
  without mutating canonical field contracts.

## Provider-Version Drift Philosophy

- Provider version drift is observable evidence, not a hidden implementation
  detail.
- Drift must be reported via validation summaries and governance documentation
  before downstream usage expands.
- Historical outputs remain append-only; prior snapshots are never rewritten to
  match new provider versions.
