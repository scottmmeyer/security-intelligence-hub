# PIS Dashboard Loading and Performance Fix

Date: 2026-06-23
Scope: Dashboard reliability and display-only performance visibility.

> Freshness note (2026-07-07): This is a historical incident/remediation note. Subsequent UI cleanup and compatibility revisions may have narrowed, replaced, or restored portions of the behaviors described below.

## Root Cause of Spinner

The dashboard script had a JavaScript parse error in `ui/pis_dashboard/app.js` caused by a malformed `SUBSYSTEM_DEFINITIONS` object (`allocationPolicyGovernance` block had an extra dangling `sectionKeys` fragment and brace).

Impact:
- `initialize()` never executed.
- The static banner remained stuck at `Loading data...` / `0 of 21 sections loaded`.

## Endpoint/Section Loading Block

After fixing parse startup, section orchestration worked. The loader now advances immediately (`runSectionTask`) and each section can fail independently without blocking global progress.

## Fix Implemented

### 1. Startup parse fix
- Repaired malformed object literal in `SUBSYSTEM_DEFINITIONS`.

### 2. Section loading resilience hardening
- Added per-section error state tracking (`sectionErrors`).
- Added endpoint-aware error decoration in `loadJson`:
  - timeout errors include `requestPath`
  - HTTP errors include `requestPath`
  - JSON parse errors include `requestPath`
- Added explicit section failure console diagnostics:
  - `console.error([PIS Dashboard] Section ... failed, endpoint/message)`
- Added dashboard status panel load outcome states:
  - `Loading`
  - `Loaded`
  - `Loaded with warnings`
  - `Loaded with unavailable sections`
- Added visible section diagnostics panel listing failed section reasons and endpoint context.

### 3. Performance return display (display-only)
- Added `Performance Returns (Snapshot-Based)` executive summary card.
- Source data: existing `timeline` from `/api/pis/summary` (`pis_value_timeline`).
- Card displays:
  - Latest portfolio value
  - Start value (first snapshot)
  - Absolute gain/loss
  - Total return
  - 1D / 5D / 1M return (when available)
  - Since inception return
  - Benchmark comparison (excess) if available
  - Confidence label
- Data quality language added:
  - `Snapshot-based estimate (cash-flow-unadjusted)`
  - explicit reconciliation warning and validation-pending fallback.

## Before/After Behavior

Before:
- Dashboard shell rendered but JS never initialized due parse failure.
- Banner remained stuck at zero progress.

After:
- Dashboard initializes and progresses immediately.
- Live check showed active loading progress (`14 of 60 sections loaded` while requests in flight).
- Executive cards render including new performance return card.
- Failed section(s), if any, are surfaced in diagnostics with endpoint context instead of silent hang.

## Performance Return Data Source and Confidence

- Data source: `/api/pis/summary` timeline history (`portfolio_value` over snapshots).
- Classification: **Estimated** snapshot-based value-change view.
- Not labeled as finalized investment performance because external cash-flow reconciliation is pending.

## Files Changed

- `ui/pis_dashboard/app.js`
- `ui/pis_dashboard/index.html`
- `tests/test_pis_dashboard_loading_resilience.py` (new)
- `tests/test_pis_performance_returns_display.py` (new)

## Tests Run

1. `node --check ui/pis_dashboard/app.js` (pass)
2. `PYTHONPATH=. .venv/bin/python -m pytest tests/test_pis_ui_phase1_dashboard.py -v` (11 passed)
3. `PYTHONPATH=. .venv/bin/python -m pytest tests/test_pis_dashboard_loading_resilience.py tests/test_pis_performance_returns_display.py -v` (3 passed)
4. `PYTHONPATH=. .venv/bin/python -m pytest tests/test_pis_ui_phase1_dashboard.py tests/test_pis_dashboard_loading_resilience.py tests/test_pis_performance_returns_display.py -v` (14 passed)

## Governance/Algorithm Safety

Confirmed: No scoring, ranking, allocation, recommendation, replay, CW-DAS, UCF, CRA, PAP, or ESS algorithm logic was modified.

All changes are dashboard reliability, diagnostics, and display-only portfolio visibility enhancements.
