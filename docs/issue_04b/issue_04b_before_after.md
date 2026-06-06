# ISSUE-04B — Before / After

**Date:** June 5, 2026

---

## Before ISSUE-04B

### JavaScript-only heuristic

The existing `_fmpDislocationType()` in `app.js` (~line 4138) implemented
classification entirely in the browser:

```javascript
function _fmpDislocationType(meta, ov, thesis, consistency) {
  // HIGH CONVICTION: intact thesis + ≥87.5% beat + bearish/neutral signal
  if (thesisLabel === "INTACT" && beat >= 0.875 && (signalBearishOrNeutral || dan < 1.5)) {
    return { label: "HIGH CONVICTION", cls: "high-conviction", ... };
  }
  // POTENTIAL: intact thesis + ≥75% beat but AI signal modest
  if (thesisLabel === "INTACT" && beat >= 0.75 && dan < 3.0) {
    return { label: "POTENTIAL", cls: "potential", ... };
  }
  return { label: "NONE", cls: "none", evidence: [] };
}
```

**Problems:**
- No backend definition — purely JS, no tests possible
- No governance documentation
- No versioning
- Labels ("POTENTIAL") not matching approved methodology ("MODERATE")
- Missing WATCH tier entirely
- No CONTRADICTORY consistency suppression
- Not accessible via API — only computable in browser
- Cannot be used in watchlist, analytics, or reporting

### API Response

```json
{
  "security_overlays": [...],
  "analyst_consensus_by_symbol": {...},
  ...
  // No dislocation key
}
```

---

## After ISSUE-04B

### Backend classifier

`src/portfolio/dislocation.py` — fully tested, versioned, stateless function:

```python
classify_dislocation(symbol, fmp_row, overlay) -> DislocationType
```

Returns `DislocationType(tier, dislocation_class, evidence, version)` for
every symbol, regardless of data availability.

**Gates enforced at backend:**
- FMP coverage required (no NO_DATA / ETF classification)
- Thesis must be INTACT (DETERIORATING/QUESTIONABLE → NONE)
- Beat rate minimum 62.5% required
- CONTRADICTORY consistency caps tier at WATCH

### API Response

```json
{
  "security_overlays": [...],
  "analyst_consensus_by_symbol": {...},
  "dislocation_by_symbol": {
    "DELL": {
      "symbol": "DELL",
      "tier": "WATCH",
      "dislocation_class": "A1_FUNDAMENTAL_BEAT_DIVERGENCE",
      "evidence": [
        "Beat rate 86% — fundamentals consistently exceeded expectations",
        "Thesis: INTACT",
        "Danelfin: 2.5 — AI model diverging from fundamentals",
        "Revenue growth: +18.8% (confirming)"
      ],
      "version": "1.0"
    },
    "PSX": { "tier": "NONE", "dislocation_class": "NONE", "evidence": [] },
    "NVDA": { "tier": "NONE", "dislocation_class": "NONE", "evidence": [] },
    ...
  }
}
```

---

## Tier Label Alignment

| Old JS label | New backend tier |
|---|---|
| "HIGH CONVICTION" | HIGH_CONVICTION |
| "POTENTIAL" | MODERATE |
| — (missing) | WATCH |
| "NONE" | NONE |

---

## JavaScript `_fmpDislocationType()` — Transition Plan

The existing UI function remains untouched in this phase. It will be replaced
in ISSUE-04C (Watchlist Panel) when the UI reads `dislocation_by_symbol` from
the API response and the function is superseded. No duplicate logic issue during
this transition — the JS function is display-only and produces no persistent state.
