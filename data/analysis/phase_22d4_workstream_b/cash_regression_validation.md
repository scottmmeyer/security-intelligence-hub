# Q8 — Cash Regression Validation
## Workstream B: SPAXX / Cash Equivalent Governance Certification

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D — Workstream B  
**Scope:** Historical Phase 6.3D defects, regression test suite, and open technical debt  

---

## Summary

Two Phase 6.3D defects were identified and fixed: (1) SPAXX double-counted in CASH allocation node, and (2) SPAXX appearing as an "ETF contributor" in recommendation cards. Both fixes are regression-tested. The underlying registry entry (SPAXX in `etf_exposure_decomposition.yaml`) is retained as technical debt but has no behavioral impact due to multiple behavioral guards.

---

## Section 1 — Phase 6.3D Defect 1: SPAXX Double-Count

### Root Cause
**File:** `src/portfolio/exposure_decomposition.py`, function `_accumulate_holding_exposure()`

For SPAXX specifically:
- `asset_class = "CASH"`
- `sector = "Cash"` → `sector.upper() = "CASH"`
- Because `sector.upper() == asset_class`, the `effective["CASH"]` bucket received two additions: once from the asset_class block and once from the sector block

**Effect:** CASH node reported as 18.051% (2×) instead of 9.025%  
**Downstream cascade:** CASH drift appeared as +16.051pp → HIGH severity "Reduce Cash" recommendation  
**Actual portfolio state:** CASH was only ~0.95pp overweight at the time

### Fix Applied
The sector accumulation block was guarded to skip when `sector.upper() == asset_class`, preventing the double-count.

**Regression test:** `tests/test_reconciliation.py:721`:
```python
def test_spaxx_double_count_detected():
    """RC-05 should FAIL if SPAXX is counted twice in CASH node."""
    ...
```

### Live Validation (Post-Fix)
From `alignment.csv` (PAR-20260602-1BF2ADA5):
```
CASH actual_pct: 8.6592   ← matches SPAXX percent_of_portfolio exactly (8.6592)
```
CASH is counted exactly once. Double-count is resolved. ✅

---

## Section 2 — Phase 6.3D Defect 2: SPAXX as ETF Contributor

### Root Cause
**File:** `src/portfolio/recommendations.py`, function `_identify_etf_contributors()`

The filter used `decomposition_source` to identify fund holdings:
```python
_FUND_SOURCES = {"REGISTRY", "HEURISTIC_FALLBACK", "SYMBOL_HEURISTIC"}
if src not in _FUND_SOURCES:
    continue
```

Because SPAXX appeared in `config/etf_exposure_decomposition.yaml`, enrichment assigned:
```
decomposition_source = "REGISTRY"
decomposition_method = "HEURISTIC_REGISTRY_V1"
```

SPAXX passed the `_FUND_SOURCES` filter and was added to `etf_contributors`. The UI then rendered:
```html
<span class="rec-etf-label">ETF contributors:</span>
<span class="rec-etf-chip">SPAXX</span>
```
This label is hardcoded in the UI — "ETF contributors:" renders for any non-empty `etf_contributors` array.

**Additional compounding:** Because of Bug 1, SPAXX's CASH contribution was doubled (18.051%). This inflated contribution made SPAXX appear to be a large indirect contributor, further misleading the display.

### Fix Applied
**File:** `src/portfolio/recommendations.py`, lines 1346–1347:
```python
is_ce = getattr(h, "is_cash_equivalent", False)
if op_state == "CASH_EQUIVALENT" or is_ce:
    continue   # Phase 6.3D fix: cash equivalents are never ETF contributors
```

This guard was added before the `_FUND_SOURCES` check. Any holding with `operational_state = "CASH_EQUIVALENT"` OR `is_cash_equivalent = True` is skipped immediately.

**Regression test:** `tests/test_reconciliation.py:458`:
```python
def test_cash_as_etf_contributor_detected():
    """RC-06 must FAIL if SPAXX appears as etf_contributors in a recommendation."""
    ...
    # Note: test line 453:
    # "SPAXX is in the ETF registry (Phase 6.3D bug) so this may FAIL in live env"
    # — Acknowledges the residual registry risk, confirms the test validates the guard
```

**RC-06 Governance Check:** `src/portfolio/reconciliation.py`, function `_rc06_security_classification_audit()`, lines 555–631:
```python
# RC-06: Detects Phase 6.3D Issue #2: SPAXX leaked into ETF contributor lists.
# Validates each cash holding:
#   1. security_type = "Cash"
#   2. is_cash_equivalent = True
#   3. NOT in ETF registry as an active position
#   4. NOT appearing as ETF contributor in any recommendation
```

### Live Validation (Post-Fix)
From live `recommendations.json` (PAR-20260602-1BF2ADA5): No recommendation has SPAXX in `etf_contributors`. ✅

---

## Section 3 — Full Regression Test Suite (Cash-Scoped)

### `tests/test_cash_semantics.py` — 31 tests, all passing
| Test | Assertion |
|------|-----------|
| `test_spaxx_enriched_as_cash_not_etf` | SPAXX.security_type=="Cash", asset_class=="CASH" |
| `test_spaxx_is_cash_equivalent_flag` | SPAXX.is_cash_equivalent==True |
| `test_spaxx_operational_state_is_cash_equivalent` | SPAXX.operational_state=="CASH_EQUIVALENT" |
| `test_vmfxx_enriched_as_cash` | VMFXX: same as SPAXX |
| `test_fzfxx_enriched_as_cash` | FZFXX: same as SPAXX |
| `test_voo_not_flagged_as_cash_equivalent` | VOO (ETF) does NOT get cash treatment |
| `test_cash_holding_no_etf_decomp_exposure` | Cash has no equity decomp exposures |
| `test_spaxx_row_is_not_active_position` | Ingestion → enrichment upgrades to CASH_EQUIVALENT |

**Live result:** `31 passed in 0.72s` ✅

### `tests/test_reconciliation.py` — 9 cash-scoped tests, all passing
| Test | Assertion |
|------|-----------|
| `test_spaxx_double_count_detected` (line 721) | RC-05 FAIL on double-count |
| `test_cash_as_etf_contributor_detected` (line 458) | RC-06 FAIL if SPAXX in etf_contributors |
| Additional cash-scoped tests | Various RC-0X checks |

**Live result:** `9 passed` ✅

### `tests/test_7_5b_deployment_queue.py` + `tests/test_7_5f_deployment_actionability.py` — 86 tests, all passing
Includes tests that validate cash exclusion from CW-DAS and deployment eligibility.

**Live result:** `86 passed in 11.99s` ✅

---

## Section 4 — Open Technical Debt (Not a Regression)

### Item: SPAXX/VMFXX/FZFXX in `config/etf_exposure_decomposition.yaml`

**Status:** Technical debt — behavioral fix complete, registry cleanup deferred.

**Root cause:** These symbols were added to the ETF registry before Phase 6.1A cash reclassification. They are not ETFs, but the registry entry has not been removed.

**Current behavioral impact:** NONE. The enrichment guard (`enrichment.py:227`) prevents ETF promotion regardless of registry presence. The `etf_contributors` guard (`recommendations.py:1346`) prevents these from appearing in ETF contributor lists.

**Stale fields on SPAXX holding (harmless):**
- `decomposition_source = "REGISTRY"` (should be `DIRECT_CLASSIFICATION`)
- `decomposition_method = "HEURISTIC_REGISTRY_V1"` (stale)

**Remediation path (future cleanup):**
1. Remove SPAXX, VMFXX, FZFXX entries from `config/etf_exposure_decomposition.yaml`
2. Update enrichment to assign `decomposition_source = "DIRECT_CLASSIFICATION"` for known cash symbols
3. Verify RC-06 still passes (no changes needed — it tests runtime behavior, not registry contents)
4. Verify test suite still passes (the `test_cash_as_etf_contributor_detected` test acknowledges the registry risk and will still pass since the behavioral guard remains)

**Classification:** This is NOT a regression. The Phase 6.3D defects are fixed. The registry cleanup is pure cosmetic/hygiene work.

---

## Section 5 — Regression Summary

| Defect | Phase | Fix Applied | Test Coverage | Live State |
|--------|-------|-------------|---------------|------------|
| SPAXX double-count in CASH node | 6.3D | `exposure_decomposition.py` sector guard | `test_spaxx_double_count_detected` (RC-05) | ✅ FIXED — CASH=8.6592% (single count) |
| SPAXX in ETF contributor lists | 6.3D | `recommendations.py:1346` `is_cash_equivalent` guard | `test_cash_as_etf_contributor_detected` (RC-06) | ✅ FIXED — etf_contributors empty for CASH rec |
| SPAXX not flagged as cash_equivalent | Pre-6.1A | `enrichment.py:227` cash-equivalent guard | `test_spaxx_is_cash_equivalent_flag` | ✅ FIXED — is_cash_equivalent=True |
| SPAXX classified as ETF by enrichment | Pre-6.1A | `_ETF_OVERRIDES["SPAXX"]` + hard guard | `test_spaxx_enriched_as_cash_not_etf` | ✅ FIXED — security_type=Cash |
| SPAXX in deployment queue | Pre-6.1A | `deployment_queue.py:205` `is_cash_equivalent` gate | CW-DAS test suite | ✅ CONFIRMED ABSENT — not in queue |
| **Registry cleanup (YAML)** | 6.3D | **Deferred** | N/A (behavioral guard covers this) | ⚠️ PENDING — stale metadata, no behavioral impact |
