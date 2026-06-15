# ESS Intake Ordering — Regression Results

**Date:** 2026-06-15

---

## Test Execution

```
.venv/bin/python -m pytest tests/test_ess_intake_ordering.py \
  tests/test_pis_integrity_01.py \
  tests/test_portfolio_compliance_validator.py \
  tests/test_pis_007a_hardening.py \
  tests/test_pis_006_post_ingestion_trigger.py \
  tests/test_pis_performance_attribution_01.py \
  tests/test_pis_benchmark_attribution_01a.py \
  tests/test_pis_benchmark_attribution_01b.py \
  tests/test_pra_impl_02_funding_policy.py -q

77 passed in 0.91s
```

**PASS — 77/77 — 0 failures**

---

## New Tests (ESS-INTAKE-ORDERING-01)

```
tests/test_ess_intake_ordering.py   9 passed
```

## Regression

```
tests/test_pis_integrity_01.py                11 passed  (no regression)
tests/test_portfolio_compliance_validator.py  24 passed  (no regression)
tests/test_pis_007a_hardening.py               5 passed  (no regression)
tests/test_pis_006_post_ingestion_trigger.py   5 passed  (no regression)
tests/test_pis_performance_attribution_01.py  15 passed  (no regression)
tests/test_pis_benchmark_attribution_01a.py    3 passed  (no regression)
tests/test_pis_benchmark_attribution_01b.py    5 passed  (no regression)
tests/test_pra_impl_02_funding_policy.py      10 passed  (no regression)
```
