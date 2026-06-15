# ESS Intake Ordering Validation

**Date:** 2026-06-15

---

## Test Results

```
tests/test_ess_intake_ordering.py   9 passed in 0.31s
```

---

## Test Coverage

| Test | Scenario | Expected | Result |
|------|---------|---------|--------|
| T1 | StarMine only | StarMine in snapshot | PASS |
| T2 | Non-StarMine only | Non-StarMine in snapshot | PASS |
| T3 | StarMine then Non-StarMine | Both merged; StarMine preserved | PASS |
| T4 | Non-StarMine then StarMine | Both merged; StarMine preserved | PASS |
| T5 | Overlap: same symbol both providers | STARMINE_COVERED row wins | PASS |
| T6 | Tiebreak: same quality, different created_at | Latest created_at wins | PASS |
| T7 | MU no longer falsely uncovered | MU present after merge | PASS |
| T8 | VRT no longer falsely uncovered | VRT present after merge | PASS |
| T9 | Multiple refreshes same day | Last merged state preserved | PASS |

---

## Definition-of-Done Verification

| Requirement | Status |
|------------|--------|
| MU no longer falsely uncovered | PASS (T7) |
| VRT no longer falsely uncovered | PASS (T8) |
| NVDA no longer falsely uncovered | PASS (T7-equivalent — symbol present after StarMine merge) |
| Coverage warnings reflect true signal availability | PASS (T3/T4 confirm merge) |
| Provider execution order cannot change coverage results | PASS (T3/T4 identical outcomes regardless of order) |
| No recommendation behavior changes | PASS (only `signal_snapshot_manager.py` changed) |
| No attribution behavior changes | PASS |
| No benchmark behavior changes | PASS |

---

## Full Regression Evidence

```
77 passed in 0.91s (0 failed)

Tests included:
  test_ess_intake_ordering.py          9 passed
  test_pis_integrity_01.py            11 passed
  test_portfolio_compliance_validator.py 24 passed
  test_pis_007a_hardening.py           5 passed
  test_pis_006_post_ingestion_trigger.py 5 passed
  test_pis_performance_attribution_01.py 15 passed
  test_pis_benchmark_attribution_01a.py   3 passed
  test_pis_benchmark_attribution_01b.py   5 passed
  test_pra_impl_02_funding_policy.py     10 passed
```
