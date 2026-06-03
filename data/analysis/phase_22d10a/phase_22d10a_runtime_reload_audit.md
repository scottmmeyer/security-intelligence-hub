# Phase 22D.10A — Runtime Reload Audit
**Date:** 2026-06-03  
**Scope:** scripts/run_outcome_ui.py, Python module loading behavior  
**Question:** Was restart required? Is old code still loaded after file edits? Is hot reload functioning?

---

## 1. Server Architecture

The server (`scripts/run_outcome_ui.py`) is implemented as:
```python
class _Handler(http.server.SimpleHTTPRequestHandler):
    ...

with socketserver.TCPServer(("127.0.0.1", args.port), _Handler) as httpd:
    httpd.serve_forever()
```

**Framework:** Python standard library `http.server` + `socketserver.TCPServer`  
**Hot Reload:** **NOT IMPLEMENTED**  
**Auto-Reload:** **NOT IMPLEMENTED**  
**Debug Mode:** **NOT AVAILABLE** (not Flask/Django; no development server with reload)

---

## 2. Python Module Load Behavior

The server imports application modules on first use via dynamic imports within handler methods:

```python
# From scripts/run_outcome_ui.py (GET /api/portfolio/runs/{id})
from src.portfolio.runner import load_analysis_run

# From POST /api/portfolio/analyze
from src.portfolio.runner import run_analysis
```

### Critical Finding: Import Caching

Python caches all imports in `sys.modules` after first import. Subsequent requests **reuse the already-loaded module objects** from the first import.

**Consequence:** If `src/portfolio/runner.py` is edited **after** the server has started and a first request has been processed, the server will continue executing the **old code** for all subsequent requests until the server process is restarted.

| Event | Python Module State |
|---|---|
| Server starts | No modules loaded yet |
| First `/api/portfolio/analyze` request | `src.portfolio.runner` loaded → cached in `sys.modules` |
| Edit to `src/portfolio/runner.py` on disk | **sys.modules unchanged — old code still active** |
| Second request | **Old code executes** |
| Server restart | `sys.modules` cleared → new code loaded on first request |

---

## 3. Phase 22D.10 Specific Analysis

Phase 22D.10 modified:
- `src/portfolio/models.py` — added `safe_to_offset_cash` field
- `src/portfolio/runner.py` — settlement adjustment engine, CW-DAS remediation, lineage
- `scripts/run_outcome_ui.py` — API endpoint cash_arg update
- `ui/portfolio_alignment/app.js` — UI disclosure

### Was the server running when the code changes were made?

Evidence: The terminal history shows `PYTHONPATH=. .venv/bin/python3 scripts/run_outcome_ui.py --port 8765 &` was run prior to and separately from the code edits. The server was running as a background process (`&`) throughout the session.

### Were Python changes immediately effective?

**NO.** The server had already cached its initial module set. Any `src/portfolio/runner.py` edits made while the server was running were not visible to the server's `sys.modules` cache.

### Was restart required for Python changes?

**YES.** Restart was required to unload cached module objects and force re-import of modified source files.

### Was restart required for JS changes?

**NO** — from the server's perspective. The server reads JS from disk on every request. However, the **browser** had cached `app.js?v=4`, so restart indirectly triggered a browser reload (see Q1 audit).

---

## 4. Effective Change Visibility Timeline

| Change Type | Visible Without Restart? |
|---|---|
| `src/portfolio/*.py` edits | **NO — requires server restart** |
| `scripts/run_outcome_ui.py` edits | **NO — requires server restart** |
| `ui/portfolio_alignment/app.js` edits | YES (served from disk) but browser cache may prevent it |
| `ui/portfolio_alignment/index.html` edits | YES (served from disk) |
| `config/*.yaml` edits | Depends — loaded per-request or cached? |
| `data/` file changes | YES — read per-request |

---

## 5. Root Cause of Phase 22D.10 Stale State

The observation that "Settlement disclosure appeared after application restart" is explained by two independent stale state mechanisms that resolved simultaneously on restart:

1. **Python stale state:** Server was running with pre-22D.10 `runner.py` (no settlement engine). New runs analyzed after code changes but before restart would have produced `deployment_queue.json` **without** `settlement_adjustment` or `adjusted_deployable_mv` fields. The UI would have shown no settlement disclosure because `cashCtx.settlement_adjustment` was `null`.

2. **Browser cache stale state:** Even if run data included settlement fields, the browser was rendering with pre-22D.10 `app.js` that did not include the disclosure variables or HTML. No banner would appear.

Both were resolved by the restart.

---

## 6. Verification

PAR-20260603-AC8FD5F0 (the certification run) was produced **after** restart and confirms the Python changes are now active:

- `snapshot.json` contains `settlement_adjustment: 3566.55` ✅
- `deployment_queue.json/cash_context` contains all 4 settlement fields ✅
- `deployment_plan.json` has `deployable_cash: 4091.7` (not 7658.25) ✅

These fields would not exist if the old code were still executing.

---

## 7. Verdict

**Was restart required? YES — for both backend Python modules and to trigger browser asset refresh.**

**Was old code still loaded before restart? YES.**

**Is hot reload functioning? NOT APPLICABLE — hot reload is not implemented and was never expected in this architecture.**

**FINDING: OPERATIONALLY ACCEPTABLE** for a single-operator local dev server. Behavior is consistent with `http.server` architecture. Operators must restart after Python code changes — this is a known characteristic of the stack, not a defect.
