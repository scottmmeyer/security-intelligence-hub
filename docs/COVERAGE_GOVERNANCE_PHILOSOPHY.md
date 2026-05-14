# Coverage Governance Philosophy

## Purpose

Coverage governance ensures that category exposure in the UI and generated
replay outputs remain synchronized and deterministic.

## Core Principles

1. Category exposure and generated replay scope are separate but linked
   contracts.
2. Out-of-scope categories must remain visible as NOT_GENERATED rather than
   hidden.
3. Missing benchmark or vehicle mappings are explicit MISSING_MAPPING failures.
4. Missing historical curves are explicit MISSING_MARKET_DATA failures.
5. Runtime blockers are represented as BLOCKED and retain diagnostic context.

## Matrix Governance

WP-05B replay matrix generation produces one replay per in-scope category and
writes references to current contracts and immutable replay partitions.

Current artifacts:

- data/current/replay_matrix.csv
- data/current/replay_availability.csv

Each generated replay partition includes:

- replay_metadata.json
- replay_availability.json
- replay_performance_series.csv

## Validation Expectations

Coverage governance validators must detect:

- mapping incompleteness,
- replay availability inconsistency,
- replay/UI contract mismatch,
- orphaned replay metadata references,
- empty replay outputs,
- unsupported category exposure marked as AVAILABLE.

## Temporal Integrity

Coverage expansion does not relax no-lookahead semantics. Replay selection and
series contracts remain point-in-time constrained.
