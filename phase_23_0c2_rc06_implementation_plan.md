# Phase 23.0C.2 — RC-06 Implementation Plan
**PAR Run:** PAR-20260603-B66B00E3  
**Check:** RC-06 — Security Classification Audit  
**Current Status:** FAIL  
**Corrected Status:** WARN  
**Source:** `src/portfolio/reconciliation.py` lines 553–641, `config/etf_exposure_decomposition.yaml`  
**Phase:** 23.0C.2 — PAP Validation + Reconciliation Governance Corrections  
**Scope:** Implementation plan for rule correction. No code changes in this phase.

---

## 1. Current Rule Definition

RC-06 audits all cash instruments in the portfolio holdings. The rule enforces four conditions:

```python
# Rule 1: security_type should be 'Cash'
if sec_type not in _CASH_SECURITY_TYPES:
    row_violations.append(...)

# Rule 2: is_cash_equivalent must be True
if not is_ce:
    row_violations.append(...)

# Rule 3: must NOT be in ETF registry
if sym in registry_symbols:
    row_violations.append(f"present in ETF decomposition registry ({sym})")

# Rule 4: must NOT appear as ETF contributor in any recommendation
for rec in recommendations:
    if sym in [str(c).upper() for c in etf_contrib]:
        row_violations.append(...)
```

The registry is loaded from `config/etf_exposure_decomposition.yaml` via `_load_etf_registry()` (line 149):

```python
_ETF_REGISTRY_PATH = _REPO_ROOT / "config" / "etf_exposure_decomposition.yaml"
```

---

## 2. The Violation

**Current reconciliation output for RC-06:**
```
Status: FAIL
Cash positions audited: 1
Violation: SPAXX: present in ETF decomposition registry (SPAXX)
actual: 0/1 PASS
variance: 1 violation(s)
```

SPAXX is flagged because it appears in `config/etf_exposure_decomposition.yaml` under the `symbols` key. Rule 3 treats any cash-instrument appearance in the ETF registry as a violation.

---

## 3. Root Cause Analysis

### 3.1 SPAXX Registry Entry

SPAXX's entry in `config/etf_exposure_decomposition.yaml`:

```yaml
SPAXX:
  decomposition_method: HEURISTIC_REGISTRY_V1
  decomposition_confidence: 0.90
  strategic_role: CASH_EQUIVALENT
  exposure_geography_mix:
    US: 100
  exposure_sector_mix:
    CASH: 100
  exposure_style_mix:
    INCOME: 100
  exposure_thematic_mix:
    CASH_EQUIVALENT: 100
```

SPAXX is Fidelity Government Money Market Fund. Its 100% CASH sector decomposition is intentional — the registry needs to model SPAXX's economic exposure (cash / money market) for ETF decomposition calculations in RC-04 and RC-03. Without this entry, the decomposition engine cannot correctly attribute cash-equivalent exposure from portfolios holding SPAXX.

### 3.2 Rule Design Assumption

Rule 3 was designed to catch a specific Phase 6.3D defect: SPAXX appearing in ETF contributor lists (e.g., as a component of an equity ETF's underlying basket). The docstring states:

```
Detects Phase 6.3D Issue #2: SPAXX leaked into ETF contributor lists.
```

The rule was written assuming "in ETF registry" was equivalent to "being used as an equity ETF component." This assumption is incorrect: the registry serves dual purposes:
1. **CASH_EQUIVALENT entries** — money market funds that need economic exposure modeling (SPAXX, VMFXX, FDRXX, etc.)
2. **Equity ETF entries** — multi-component ETFs whose geographic/sector/style exposure is decomposed from their underlying holdings

Rule 3 does not distinguish between these two registry entry types.

### 3.3 Why This Is a False Positive

SPAXX satisfies Rules 1, 2, and 4:
- Rule 1: `security_type = CASH` (correct)
- Rule 2: `is_cash_equivalent = True` (correct)
- Rule 4: SPAXX is not listed as an `etf_contributors` field in any recommendation (it is not a component of an equity ETF in this portfolio)

Rule 3 fires solely because SPAXX has a registry entry defining its exposure decomposition — which is correct, intentional behavior, not a data quality issue.

---

## 4. Phase 23.0C.1 Verdict Established

As established in `phase_23_0c1_spaxx_duplicate_analysis.md` and `phase_23_0c1_reconciliation_rule_review.md`, RC-06 is a **false positive** with no analytical impact on any other reconciliation check or signal output. The corrected severity is **WARN**, not FAIL.

---

## 5. Implementation Plan

### 5.1 Option A — Registry Entry Type Flag (Preferred)

Add a `registry_entry_type` field to ETF registry entries. Rule 3 only fires for entries where `registry_entry_type != CASH_DECOMPOSABLE`.

**YAML change** (`config/etf_exposure_decomposition.yaml`):
```yaml
SPAXX:
  registry_entry_type: CASH_DECOMPOSABLE   # ← add this field
  decomposition_method: HEURISTIC_REGISTRY_V1
  decomposition_confidence: 0.90
  strategic_role: CASH_EQUIVALENT
  ...
```

Apply the same `registry_entry_type: CASH_DECOMPOSABLE` to all cash-equivalent entries (VMFXX, FDRXX, FZFXX, SPRXX, FCASH, etc.).

**Rule 3 updated logic** (`src/portfolio/reconciliation.py`):
```python
# Rule 3: must NOT be in ETF registry UNLESS it is a cash-decomposable entry
if sym in registry_symbols:
    entry = registry.get(sym, {})
    if entry.get("registry_entry_type") != "CASH_DECOMPOSABLE":
        row_violations.append(f"present in ETF decomposition registry ({sym})")
```

**Severity:** On violation: WARN (not FAIL), since presence in registry does not indicate a security classification defect.

### 5.2 Option B — Symbol Whitelist (Simpler, Less Robust)

Maintain a set `_CASH_DECOMPOSABLE_REGISTRY_SYMBOLS` in reconciliation.py that enumerates known money-market registry entries and exempts them from Rule 3.

```python
_CASH_DECOMPOSABLE_REGISTRY_SYMBOLS = frozenset({
    "SPAXX", "VMFXX", "FDRXX", "FZFXX", "SPRXX", "FCASH",
})
# Rule 3
if sym in registry_symbols and sym not in _CASH_DECOMPOSABLE_REGISTRY_SYMBOLS:
    row_violations.append(...)
```

**Drawback:** Requires manual maintenance as new money-market instruments are added to the registry. Option A is self-documenting.

### 5.3 Option C — Severity Downgrade Only (Minimal Change)

Without changing the detection logic, downgrade RC-06 violations from FAIL to WARN by changing the final status computation:

```python
# Change: overall_status = "PASS" if not violations else "FAIL"
overall_status = "PASS" if not violations else "WARN"
```

**Drawback:** Does not distinguish true violations (SPAXX genuinely in an equity ETF contributor list) from false positives (SPAXX in registry for legitimate decomposition reasons). Option A is preferred for long-term rule clarity.

---

## 6. Recommended Path

**Option A is recommended.** It:
1. Preserves the ability to detect genuine Rule 3 violations (cash instrument incorrectly classified as ETF component)
2. Explicitly documents the intentional dual-use nature of the registry via `registry_entry_type`
3. Is self-documenting — future registry additions for money-market instruments carry their own exemption flag
4. Requires a modest YAML metadata addition and a 4-line Python change

### 6.1 Affected Files

| File | Change | Type |
|------|--------|------|
| `config/etf_exposure_decomposition.yaml` | Add `registry_entry_type: CASH_DECOMPOSABLE` to SPAXX, VMFXX, FDRXX, FZFXX, SPRXX, FCASH, and any other money-market entries | Config metadata |
| `src/portfolio/reconciliation.py` | Update Rule 3 in `_rc06_classification_audit()` to exempt `CASH_DECOMPOSABLE` entries; downgrade violation severity to WARN | Logic change |

### 6.2 Expected Post-Fix Scorecard

| Check | Before | After |
|-------|--------|-------|
| RC-06 | **FAIL** (1 violation) | **WARN** (0 violations, rule exemption noted) |

If no other violations are ever found, RC-06 PASS is achievable by also converting the result to PASS when all sub_checks pass (regardless of registry type flags). The minimal path is WARN; the clean path is PASS after full rule correction.

---

## 7. Testing Requirements

After implementing Option A, the following test assertions should hold:

1. `test_reconciliation.py`: RC-06 status = `WARN` (or PASS) for PAR-20260603-B66B00E3
2. Introduce a synthetic holdings entry where a cash instrument is listed as `etf_contributors` in a recommendation → Rule 4 still fires as FAIL
3. Introduce a synthetic equity ETF (e.g., VOO) in registry with no `registry_entry_type` → Rule 3 still fires if it appears as a cash holding
4. SPAXX in registry with `registry_entry_type: CASH_DECOMPOSABLE` → Rule 3 does not fire

---

## 8. Verdict

**RC-06 root cause confirmed: false positive.** SPAXX is correctly classified (security_type=CASH, is_cash_equivalent=True) and correctly present in the ETF registry for decomposition modeling purposes. Rule 3's assumption that "registry presence = ETF component contamination" is incorrect. Option A implementation plan resolves the defect with minimal, targeted changes.

---

*Phase 23.0C.2 — RC-06 Implementation Plan*  
*Run: PAR-20260603-B66B00E3 | Generated: Phase 23 governance hardening*
