# PA-006 — Allocation Drift Trend Visibility

**Issue ID:** PA-006  
**Area:** Portfolio Alignment  
**Priority:** MEDIUM  
**Complexity:** L  
**Status:** Open

---

## Title

Allocation Drift Trend Visibility — Only Current Snapshot Drift Is Displayed

---

## Problem Statement

The Portfolio Alignment panel shows current allocation drift values (e.g., INTERNATIONAL = +6.1pp overweight) but provides no historical trend context. An operator cannot determine whether a drift is worsening, improving, or stable. A +6.1pp overweight today might be improving from +8pp last week or worsening from +4pp — the system provides no way to distinguish these scenarios.

---

## Current Behavior

- Per-node drift is shown as a single current value (e.g., +6.1pp, +4.4pp, -6.2pp)
- No historical drift data is displayed
- No trend direction (improving / worsening / stable) is indicated

---

## Expected Behavior

The Portfolio Alignment panel should surface drift trend context alongside current drift values:

1. **30-day drift trend** — how has the drift changed over the past 30 days?
2. **Since last deployment** — what was the drift at the last capital deployment event?
3. **Trend direction indicator** — improving / worsening / stable (with threshold for significance)

Optional enhancements:
- 90-day drift trend
- Sparkline chart per node

---

## Evidence

- Portfolio Alignment panel showing static drift values: INTERNATIONAL +6.1pp, ULTRA_MEGA +4.4pp, US.LARGE -6.2pp
- Historical PAR runs available (data/portfolio_ingestion/analysis_runs/) — drift history is computable
- Operator question during review: "Is this getting better or worse?"

---

## Acceptance Criteria

- [ ] Drift trend direction (↑ worsening / ↓ improving / → stable) displayed per allocation node
- [ ] 30-day trend context available on demand (tooltip, drill-down, or inline)
- [ ] "Since last deployment" drift comparison available
- [ ] Trend calculation uses actual historical PAR data (not estimated)
- [ ] Missing history gracefully handled (new portfolio, first run, etc.)

---

## Dependencies

- Historical PAR run data (data/portfolio_ingestion/analysis_runs/)
- Alignment data model (per-run drift values)
- Portfolio Alignment UI component

---

## Complexity Notes

L complexity. Requires:
1. A drift history aggregator that reads alignment data across multiple PAR runs for the same portfolio
2. A trend computation layer (delta, direction, significance threshold)
3. UI components to display trend indicators

This is a meaningful new capability, not a display tweak.
