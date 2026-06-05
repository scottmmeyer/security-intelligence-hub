# Phase 23.6B.2 — Test Results

**Date:** 2026-06-04  
**Command:** `PYTHONPATH=. .venv/bin/python3 -m pytest tests/test_cra_phase_23_6a.py -v`

---

## New Tests Added: TestNonTradeableExclusion (9 tests)

| Test | Result |
|------|--------|
| `test_spaxx_excluded_as_cash_equivalent` | PASS |
| `test_pending_activity_excluded_by_operational_state` | PASS |
| `test_closed_position_excluded` | PASS |
| `test_accounting_adjustment_excluded` | PASS |
| `test_non_analyzable_excluded` | PASS |
| `test_safe_to_offset_excluded` | PASS |
| `test_active_equity_still_included` | PASS |
| `test_missing_operational_state_treated_as_active` | PASS |
| `test_bearish_spaxx_still_excluded` | PASS |

## New Tests Added: TestTierAwareAllocation (6 tests)

| Test | Result |
|------|--------|
| `test_multiple_targets_with_large_pool` | PASS |
| `test_no_target_exceeds_warn_threshold` | PASS |
| `test_rank_order_preserved_across_tiers` | PASS |
| `test_per_candidate_cap_20pct` | PASS |
| `test_hca_candidates_receive_allocation` | PASS |
| `test_small_pool_still_works` | PASS |

## Updated Tests

| Test | Change | Result |
|------|--------|--------|
| `test_proportional_cap_limits_single_target` | Updated assertion from 50% → 20% cap | PASS |
| `test_pending_activity_excluded_by_operational_state` | Reflects real data (ACTIVE_POSITION) + pattern exclusion | PASS |

---

## CRA Suite Total: 78 tests, 0 failures

## Full Suite: 943 passed, 1 skipped, 0 failed

Zero regressions.
