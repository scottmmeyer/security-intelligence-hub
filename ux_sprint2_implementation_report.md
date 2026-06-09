# UX Sprint 2 — Implementation Report

**Sprint ID:** UX-SPRINT-2  
**Date:** 2026-06-09  
**Scope:** STALE-PAR-01 backend fix + UX-PA-02/05/08/09

---

## Items Implemented

| Issue | Title | Priority | Files Changed | Status |
|---|---|---|---|---|
| STALE-PAR-01 | Policy replay on load | HIGH | src/portfolio/runner.py | COMPLETE |
| UX-PA-02 | Reconciliation FAIL explainability | P0 | app.js, index.html | COMPLETE |
| UX-PA-05 | Top allocation drivers summary | P1 | app.js, index.html | COMPLETE |
| UX-PA-08 | Score explanation cleanup | P1 | app.js, index.html | COMPLETE |
| UX-PA-09 | Portfolio alignment narrative | P1 | app.js, index.html | COMPLETE |

---

## Summary of Changes

### STALE-PAR-01 — Policy Replay on Load

**`src/portfolio/runner.py` — `load_analysis_run()`:**
- Calls `_apply_policy_to_recs(recs_list, _load_registry)` after loading recommendations from disk
- Exposes `policy_replay_applied`, `policy_replay_timestamp`, `current_policy_snapshot`, `policy_is_stale` in result
- Loads `reconciliation.json` and exposes `reconciliation_checks` array for UX-PA-02

**`src/portfolio/runner.py` — `run_analysis()` result:**
- Added `reconciliation_checks_warned` field (was missing from fresh-run result)
- Added `reconciliation_checks` full array to fresh-run result

**Effect:** Any PAR loaded via the UI now has policy applied using the current operator policy registry. Historical PARs are not modified on disk. `policy_is_stale` signals when correction was made.

### UX-PA-02 — Reconciliation FAIL Explainability

**New function: `renderReconciliationPanel(data)`**
- Hidden when all checks pass (PASS status + no WARN/FAIL)
- Shown when any FAIL or WARN exists
- Collapsible panel with title, status badge, and certification summary
- Table: Check name, expected vs actual values, operator guidance, `affects_recommendations` label
- For RC-02: shows sub-checks with BSVN/STNG/SIMO classification root cause
- PASS-only state is suppressed to reduce noise

### UX-PA-05 — Top Allocation Drivers Summary

**Modified: `renderAllocationMap()`**
- Computes top 3 overweights, top 3 underweights, top 3 largest gaps from L1 nodes (excluding CASH)
- Rendered as 3-column card strip above the full allocation table
- Each card: node label + drift pp with color coding (red=over, green=under, amber=gap)
- Empty state handled per column ("None above threshold")

### UX-PA-08 — Score Explanation Cleanup

**Modified: `renderMultiDimScores()`**
- Added `defn` field to each dim object with plain-language definition
- Rendered as `.multidim-defn` styled italic text below the sublabel
- Definitions:
  - Allocation Alignment: "How close the portfolio is to its target asset class weights..."
  - Portfolio Quality: "Signal strength, concentration risk, and strategic profile..."
  - Implementation Quality: "How well each position is implemented..."
  - Replay Alignment: "How much of the portfolio has replay evidence backing it..."
- Removed navEl unused variable (dead code cleanup)

### UX-PA-09 — "What matters right now" Narrative

**New function: `renderNarrativeSummary(data)`**
- Rendered between KPI strip and multi-dim scores
- Two-column layout: Observations (left) | Actionable Items (right)
- Up to 3 items per column with color-coded dot indicators (amber=observation, red=action/warn, green=ok)
- Observations sourced from: stale PAR advisory, reconciliation status, alignment score, blocked actions, overweight nodes
- Actionable items sourced from top 3 EXECUTABLE ACTION recs
- Stale PAR advisory badge shown when `data.policy_is_stale === true`

---

## Files Changed

| File | Changes |
|---|---|
| `src/portfolio/runner.py` | Policy replay in load_analysis_run; reconciliation_checks in both load and run result |
| `ui/portfolio_alignment/app.js` | +renderNarrativeSummary, +renderReconciliationPanel, updated renderMultiDimScores (defn), updated renderAllocationMap (drivers), updated renderResults call order |
| `ui/portfolio_alignment/index.html` | +narrativeSummaryContainer, +reconciliationContainer in HTML; +100 lines of CSS for new components |
