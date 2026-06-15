# Benchmark Engine Reuse Assessment

## Scope

Assess whether the existing legacy benchmark engine can be reused for PIS benchmark attribution.

Primary review target:
- [src/portfolio/outcome_tracker.py](src/portfolio/outcome_tracker.py)

Supporting benchmark infrastructure reviewed:
- [src/history/market_data_manager.py](src/history/market_data_manager.py)
- [src/replay/foundation_service.py](src/replay/foundation_service.py)
- [data/current/benchmark_returns.csv](data/current/benchmark_returns.csv)
- [data/history/benchmarks/benchmark_snapshots.csv](data/history/benchmarks/benchmark_snapshots.csv)
- [docs/issue_12c/issue_12c_benchmark_validation.md](docs/issue_12c/issue_12c_benchmark_validation.md)

## Q1. What benchmark calculations already exist?

The existing legacy engine in [src/portfolio/outcome_tracker.py](src/portfolio/outcome_tracker.py) already implements:
- SPY price fetch via `yfinance`
- adjusted-close based SPY return calculation
- nearest-prior-trading-day alignment fallback
- symbol return calculation over a fixed holding period
- excess return calculation as `symbol_return_pct - spy_return_pct`
- outcome status classification (`WIN`, `LOSS`, `FLAT`)
- summary aggregation by tier and class

The formula already present there is:
- `sym_ret = (sym_exit - sym_entry) / sym_entry * 100`
- `spy_ret = (spy_exit - spy_entry) / spy_entry * 100`
- `excess = sym_ret - spy_ret`

## Q2. Can they be reused inside PIS?

Yes, partially.

What is reusable:
- SPY fetch pattern
- adjusted-close handling
- nearest-prior-day alignment logic
- excess-return formula
- deterministic test style

What is not directly reusable:
- the current engine is detection-centric, not PIS snapshot-centric
- its storage lives under `data/derived/`, not `data/history/pis/`
- it measures symbol outcomes from dislocation detections, not portfolio and recommendation outcomes from canonical PIS history
- its API and dashboard surfaces are not part of the PIS stack

Conclusion:
- reuse the benchmark math and date-alignment primitives
- do not reuse the current module wholesale as the PIS benchmark engine

## Q3. What refactoring would be required?

Recommended refactor:

1. Extract benchmark price loading into a shared utility.
- Current code path: `fetch_price_history()` in [src/portfolio/outcome_tracker.py](src/portfolio/outcome_tracker.py)
- Desired result: reusable benchmark series loader for SPY

2. Extract date alignment helper into a shared utility.
- Current code path: `_nearest_price()` in [src/portfolio/outcome_tracker.py](src/portfolio/outcome_tracker.py)
- Desired result: shared date-window alignment for both legacy outcomes and PIS benchmark attribution

3. Build a PIS-specific benchmark attribution layer under `src/pis/`.
- Input model should be canonical daily PIS history plus attribution records
- Output model should persist under `data/history/pis/benchmark_attribution/`

4. Add a benchmark series persistence/read-model contract for PIS.
- Prefer reading SPY data from benchmark returns storage when production-ready
- fall back to direct SPY fetch only if that storage contract is not yet reliable

5. Keep the current legacy outcome engine isolated.
- It should remain valid for ISSUE-12 style detection outcome analysis
- It should not become the storage or API layer for PIS

## Q4. What benchmark data sources already exist?

Existing sources and status:
- [src/portfolio/outcome_tracker.py](src/portfolio/outcome_tracker.py): live SPY fetch from `yfinance` using adjusted close
- [src/history/market_data_manager.py](src/history/market_data_manager.py): generic benchmark return persistence contract
- [src/replay/foundation_service.py](src/replay/foundation_service.py): benchmark return provider integration for replay/foundation flows
- [data/current/benchmark_returns.csv](data/current/benchmark_returns.csv): placeholder only, not production-ready for PIS attribution
- [data/history/benchmarks/benchmark_snapshots.csv](data/history/benchmarks/benchmark_snapshots.csv): header only in current repo state

Practical conclusion:
- benchmark data support exists conceptually and architecturally
- the persisted benchmark history visible in this repo state is not yet a robust PIS-ready source of truth

## Q5. Can SPY attribution be implemented without creating a second benchmark pipeline?

Yes, if "second benchmark pipeline" means a separate parallel benchmark architecture.

Recommended approach:
- do not build a brand new benchmark subsystem
- extend the existing benchmark data foundation and reuse the legacy SPY fetch/alignment logic
- create only a PIS-specific attribution computation layer that consumes canonical PIS history and the shared SPY series

The clean implementation path is:
1. promote SPY series acquisition into a shared benchmark utility or provider
2. materialize daily SPY returns in the existing benchmark return storage contract
3. compute PIS portfolio return, recommendation return, and source return relative to that shared SPY series

So the answer is:
- no second benchmark pipeline is required
- a PIS-specific benchmark attribution layer is still required

## Recommendation

Reuse the benchmark math, fetch, and date-alignment primitives from the legacy engine, but implement benchmark attribution as a new module under `src/pis/` backed by the existing benchmark data foundation rather than by `data/derived/` legacy outputs.
