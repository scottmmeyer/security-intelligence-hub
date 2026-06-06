# ISSUE-04C — Implementation Report
## Dislocation Watchlist Panel UI

**Date:** June 5, 2026  
**Status:** COMPLETE  
**Scope:** UI panel + Fundamental Snapshot badge migration. No scoring changes.

---

## 1. Summary

Added the Dislocation Watchlist Panel to the Portfolio Alignment page. The panel:
- Reads backend-computed `dislocation_by_symbol` payload (ISSUE-04B)
- Shows HIGH_CONVICTION and MODERATE tiers by default
- Provides a toggle to include WATCH tier
- Supports row expansion to display evidence
- Replaced the JS-only `_fmpDislocationType()` heuristic in the Fundamental Snapshot badge with backend payload

---

## 2. Files Changed

| File | Change |
|------|--------|
| `ui/portfolio_alignment/index.html` | Add `#dislocationWatchlistContainer` div; add `dq-fs-*` + `dis-*` CSS; bump v24→v25 |
| `ui/portfolio_alignment/app.js` | `renderDislocationWatchlist()`, `_disRenderRows()`, `_disToggleExpand()`, `_disToggleWatch()`, `_disFromBackend()` added; `renderResults()` calls `renderDislocationWatchlist(data)`; `_dqFundamentalSnapshotHtml()` updated to use backend payload |

**No backend changes. No scoring changes. No CW-DAS changes. No CRA changes.**

---

## 3. Panel Architecture

**Placement:** Below Deployment Queue, above CRA (between `#deploymentPlanContainer` and `#craSection`)

**Container:** `#dislocationWatchlistContainer` — hidden (`display:none`) until data arrives

**Data source:** `data.dislocation_by_symbol` — backend-authoritative, no JS recomputation

**Default visibility:** HIGH_CONVICTION + MODERATE (WATCH hidden until toggled)

**Render path:**
```
renderResults(data)
  └── renderDislocationWatchlist(data)
        └── data.dislocation_by_symbol
              └── _disRenderRows(all, ovBySymbol)
```

---

## 4. New Functions

### `renderDislocationWatchlist(data)`
Top-level panel renderer. Reads `dislocation_by_symbol`, builds the full panel HTML including header, advisory strip, tier summary chips, filter toggle, and table. Calls `_disRenderRows()` for the table body.

### `_disRenderRows(all, ovBySymbol)`
Table body renderer. Filters by `_disShowWatch` flag. Sorts HIGH_CONVICTION → MODERATE → WATCH. Each row is clickable to expand evidence.

### `_disToggleExpand(id)`
Toggles the `.open` class on the expand row identified by `id`.

### `_disToggleWatch()`
Checkbox handler. Sets `_disShowWatch` and calls `_disRenderRows()` with updated filter.

### `_disFromBackend(d)`
Adapter: converts `DislocationType` dict (backend format) to the `{label, cls, evidence}` shape expected by `_dqFundamentalSnapshotHtml()`. Maps:
- `HIGH_CONVICTION` → `{label: "HIGH CONVICTION", cls: "high-conviction"}`
- `MODERATE` → `{label: "MODERATE", cls: "potential"}`
- `WATCH` → `{label: "WATCH", cls: "watch"}`

---

## 5. Legacy Heuristic Migration

`_fmpDislocationType()` is **deprecated** but not removed. The updated `_dqFundamentalSnapshotHtml()` now:

```javascript
const _disBackend = (_lastAnalysisData?.dislocation_by_symbol || {})[sym.toUpperCase()];
const dislocation = _disBackend
  ? _disFromBackend(_disBackend)
  : _fmpDislocationType(meta, ov, thesis, consistency);  // fallback for old runs
```

The fallback ensures old runs (pre-ISSUE-04B) without the payload field continue to work.

---

## 6. New CSS Classes

| Class | Purpose |
|-------|---------|
| `dis-panel` | Watchlist panel container |
| `dis-section-title` | "Dislocation Watchlist" title |
| `dis-advisory-strip` | Amber governance advisory banner |
| `dis-tier-HIGH_CONVICTION` | Green tier badge |
| `dis-tier-MODERATE` | Amber tier badge |
| `dis-tier-WATCH` | Gray tier badge |
| `dis-chip-hc/mod/watch` | Summary count chips in header |
| `dis-expand-row.open` | Expanded evidence row |
| `dis-evidence-list` | Evidence bullet list |
| `dq-fs-badge.*` | Fundamental Snapshot badge variants (newly added to CSS) |
