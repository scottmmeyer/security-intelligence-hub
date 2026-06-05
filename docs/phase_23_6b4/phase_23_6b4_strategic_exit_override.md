# Phase 23.6B.4 — Strategic Exit Override

**Date:** 2026-06-04  

---

## Problem

FIS was designated in `strategic_exit_symbols` (operator intends full exit) but CRA output was:
- Category: SIGNAL_DETERIORATION (not STRATEGIC_EXIT)
- Sizing: 25% ($1,537 of $6,146)
- Reason: SIGNAL_DETERIORATION wins category priority stack (index 0 vs index 1 for STRATEGIC_EXIT)

Operator intent: **full exit** (~$6,146)

---

## Fix

**File:** `src/portfolio/cra/capital_source_builder.py`

Post-processing override added after all categories are detected and tax annotations applied, before the sort:

```python
for sym in strategic_exit_symbols:
    cand = candidates.get(sym)
    if cand is None:
        continue
    if cand.category == CATEGORY_STRATEGIC_EXIT:
        cand.sizing_pct = _SIZING_FULL  # ensure 100%
    else:
        # Override: preserve existing evidence but promote category + sizing
        original_evidence = list(cand.evidence_parts)
        cand.evidence_parts = [
            "operator-designated strategic exit (no STI profile available)",
        ] + [f"[signal context] {e}" for e in original_evidence]
        cand.category = CATEGORY_STRATEGIC_EXIT
        cand.sizing_pct = _SIZING_FULL
        if cand.priority in ("MODERATE", "LOW", "DEFER"):
            cand.priority = "HIGH"
```

The evidence summary retains the ESS signal as `[signal context]` so the operator can see both the operator intent and the signal reason.

---

## Live Validation

```
FIS category:  STRATEGIC_EXIT    ✅ PASS
FIS sizing:    1.0               ✅ PASS
FIS proceeds:  $6,146.49         ✅ PASS (full position value)
FIS priority:  HIGH              ✅ PASS
```

Before: $1,537 (25% sizing, wrong category)
After:  $6,146 (100% sizing, STRATEGIC_EXIT category)
