# ISSUE-04C — Payload Reconciliation

**Date:** June 5, 2026

---

## Backend Payload (PAR-20260605-BC438F9E)

From `GET /api/portfolio/runs/PAR-20260605-BC438F9E`:

```
dislocation_by_symbol:
  Total symbols: 78
  Tier distribution:
    NONE:             56  (71.8%)
    WATCH:            17  (21.8%)
    MODERATE:          5   (6.4%)
    HIGH_CONVICTION:   0   (0.0%)
```

## UI Panel Reconciliation

| Metric | Backend | Panel (default) | Panel (+ WATCH) |
|--------|---------|-----------------|----------------|
| NONE | 56 | Not shown | Not shown |
| WATCH | 17 | Not shown | 17 rows |
| MODERATE | 5 | 5 rows | 5 rows |
| HIGH_CONVICTION | 0 | 0 rows | 0 rows |
| **Visible** | 22 non-NONE | **5** | **22** |

✅ Panel correctly shows 5 rows by default (MODERATE only)  
✅ Panel shows 22 rows after WATCH toggle  
✅ No NONE entries shown in either mode  

## PSX Reconciliation

PSX backend payload:
```json
{ "symbol": "PSX", "tier": "NONE", "dislocation_class": "NONE", "evidence": [] }
```

PSX in panel: **ABSENT** ✅  
Reason: DETERIORATING thesis gates it out at Step 1. This is the most critical governance validation.

## DELL Reconciliation

DELL backend payload:
```json
{
  "tier": "WATCH",
  "dislocation_class": "A1_FUNDAMENTAL_BEAT_DIVERGENCE",
  "evidence": [
    "Beat rate 86% — fundamentals consistently exceeded expectations",
    "Thesis: INTACT",
    "Danelfin: 2.5 — AI model diverging from fundamentals",
    "Revenue growth: +18.8% (confirming)"
  ]
}
```

DELL in panel (default): **ABSENT** ✅ (WATCH hidden by default)  
DELL in panel (+ WATCH): **PRESENT** ✅  
Evidence items shown on expand: 4 ✅

## Fundamental Snapshot Badge Reconciliation

The `_dqFundamentalSnapshotHtml()` function now reads:
```javascript
const _disBackend = (_lastAnalysisData?.dislocation_by_symbol || {})[sym];
const dislocation = _disBackend ? _disFromBackend(_disBackend) : _fmpDislocationType(...);
```

For DELL:
- Backend tier: WATCH
- `_disFromBackend()` output: `{ label: "WATCH", cls: "watch" }`
- Badge displays: "WATCH" (`.dq-fs-badge.watch` style)

For PSX:
- Backend tier: NONE
- Badge displays: "NONE" (`.dq-fs-badge.none` style)

This replaces the legacy JS heuristic which would have computed `_fmpDislocationType()` for every row expansion.
