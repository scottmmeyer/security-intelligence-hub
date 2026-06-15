# Benchmark Integration Assessment
**Project:** PIS-001
**Date:** 2026-06-12

## Recommendation

Benchmark history should remain owned by SIH.
PIS should consume benchmark history through SIH APIs or SIH-owned history artifacts.

## Why SIH Should Own Benchmarks

- SIH already owns market-data history and benchmark persistence patterns.
- Benchmark storage belongs with the platform that already manages historical market inputs.
- Keeping benchmark ownership in SIH prevents duplication and version drift.
- PIS should remain focused on portfolio outcomes, not market data ingestion.

## Relevant SIH Surfaces

Current SIH infrastructure already includes:
- benchmark return persistence in `data/current/benchmark_returns.csv`
- benchmark history partitions under `data/history/benchmarks/`
- benchmark provider interfaces in replay/history code
- replay and benchmark scaffolding already used elsewhere in SIH

## Recommended Benchmarks

For PIS Phase 1, use:
- S&P 500
- Total Market
- ACWI
- AGG

## Role of Each Benchmark

### S&P 500
Primary default benchmark for concentrated equity portfolios.

### Total Market
Secondary domestic equity reference.

### ACWI
International context reference.

### AGG
Fixed-income reference for cash or bond allocation context.

## Ownership Model

### SIH responsibilities
- fetch benchmark market data
- normalize benchmark history
- persist benchmark history
- expose benchmark history to downstream consumers

### PIS responsibilities
- request benchmark history
- compare portfolio vs benchmark
- compute alpha and contribution views
- display benchmark-relative outcomes

## Interface Recommendation

Use a read-only contract such as:
- benchmark history API
- benchmark history CSV artifact
- benchmark provider abstraction

PIS should not re-fetch or recompute benchmark history independently.

## Conclusion

Benchmark history should remain in SIH because it is part of the shared market-data substrate. PIS should treat benchmarks as an external read-only dependency.
