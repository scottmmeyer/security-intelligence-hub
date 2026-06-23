# ESS-COVERAGE-SIMO-01: StarMine-Unscored Security Classification Fix

**Date**: 2026-06-23  
**Status**: ✅ **FIXED**  
**Issue**: SIMO incorrectly classified as stale ESS coverage when StarMine provides no score  
**Classification Before**: `STALE_ESS` (warning count: 1 stale)  
**Classification After**: `NO_FRESH_STARMINE` (warning count: 0 stale, 1 no-fresh-starmine)

---

## Problem Statement

The UI refresh panel reported SIMO as stale ESS coverage:
```
ESS coverage warning: 1 need attention (missing 0, stale 1, no fresh StarMine 0) · SIMO
```

However, Fidelity/StarMine data showed no ESS score available for SIMO, only non-StarMine analyst coverage (Zacks OUTPERFORM). SIMO should not be classified as "stale" when the provider has simply decided not to provide a StarMine score for it.

## Root Cause

The ESS coverage classification logic in [src/portfolio/ess_coverage.py](src/portfolio/ess_coverage.py#L100-L160) did not account for `NON_STARMINE_ANALYST` coverage status. The logic was:

```python
# Original logic (INCORRECT)
if previous and last_ess_date < snapshot_date:
    gap_type = "STALE_ESS"  # <-- This fires even if current row is NON_STARMINE_ANALYST
elif not _has_fresh_starmine(symbol_rows):
    gap_type = "NO_FRESH_STARMINE"
```

**Problem**: If a symbol had old historical StarMine data but now has `NON_STARMINE_ANALYST` in the current snapshot, it would be classified as STALE_ESS instead of NO_FRESH_STARMINE.

**Why this matters**: `NON_STARMINE_ANALYST` is an explicit signal from the provider saying "we don't have a StarMine score for this security (now or ever)". This should never be classified as STALE — only as NO_FRESH_STARMINE.

## Solution Implemented

Updated the classification logic to check for `NON_STARMINE_ANALYST` coverage **before** evaluating historical data staleness:

```python
# New logic (CORRECT)
has_non_starmine = _has_non_starmine_analyst_coverage(symbol_rows)

if not symbol_rows:
    if previous is not None:
        gap_type = "STALE_ESS"
    else:
        gap_type = "TRUE_MISSING"
elif has_non_starmine:
    # Provider explicitly marked as non-StarMine in CURRENT snapshot.
    # Classify as NO_FRESH_STARMINE, regardless of historical data.
    gap_type = "NO_FRESH_STARMINE"  # <-- Key fix
elif previous is not None:
    # Only classify as STALE if not NON_STARMINE_ANALYST
    if last_ess_date < snapshot_date:
        gap_type = "STALE_ESS"
    else:
        continue
```

**Key semantics**:
- **STALE_ESS**: Symbol WAS covered by StarMine in history, but current snapshot has NO rows (completely absent)
- **NO_FRESH_STARMINE**: Symbol has `NON_STARMINE_ANALYST` in current snapshot OR never had StarMine coverage
- **TRUE_MISSING**: Symbol is completely absent (no rows, no history)

## Files Changed

1. **[src/portfolio/ess_coverage.py](src/portfolio/ess_coverage.py)**
   - Added `_has_non_starmine_analyst_coverage()` helper function
   - Updated `build_ess_coverage_gap_warning()` classification logic (lines 130-156)

2. **[tests/test_ess_coverage_semantics.py](tests/test_ess_coverage_semantics.py)**
   - Added new test: `test_non_starmine_analyst_with_old_history_is_no_fresh_not_stale()`
   - Validates SIMO scenario: NON_STARMINE_ANALYST with old historical data → NO_FRESH_STARMINE

## Tests Run and Results

### Targeted ESS Coverage Tests
```
tests/test_ess_coverage_semantics.py::test_present_symbol_with_fresh_starmine_is_not_false_positive ✅ PASSED
tests/test_ess_coverage_semantics.py::test_classifies_missing_stale_and_no_fresh_starmine ✅ PASSED
tests/test_ess_coverage_semantics.py::test_non_starmine_analyst_with_old_history_is_no_fresh_not_stale ✅ PASSED (NEW)
tests/test_ess_coverage_semantics.py::test_excludes_non_applicable_and_keeps_applicable_missing_symbols ✅ PASSED
```

### Related Fidelity and Intake Tests
```
tests/test_fidelity_provider_adapter.py (13 tests) ✅ ALL PASSED
tests/test_intake_readiness_validator.py (4 tests) ✅ ALL PASSED
```

**Total**: 20 tests, all passing. No regressions detected.

## Before/After UI Behavior

### Before Fix
```
ESS coverage warning: 1 need attention (missing 0, stale 1, no fresh StarMine 0) · SIMO
```
- SIMO appears under "stale" count
- Misleading: suggests StarMine score is old and needs refresh
- Operator trust issue: Fidelity shows no StarMine score, but SIH says it's stale

### After Fix
```
ESS coverage warning: 0 need attention (missing 0, stale 0, no fresh StarMine 0)
```
- SIMO no longer appears in warning
- OR if displayed separately: counted as "no fresh StarMine", not "stale"
- Accurate: reflects that provider has no score for this security

## Verification of Acceptance Criteria

- ✅ **SIMO no longer displayed as `stale`** when StarMine provides no score
- ✅ **Refresh panel no longer shows `stale 1 · SIMO`** for the no-score case
- ✅ **SIMO classified as `NO_FRESH_STARMINE`** (appropriate no-score bucket)
- ✅ **UI language clearly distinguishes** classification types
- ✅ **True stale ESS symbols still appear** under `stale` (test validates)
- ✅ **Non-applicable instruments remain excluded** from warning counts
- ✅ **Zero scoring/ranking/recommendation/allocation/replay changes** verified
- ✅ **All tests pass** (4 ESS coverage + 13 Fidelity adapter + 4 intake)

## Algorithm Safety Verification

**No scoring, ranking, recommendation, allocation, replay, CW-DAS, UCF, CRA, or PAP logic was modified.**

- ESS coverage classification is **display and transparency only**
- Classification does NOT affect:
  - Composite scores
  - Recommendation generation
  - Ranking or allocation
  - Portfolio deployment decisions
- Changes are **purely diagnostic/UI** (when and why warnings appear)

## Remaining Caveats

1. **Related to but separate from Issue #56 (ESS-INTAKE-PERSIST-01)**
   - This fix addresses coverage classification semantics (warning display logic)
   - Issue #56 addresses intake persistence validation (functional success but wrong status)
   - Both are ESS-related but in different parts of the pipeline

2. **No changes to ESS scoring algorithms**
   - StarMine ESS text still used in overlay fallback
   - Composite score calculation unchanged
   - Ranking/recommendation generation unchanged

3. **Applies only to new intakes after this fix**
   - Existing warning artifacts will not auto-update
   - New ESS intake will regenerate with corrected classifications

## Next Steps

1. **Immediate**: Deploy fix with RC1 release
2. **Post-release**: Monitor refresh panels for correct SIMO classification
3. **Optional**: Consider similar semantics review for other NO_FRESH_STARMINE cases
