# Performance Data Inventory (PERF-VAL-01)

Date: 2026-06-17  
Scope: Inventory SIH inputs required to reconstruct 1-year return vs Fidelity

## Inventory Summary

| Data Domain | Source Path | Status | Notes |
|---|---|---|---|
| Canonical portfolio snapshots | data/history/pis/canonical/canonical_daily_snapshots.csv | AVAILABLE | PASS snapshots from 2026-05-21 through 2026-06-16 |
| PIS snapshot index | data/history/pis/pis_snapshot_index.csv | AVAILABLE | Rich snapshot metadata; includes portfolio_value/cash/equity per snapshot |
| Raw Fidelity position exports | incoming/portfolio/*.csv and data/portfolio_ingestion/archive/*.csv | AVAILABLE | Position-level exports with cost basis and daily/total gain/loss fields |
| Benchmark current store | data/current/benchmark_returns.csv | INSUFFICIENT | Placeholder TEST rows only |
| Benchmark history snapshots | data/history/benchmarks/benchmark_snapshots.csv | INSUFFICIENT | Header-only at time of validation |
| Benchmark outcomes | data/history/benchmarks/benchmark_outcomes.csv | INSUFFICIENT | Header-only at time of validation |
| Benchmark attribution intervals | data/history/pis/benchmark_attribution/benchmark_return_series.csv | PARTIAL | Portfolio interval returns exist; benchmark side mostly missing (MISSING_BENCHMARK_ENTRY) |
| Deposits/withdrawals ledger | No complete explicit ledger discovered | MISSING | Required for audited 1Y reconstruction |
| Dividends/distributions ledger | No complete explicit ledger discovered | MISSING | Required for audited total-return chaining |
| Cash balances over full 1Y | Partially present in snapshot files | PARTIAL | Not complete/continuous over 1Y horizon |
| Pending activity event ledger | No complete explicit ledger discovered | MISSING | Settlement timing impacts variance |

## Earliest Reliable Date

Earliest reliable canonical PASS snapshot date:
- 2026-05-21

Latest validated canonical PASS snapshot date:
- 2026-06-16

Effective reliable window:
- 26 calendar days
- 20 PASS snapshots

## Sufficiency for 1-Year Reconstruction

Assessment: NOT SUFFICIENT

Reasons:
- Canonical valuation history is far shorter than 1 year.
- No complete event ledger for deposits, withdrawals, dividends, distributions.
- Persisted benchmark series is not populated for production-quality 1Y reconciliation.
- Pending activity treatment is not represented as an auditable event-time return chain.

## Sufficiency for Short-Window Validation

Assessment: SUFFICIENT (with constraints)

What SIH can do now:
- Compute beginning/end snapshot return over available canonical history.
- Compute benchmark returns over same available window via market-data fetch.
- Compute short-window apparent alpha over same window.

## Data Readiness Conclusion

For full PERF-VAL-01 objective (Fidelity-like 1Y replication), SIH needs additional data foundation:
- 1Y+ canonical valuation continuity
- Flow/event ledger completeness
- Production-populated benchmark persistence
- Cash and pending-event timing policy formalization
