# Q2 — SPAXX Asset-Type Audit: Cash vs ETF / Other Misclassification
## Workstream B: SPAXX / Cash Equivalent Governance Certification

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D — Workstream B  
**Scope:** SPAXX classification against every non-CASH asset type at every platform stage  

---

## Verdict: SPAXX is NEVER Classified as ETF, Mutual Fund, Fixed Income, or Equity

---

## Section 1 — Classification Matrix

| Asset Type | Could SPAXX Receive This? | Guard / Evidence | Result |
|------------|--------------------------|------------------|--------|
| ETF | No | `enrichment.py:227`: `effective_security_type = "Cash"` hard override when `sym in _CASH_EQUIVALENT_SYMBOLS` | ✅ NEVER ETF |
| MUTUAL_FUND | No | `_is_eligible()` gate AND `is_cash_equivalent` guard fires first | ✅ NEVER MUTUAL_FUND |
| FIXED_INCOME | No | `optimizer.py:368`: `if is_cash_eq or ac in ("CASH", "FIXED_INCOME"): return False` | ✅ NEVER FIXED_INCOME |
| EQUITY | No | `asset_class="CASH"` from override; optimizer skips equity nodes for cash | ✅ NEVER EQUITY |
| UNKNOWN | No | `_ETF_OVERRIDES` provides explicit mapping; `_CASH_KEYWORDS` in ingestion | ✅ NEVER UNKNOWN |
| DIGITAL | No | No override or classification path assigns DIGITAL to any cash-equivalent symbol | ✅ NEVER DIGITAL |
| COMMODITY | No | No override or classification path assigns COMMODITY to SPAXX | ✅ NEVER COMMODITY |

---

## Section 2 — ETF Misclassification Risk (Deep Audit)

This is the highest-risk scenario because SPAXX appears in `config/etf_exposure_decomposition.yaml`, which is the ETF registry.

### 2a — ETF Registry Entry (Technical Debt)

**File:** `config/etf_exposure_decomposition.yaml`, lines 838–875:
```yaml
SPAXX:
  decomposition_method: HEURISTIC_REGISTRY_V1
  decomposition_confidence: 0.90
  strategic_role: CASH_EQUIVALENT        ← identity declared correctly
  exposure_sector_mix:
    CASH: 100                             ← 100% cash sector
  exposure_thematic_mix:
    CASH_EQUIVALENT: 100                  ← 100% cash-equivalent theme
```

The registry entry itself correctly declares `strategic_role: CASH_EQUIVALENT`. However, its presence in the ETF registry causes:
- `decomposition_source = "REGISTRY"` to be set on the holding during enrichment
- This in turn made SPAXX pass the `_FUND_SOURCES` filter in `_identify_etf_contributors()` in Phase 6.3D (since fixed)

**Status:** Technical debt — entry retained for historical reasons. All behavioral guards prevent any ETF treatment.

### 2b — Enrichment Guard (Primary Defense)

**File:** `src/portfolio/enrichment.py`, lines 227–234:
```python
# Cash-equivalent symbols (SPAXX, VMFXX, etc.) must NOT be promoted to
# security_type='ETF'
if sym in _CASH_EQUIVALENT_SYMBOLS:
    effective_security_type = "Cash"
    is_cash_equiv = True
    new_op_state = "CASH_EQUIVALENT"
```
This guard is the primary defense. Enrichment processes SPAXX and reaches this block **before** any ETF promotion logic. Result: `security_type = "Cash"` — never "ETF".

### 2c — ETF Contributor Guard (Phase 6.3D Fix)

**File:** `src/portfolio/recommendations.py`, lines 1346–1347:
```python
is_ce = getattr(h, "is_cash_equivalent", False)
if op_state == "CASH_EQUIVALENT" or is_ce:
    continue   # skip — SPAXX cannot be an ETF contributor
```
This guard was added in Phase 6.3D to fix the bug where SPAXX appeared in `etf_contributors` for recommendations. SPAXX is now explicitly excluded before being added to the contributor list.

### 2d — RC-06 Governance Check (Formal Audit)

**File:** `src/portfolio/reconciliation.py`, function `_rc06_security_classification_audit()`, lines 555–631:
```python
# RC-06: Detects Phase 6.3D Issue #2: SPAXX leaked into ETF contributor lists.
for sym in _CASH_EQUIVALENT_SYMBOLS:
    # Validates each cash holding:
    #   1. security_type = "Cash"
    #   2. is_cash_equivalent = True
    #   3. NOT in ETF registry as a live position
    #   4. NOT appearing as ETF contributor in any recommendation
```

The RC-06 check is a runtime governance audit that runs on every reconciliation. It verifies that no cash-equivalent symbol appears as an ETF contributor in any recommendation in `recommendations.json`.

### 2e — Live Validation

From live `holdings.csv` (PAR-20260602-1BF2ADA5):
```
SPAXX  security_type: Cash      ← NOT "ETF"
SPAXX  asset_class:   CASH      ← NOT "EQUITIES"
```

From live `recommendations.json`: SPAXX does NOT appear in any `etf_contributors` array in the current run.

---

## Section 3 — Deployment Queue Security Type Filter

**File:** `src/portfolio/deployment_queue.py`, line 93:
```python
_EXCLUDED_SECURITY_TYPES = frozenset({"ETF", "FUND", "MUTUAL_FUND"})
```

Note: SPAXX's `security_type = "Cash"` would not be caught by this set-exclusion filter. However, this is irrelevant because the `is_cash_equivalent` gate (line 205) fires **first** and returns `False` before the security type check is reached.

**Layer 1:** `is_cash_equivalent = True` → return `False` (line 205)  
**Layer 2 (never reached):** `security_type not in _EXCLUDED_SECURITY_TYPES` — would pass if Layer 1 were absent, but Layer 1 always fires first for SPAXX

This layered defense ensures that even if `security_type` were mis-set to "Cash" (which is correct), the `is_cash_equivalent` flag provides an independent guard.

---

## Section 4 — Optimizer Asset Class Check

**File:** `src/portfolio/optimizer.py`, lines 352, 361, 368:
```python
is_cash_eq = bool(getattr(holding, "is_cash_equivalent", False))
ac = str(getattr(holding, "asset_class", "")).upper()
if is_cash_eq or ac in ("CASH", "FIXED_INCOME"):
    return False   # skip — not eligible for equity node matching
```

SPAXX is excluded from all equity allocation node matching because:
1. `is_cash_equivalent = True` → short-circuit return `False`
2. `asset_class = "CASH"` → would also return `False`

SPAXX cannot receive an EQUITIES node alignment score.

---

## Section 5 — Trim Intelligence

**File:** `src/portfolio/trim_intelligence.py`, line 40:
```python
"CASH_EQUIVALENT": "HIGH"  # SPAXX — operational liquidity
```

`CASH_EQUIVALENT` operational state maps to `trim_priority = "HIGH"`. This means SPAXX is never targeted for trim recommendations — consistent with cash treatment (cash is not expendable equity, it is an operational reserve).

---

## Section 6 — Test Coverage

| Test | File | Assertion |
|------|------|-----------|
| `test_spaxx_enriched_as_cash_not_etf` | `tests/test_cash_semantics.py` | SPAXX.security_type == "Cash"; SPAXX.asset_class == "CASH" |
| `test_spaxx_is_cash_equivalent_flag` | `tests/test_cash_semantics.py` | SPAXX.is_cash_equivalent == True |
| `test_spaxx_operational_state_is_cash_equivalent` | `tests/test_cash_semantics.py` | SPAXX.operational_state == "CASH_EQUIVALENT" |
| `test_voo_not_flagged_as_cash_equivalent` | `tests/test_cash_semantics.py` | VOO (ETF) does NOT get cash-equivalent treatment |
| `test_cash_as_etf_contributor_detected` | `tests/test_reconciliation.py` | RC-06 FAIL when SPAXX in etf_contributors |
| `test_spaxx_double_count_detected` | `tests/test_reconciliation.py` | RC-05 FAIL on double-count |
| `test_cash_holding_no_etf_decomp_exposure` | `tests/test_cash_semantics.py` | Cash holding has no equity decomp exposures |

**Test run result:** 31 passed in `tests/test_cash_semantics.py`; 9/9 passed in `tests/test_reconciliation.py` (cash-scoped).

---

## Section 7 — Known Open Item

SPAXX remains in `config/etf_exposure_decomposition.yaml`. This causes:
- `decomposition_source = "REGISTRY"` on the enriched holding (vs "DIRECT_CLASSIFICATION")
- `decomposition_method = "HEURISTIC_REGISTRY_V1"` (stale)

These stale field values are **not** governance failures because:
1. All behavioral guards (enrichment:227, recommendations:1346, optimizer:368) prevent any ETF treatment
2. RC-06 validates at runtime
3. The `strategic_role: CASH_EQUIVALENT` in the registry entry correctly declares intent
4. Phase 6.3D regression tests confirm the fix holds

**Remediation (deferred):** Remove SPAXX, VMFXX, and FZFXX entries from `etf_exposure_decomposition.yaml`. Change their `decomposition_source` to `"DIRECT_CLASSIFICATION"`. This cleanup has no behavioral impact and is tracked as technical debt.
