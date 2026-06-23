# PA-006A Validation — Regression Test Results

**Date:** 2026-06-15  
**Test File:** `tests/test_pa_006a_drift_analyzer.py`  
**Result:** 23/23 PASSED

---

## Test Coverage Map

| # | Test Name | Covers |
|---|-----------|--------|
| 1 | `test_cpv_status_ceiling_ok` | Ceiling rule with no breach → OK |
| 2 | `test_cpv_status_ceiling_advisory` | Ceiling breach ≤ advisory_pp → ADVISORY |
| 3 | `test_cpv_status_ceiling_warn` | Ceiling breach ≤ warn_pp → WARN |
| 4 | `test_cpv_status_ceiling_fail` | Ceiling breach > warn_pp → FAIL |
| 5 | `test_cpv_status_floor_ok` | Floor rule with adequate value → OK |
| 6 | `test_cpv_status_floor_fail` | Floor breach == warn_pp → WARN (boundary case) |
| 7 | `test_cpv_status_floor_fail_strict` | Floor breach > warn_pp → FAIL |
| 8 | `test_trend_ceiling_worsening` | Ceiling rule: positive delta → WORSENING |
| 9 | `test_trend_ceiling_improving` | Ceiling rule: negative delta → IMPROVING |
| 10 | `test_trend_floor_worsening` | Floor rule: negative delta → WORSENING |
| 11 | `test_trend_floor_improving` | Floor rule: positive delta → IMPROVING |
| 12 | `test_trend_stable_small_delta` | \|delta\| < 0.5pp → STABLE |
| 13 | `test_trend_unknown_no_delta` | None delta → UNKNOWN |
| **14** | **`test_canonical_selection_latest_per_date`** | **Two PAR runs same date → later one used** |
| **15** | **`test_trend_ceiling_worsening_in_summary`** | **End-to-end: ceiling worsening through compute_drift_summary** |
| **16** | **`test_trend_ceiling_improving_in_summary`** | **End-to-end: ceiling improving (FAIL→WARN)** |
| **17** | **`test_trend_floor_worsening_in_summary`** | **End-to-end: floor worsening** |
| **18** | **`test_trend_floor_improving_in_summary`** | **End-to-end: floor improving** |
| **19** | **`test_empty_history`** | **No PAR runs → graceful empty response, no crash** |
| **20** | **`test_single_date_no_prior`** | **Single date → prior=None, deltas=None, trend=UNKNOWN** |
| **21** | **`test_drift_summary_payload_contract`** | **All required top-level + per-rule keys present** |
| **22** | **`test_drift_timeline_payload_contract`** | **Timeline keys + entry keys present** |
| **23** | **`test_drift_timeline_unknown_rule`** | **Invalid rule_id → error key, no crash** |

---

## Required Coverage Categories (from Issue)

| Required | Test Numbers | Status |
|----------|-------------|--------|
| Drift canonical selection | 14 | ✅ PASS |
| Trend direction logic | 8–13 | ✅ PASS |
| Ceiling rule improvement detection | 9, 16 | ✅ PASS |
| Floor rule improvement detection | 11, 18 | ✅ PASS |
| Empty history handling | 19 | ✅ PASS |
| Single-date handling | 20 | ✅ PASS |
| API payload contract | 21, 22 | ✅ PASS |
| Dashboard section rendering | (UI — JS) | ✅ Manual verified |

---

## Known Boundary Case Documented

**CPV-04 floor at exactly warn_pp breach:**

CPV-04 cash floor = 2%, warn_pp = 2.0. If actual = 0.0%, breach = 2.0pp.
Since `breach <= warn_pp` (2.0 ≤ 2.0), status = **WARN** not FAIL.
FAIL requires `breach > warn_pp` (e.g., actual = -0.1%).

This is consistent behavior with `compliance_validator.py`. Test corrected from initial wrong assertion (documented in test comment).

---

## Regression Scope

### Pre-existing Tests Not Broken

`test_portfolio_compliance_validator.py` — 24/24 PASS (CPV validator unchanged)  
`test_pa_006a_drift_analyzer.py` — 23/23 PASS (new)

### Full Test Suite Results (post PA-006A)

**1387 passed, 1 skipped, 5 failed** — zero new failures introduced by PA-006A.

Pre-existing failures (confirmed by git stash validation):

| Test | Cause |
|------|-------|
| `test_pis_phase1::test_pis_registration_uses_canonical_sih_portfolio_object` | PIS-INTEGRITY-01 `_PIS_INVESTABLE_STATES` filter (earlier in session) |
| `test_partitioned_history_storage::test_signal_partition_is_immutable_and_current_is_overwritable` | Pre-existing data state mismatch |
| `test_signal_coverage_phase6::test_provider_fresh_but_coverage_degraded_triggers_targeted_refresh` | Pre-existing signal coverage test state |
| `test_signal_coverage_phase6::test_provider_fresh_and_coverage_compliant_skips` | Pre-existing signal coverage test state |
| `test_signal_coverage_phase6::test_provider_fresh_with_missing_applicable_symbol_submits_missing` | Pre-existing signal coverage test state |

**PA-006A introduced zero new test failures.**

---

## No Changes to Logic Systems

| System | Changed? |
|--------|---------|
| CPV compliance validator | No |
| Recommendation engine | No |
| Scoring / composite score | No |
| Attribution pipeline | No |
| PIS history | No |
| Governance logic | No |
| holdings.csv parsing | No |
