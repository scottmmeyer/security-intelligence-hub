# Phase 23.6B — UI Implementation Summary

**Date:** 2026-06-04
**Status:** COMPLETE

---

## Files Modified

| File | Change | Lines Added |
|------|--------|------------|
| `ui/portfolio_alignment/index.html` | CRA section HTML + ~230 lines CSS | ~270 |
| `ui/portfolio_alignment/app.js` | CRA JS functions + `loadCRAProposal()` call in `renderResults` | ~310 |

**Total lines added:** ~580 (UI only; no backend changes required)

---

## UI Architecture

### Placement
- New collapsible panel below Capital Deployment Queue
- Auto-triggers on portfolio analysis completion (via `renderResults()`)
- Also available via ↺ Refresh Proposal button for standalone refresh without re-running analysis

### Three-Column Layout

```
┌──────────────────────────┬──────────────────────┬──────────────────────────┐
│   Capital Sources         │   Rotation Map        │   Portfolio Impact       │
│   (What to Sell)          │   (Proceeds → Targets)│   (Estimate)             │
├──────────────────────────┼──────────────────────┼──────────────────────────┤
│ Est. Capital Pool: $xxx   │ Pool → CW-DAS Queue   │ ⚠ ESTIMATE ONLY banner   │
│                           │                       │                          │
│ [1] Signal Deterioration  │ #1 VRT CCL DAS 95.1   │ Alignment: 0.41 → 0.55   │
│   TSLA URGENT 🔒 BLOCKED  │    $49,506 | 3.8%→5.8%│ Δ +0.14 (estimated)      │
│   FIS HIGH Tax·A ✓ Include│                       │                          │
│                           │ #2 ARW HCA DAS 93.9   │ Concentration: 27.5%     │
│ [2] Strategic Exit        │    $49,506 | 2.2%→3.0%│ → 25.3% (estimated)      │
│   (empty)                 │                       │                          │
│ [3] Exposure Reduction    │                       │ OW Nodes Before: 21      │
│   ...                     │                       │ OW Nodes After:  20      │
└──────────────────────────┴──────────────────────┴──────────────────────────┘
```

---

## Key UI Functions Implemented

| Function | Purpose |
|----------|---------|
| `loadCRAProposal()` | Async fetch of `GET /api/cra/proposal`; handles loading/error states |
| `_renderCRAProposal(p)` | Top-level render: status badge, review flags, 3-column layout |
| `_craBuildSourcesCol(p)` | Column 1: pool strip + 5 category accordions |
| `_craBuildSourceCard(s)` | Individual source card with badges, proceeds, checkboxes |
| `_craBuildRotationMapCol(p)` | Column 2: pool summary + deployment target cards |
| `_craBuildTargetCard(t)` | Individual deployment target card |
| `_craBuildImpactCol(p)` | Column 3: alignment delta, concentration delta, OW nodes, narrative |
| `_craCatToggle(el)` | Category accordion expand/collapse |
| `_craSkipToggle(symbol)` | Skip/Include mutual exclusion logic |
| `_craUpdatePool()` | Recalculate capital pool display from Include checkboxes |
| `_craFmt(v)` | Currency formatter (M/K suffix) |
| `_craShortNode(node)` | Shorten allocation node labels for display |

---

## CSS Classes Implemented

**Panel structure:** `.cra-section`, `.cra-panel`, `.cra-panel-header`, `.cra-columns`

**Status badges:** `.cra-status-badge`, `.cra-status-READY`, `.cra-status-DRAFT`, `.cra-status-OPERATOR_REVIEW_REQUIRED`

**Source cards:** `.cra-source-card`, `.cra-blocked`, `.cra-sym`, `.cra-pri-{PRIORITY}`, `.cra-tax-{BUCKET}`, `.cra-policy-badge`, `.cra-monitor-badge`

**Target cards:** `.cra-target-card`, `.cra-target-rank`, `.cra-tier-CCL`, `.cra-tier-HCA`, `.cra-target-amount`

**Impact column:** `.cra-impact-card`, `.cra-estimate-banner`, `.cra-impact-row`, `.cra-delta-pos`, `.cra-delta-neg`, `.cra-node-resolved`, `.cra-node-remaining`

---

## Responsive Design
Grid collapses to single column at ≤960px viewport width.

---

## Integration Points
- Auto-loads after `renderResults(data)` — no user action required on analysis completion
- `↺ Refresh Proposal` button re-queries API without triggering a PAR run
- Include/Skip checkboxes update capital pool display in real-time (client-side only; no API call)
- Review flags panel auto-shows/hides based on `review_flags.length`
