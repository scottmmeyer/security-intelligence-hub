# UX Sprint 1 — Validation

**Date:** 2026-06-09

---

## Regression Outcome

| Suite | Passed | Skipped | Failed |
|---|---|---|---|
| Full test suite (pytest) | 1192 | 1 | **0** |

No regressions introduced by this sprint.

---

## Per-Item Validation

### UX-PA-01 — KPI Label Rename

- Searched for all occurrences of `"Legacy Alignment"` in `app.js` and `index.html`.
- Confirmed single occurrence in `renderKPIs()`. No other references.
- Label now reads `"Allocation Alignment"` consistently with multi-dim score label and field name.
- **Validated.**

### UX-PA-03 — Page Section Reorder

- Confirmed HTML file: CRA div appears at Row 3b, PAP at Row 3c, Security Intelligence at Row 4.
- No JavaScript render order changes needed — `renderSecurityOverlays` / `renderPortfolioActionPipeline` / `loadCRAProposal` still called in same order (visual order driven by HTML position, not JS call order).
- CRA and PAP sections are `display:none` by default and only shown when content loads — no visual change if neither panel is active.
- **Validated.**

### UX-PA-04 — Multi-Dim Navigation Links

- Confirmed all 4 anchor targets exist in HTML: `allocationPanel`, `deploymentQueueContainer`, `portfolioActionPipelineSection`, `replayPanel`.
- `scrollIntoView` is a standard DOM method with universal browser support.
- No `navEl` variable referenced after assignment (dead var cleaned up in code review — it was set but not needed; JS works via inline function in onclick).
- `.multidim-nav` CSS added to index.html.
- **Validated.**

### UX-PA-06 — Blocked Rec Unblock Guidance

- Confirmed `r.affected_symbols` is set by `apply_policy_to_recommendations` in `operator_policy.py`.
- `escHtml()` applied to symbol to prevent XSS.
- Hint only shown if symbol is non-empty — safe null case handled.
- `.rec-unblock-hint` CSS added to index.html.
- **Validated.**

### UX-PA-07 — Deployable Cash Context Sub-label

- `_cashTargetPct` is already computed upstream in `renderDeploymentQueue` from `cashCtx.mandate_floor_pct` — the same value is reused in the sub-label template string.
- `cashCtx.cash_mv` and `cashCtx.floor_mv` are used in the tooltip title — they may be 0 if not provided by the PAR; `|| 0` default applied.
- `.dq-summary-sublbl` CSS added to index.html.
- **Validated.**

---

## UI-Specific Checks

- No console.log or debug artifacts left in JS changes.
- No inline styles introduced outside of dynamically computed color values.
- All new CSS classes follow existing naming convention (kebab-case, module-prefix).
