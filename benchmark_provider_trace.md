# PERFORMANCE-ATTRIBUTION-01E Phase A - Benchmark Provider Trace

## Scope

Traced provider and lookup flow in:
- src/pis/benchmark_attribution.py
- scripts/run_outcome_ui.py

## Provider Trace

1. PIS benchmark routes call pis_benchmark_* functions.
2. compute_benchmark_return_series uses CsvBenchmarkPriceProvider by default.
3. CsvBenchmarkPriceProvider loads and merges two local CSV inputs:
   - data/current/benchmark_returns.csv (key field: symbol_or_index)
   - data/history/benchmarks/benchmark_snapshots.csv (key field: benchmark_symbol)
4. Symbol normalization is applied with strip().upper() in both loaders.
5. Benchmark lookup key is config.benchmark_symbol, default SPY.
6. Date resolution uses NEAREST_PRIOR_TRADING_DAY via _nearest_prior_date.
7. Optional online fallback exists (YFinanceBenchmarkPriceProvider) but only if allow_online_fallback=True.
8. API routes do not enable online fallback, so local CSVs are authoritative for runtime.

## Answers

Q1. What file(s) are expected to contain SPY data?
- data/current/benchmark_returns.csv
- data/history/benchmarks/benchmark_snapshots.csv

Q2. What symbol key is expected?
- SPY (uppercase after normalization).

Q3. Is symbol normalization occurring?
- Yes. Inputs and requested symbol are normalized using strip().upper().

Q4. Is SPY data present but mismatched?
- Before repair: yes, provider data was mismatched to IDX test rows and no SPY rows were present.
- After repair: SPY is present in data/current/benchmark_returns.csv.

Q5. Is SPY data completely absent?
- Before repair: effectively absent for provider lookup (0 SPY rows).
- After repair: present with 22 SPY rows (2026-05-12 to 2026-06-11).

## Root Cause Statement (Provider Layer)

The benchmark engine expected SPY in local provider CSVs, but the active current provider file had only IDX test rows and snapshots file had no SPY rows, so all interval entry lookups failed.
