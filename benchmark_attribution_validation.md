# Benchmark Attribution Validation (01B-A)

## Test Suite

Primary:
- `.venv/bin/python -m pytest -q tests/test_pis_benchmark_attribution_01a.py`
- Result: `5 passed`

Regression slice:
- `.venv/bin/python -m pytest -q tests/test_pis_performance_attribution_01.py tests/test_pis_ui_phase1_dashboard.py tests/test_pis_benchmark_attribution_01a.py`
- Result: `21 passed`

## Validated Behaviors

1. Exact same-day alignment produces expected benchmark returns.
2. Weekend/non-trading canonical dates resolve via nearest-prior-trading-day alignment.
3. Benchmark return formula is correct.
4. Portfolio return formula uses canonical daily values only.
5. Excess return formula is correct.
6. Missing benchmark data behavior is deterministic and surfaced via `data_quality_status`.
7. CSV persistence header contract is stable.
8. API route contracts exist for returns/latest/summary endpoints.

## Endpoints Verified by Contract

- `/api/pis/benchmark-attribution/returns`
- `/api/pis/benchmark-attribution/latest`
- `/api/pis/benchmark-attribution-summary`

## Phase Boundary

Validated for 01B-A only (foundation). Source-level alpha ranking and benchmark dashboard rendering remain deferred.
