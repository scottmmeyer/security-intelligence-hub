# Deployment Queue Render Audit — Phase 7.5C.1

**Date**: 2026-05-31  
**Run under investigation**: PAR-20260531-7F1113AB  
**Investigator**: GitHub Copilot  
**Mandate**: Root-cause only. No code changes. Evidence required.

---

## Executive Summary

Two independent failures prevent the Capital Deployment Queue from appearing in the live UI. Both failures are in the data pipeline, not in the UI render code. The HTML, CSS, and JavaScript are correct.

**Root cause A (primary):** The server process (PID 26613) is stale — started at 09:04:52, before Phase 7.5B code was written to disk at 10:35. Python's module import cache (`sys.modules`) holds the pre-7.5B runner in memory. The `run_analysis` function that ran PAR-20260531-7F1113AB never had deployment_queue logic. No `deployment_queue.json` was written; no `deployment_queue` key appears in the API response.

**Root cause B (secondary / independent):** `load_analysis_run()` in `runner.py` does not read `deployment_queue.json` from disk. Even for the older run PAR-20260529-1463E074, which _does_ have `deployment_queue.json` on disk, the `GET /api/portfolio/runs/{id}` endpoint returns no `deployment_queue` key. This is a structural gap that exists regardless of the server restart issue.

---

## Layer-by-Layer Status Table

| Layer | Status | Evidence |
|-------|--------|----------|
| **Server process** | ❌ FAIL | PID 26613 started 09:04:52 — 88 min before Phase 7.5B changes at 10:35 |
| **runner.py (on disk)** | ✅ PASS | File has deployment_queue code at lines 40, 696, 714, 715, 762, 897 |
| **runner.py (in memory)** | ❌ FAIL | Server's `sys.modules` cache holds pre-7.5B module; on-disk changes are invisible |
| **API — analyze endpoint** | ❌ FAIL | POST /api/portfolio/analyze runs stale `run_analysis`; no `deployment_queue` in response |
| **Artifact on disk** | ❌ FAIL | PAR-20260531-7F1113AB directory has no `deployment_queue.json` |
| **load_analysis_run()** | ❌ FAIL | Only loads: run_metadata, snapshot, concentration, recommendations, alignment, holdings, overlays — `deployment_queue.json` is never read back |
| **API — GET run endpoint** | ❌ FAIL | `GET /api/portfolio/runs/PAR-20260529-1463E074` (run _with_ deployment_queue.json on disk) returns no `deployment_queue` key (confirmed via curl) |
| **API payload** | ❌ FAIL | Both analyze and load-run paths return `{}` for deployment_queue |
| **localStorage (browser)** | ❌ FAIL | `_saveResult(data)` persists whatever analyze returned; no deployment_queue saved |
| **renderDeploymentQueue()** | ⚠ WARN | Function is wired, executes, but hits `if (!dq \|\| ...)` guard and returns `""` silently — no error |
| **#deploymentQueueContainer** | ⚠ WARN | Element exists in DOM; `innerHTML = ""` (empty, not hidden); invisible but structurally correct |
| **CSS** | ✅ PASS | All Phase 7.5C styles present in index.html |
| **app.js version** | ⚠ WARN | `?v=4` is in index.html; browser may still serve cached `?v=3` depending on hard-refresh state, but is a moot secondary issue given upstream failures |

---

## Detailed Evidence

### Server Start Time vs. Code Write Time

```
Server PID 26613 started:  Sun May 31 09:04:52 2026
runner.py modified:        May 31 10:35  (88 minutes after server start)
deployment_queue.py:       May 31 10:35  (same — Phase 7.5B changes)
app.js / index.html:       May 31 10:49  (Phase 7.5C changes)
```

Python `import` is done **inside** the request handler (line 390 of `run_outcome_ui.py`):
```python
from src.portfolio.runner import run_analysis
```
The first call after server start cached the pre-7.5B `runner` module in `sys.modules`. All subsequent calls use the cached module. The on-disk changes at 10:35 have no effect until the server is restarted.

### Artifact Directory Comparison

```
PAR-20260529-1463E074 (pre-7.5B run, server was restarted after 7.5B):
  alignment.csv        concentration.json   deployment_queue.json  ← present
  holdings.csv         recommendations.json run_metadata.json
  reconciliation.json  security_overlays.csv  snapshot.json

PAR-20260531-7F1113AB (new run, stale server):
  alignment.csv        concentration.json   holdings.csv
  recommendations.json reconciliation.json  run_metadata.json
  security_overlays.csv  snapshot.json
                                              ← deployment_queue.json ABSENT
```

### Live API Confirmation

```bash
$ curl http://127.0.0.1:8766/api/portfolio/runs/PAR-20260529-1463E074 | python3 -c "import sys,json; d=json.load(sys.stdin); print(sorted(d.keys()))"
['alignment', 'concentration', 'holdings_count', 'recommendations', 'run_id', 'run_metadata', 'security_overlays', 'snapshot']
# deployment_queue: NOT PRESENT (despite deployment_queue.json existing on disk)

$ curl http://127.0.0.1:8766/api/portfolio/runs/PAR-20260531-7F1113AB | python3 -c "..."
['alignment', 'concentration', 'holdings_count', 'recommendations', 'run_id', 'run_metadata', 'security_overlays', 'snapshot']
# deployment_queue: NOT PRESENT
```

Both confirmed absent via live HTTP.

### renderDeploymentQueue() Behavior

```javascript
function renderDeploymentQueue(data) {
  const el = document.getElementById("deploymentQueueContainer");
  if (!el) return;

  const dq = data.deployment_queue;  // ← undefined (not in API response)
  if (!dq || !Array.isArray(dq.queue) || dq.queue.length === 0) {
    el.innerHTML = "";   // ← silently empties container, returns
    return;
  }
  // ... never reached
}
```

No JavaScript error is thrown. The container is cleared to `""` and the function exits. This is **correct defensive behavior** — the bug is not in the render layer.

### load_analysis_run() Code Gap

```python
def load_analysis_run(run_id: str) -> Optional[dict]:
    result: dict = {"run_id": run_id}
    for fname in ("run_metadata.json", "snapshot.json", "concentration.json"):
        ...
    for fname in ("recommendations.json",):
        ...
    # alignment.csv
    # holdings.csv
    # security_overlays.csv
    # ← NO deployment_queue.json read
    return result
```

`deployment_queue.json` is never read. This is a **separate, independent failure** that persists even after a server restart — any run loaded via `GET /api/portfolio/runs/{id}` will never have deployment_queue data.

---

## Causal Chain

```
Phase 7.5B code written at 10:35
        |
        ↓
Server NOT restarted after 10:35
        |
        ↓
sys.modules['src.portfolio.runner'] = OLD module (no deployment_queue)
        |
        ↓
PAR-20260531-7F1113AB analyzed at 15:53 with old run_analysis()
        |
        ├── deployment_queue.json: NOT written to disk
        └── API response: no deployment_queue key
                |
                ↓
        localStorage saves response without deployment_queue
                |
                ↓
        renderDeploymentQueue(data) → dq = undefined → el.innerHTML = "" → returns
                |
                ↓
        #deploymentQueueContainer: present in DOM, empty, invisible
                |
                ↓
        "CAPITAL DEPLOYMENT QUEUE" section absent from UI ← observed symptom
```

### Independent second failure (load_analysis_run):

```
Even after server restart + re-run:
load_analysis_run() reads deployment_queue.json? → NO
GET /api/portfolio/runs/{id} → response has no deployment_queue
→ Any previously-saved or reloaded run also cannot render the queue
```

---

## What Is Confirmed Working

- `src/portfolio/deployment_queue.py` — correct on disk, 53 tests pass
- `runner.py` on disk — deployment_queue code present at the right lines
- `#deploymentQueueContainer` — present in DOM (Phase 7.5C HTML change confirmed)
- Phase 7.5C CSS — present in `<style>` block of index.html
- `renderDeploymentQueue()` — present in app.js at line 1471
- `renderResults()` call to `renderDeploymentQueue(data)` — wired at line 204
- `app.js?v=4` — version bump confirmed in index.html

---

## Required Fixes (not applied per audit-only scope)

| Fix | Target | Addresses |
|-----|--------|-----------|
| **Restart server** | Process kill + relaunch | Root cause A — clears stale sys.modules cache |
| **Add deployment_queue.json reader to `load_analysis_run()`** | `src/portfolio/runner.py` | Root cause B — enables GET run path to serve queue data |

Both fixes are required. Restarting alone will not fix the GET run path; fixing `load_analysis_run` alone will not help until the server is restarted so new runs write `deployment_queue.json` to disk.
