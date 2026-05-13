# ESS Numeric Mapping Philosophy

## Fidelity Text Categories

Current Fidelity-oriented ESS exports frequently provide text categories rather
than direct numeric precision scores.

## Underlying StarMine Numeric Precision

Underlying StarMine methodology likely operates with numeric precision, but
those values are not always directly exposed in current intake sources.

## Inferred Numeric Mappings

Deterministic text-to-numeric mappings may be introduced for normalization
support, trend scaffolding, and composite signal preparation.

## Non-Authoritative Derived Values

Derived numeric values are not authoritative source values unless explicitly
provided as direct numeric data from source.

## Provenance Requirements

- source type must be explicit: DIRECT_NUMERIC, TEXT_MAPPED,
  MANUAL_ESTIMATE, or UNKNOWN.
- estimated numeric flags must be preserved.
- text values remain preserved for audit and replayability.

## Future Direct StarMine Integration

If direct StarMine numeric ingestion becomes available, source type should move
to DIRECT_NUMERIC while preserving prior historical lineage semantics.

## Importance for Trend Analytics and Composite Scoring

Trend analytics and composite scoring require stable representation of ESS
signals. Provenance-aware numeric mapping prevents accidental misuse of derived
values as authoritative source truth.