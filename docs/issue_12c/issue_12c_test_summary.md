# ISSUE-12C — Test Summary

**Date:** June 5, 2026  
**Test file:** `tests/test_issue_12bc_outcome_tracker.py`  
**Tests:** 30 | **Result:** 30 passed, 0 failed

---

## Coverage Matrix

### `_outcome_status()` Tests (6)

| Test | Scenario | Expected | Result |
|------|----------|----------|--------|
| `test_outcome_status_win` | excess = +5.0% | WIN | ✅ |
| `test_outcome_status_loss` | excess = −3.0% | LOSS | ✅ |
| `test_outcome_status_flat_positive` | excess = +0.1% | FLAT | ✅ |
| `test_outcome_status_flat_negative` | excess = −0.1% | FLAT | ✅ |
| `test_outcome_status_boundary_win` | excess = +0.26% | WIN | ✅ |
| `test_outcome_status_boundary_loss` | excess = −0.26% | LOSS | ✅ |

### `_nearest_price()` Tests (4)

| Test | Scenario | Expected | Result |
|------|----------|----------|--------|
| `test_nearest_price_exact_match` | date in map | returns exact | ✅ |
| `test_nearest_price_fallback_prior_day` | date -1 in map | returns prior | ✅ |
| `test_nearest_price_empty_returns_none` | empty map | None | ✅ |
| `test_nearest_price_too_far_back_returns_none` | date -7 in map | None | ✅ |

### Immature Detection Exclusion (3)

| Test | Scenario | Expected | Result |
|------|----------|----------|--------|
| `test_immature_detections_excluded_30d` | 20-day-old detection for 30d window | excluded | ✅ |
| `test_immature_detections_excluded_90d` | 60-day-old detection for 90d window | excluded | ✅ |
| `test_mature_detection_included_90d` | 95-day-old detection for 90d window | included | ✅ |

### Math Validation (2)

| Test | Scenario | Expected | Result |
|------|----------|----------|--------|
| `test_excess_return_math` | DELL +10%, SPY +5% → excess +5%, WIN | exact | ✅ |
| `test_negative_excess_return_is_loss` | DELL −5%, SPY +5% → excess −10%, LOSS | LOSS | ✅ |

### Missing Price Handling (3)

| Test | Scenario | Expected | Result |
|------|----------|----------|--------|
| `test_missing_spy_price_excludes_row` | no SPY prices | excluded | ✅ |
| `test_missing_symbol_price_excludes_row` | no symbol outcome price | excluded | ✅ |
| `test_no_price_at_detection_excludes_row` | empty price_at_detection | excluded | ✅ |

### Multi-class Preservation (1)

| Test | Scenario | Expected | Result |
|------|----------|----------|--------|
| `test_multi_class_preserved_in_output` | A1\|D1\|B2 active_classes | preserved exactly | ✅ |

### Empty Cohort (1)

| Test | Scenario | Expected | Result |
|------|----------|----------|--------|
| `test_empty_detections_file_returns_empty` | missing file | [] | ✅ |

### Summary Generation (2)

| Test | Scenario | Expected | Result |
|------|----------|----------|--------|
| `test_summary_by_tier_correct` | 3 MODERATE rows (2 WIN, 1 LOSS) | hit_rate ≈ 66.67% | ✅ |
| `test_summary_json_written` | 1 HC row | JSON with by_tier + by_class | ✅ |

### Detection Persistence (3)

| Test | Scenario | Expected | Result |
|------|----------|----------|--------|
| `test_persist_detections_writes_csv` | DELL MODERATE + PSX NONE | 1 row written (DELL only) | ✅ |
| `test_persist_detections_deduplication` | same (date, symbol, tier) twice | 2nd call returns 0 | ✅ |
| `test_persist_none_tier_not_recorded` | NVDA NONE | 0 rows, file not created | ✅ |

### Helpers (5)

| Test | Scenario | Expected | Result |
|------|----------|----------|--------|
| `test_safe_median_odd` | [1,3,5] | 3.0 | ✅ |
| `test_safe_median_even` | [1,3] | 2.0 | ✅ |
| `test_safe_median_empty_returns_none` | [] | None | ✅ |
| `test_safe_mean_basic` | [1,2,3] | 2.0 | ✅ |
| `test_safe_mean_empty_returns_none` | [] | None | ✅ |
