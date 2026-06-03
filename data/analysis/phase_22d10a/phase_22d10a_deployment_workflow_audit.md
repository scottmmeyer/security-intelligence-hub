# Phase 22D.10A — Deployment Workflow Audit
**Date:** 2026-06-03  
**Scope:** Operator deployment procedure after code changes  
**Question:** What steps are required after code changes? Are they documented? Could future operators encounter stale logic?

---

## 1. Current Deployment Steps (Reconstructed)

No formal deployment runbook was found in the repository. The following steps have been reconstructed from architecture analysis and session observation:

### Required Steps After Python Code Changes

| Step | Action | Required? | Documented? |
|---|---|---|---|
| 1 | Stop running server: `pkill -f run_outcome_ui.py` | **YES** | No |
| 2 | Start fresh server: `PYTHONPATH=. .venv/bin/python3 scripts/run_outcome_ui.py --port 8765 &` | **YES** | No |
| 3 | Hard-refresh browser (Cmd+Shift+R) | **YES** (for JS changes) | No |
| 4 | Increment `?v=N` in index.html if app.js changed | **RECOMMENDED** | No |
| 5 | Submit a new analysis run (re-run the portfolio CSV) | **YES** (for backend logic changes) | No |

### Required Steps After JavaScript-Only Changes

| Step | Action | Required? |
|---|---|---|
| 1 | Increment `?v=N` in index.html | **YES** |
| 2 | Hard-refresh browser | **YES** |
| 3 | Server restart | Not required |

### Required Steps After Config/YAML Changes

| Step | Action | Required? |
|---|---|---|
| 1 | Verify module-level caching of config | Depends on impl |
| 2 | Server restart if config loaded at import time | Conditional |

---

## 2. Documentation Status

| Document | Exists? | Location |
|---|---|---|
| Deployment runbook | **NO** | — |
| Code change checklist | **NO** | — |
| README restart instructions | Partial | README.md (server start command documented, restart procedure not) |
| CHANGELOG / release notes | **NO** | — |
| Phase completion checklists | **YES** | `data/analysis/phase_*/` (per-phase, not operational) |

---

## 3. Stale Recommendation Risk Assessment

### Scenario: Future operator edits runner.py and does not restart

**Risk:** The operator edits the settlement adjustment logic (or any other business logic in `src/portfolio/runner.py`) and immediately analyzes a portfolio without restarting the server.

**Result:** The analysis runs against the **old** business logic. The resulting `snapshot.json`, `deployment_queue.json`, and `deployment_plan.json` reflect the **pre-edit** behavior. The operator may believe the change is active when it is not.

**Severity:** HIGH — could produce materially incorrect investment recommendations that appear legitimate.

### Scenario: Future operator edits app.js and does not hard-refresh

**Risk:** UI continues to display pre-edit behavior. Settlement disclosure does not appear even if backend data is correct.

**Severity:** MEDIUM — UI misrepresentation of correct backend state; operator may believe remediation is not applied.

### Scenario: Phase 22D.10 recurs (another backend fix is deployed)

Without a documented restart requirement, the exact stale-state scenario that occurred in Phase 22D.10 will recur. The operator will make backend changes, run an analysis, observe no change in output, and may incorrectly conclude the code change was ineffective — or worse, may not notice the discrepancy at all.

---

## 4. Operator Knowledge Requirements

The following implicit knowledge is required to correctly deploy changes and is currently undocumented:

1. Python server is **not hot-reload capable** — restart is mandatory for any `.py` change
2. `app.js` is cached by the browser — version string must be incremented or hard refresh required
3. Existing run artifacts (snapshot.json, deployment_queue.json) are **not retroactively updated** — to certify a code change, a fresh analysis run on the same portfolio CSV must be submitted
4. `deployment_plan.json` is generated on-demand (via the `/api/portfolio/deployment-plan` endpoint or the UI button) — it is not regenerated automatically when code changes
5. The server must be started from the repository root with `PYTHONPATH=.` set

---

## 5. Recommended Operational Protocol (Advisory — Not Implemented)

After any code change to `src/**/*.py`, `scripts/run_outcome_ui.py`:
```
1. pkill -f run_outcome_ui.py
2. PYTHONPATH=. .venv/bin/python3 scripts/run_outcome_ui.py --port 8765 &
3. Resubmit reference portfolio for fresh run
4. Verify output JSON fields match expected values
```

After any change to `ui/**/*.js`:
```
1. Increment ?v=N in the affected index.html
2. Hard-refresh browser (Cmd+Shift+R)
3. Verify UI renders expected new elements
```

---

## 6. Verdict

**What steps are required after code changes?** Server restart (mandatory for Python) + browser hard refresh + version string increment (for JS) + fresh analysis run.

**Are those steps documented?** **NO.** No runbook exists in the repository.

**Could future operators encounter stale recommendation logic?** **YES.** Without documented restart requirements, future operators may unknowingly submit analysis runs against stale Python logic and make investment decisions based on pre-fix behavior.

**FINDING: OPERATIONALLY ACCEPTABLE** for a single-operator local dev server, given the operator understands the stack. The risk increases proportionally with operator count and session gap between edits and testing. A minimal deployment checklist is advisable but not blocking.
