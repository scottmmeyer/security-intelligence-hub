# Phase 23.6B — Governance Review

**Date:** 2026-06-04

---

## Non-Negotiable Constraint Verification

| Constraint | Status | Evidence |
|------------|--------|----------|
| CW-DAS not modified | ✅ COMPLIANT | UI displays `deployment_score` and `rank` as received from API — no recalculation |
| ESS not modified | ✅ COMPLIANT | ESS values displayed read-only from source card `evidence_summary` |
| Replay not modified | ✅ COMPLIANT | No replay fields modified in UI |
| FMI not modified | ✅ COMPLIANT | No FMI logic in UI |
| Policy engine not modified | ✅ COMPLIANT | Policies displayed as badges; DO_NOT_SELL disables checkbox and shows MONITOR ONLY |
| No new scoring | ✅ COMPLIANT | UI renders values from API; no client-side scoring |
| No backend mutations | ✅ COMPLIANT | `loadCRAProposal()` is GET-only; no POST/PUT/DELETE |
| Operator authority preserved | ✅ COMPLIANT | Include/Skip checkboxes; all guidance labels explicit |

---

## Guidance Transparency

Every guidance element in the CRA UI is explicitly labeled:

| UI Element | Transparency Label |
|------------|-------------------|
| CRA Panel header | "Guidance only — not trade instructions" |
| Impact column | Yellow ⚠ "ESTIMATE ONLY — Full Re-Analysis Required for Precision" banner |
| Target cards | Rank and DAS score shown as-is from CW-DAS queue |
| Deployment targets | No auto-execution, no trade buttons |
| Review flags | Explicit ⚠ "Operator Review Required" section |

---

## Operator Authority Design

| Feature | Implementation |
|---------|---------------|
| Include/Skip checkboxes | Every non-blocked source has Include/Skip controls |
| DO_NOT_SELL blocking | Checkbox disabled, labelled "MONITOR ONLY", greyed card |
| CORE_ANCHOR review | "⚠ Review required" badge visible on card |
| SELL_LAST deference | "⏸ SELL LAST" badge shown; not blocked from pool |
| Capital pool update | Real-time recalculation as operator includes/excludes |
| Refresh Proposal | Operator can re-query at any time without re-running analysis |

---

## No Backend Modifications

No backend files were modified in Phase 23.6B. Only UI files changed:

- `ui/portfolio_alignment/index.html` — HTML structure + CSS
- `ui/portfolio_alignment/app.js` — JavaScript functions

The `GET /api/cra/proposal` endpoint (implemented in Phase 23.6A) was used unchanged.

---

## XSS Prevention

All user-derived strings are sanitized via `escHtml()` before insertion into the DOM:

- All `s.symbol`, `s.evidence_summary`, `s.tax_annotation` fields passed through `escHtml()`
- All `t.symbol`, `t.allocation_node`, `t.allocation_note` fields passed through `escHtml()`
- Review flags, narrative text, all string fields: `escHtml()` applied
- No `innerHTML` assignments with raw API strings; all use `escHtml()`
