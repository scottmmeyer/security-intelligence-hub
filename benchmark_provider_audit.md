# PERFORMANCE-ATTRIBUTION-01B-D Phase 4 Audit

## Scope

Inspected:
- src/pis/benchmark_attribution.py
- scripts/run_outcome_ui.py
- data/current/benchmark_returns.csv
- data/history/benchmarks/benchmark_snapshots.csv
- data/history/pis/canonical/canonical_daily_snapshots.csv
- data/history/pis/benchmark_attribution/benchmark_return_series.csv

## Answers

Q14. Where does SPY data come from?
- From CsvBenchmarkPriceProvider in src/pis/benchmark_attribution.py.
- It loads and merges:
  - data/current/benchmark_returns.csv using symbol_or_index
  - data/history/benchmarks/benchmark_snapshots.csv using benchmark_symbol
- API routes call pis_benchmark_* defaults, which use benchmark_symbol = SPY and do not pass allow_online_fallback=True.

Q15. Was SPY history successfully loaded?
- No.
- SPY row count in data/current/benchmark_returns.csv: 0.
- SPY row count in data/history/benchmarks/benchmark_snapshots.csv: 0.

Q16. How many benchmark price points are available?
- For required symbol SPY: 0 points.
- Total rows in current provider file: 2 (both symbol_or_index = IDX, not SPY).
- Snapshot provider file contains 0 lines.

Q17. Earliest benchmark date available?
- For SPY: not available (no rows).
- In current provider file (non-SPY IDX rows): 2025-05-13.

Q18. Latest benchmark date available?
- For SPY: not available (no rows).
- In current provider file (non-SPY IDX rows): 2026-05-13.

Q19. Do benchmark dates cover canonical portfolio dates?
- For SPY: No, because SPY dataset is empty.
- Canonical date window is 2026-05-21 through 2026-06-11.

Q20. Is nearest-prior-trading-day alignment succeeding? Provide examples.
- No. It is failing for all intervals.
- Examples from benchmark_return_series.csv:
  - 2026-06-11 vs 2026-06-10: entry=blank, exit=blank, status=MISSING_BENCHMARK_ENTRY
  - 2026-06-10 vs 2026-06-09: entry=blank, exit=blank, status=MISSING_BENCHMARK_ENTRY
  - 2026-06-09 vs 2026-06-08: entry=blank, exit=blank, status=MISSING_BENCHMARK_ENTRY

## Evidence Notes

- benchmark_return_series.csv has 16/16 rows with MISSING_BENCHMARK_ENTRY.
- The provider path is wired correctly, but required SPY input data is absent.
