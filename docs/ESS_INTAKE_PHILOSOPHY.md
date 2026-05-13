# ESS Intake Philosophy

## ESS Coverage Philosophy

ESS intake captures market intelligence from distinct coverage universes while
preserving provenance, snapshot-time context, and deterministic normalization.

## Coverage Domains

ESS intake treats coverage domains as first-class metadata:

- STARMINE_COVERED
- NON_STARMINE_ANALYST
- PARTIAL_COVERAGE
- NO_COVERAGE

## Why Non-Covered Securities Matter

Absence of StarMine coverage is not a quality signal. Small-cap and micro-cap
securities may lack institutional coverage and still provide high-opportunity
analyst intelligence.

## ESS Text vs Numeric Distinction

Fidelity exports are often text-category driven while underlying StarMine may
operate with numeric precision. The platform preserves both forms explicitly
without conflating derived numeric estimates with authoritative source values.

## Provenance Philosophy

- Source file and provider lineage are preserved at row and snapshot level.
- Any derived numeric mapping is explicitly marked as estimated.
- No silent conversions are allowed.

## Immutable Signal Snapshots

Each ingestion run appends immutable signal snapshots keyed by run lineage and
snapshot date. Historical signal truth is append-only and never overwritten.

## Overlapping Universe Handling

If a symbol appears across universes, each observation remains lineage-scoped
to its source universe and source file. Merge behavior is deferred to later
waypoints and must preserve original provenance.

## Future Provider Expansion Philosophy

Future providers can be onboarded through explicit schemas and coverage-domain
assignments without changing canonical provenance rules.

## Relationship to Future Effectiveness Analytics

Coverage-aware, provenance-aware snapshots prevent false conclusions in signal
effectiveness analysis and provide reliable inputs for later analytics and ML.