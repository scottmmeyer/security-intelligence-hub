# PERFORMANCE-ATTRIBUTION-01B-D Phase 5 Root Cause

## Root Cause Selection

Selected: G. Multiple causes

Contributing causes:
1. Benchmark provider is effectively empty for the required benchmark symbol (SPY).
2. Current benchmark file is populated with placeholder symbol IDX rows instead of SPY rows.

## Answers

Q21. What exact condition causes all 28 rows to be excluded?
- In compute_benchmark_return_series, _nearest_prior_date cannot resolve an entry price for SPY because prices_by_date for SPY is empty.
- This sets each interval data_quality_status to MISSING_BENCHMARK_ENTRY.
- Recommendation attribution propagates that status to every joined recommendation row.
- Result: 28/28 recommendation rows excluded.

Q22. Is benchmark attribution mathematically valid once data is available?
- Yes.
- Focused benchmark test suite result: 10 passed (tests/test_pis_benchmark_attribution_01a.py + tests/test_pis_benchmark_attribution_01b.py).

Q23. Is Issue #50 truly complete?
- Not operationally complete.
- Infrastructure and API wiring are present, but benchmark alpha outputs are not meaningful with current benchmark data state.

Q24. What specific fix is required?
- Smallest corrective action:
  1. Populate benchmark provider data for SPY (symbol_or_index = SPY and/or benchmark_symbol = SPY) across the canonical window, including at least one prior trading day at or before 2026-05-21 and coverage through 2026-06-11.
  2. Refresh benchmark attribution artifacts (benchmark_return_series.csv, recommendation_benchmark_records.csv, source_benchmark_summary.csv).
- No benchmark calculation code change is required based on this audit.

## Why This Explains Current Symptoms

- Included Rows = 0 / Excluded Rows = 28: every recommendation row inherits non-OK status.
- Benchmark Return = 0.00%: benchmark returns are zeroed when entry/exit prices are unresolved.
- Alpha rankings empty: ranking logic uses only included OK rows; there are none.
