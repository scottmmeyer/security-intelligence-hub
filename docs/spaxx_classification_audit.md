# SPAXX Classification Audit

**Date:** 2026-06-16  
**Status:** NO ACTION REQUIRED — WARN is expected by design

---

## Executive Summary

SPAXX (Fidelity Government Money Market Fund) is correctly classified as a cash equivalent. The RC-06 WARN is **intentional advisory behavior**, not a defect. SPAXX is in the ETF decomposition registry as `CASH_DECOMPOSABLE`, which RC-06 correctly reports as an advisory note rather than a hard violation.

---

## Q6: Is SPAXX properly classified today?

**Yes.** SPAXX is fully and correctly classified across all systems:

| Classification Field | Value | Source |
|---------------------|-------|--------|
| `asset_class` | CASH | `_ETF_OVERRIDES` in `enrichment.py` |
| `is_cash_equivalent` | True | Set by enrichment step |
| `operational_state` | CASH_EQUIVALENT | Set by enrichment step |
| `security_type` | Cash | From Fidelity CSV |
| `geography` | US | `_ETF_OVERRIDES` |
| `sector` | Cash | `_ETF_OVERRIDES` |
| `industry` | Money Market | `_ETF_OVERRIDES` |

SPAXX is excluded from all deployment queues, reduction queues, and UCF ranking — as expected for cash equivalents. It contributes to the CASH L1 allocation node correctly.

---

## Q7: Why does the audit emit WARN?

RC-06 (Security Classification Audit) checks three rules for cash instruments:
1. `security_type == "Cash"` ✓ PASS
2. `is_cash_equivalent == True` ✓ PASS
3. Not in ETF decomposition registry unless `CASH_DECOMPOSABLE` ← ADVISORY

SPAXX has a `CASH_DECOMPOSABLE` registry entry in `config/etf_exposure_decomposition.yaml`. This entry models SPAXX's economic exposure (100% US CASH) for portfolio decomposition purposes.

RC-06 Rule 3 is designed to catch **Phase 6.3D Issue #2**: cash instruments leaking into ETF contributor lists. The `CASH_DECOMPOSABLE` entry type is an **approved exception** — it is a legitimate registry entry that models economic exposure without reclassifying the instrument away from CASH.

RC-06 correctly emits `WARN` (not `FAIL`) for `CASH_DECOMPOSABLE` entries, per the comment in `reconciliation.py`:
```python
# CASH_DECOMPOSABLE entries (e.g. SPAXX, VMFXX) have legitimate registry
# entries to model their economic exposure — not a classification defect.
```

---

## Q8: Should the audit remain WARN or become PASS?

**WARN is correct.** The advisory behavior serves a governance purpose:
- It confirms SPAXX is in the ETF registry (which could be surprising and worth visibility)
- It distinguishes `CASH_DECOMPOSABLE` (approved) from other registry entries that would be hard violations
- It provides an audit trail that a human reviewed this classification

Changing this to PASS would suppress potentially useful governance visibility. The current behavior is correct.

---

## Q9: Does any code change need to be made?

**No.** SPAXX is correctly classified. RC-06 is operating as designed. The WARN is advisory and informational.

The only scenario where code change would be needed is if:
1. SPAXX appeared in an ETF contributor list (Rule 4 violation → FAIL) — **not occurring**
2. SPAXX had `is_cash_equivalent=False` (Rule 2 violation → FAIL) — **not occurring**
3. The `CASH_DECOMPOSABLE` registry entry was removed — but that would break look-through decomposition

**No action required.**

---

## Downstream Consumer Impact Assessment

| Consumer | SPAXX Behavior | Status |
|----------|---------------|--------|
| RC-06 | WARN (advisory) | Expected ✓ |
| L1 allocation sum | Included in CASH (10.2268%) | Correct ✓ |
| CPV-04 (Cash Floor) | Counted as cash | Correct ✓ |
| UCF/CW-DAS | Excluded (operational_state=CASH_EQUIVALENT) | Correct ✓ |
| Deployment queue | Not eligible | Correct ✓ |
| Reduction queue | Not eligible | Correct ✓ |
| PIS change detection | Included, labeled is_cash_equivalent=True | Correct ✓ |
| ETF decomposition | CASH_DECOMPOSABLE registry entry used for exposure modeling | Correct ✓ |
