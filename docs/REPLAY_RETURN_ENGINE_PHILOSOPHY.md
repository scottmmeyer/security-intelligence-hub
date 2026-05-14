# Replay Return Engine Philosophy

## Purpose

Define deterministic no-lookahead replay valuation semantics for comparative
performance lines.

## Replay Selection Purity

- Selection uses analytical universe rows from replay start_date only.
- Ranking is composite_score descending with symbol ascending tie-break.
- Top-N basket is selected once and held through replay end_date.
- Full-universe basket is fixed at replay start and contains all eligible
  securities with historical coverage.

## Comparative Line Semantics

- BENCHMARK: analytical baseline, not necessarily directly investable.
- INVESTABLE_VEHICLE: ETF or fund passive alternative.
- FULL_UNIVERSE: equal-weight fixed universe exposure.
- TOP_N_STRATEGY: equal-weight fixed selected basket.

## Return Calculation Rules

- Value series is based on adjusted close.
- Cumulative return is computed as value_t / value_0 - 1.
- No rebalancing is applied in this waypoint.
- Missing market data coverage is explicit and validated.

## No-Lookahead Enforcement

- Series dates cannot precede replay start_date.
- Series dates cannot exceed replay end_date.
- Future symbols or score revisions cannot enter the fixed replay basket.
