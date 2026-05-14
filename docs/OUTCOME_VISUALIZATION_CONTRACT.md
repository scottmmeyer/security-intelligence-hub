# Outcome Visualization Contract

## Purpose

Define deterministic UI-facing contracts for replay and comparative performance
visualization without introducing lookahead bias.

## Filters

Required user filters:

- market_cap_bucket: MEGA | LARGE | MID | SMALL | MICRO
- geography: US | INTERNATIONAL
- industry: ALL by default, optional specific industry values later
- timeframe: initially 1 year
- strategy_mode: TOP_N_COMPOSITE_AT_START
- top_n: integer, default 20

## Graph Lines

Each replay produces up to four conceptual lines:

1. BENCHMARK
2. INVESTABLE_VEHICLE
3. FULL_UNIVERSE
4. TOP_N_STRATEGY

### Distinction Rules

- Benchmark is an analytical baseline and not necessarily directly investable.
- Investable vehicle is an ETF or fund proxy mapped to the category.
- Full universe is all eligible securities after filters at replay start date.
- Top-N strategy is a fixed basket chosen at start date and held to end date.

## Expected Data Shapes

### Replay Selection Input

- replay_id
- start_date
- end_date
- filter_market_cap_bucket
- filter_geography
- filter_industry
- selection_method
- top_n
- selected_symbols
- composite_score_snapshot_date

### Performance Series Row

- series_id
- replay_id
- series_type
- date
- value
- cumulative_return
- source

## Replay Semantics

Deterministic replay sequence:

1. Load analytical universe rows for start_date.
2. Apply category and industry filters.
3. Rank by composite_score descending; tie-break by symbol ascending.
4. Select top_n symbols.
5. Freeze selected basket through end_date.
6. Compare benchmark, investable vehicle, full-universe average, and top-N basket.

## No-Lookahead Rule

- Selection must only use analytical rows where snapshot_date == start_date.
- composite_score_snapshot_date must match start_date.
- Future scores or revised point-in-time rows cannot influence start basket.

## User-Visible Explanations

UI must clearly explain:

- benchmark vs investable vehicle distinction
- top-N is selected once at start and held
- full universe is category-filtered start-date universe
- missing market data can produce empty series rows
- no-lookahead policy is enforced for replay integrity

## Current Data Availability

Historical market data providers are currently interfaces/stubs.
Replay contracts are emitted even when series rows are empty so downstream UI
contracts remain stable.
