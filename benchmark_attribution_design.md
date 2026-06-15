# Benchmark Attribution Design (01B-A)

## Objective

Implement deterministic benchmark source ingestion and canonical-date-aligned return series for PIS.

## Scope Implemented

- SPY benchmark source abstraction
- Canonical interval benchmark return calculation
- Canonical interval portfolio return calculation
- Excess return calculation
- Deterministic nearest-prior-trading-day alignment
- Persistent benchmark return-series CSV
- Read APIs for returns/latest/summary

## Core Module

- `src/pis/benchmark_attribution.py`

Key capabilities:
- `CsvBenchmarkPriceProvider` reads benchmark prices from:
  - `data/current/benchmark_returns.csv`
  - `data/history/benchmarks/benchmark_snapshots.csv`
- Optional online fallback provider (`YFinanceBenchmarkPriceProvider`) is available but off by default.
- `compute_benchmark_return_series(...)` computes and persists canonical interval rows.
- `pis_benchmark_returns(...)`, `pis_benchmark_latest(...)`, and `pis_benchmark_summary(...)` expose read-model payloads.

## Data Inputs

- Canonical daily snapshots (`data/history/pis/canonical/canonical_daily_snapshots.csv`)
- Benchmark current history (`data/current/benchmark_returns.csv`)
- Benchmark historical snapshots (`data/history/benchmarks/benchmark_snapshots.csv`)

## API Surface

Added in `scripts/run_outcome_ui.py`:
- `/api/pis/benchmark-attribution/returns`
- `/api/pis/benchmark-attribution/latest`
- `/api/pis/benchmark-attribution-summary`

## Out of Scope (Deferred)

- Recommendation-level benchmark excess attribution
- Source-level alpha ranking
- Full benchmark dashboard rendering sections

These remain 01B-B/01B-C work.
