# PIS-006 Regression Results

**Date:** 2026-06-15

---

## PIS-006 New Tests

```
tests/test_pis_006_post_ingestion_trigger.py  5 passed
```

## Focused Regression Suite

```
tests/test_pis_performance_attribution_01.py    PASS
tests/test_pis_benchmark_attribution_01a.py     PASS
tests/test_pis_benchmark_attribution_01b.py     PASS
tests/test_pra_impl_02_funding_policy.py        PASS

23 passed in 0.46s
```

## Total

```
28 passed, 0 failed
```

## Regression Surface Confirmed

`src/portfolio/runner.py` was the only file modified. The change is additive:
- New helper function `_trigger_pis_refresh_background()`
- One conditional call `if pis_result.registered: _trigger_pis_refresh_background(...)`

No existing function signatures, return values, or logic branches were altered. All 23 pre-existing regression tests pass without modification.
