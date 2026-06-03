# Cash Governance Implementation Trace — Phase 22D.6

**Phase**: 22D.6 — Strategic Cash Governance Implementation  
**Generated**: 2026-06-02  
**Status**: IMPLEMENTATION COMPLETE  
**Mandate**: CONCENTRATED_ALPHA

---

## 1. Problem Statement

Phase 22D.5 identified that `compute_deployable_cash()` used a hard-coded governance floor
(`MIN_CASH_PCT = 2.0%`) as its deployment threshold. The CONCENTRATED_ALPHA mandate's
strategic cash target is 7.0%. Because these evolved independently with no integration,
the system offered $31,683 as deployable (cash above 2%) instead of the correct $7,894
(cash above 7%).

**Before fix**: Deploy from 8.66% → 2.00% = $31,683 deployable  
**After fix**: Deploy from 8.66% → 7.00% = $7,894 deployable

---

## 2. Design Decision (Option 4 — Approved)

Add `mandate_cash_target_pct: float` as a required parameter to `compute_deployable_cash()`.
Compute effective floor as `max(MIN_CASH_PCT, mandate_cash_target_pct)`. Pass mandate's
CASH node target at the call site in `runner.py`.

**Rationale for Option 4 over alternatives**:
- Option 1 (raise MIN_CASH_PCT globally): would break non-CONCENTRATED_ALPHA mandates
- Option 2 (separate function): code duplication with no benefit
- Option 3 (look up internally): breaks separation of concerns; function would need mandate context
- Option 4 (parameter at call site): surgical, mandate-agnostic, fail-closed, zero new loading

---

## 3. Files Modified

### 3.1 `src/portfolio/deployment_queue.py`

**Function**: `compute_deployable_cash()`

**Change**: Added required `mandate_cash_target_pct: float` parameter.
- No default value → TypeError at all existing call sites if not updated (fail-closed pattern)
- Effective floor = `max(MIN_CASH_PCT, mandate_cash_target_pct)`
- `MIN_CASH_PCT = 2.0` remains unchanged — governance hard minimum
- Added 4 new keys to returned dict:
  - `mandate_cash_target_pct`: the mandate target used as input
  - `effective_floor_pct`: `max(MIN_CASH_PCT, mandate_cash_target_pct)`
  - `excess_mv`: cash MV above mandate target (can be negative)
  - `excess_pct`: excess as % of total MV

**Backward compatibility**: Intentionally breaking. All call sites must be updated.
As of this commit, there is one call site: `runner.py:713`.

### 3.2 `src/portfolio/runner.py`

**Call site**: line 713 (formerly 3-line call, now 9-line block)

**Change**: Extract `_cash_target_pct` from `archetype_targets.get("CASH")` — the
`archetype_targets` dict is already populated at line 568 (`load_archetype_targets(mandate_type)`).
Raise `ValueError` if CASH node is missing from the mandate profile (fail-closed).

**Key insight**: No new loading was required. The archetype targets dict is already in scope
at the call site, loaded 145 lines earlier in the same function.

### 3.3 `tests/test_7_5b_deployment_queue.py`

**Existing tests updated** (`TestDeployableCash`):
- `test_deployable_above_floor`: updated to pass `mandate_cash_target_pct=7.0`; assertion
  comments clarified (now tests floor = 7%, not floor = 2%)
- `test_no_deployable_below_floor`: updated to pass `mandate_cash_target_pct=7.0`

**New test class added** (`TestMandateAwareCash` — 8 tests, AC1–AC7):
See section 5 below.

### 3.4 `ui/portfolio_alignment/app.js`

**Change**: Added `cashContextHtml` strip rendered immediately after `summaryHtml` in the
Capital Deployment Queue panel.

The strip shows four cards:
- **Current Cash**: `cash_pct` (e.g. 8.66%)
- **Mandate Target**: `mandate_cash_target_pct` (e.g. 7.0%)
- **Excess vs Target**: `excess_pct` + `excess_mv` (e.g. +1.66% / +$7,894)
- **Deployable**: `deployable_mv` (e.g. $7,894)

Excess card receives `dq-cash-ctx-deficit` class when excess is negative (cash below mandate
target), and `dq-cash-ctx-excess` class when positive. The existing summary strip's
"Deployable Cash" card is preserved for compatibility.

---

## 4. Data Flow

```
mandate_type (e.g. "CONCENTRATED_ALPHA")
    ↓
load_archetype_targets(mandate_type)          runner.py:568
    → archetype_targets = {"CASH": 7.0, ...}
    ↓
_cash_target_pct = archetype_targets.get("CASH")   runner.py:~714
    → 7.0
    ↓
compute_deployable_cash(                      runner.py:~718
    holdings=investable,
    total_market_value=snapshot.total_market_value,
    mandate_cash_target_pct=7.0,
)
    → effective_floor_pct = max(2.0, 7.0) = 7.0
    → floor_mv = $475,779.42 × 7.0% = $33,304.56
    → deployable_mv = $41,198.92 − $33,304.56 = $7,894.36
    ↓
cash_context dict injected into deployment_queue result
    → UI renders Current=8.66% / Target=7.0% / Excess=+1.66% / Deployable=$7,894
```

---

## 5. Acceptance Criteria (WS-E Test Coverage)

| AC | Description | Test | Result |
|----|-------------|------|--------|
| AC1 | deployable_mv uses mandate target (7%), not governance floor (2%) | `test_ac1_deployable_uses_mandate_target` | PASS |
| AC2 | cash after deployment ≈ 7.00% | `test_ac2_cash_after_deployment_is_7pct` | PASS |
| AC3 | BALANCED mandate uses 5% target | `test_ac3_balanced_mandate_uses_5pct_target` | PASS |
| AC4 | GROWTH mandate uses 3% target | `test_ac4_growth_mandate_uses_3pct_target` | PASS |
| AC4b | Governance min overrides if mandate target < 2% | `test_ac4b_governance_minimum_overrides_low_target` | PASS |
| AC5 | None target raises ValueError | `test_ac5_missing_target_raises_value_error` | PASS |
| AC6 | All new dict keys present | `test_ac6_result_dict_contains_new_fields` | PASS |
| AC7 | Allocation math reconciles | `test_ac7_allocation_math_reconciles` | PASS |

Total test suite: **61/61 passed** (including 8 new mandate-aware tests).

---

## 6. Mandate CASH Targets (for Multi-Mandate Compatibility)

| Mandate | CASH Target | Source YAML |
|---------|-------------|-------------|
| CONCENTRATED_ALPHA | 7.0% | `concentrated_alpha_profile.yaml:18` |
| BALANCED | 5.0% | `balanced_allocation_profile.yaml:14` |
| GROWTH | 3.0% | `growth_allocation_profile.yaml:15` |
| DEFENSIVE | (check YAML) | `defensive_allocation_profile.yaml` |
| INCOME | (check YAML) | `income_allocation_profile.yaml` |

All mandate profiles must include a `CASH:` node under `nodes:` or `run_analysis()`
will raise `ValueError` before computing cash context.

---

## 7. Invariants Preserved

- `MIN_CASH_PCT = 2.0` constant value unchanged (governance hard minimum)
- `MIN_CASH_PCT == 2.0` assertion in `TestConstants.test_min_cash_pct` still passes
- CW-DAS scoring logic unchanged (WS-E AC6: no ranking changes — score formulas unmodified)
- `build_deployment_queue()` signature unchanged
- Deployment queue queue records unchanged
- All 53 pre-existing tests still pass

---

## 8. Risk Assessment

**Risk**: Mandate profile missing CASH node  
**Mitigation**: Fail-closed ValueError in runner.py with descriptive message naming the offending mandate  

**Risk**: Mandate target below governance minimum (e.g. 1%)  
**Mitigation**: `max(MIN_CASH_PCT, mandate_cash_target_pct)` ensures governance floor always applies  

**Risk**: UI showing incorrect cash target after update  
**Mitigation**: `mandate_cash_target_pct` key is sourced directly from the mandate YAML, not hardcoded  

**Risk**: Other callers of `compute_deployable_cash()` missing the new required param  
**Mitigation**: No default = TypeError on import/call; no silent drift possible  
