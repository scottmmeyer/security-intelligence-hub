# ISSUE-04C — Before / After

**Date:** June 5, 2026

---

## Before ISSUE-04C

### No Watchlist Panel

No dedicated dislocation watchlist existed. The only dislocation display was:

1. A "Dislocation" badge in the Fundamental Snapshot (inside the DQ row expansion):
   - Computed by `_fmpDislocationType()` in JavaScript
   - No backend definition
   - Labels: "HIGH CONVICTION", "POTENTIAL", "NONE"
   - No governance advisory
   - No filtering capability
   - Not visible at the portfolio level — only inside individual row expansions

### No Backend Payload

`dislocation_by_symbol` key did not exist in API response (pre-ISSUE-04B).

---

## After ISSUE-04C

### Dislocation Watchlist Panel

A dedicated panel appears below the Deployment Queue when the portfolio has any non-NONE classifications:

```
┌─────────────────────────────────────────────────────────────────┐
│ DISLOCATION WATCHLIST   [A1 v1.0]          Guidance only — ... │
│ Evidence of divergence between verified fundamentals and        │
│ current market signals.                                         │
│                                                                 │
│ ⚠ Evidence of divergence only — no action implied.             │
│   Operator judgment required.                                   │
│                                                                 │
│ [ ] Include WATCH          [5 MODERATE] [17 WATCH]             │
│                                                                 │
│ Symbol  │ Tier          │ Class                │ Evidence       │
│ ─────────┼───────────────┼──────────────────────┼────────────────│
│ AMG     │ [MODERATE]    │ fundamental beat div  │ 3 signals      │
│ FIS     │ [MODERATE]    │ fundamental beat div  │ 3 signals      │
│ ...     │               │                       │                │
└─────────────────────────────────────────────────────────────────┘
```

### Row Expansion

Clicking a row expands the evidence:

```
MODERATE — AMG
• Beat rate 87% — fundamentals consistently exceeded expectations
• Thesis: INTACT
• Danelfin: 2.1 — AI model diverging from fundamentals
• Revenue growth: +12.4% (confirming)
```

### Fundamental Snapshot Badge: Before vs. After

**Before:**

Dislocation badge computed in JS (`_fmpDislocationType()`):
- Labels: "HIGH CONVICTION" / "POTENTIAL" / "NONE"
- JS heuristic, no backend

**After:**

Dislocation badge reads from `dislocation_by_symbol` (backend, ISSUE-04B):
- Labels: "HIGH CONVICTION" / "MODERATE" / "WATCH" / "NONE"
- Backend-authoritative, consistent with watchlist panel
- Fallback to JS heuristic for old runs without payload

---

## Label Changes (Legacy → New)

| Old JS label | New label | Source |
|---|---|---|
| "HIGH CONVICTION" | "HIGH CONVICTION" | Unchanged |
| "POTENTIAL" | "MODERATE" | Renamed to match methodology |
| (missing) | "WATCH" | New tier from ISSUE-04B |
| "NONE" | "NONE" | Unchanged |

---

## What Did Not Change

- CW-DAS scores
- Deployment queue ranking
- Composite scores
- Fundamental Modifier values
- CRA logic
- All 1,063 tests
