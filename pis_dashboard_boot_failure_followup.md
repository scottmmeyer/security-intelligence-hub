# PIS Dashboard Boot Failure Follow-up

Date: 2026-06-23

## Actual Browser-Grounded Findings

### 1) Build/load identity verification
- Opened: `http://127.0.0.1:8765/ui/pis_dashboard/index.html?v=debug-boot-2`
- Confirmed HTML marker rendered in page:
  - `PIS_BUILD_HTML=2026-06-23-debug-2`
- Confirmed JS marker in runtime:
  - `window.__PIS_BUILD_JS__ = 2026-06-23-debug-2`
- Confirmed cache-busted URL detection:
  - `YES`

### 2) Why prior screenshot still showed `0 of 21`
- The old page path used plain `app.js` without a version query string.
- Browser could keep serving stale JS while HTML updated (or user remained on a stale tab/session).
- Added explicit cache-busted script URL and visible build markers to verify the loaded assets in-browser.

### 3) Runtime failure found in live diagnostics
After forcing current assets, startup executed and API calls fired, but one runtime render failure appeared:
- `escHtml is not defined`
- This caused section-level failures in rendering paths using `escHtml(...)`.

This is now fixed by adding a shared `escHtml` helper in `ui/pis_dashboard/app.js`.

### 4) Section-count mismatch (`21` vs `60`)
- `21` came from stale/older JS path previously observed in browser shell.
- Current `SECTION_DEFINITIONS` in live loaded JS defines `60` sections.
- Verified in browser diagnostics:
  - `Sections planned: 60`
  - `Sections completed: 60`
  - `Sections failed: 0`
  - `Dashboard load outcome: Loaded`

### 5) API call evidence
- Browser runtime reported 45 `/api/pis/*` and `/api/mei/*` resource requests.
- Sample observed calls:
  - `/api/pis/snapshots`
  - `/api/pis/summary`
  - `/api/pis/latest`
  - `/api/pis/health`
  - `/api/pis/governance/latest`
  - `/api/pis/governance-summary`
  - `/api/pis/canonical/history`
  - `/api/pis/attribution/latest`
  - etc.

Conclusion: API calls are being issued and the loader is no longer stuck at zero.

## Root Cause
1. Stale JS path/caching ambiguity (`app.js` without explicit cache-busting) allowed mismatch between visible HTML and loaded runtime script.
2. Runtime render exception (`escHtml is not defined`) caused section failures after boot.
3. No startup-proof visual diagnostics previously guaranteed immediate visibility when boot failed.

## Why Prior Fix Was Insufficient
- Prior changes improved internals but did not conclusively prove browser was loading the newest JS in the affected user session.
- Missing build markers and cache-busted script URL left stale-asset ambiguity unresolved.
- Runtime `escHtml` missing helper still existed and could degrade sections.

## Files Changed
- `ui/pis_dashboard/index.html`
  - Added visible HTML build marker.
  - Updated script reference to cache-busted URL: `app.js?v=2026-06-23-debug-2`.
- `ui/pis_dashboard/app.js`
  - Added JS build marker and global marker (`window.__PIS_BUILD_JS__`).
  - Added boot logs and guarded bootstrap (`DOMContentLoaded` + try/catch).
  - Added startup failure rendering block (status panel + stack preview).
  - Added explicit status diagnostics (sections planned/completed/failed, first failed section/endpoint/message, cache-busted detection).
  - Added endpoint-aware error context for fetch/timeout/json failures.
  - Added shared `escHtml` helper to prevent runtime renderer failures.
  - Preserved fail-open section semantics and performance card behavior.
- `tests/test_pis_dashboard_loading_resilience.py`
- `tests/test_pis_performance_returns_display.py`
- `tests/test_pis_dashboard_boot_path.py` (new)

## Before/After Behavior

### Before
- Could show shell with static loader text at `0 of 21`.
- Ambiguous whether current JS was loaded.
- No definitive boot marker proof in UI.

### After
- Build markers confirm exact HTML/JS revision in browser.
- Boot path is guarded and logs startup steps.
- Startup failures are visible in status panel (not silent spinner).
- Loader completed fully in browser validation:
  - `Dashboard load outcome: Loaded`
  - `Sections planned/completed: 60/60`
  - `Sections failed: 0`
- Performance Returns card remains visible and non-blocking with validation language.

## Tests Run
1. `node --check ui/pis_dashboard/app.js`
2. `PYTHONPATH=. .venv/bin/python -m pytest tests/test_pis_ui_phase1_dashboard.py tests/test_pis_dashboard_loading_resilience.py tests/test_pis_performance_returns_display.py tests/test_pis_dashboard_boot_path.py -v`

Result: 16 passed.

## Browser Validation Result
- URL: `http://127.0.0.1:8765/ui/pis_dashboard/index.html?v=debug-boot-2`
- HTML marker: `PIS_BUILD_HTML=2026-06-23-debug-2`
- JS marker: `2026-06-23-debug-2`
- Cache-busted detected: `YES`
- Load outcome: `Loaded`
- Sections: `60 planned / 60 completed / 0 failed`
- API resource requests observed: 45

## Governance Safety Confirmation
No scoring, ranking, allocation, recommendation, replay, CW-DAS, UCF, CRA, PAP, or ESS algorithm logic changed.
All changes are dashboard boot reliability, diagnostics, and display-only visibility improvements.
