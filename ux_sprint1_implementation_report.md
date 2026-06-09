# UX Sprint 1 — Implementation Report

**Sprint ID:** UX-SPRINT-1  
**Date:** 2026-06-09  
**Scope:** Portfolio Alignment page UX improvements (5 items)

---

## Items Implemented

| Issue   | Title                              | Priority | File(s) Changed                      | Status    |
|---------|------------------------------------|----------|--------------------------------------|-----------|
| UX-PA-01 | Rename "Legacy Alignment" KPI      | P0       | app.js                               | COMPLETE  |
| UX-PA-03 | Reorder page sections              | P0       | index.html                           | COMPLETE  |
| UX-PA-04 | Multi-dim score nav links          | P1       | app.js, index.html (CSS)             | COMPLETE  |
| UX-PA-06 | Blocked rec unblock guidance       | P1       | app.js, index.html (CSS)             | COMPLETE  |
| UX-PA-07 | Deployable cash context sub-label  | P1       | app.js, index.html (CSS)             | COMPLETE  |

## Items NOT Implemented

- **UX-PA-02**: Deferred by explicit user direction ("do not implement UX-PA-02 in this sprint")

---

## Summary of Changes

### UX-PA-01 — KPI Label Rename
- Changed `"Legacy Alignment"` → `"Allocation Alignment"` in `renderKPIs()`.
- Aligns with how the field is named throughout the rest of the page and in multi-dim scores.
- No behavioral change; display label only.

### UX-PA-03 — Page Section Reorder
- Moved CRA (Capital Rotation Advisor) and PAP (Portfolio Action Pipeline) HTML sections to appear **before** the Security-Level Intelligence Overlay row.
- Previous order: Recs/Replay → Security Intelligence → CRA → PAP
- New order: Recs/Replay → CRA → PAP → Security Intelligence
- This puts the most actionable panels (CRA, PAP) closer to the recommendation lanes, above the more diagnostic security overlay.

### UX-PA-04 — Multi-Dim Navigation Links
- Each of the 4 multi-dim score cards now has a clickable "↓ View" link that smooth-scrolls to its corresponding page section:
  - Allocation Alignment → `#allocationPanel`
  - Portfolio Quality → `#deploymentQueueContainer`
  - Implementation Quality → `#portfolioActionPipelineSection`
  - Replay Alignment → `#replayPanel`
- Added `.multidim-nav` CSS class (styled as a subtle underlined accent link).

### UX-PA-06 — Blocked Rec Unblock Guidance
- For `BLOCKED_BY_POLICY` recs: displays `"To unblock: remove DO_NOT_SELL policy on [SYMBOL]."` in italic muted text below the blocked badge.
- For `DEFERRED_BY_POLICY` recs: displays `"To prioritize: remove SELL_LAST policy on [SYMBOL]."` similarly.
- Symbol extracted from `r.affected_symbols[0]`.
- Added `.rec-unblock-hint` CSS class (block, italic, muted, small text).
- Zero policy logic change — display only.

### UX-PA-07 — Deployable Cash Context Sub-label
- The "Deployable Cash" summary card in the Deployment Queue now shows a sub-label:
  `"Excess above {X}% mandate floor ⓘ"` with a `title` tooltip detailing full cash MV, floor reserve, and deployable amount.
- Added `.dq-summary-sublbl` CSS class.
- Makes clear to operators that "deployable" means excess above the mandate floor, not total cash.

---

## Files Changed

- `ui/portfolio_alignment/app.js` — 4 changes (PA-01, PA-04, PA-06, PA-07)
- `ui/portfolio_alignment/index.html` — 4 changes (PA-03 section reorder + PA-04/PA-06/PA-07 CSS)
