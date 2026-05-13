# Provider Lineage Philosophy

## Purpose

Maintain provider-native truth while producing deterministic canonical contracts with explicit provenance.

## Provider-Native Truth Preservation

- Provider payload semantics are preserved as authoritative source context.
- Canonical normalization does not erase provider lineage metadata.
- Source-specific meaning must remain reconstructable from lineage fields.

## Canonical Normalization Boundaries

- Normalization maps structure and taxonomy, not provider intent reinterpretation.
- Canonical fields must retain direct links to provider and source_file.
- Any derived value must be explicitly marked as derived or estimated.

## Provider Disagreement Philosophy

- Provider disagreements are expected and must remain visible.
- Conflicts are represented, not silently averaged or overwritten.
- Resolution policy is explicit, deterministic, and contract-driven.

## Derived-Value Provenance Requirements

- Derived values must record source inputs and transformation rationale.
- Estimated values must be flagged and separated from authoritative values.
- Provenance must remain queryable through immutable lineage records.

## Future Multi-Provider Coexistence

- Multiple providers can coexist under canonical contracts.
- Provider boundary isolation prevents leakage of provider-specific assumptions.
- Canonical expansion must preserve benchmark-relative comparability.

## Fidelity And StarMine Alignment Rationale

- Current classification and intake conventions align with known provider exports.
- Alignment is explicit configuration and contract behavior, not hidden defaults.
- Future provider divergence must be handled through deterministic adapters.

## Provider Conflict Handling Philosophy

- Conflicts are fail-closed when required fields or semantics are missing.
- Non-blocking disagreements are retained with provider-specific lineage labels.
- No silent conversions are allowed for ambiguous provider-native values.

## Why Traceable Provider Semantics Matter

- Auditability requires replayable source-to-canonical evidence.
- Historical truth requires preservation of what each provider actually published.
- Future analytics integrity depends on transparent provider lineage.
