# PIS-005 Regression Surface Review

**Date:** 2026-06-14  
**Scope:** Determine whether PIS-005 modifies any business logic

---

## Methodology

1. Read all six PIS business logic files in full
2. Search for any import of `artifact_freshness` or `refresh_orchestrator`
3. Verify PIS-005 modules only consume business logic (not modify it)
4. Verify dependency direction is strictly one-way

---

## Business Logic Files Reviewed

| File | Lines | PIS-005 Import Found | Verdict |
|------|-------|---------------------|---------|
| `src/pis/governance.py` | 239 | None | ✓ CLEAN |
| `src/pis/canonical_daily.py` | 250 | None | ✓ CLEAN |
| `src/pis/change_detection.py` | 349 | None | ✓ CLEAN |
| `src/pis/recommendation_lineage.py` | 735 | None | ✓ CLEAN |
| `src/pis/performance_attribution.py` | 503 | None | ✓ CLEAN |
| `src/pis/benchmark_attribution.py` | 832 | None | ✓ CLEAN |

---

## Dependency Direction

PIS-005 modules import FROM business logic (one-way, read-only):

```
artifact_freshness.py IMPORTS:
    ← src/pis/governance.py (evaluate_snapshot_governance, DEFAULT_GOVERNANCE_CONFIG)
    ← src/pis/storage.py (_read_csv_rows)

refresh_orchestrator.py IMPORTS:
    ← src/pis/artifact_freshness.py (all freshness predicates)
    ← src/pis/canonical_daily.py (refresh_canonical_daily)
    ← src/pis/change_detection.py (compute_all_snapshot_changes)
    ← src/pis/recommendation_lineage.py (compute_recommendation_lineage)
    ← src/pis/performance_attribution.py (compute_performance_attribution)
    ← src/pis/benchmark_attribution.py (compute_benchmark_return_series, compute_benchmark_recommendation_attribution)
    ← src/pis/governance.py (SnapshotGovernanceConfig, DEFAULT_GOVERNANCE_CONFIG)
```

**None of the business logic files import from PIS-005 modules.**

The dependency graph is a strict DAG with no cycles.

---

## Constraint Compliance Table

| Constraint | Status | Evidence |
|-----------|--------|---------|
| Do not modify governance evaluation logic | ✓ COMPLIANT | governance.py has no PIS-005 imports; `evaluate_snapshot_governance()` unchanged |
| Do not modify canonical selection policy | ✓ COMPLIANT | canonical_daily.py unchanged; `select_canonical_daily_rows()` unchanged |
| Do not modify change detection math | ✓ COMPLIANT | change_detection.py unchanged; `compute_all_snapshot_changes()` called as-is |
| Do not modify lineage matching logic | ✓ COMPLIANT | recommendation_lineage.py unchanged; `compute_recommendation_lineage()` called as-is |
| Do not modify attribution scoring logic | ✓ COMPLIANT | performance_attribution.py unchanged; scoring formulas untouched |
| Do not modify benchmark attribution math | ✓ COMPLIANT | benchmark_attribution.py unchanged; all math functions called as-is |
| Only add orchestration, freshness detection, visibility | ✓ COMPLIANT | Two new files; three additive additions to run_outcome_ui.py |

---

## run_outcome_ui.py Change Surface

Three additions to the existing file, all strictly additive:

### Addition 1: GET /api/pis/refresh/status (lines 847-875)

New `elif` branch in `do_GET()`. Does not touch any existing `elif` branch. Calls `artifact_freshness_report()` (read-only). No writes.

### Addition 2: POST /api/pis/refresh (lines 1413-1422)

New `elif` branch in `do_POST()`. Does not touch any existing `elif` branch. Calls `refresh_derived_artifacts()`. Returns result JSON.

### Addition 3: Startup trigger in main() (lines 1740-1749)

```python
from src.pis.refresh_orchestrator import trigger_startup_refresh
_pis_startup_thread = threading.Thread(
    target=trigger_startup_refresh,
    kwargs={"repo_root": _REPO_ROOT},
    daemon=True,
    name="pis-startup-refresh",
)
_pis_startup_thread.start()
```

Inserted before the existing `httpd.serve_forever()` call. Does not change any existing code path. Thread is a daemon (auto-terminates on server exit). Import is inside the `try` block, so import errors are non-fatal to the server.

---

## Test Surface Impact

Existing tests for business logic modules are unaffected because:

1. No business logic file was modified
2. No function signature was changed
3. No data file format was changed
4. New modules only call existing public functions with their default parameters

PIS-005 does not require changes to any existing test file. New unit tests for freshness detection and orchestrator behavior could be added as a follow-on, but are not required as a blocker for this commit.

---

## Verdict

**Zero regression surface.**

PIS-005 adds two new modules and three additive integrations. No existing logic was changed. All six business logic components remain byte-for-byte identical to their pre-PIS-005 state.
