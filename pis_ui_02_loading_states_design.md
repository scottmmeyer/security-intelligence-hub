# PIS-UI-02 Loading States Design

## Objective
Improve operator visibility during dashboard startup and degraded lineage conditions without changing backend business logic, API shapes, or calculation rules.

## Scope
- Presentation-layer only.
- Files changed:
  - `ui/pis_dashboard/index.html`
  - `ui/pis_dashboard/app.js`
- Files not changed for business logic:
  - governance logic
  - canonical selection logic
  - change detection logic
  - lineage matching logic

## UX Additions
- Global loading banner at startup:
  - `Portfolio Intelligence Dashboard`
  - `Loading data...`
  - loaded-section progress count
  - elapsed time
- Top-level dashboard status panel for major subsystems:
  - Snapshot Inventory
  - Governance
  - Canonical Daily State
  - Change Detection
  - Lineage
- Section-level status badges:
  - `LOADING`
  - `LOADED`
  - `SLOW`
  - `FAILED`
- Section placeholders while data is pending.
- Explicit slow/failure states for degraded endpoints.

## Design Choice
The dashboard no longer waits for one aggregate completion point. Each section is treated as an independently observable task, so healthy sections can render while slow sections remain visible as pending or degraded.

## Lineage Nuance
The top summary section (`Section 5: SIH Lineage Summary`) is backed by `/api/pis/summary` and can remain healthy even when detailed lineage endpoints degrade. Detailed lineage panels use `/api/pis/lineage/latest` and `/api/pis/lineage-summary`, so they correctly transition through `LOADING -> SLOW -> FAILED` when those routes stall.