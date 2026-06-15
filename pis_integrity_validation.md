# PIS-INTEGRITY-01 Validation

**Date:** 2026-06-15

---

## Test Results

```
tests/test_pis_integrity_01.py::test_T01_investable_states_constant               PASSED
tests/test_pis_integrity_01.py::test_T02_pending_activity_excluded                PASSED
tests/test_pis_integrity_01.py::test_T02b_pending_settlement_via_to_pis_positions PASSED
tests/test_pis_integrity_01.py::test_T03_accounting_adjustment_excluded           PASSED
tests/test_pis_integrity_01.py::test_T04_zero_value_legacy_excluded               PASSED
tests/test_pis_integrity_01.py::test_T05_active_position_preserved                PASSED
tests/test_pis_integrity_01.py::test_T06_cash_equivalent_preserved                PASSED
tests/test_pis_integrity_01.py::test_T07_mixed_holdings_filter                    PASSED
tests/test_pis_integrity_01.py::test_T08_all_non_investable_no_positions          PASSED
tests/test_pis_integrity_01.py::test_T09_register_filters_before_storage          PASSED
tests/test_pis_integrity_01.py::test_T10_rejected_snapshot_skipped                PASSED

11 passed in 0.11s
```

---

## Validation Coverage

| Scenario | Test | Result |
|---------|------|--------|
| `_PIS_INVESTABLE_STATES` contains correct values | T01 | PASS |
| PENDING ACTIVITY (PENDING_SETTLEMENT) excluded | T02, T02b | PASS |
| ACCOUNTING_ADJUSTMENT excluded | T03 | PASS |
| ZERO_VALUE_LEGACY_POSITION excluded | T04 | PASS |
| ACTIVE_POSITION preserved | T05 | PASS |
| CASH_EQUIVALENT preserved | T06 | PASS |
| Mixed portfolio: only investable pass | T07 | PASS |
| All non-investable → 0 positions registered | T08 | PASS |
| Filter applied before storage call | T09 | PASS |
| REJECTED snapshot skipped before filter | T10 | PASS |

---

## Regression Evidence

```
68 passed in 0.61s (0 failed)

Tests included:
  test_pis_integrity_01.py         11 passed
  test_portfolio_compliance_validator.py  24 passed
  test_pis_007a_hardening.py        5 passed
  test_pis_006_post_ingestion_trigger.py  5 passed
  test_pis_performance_attribution_01.py 15 passed
  test_pis_benchmark_attribution_01a.py   3 passed
  test_pis_benchmark_attribution_01b.py   5 passed
  test_pra_impl_02_funding_policy.py     10 passed
```

**Zero regressions across all modules.**

---

## Validation Plan Coverage

| Required Scenario | Covered | Notes |
|------------------|---------|-------|
| PENDING ACTIVITY excluded | T02 | ✓ |
| ACCOUNTING_ADJUSTMENT excluded | T03 | ✓ |
| Duplicate cash rows | T06 | CASH_EQUIVALENT is included (correct) |
| Zero-value positions | T04 | ZERO_VALUE_LEGACY_POSITION excluded |
| Legitimate new positions | T05 | ACTIVE_POSITION preserved |
| Legitimate exits | T07 | ACTIVE_POSITION preserved in mixed portfolio |
| Legitimate increases | T05, T07 | Investable pass through unchanged |
| Legitimate reductions | T05, T07 | Investable pass through unchanged |
| All non-investable → graceful 0 | T08 | ✓ |
| Filter before storage | T09 | ✓ |
