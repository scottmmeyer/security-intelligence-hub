# PIS-UI-03 Executive Dashboard Design

## Scope

Presentation-only refinement of the PIS dashboard for executive readability.

Out of scope:
- no changes to governance/canonical/change-detection/lineage algorithms
- no backend API contract changes

## UX Objectives

1. Surface top KPIs immediately at page load.
2. Show a clear system-health state (`Loading`, `Healthy`, `Degraded`) independent of table detail visibility.
3. Present concise decision-oriented summary cards for each major subsystem.
4. Reduce cognitive load by collapsing detail tables behind explicit toggles.
5. Preserve PIS-UI-02 progressive rendering behavior and fail-open section loading.

## Layout Decisions

1. Keep existing global loading banner and subsystem panel.
2. Rename subsystem panel heading to **System Status** and add overall health badge.
3. Add `Executive KPI Header` with 8 KPIs:
   - snapshots
   - canonical days
   - PASS
   - WARNING
   - REJECT
   - latest portfolio value
   - latest change
   - lineage matches
4. Add `Executive Summary Cards`:
   - Governance Summary
   - Canonical Selection Summary
   - Portfolio Trend
   - Latest Change Detection
   - Lineage Summary
5. Convert high-volume detail sections to collapsible `<details>` blocks.

## Data Mapping

All data is derived from existing payloads:
- `/api/pis/snapshots`
- `/api/pis/summary`
- `/api/pis/latest`
- `/api/pis/governance-summary`
- `/api/pis/governance/latest`
- `/api/pis/canonical-summary`
- `/api/pis/canonical/latest`
- `/api/pis/changes/latest`
- `/api/pis/lineage/latest`
- `/api/pis/lineage-summary`

## Interaction Model

1. Executive KPI and summary cards render loading placeholders at initialization.
2. As each section payload resolves, derived executive elements refresh incrementally.
3. Slow/failure states continue to use section status contracts from PIS-UI-02.
4. Detail tables remain accessible on demand via collapsible controls.

## Accessibility and Responsiveness

1. Existing status `role="status"` + `aria-live="polite"` shell retained.
2. KPI and summary grids collapse to single-column/two-column responsive layouts below the existing breakpoint.
3. `<summary>` labels are explicit and action-oriented (`Show ... Table`).

## Acceptance Notes

PIS-UI-03 is complete when:
- executive KPI header is visible by default
- executive summary cards are visible by default
- detailed inventory/governance/canonical/change-summary/lineage tables are collapsible
- progressive loading and degraded/failure UX still operate unchanged
