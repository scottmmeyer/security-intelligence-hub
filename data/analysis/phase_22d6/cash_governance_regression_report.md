# Cash Governance Regression Report — Phase 22D.6

**Phase**: 22D.6 — Strategic Cash Governance Implementation  
**Generated**: 2026-06-02  
**Test Suite**: `tests/test_7_5b_deployment_queue.py`  
**Run Command**: `PYTHONPATH=. .venv/bin/python3 -m pytest tests/test_7_5b_deployment_queue.py -x -q`

---

## Result

**61 / 61 PASSED** — 0 failures, 0 errors, 0 warnings

---

## Test Inventory

### Section 1: Module Version Contract (2 tests)
| Test | Result |
|------|--------|
| `TestVersionContract::test_version_str` | ✓ PASS |
| `TestVersionContract::test_version_locked` | ✓ PASS |

### Section 2: CwDasBreakdown Dataclass (3 tests)
| Test | Result |
|------|--------|
| `TestCwDasBreakdown::test_*` (3) | ✓ PASS |

### Section 3: build_deployment_queue() (5 tests)
| Test | Result |
|------|--------|
| `TestBuildDeploymentQueue::test_*` (5) | ✓ PASS |

### Section 4: compute_deployable_cash() — Original (2 tests updated)
| Test | Change | Result |
|------|--------|--------|
| `TestDeployableCash::test_deployable_above_floor` | Updated to pass `mandate_cash_target_pct=7.0` | ✓ PASS |
| `TestDeployableCash::test_no_deployable_below_floor` | Updated to pass `mandate_cash_target_pct=7.0` | ✓ PASS |

### Section 4b: TestMandateAwareCash — Phase 22D.6 (8 new tests)
| Test | AC | Result |
|------|----|----|
| `test_ac1_deployable_uses_mandate_target` | AC1 | ✓ PASS |
| `test_ac2_cash_after_deployment_is_7pct` | AC2 | ✓ PASS |
| `test_ac3_balanced_mandate_uses_5pct_target` | AC3 | ✓ PASS |
| `test_ac4_growth_mandate_uses_3pct_target` | AC4 | ✓ PASS |
| `test_ac4b_governance_minimum_overrides_low_target` | AC4b | ✓ PASS |
| `test_ac5_missing_target_raises_value_error` | AC5 | ✓ PASS |
| `test_ac6_result_dict_contains_new_fields` | AC6 | ✓ PASS |
| `test_ac7_allocation_math_reconciles` | AC7 | ✓ PASS |

### Section 5: Constants Contract (4 tests)
| Test | Result |
|------|--------|
| `TestConstants::test_warn_position_pct` — `WARN_POSITION_PCT == 6.0` | ✓ PASS |
| `TestConstants::test_max_position_pct` — `MAX_POSITION_PCT == 8.0` | ✓ PASS |
| `TestConstants::test_min_cash_pct` — `MIN_CASH_PCT == 2.0` | ✓ PASS |
| `TestConstants::test_queue_version` — `CW_DAS_VERSION == "1.0"` | ✓ PASS |

### Section 6: DeploymentCandidate Model + Integration Tests
All remaining tests in sections 7+ passed without modification.

---

## Breaking Change Handling

The `mandate_cash_target_pct` parameter has no default value. This is an intentional
breaking change: any call site that does not pass the new parameter receives a `TypeError`
at runtime rather than silently using an incorrect floor.

**Affected call sites updated**:
- `src/portfolio/runner.py:713–721` ✓

**No other call sites found** in:
- `scripts/` directory (grep confirmed no other `compute_deployable_cash` usages)
- `src/` modules (only `deployment_queue.py` definition + `runner.py` call site)
- Other test files (only `test_7_5b_deployment_queue.py`)

---

## Governance Invariant Preserved

`MIN_CASH_PCT = 2.0` — the hard-coded governance minimum — is unchanged and its contract
test (`test_min_cash_pct`) still passes. The governance floor is never overridden downward;
`max(MIN_CASH_PCT, mandate_cash_target_pct)` guarantees it remains the floor of last resort.

---

## Test Duration

11.42 seconds (integration tests load live data from disk; unit tests are instantaneous)
