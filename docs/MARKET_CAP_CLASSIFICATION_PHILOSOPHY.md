# Market Cap Classification Philosophy

## Why Canonical Classification Is Required

Security Intelligence Hub needs one deterministic internal market-cap framework
to normalize intelligence across providers and keep benchmark-relative analysis
consistent across runs.

## Fidelity Alignment Rationale

Initial canonical thresholds are aligned to Fidelity definitions because
Fidelity and StarMine ESS are primary intelligence dependencies in the current
delivery sequence.

## Provider Divergence Philosophy

- Providers may define market-cap buckets differently.
- Canonical classification is required for normalization consistency.
- Provider-origin metadata must be preserved for lineage and auditability.

## Historical Snapshot Philosophy

- Market-cap classification is temporal and tied to snapshot date.
- Historical classifications are append-oriented and must not be overwritten.
- Reclassification over time must be represented as new snapshot evidence.

## Temporal Classification Behavior

- Bucket assignment is computed from raw USD market cap for a specific snapshot.
- Classification may change across dates for the same security.
- Any consumer of historical intelligence must use point-in-time classification.

## Future Multi-Provider Support

- Additional providers can introduce alternate threshold mappings.
- Canonical output remains stable while lineage preserves source semantics.
- Provider conflicts are managed through explicit normalization contracts.

## Importance for Benchmark-Relative Analytics

- Market-cap bucket drives benchmark mapping context.
- Benchmark-relative outcomes depend on stable, reproducible bucket assignment.
- Incorrect bucket normalization degrades interpretability of signal outcomes.

## Importance for Future ML Integrity

- ML features must reflect point-in-time market-cap state.
- Provider lineage metadata supports reproducible feature provenance.
- Temporal bucket drift must be observable and versioned.

## Relationship to Effectiveness Analytics

- Effectiveness analytics require historical consistency of classification.
- Snapshot-aware bucket assignment avoids lookahead bias in outcomes.
- Lineage-aware classification enables cross-provider effectiveness comparison.

## Explicit Rule

Market-cap classification is snapshot-based and must not be treated as
immutable security metadata.