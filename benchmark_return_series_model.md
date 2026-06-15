# Benchmark Return Series Model (01B-A)

## Persistence Target

- `data/history/pis/benchmark_attribution/benchmark_return_series.csv`

## Row Contract

Fields:
- `snapshot_date`
- `prior_snapshot_date`
- `benchmark_symbol`
- `benchmark_entry_date`
- `benchmark_exit_date`
- `benchmark_entry_price`
- `benchmark_exit_price`
- `benchmark_return_pct`
- `portfolio_return_pct`
- `excess_return_pct`
- `alignment_policy`
- `data_quality_status`

## Interval Definition

Each row is computed over one canonical interval:
- `prior_snapshot_date -> snapshot_date`

Canonical rows are ordered newest-first and paired with their immediate prior row.

## Math

Benchmark return:

`benchmark_return_pct = (benchmark_exit_price - benchmark_entry_price) / benchmark_entry_price * 100`

Portfolio return:

`portfolio_return_pct = (current_portfolio_value - prior_portfolio_value) / prior_portfolio_value * 100`

Excess return:

`excess_return_pct = portfolio_return_pct - benchmark_return_pct`

## Data Quality Status

Current deterministic statuses:
- `OK`
- `MISSING_BENCHMARK_ENTRY`
- `MISSING_BENCHMARK_EXIT`
- `INVALID_BENCHMARK_BASE`
- `INVALID_PORTFOLIO_BASE`

## Benchmark Symbol

- Default symbol: `SPY`
