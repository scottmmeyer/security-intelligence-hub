# Phase 23.6B.5 — Validation Results

**Date:** 2026-06-04  

---

## Live Validation

| # | Criterion | Result |
|---|-----------|--------|
| 1 | FIS no longer STRATEGIC_EXIT | ✅ PASS — category=SIGNAL_DETERIORATION |
| 2 | FIS receives normal sizing | ✅ PASS — sizing_pct=0.25 |
| 3 | FIS proceeds reflect partial sizing | ✅ PASS — $1,547 (25% of $6,189) |
| 4 | Tax bucket preserved | ✅ PASS — tax_bucket=A (unrealized loss ~$3,673) |
| 5 | Priority reasonable | ✅ PASS — HIGH (Bucket A upgrade from MODERATE) |
| 6 | strategic_exit_symbols is empty | ✅ PASS — `[]` |
| 7 | Source ranking sensible | ✅ PASS — FIS at #5–6, behind larger tax harvest candidates |
| 8 | CRA source count unchanged | ✅ PASS — 26 sources |
| 9 | No regressions | ✅ PASS — 954/954 |

---

## CRA Output Before / After

| Field | Before (strategic exit) | After (normal rules) |
|-------|------------------------|---------------------|
| `strategic_exit_symbols` | `["FIS"]` | `[]` |
| Category | STRATEGIC_EXIT | SIGNAL_DETERIORATION |
| Priority | HIGH | HIGH (Bucket A) |
| Sizing | 100% | 25% |
| Proceeds | $6,189 | $1,547 |
| Source rank | #2 | #5–6 |
| Implied action | Full exit mandate | Opportunistic partial sell |

---

## Change Made

**File:** `data/operator/portfolio_alignment_state.json`

```json
"strategic_exit_symbols": ["FIS"]   →   "strategic_exit_symbols": []
```

One field, one value removed. No code changes, no algorithm changes.
