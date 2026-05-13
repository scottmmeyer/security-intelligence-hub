# Benchmark Philosophy

## Purpose

Benchmark context anchors signal interpretation and outcome analysis.
Security-level returns are interpreted relative to an authoritative benchmark,
not in isolation.

## Benchmark-Relative Philosophy

- Raw returns alone are insufficient because they do not capture market context.
- Benchmark-relative analysis separates security-specific signal impact from
	broad market movement.
- Benchmark assignments are deterministic and explicit, not inferred at runtime.

## Why Raw Return Is Insufficient

- A positive return can still underperform an appropriate benchmark.
- A negative return may still represent outperformance in weak market regimes.
- Provider signal effectiveness requires normalized context across universes.

## Importance of Adjusted Close

- Adjusted close preserves comparability across splits and corporate actions.
- Return windows must be derived from adjusted series for historical integrity.
- Snapshot contracts therefore include adjusted close as canonical price anchor.

## Initial Dimensions

- Geography: US, INTERNATIONAL
- Market-cap buckets: MEGA, LARGE, MID, SMALL, MICRO
- Optional INTERNATIONAL placeholder category: EMERGING

## Mapping Principles

- Mappings are explicit and configuration-driven.
- Placeholders are permitted but must remain versioned and reviewable.
- Benchmark selection must preserve comparability for each security universe.
- Inactive benchmarks cannot be assigned as active category anchors.

## Immutable Snapshot Integrity

- Benchmark snapshots are append-only and never overwritten.
- Registry changes are recorded as new historical entries with run lineage.
- Historical truth is preserved even when benchmark definitions evolve.

## Relationship to Effectiveness Analytics

- Future effectiveness metrics depend on benchmark-relative outcome windows.
- Trend and outcome analytics consume immutable benchmark snapshots.
- Predictive and ML layers must inherit point-in-time benchmark truth.

## Future Expansion

- Add sector and industry benchmark overlays in a future waypoint.
- Add macro regime overlays that contextualize benchmark-relative outcomes.
- Add fixed-income benchmark families once fixed-income signal contracts exist.