# Benchmark 01B-B Validation

## Commands

1. Benchmark attribution layers:

- .venv/bin/python -m pytest -q tests/test_pis_benchmark_attribution_01a.py tests/test_pis_benchmark_attribution_01b.py
- Result: 10 passed

2. Focused PIS regression including benchmark alpha:

- .venv/bin/python -m pytest -q tests/test_pis_performance_attribution_01.py tests/test_pis_ui_phase1_dashboard.py tests/test_pis_benchmark_attribution_01a.py tests/test_pis_benchmark_attribution_01b.py
- Result: 26 passed

## Coverage Highlights

- Recommendation-to-benchmark interval join by snapshot_date/prior_snapshot_date
- Recommendation excess-return math
- Source aggregation metrics
- Positive/negative alpha classification
- Exclusion of non-OK benchmark rows from headline summaries
- Preservation and auditability of non-OK rows
- API payload contract presence for recommendation/source/latest benchmark attribution endpoints

## Endpoints

- /api/pis/benchmark-attribution/recommendations
- /api/pis/benchmark-attribution/sources
- /api/pis/benchmark-attribution/latest

## Deferred Scope

Dashboard integration remains deferred to 01B-C.
