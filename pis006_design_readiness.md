# PIS-006 Design Readiness

**Date:** 2026-06-15  
**Branch:** stream/pis-006-post-ingestion-trigger  
**Scope:** Plan the post-ingestion refresh trigger for PIS-005 orchestration

---

## Q1. Exact ingestion completion point?

**`_register_pis_snapshot_best_effort()` in `src/portfolio/runner.py:668`**

The ingestion chain is:

```
POST /api/portfolio/analyze (run_outcome_ui.py:1445)
    ↓
run_analysis(portfolio_csv, source_filename, snapshot_date, mandate_type) (runner.py)
    ↓
ingest_portfolio(portfolio_csv, source_filename, snapshot_date)
    ↓ (on success)
_register_pis_snapshot_best_effort(snapshot, raw_holdings)  ← PIS registration
    ↓ (returns pis_registration dict)
(continues: enrich, align, recommendations, etc.)
    ↓
returns result dict including pis_registration
```

**PIS registration is the first thing after ingestion succeeds (runner.py line 668).** The `PortfolioSnapshot` is persisted to `pis_snapshot_index.csv` via `append_portfolio_history()` inside `register_portfolio_snapshot_from_sih()`.

After `_register_pis_snapshot_best_effort()` returns, the snapshot is:
- Physically on disk (partition + index)
- Governance-evaluable (governance reads from index)
- Ready for canonical selection

---

## Q2. Safest insertion point for refresh trigger?

**Inside `_register_pis_snapshot_best_effort()`, after successful registration, before return.**

Specifically: after `pis_result = register_portfolio_snapshot_from_sih(...)` and only when `pis_result.registered == True` (not for duplicates or failures).

```python
# Safest insertion in runner.py
pis_result = register_portfolio_snapshot_from_sih(...)
pis_registration = dataclasses.asdict(pis_result)
pis_registration["status"] = ...

if pis_result.registered:
    # NEW: trigger PIS derived artifact refresh
    _trigger_pis_refresh_background(repo_root=_REPO_ROOT)
```

**Why this point:**
- Snapshot is already committed to disk (idempotent trigger)
- Only fires on new registrations (not duplicates → no refresh loop)
- Isolated from SIH analysis path (best-effort design preserved)
- Any exception from refresh doesn't affect the analysis response

Alternative point: in `run_outcome_ui.py` after `run_analysis()` returns. This is less precise because it would trigger on every API call regardless of registration status. The runner point is more targeted.

---

## Q3. Synchronous or background execution?

**Background execution (daemon thread).**

Rationale:
- `refresh_derived_artifacts()` with a full chain can take 1-10 seconds (lineage matching over 18,872 candidates)
- `/api/portfolio/analyze` response time must not be affected
- Failure must not block or corrupt the analysis response
- Same pattern as `trigger_startup_refresh()` already in use

Implementation pattern (same as startup trigger):

```python
def _trigger_pis_refresh_background(*, repo_root: Path) -> None:
    """Fire-and-forget PIS refresh after successful snapshot registration."""
    import threading
    from src.pis.refresh_orchestrator import trigger_startup_refresh
    t = threading.Thread(
        target=trigger_startup_refresh,
        kwargs={"repo_root": repo_root},
        daemon=True,
        name="pis-post-ingestion-refresh",
    )
    t.start()
```

`trigger_startup_refresh()` already swallows exceptions and logs to stderr — exactly the right behavior for a background best-effort operation.

---

## Q4. Idempotency concerns?

**NONE — by design.**

`refresh_derived_artifacts()` checks staleness before each stage. If canonical already includes the new snapshot (e.g., a duplicate submission), all stages skip. If the same snapshot is registered twice (blocked by `append_portfolio_history()` duplicate protection), the second call registers as DUPLICATE and no refresh is triggered.

**No recomputation loops are possible:**
- Duplicate registrations are blocked at the storage level
- Each refresh call evaluates freshness from artifacts, not from a counter
- `_ORCHESTRATION_LOCK` prevents concurrent overlapping refreshes

---

## Q5. Locking concerns?

**Addressed by existing lock infrastructure.**

`_ORCHESTRATION_LOCK` in `refresh_orchestrator.py` is a `threading.Lock()`. If a background refresh is already running (e.g., from startup) when a new registration triggers another, the second call queues behind the lock and runs when the first completes.

**No deadlock risk:** The background thread runs `refresh_derived_artifacts()` which acquires `_ORCHESTRATION_LOCK`. The main analysis thread doesn't hold this lock. No circular dependency exists.

**No starvation risk:** Each refresh completes in bounded time (sequential 5-stage chain). The next queued call will run once the lock releases.

---

## Q6. Expected runtime impact?

**Zero impact on `/api/portfolio/analyze` response time.**

The refresh runs in a background daemon thread. The analysis response returns immediately after `_trigger_pis_refresh_background()` starts the thread.

**Estimated refresh latency (background):**
- Canonical already CURRENT → skip (0ms)
- Change detection already CURRENT → skip (0ms)
- Lineage recomputation (18,872 candidates × matching) → ~2-5 seconds
- Attribution scoring → ~500ms
- Benchmark computation → ~200ms

**Typical refresh after new snapshot:** 3-6 seconds in background, transparent to user.

**If all stages CURRENT (e.g., duplicate upload):** < 10ms (freshness checks only).

---

## Q7. Required tests?

**Two new test scenarios:**

### Test 1: Post-ingestion trigger fires on new registration

```python
def test_pis_refresh_triggered_on_new_registration(tmp_path, monkeypatch):
    # Setup: mock register_portfolio_snapshot_from_sih to return registered=True
    # Assert: _trigger_pis_refresh_background called once
    # Assert: not called if duplicate=True
```

### Test 2: Post-ingestion trigger does NOT fire on duplicate

```python
def test_pis_refresh_not_triggered_on_duplicate(tmp_path, monkeypatch):
    # Setup: mock returns duplicate=True
    # Assert: refresh NOT triggered
```

### Test 3: Post-ingestion trigger does NOT fire on registration failure

```python
def test_pis_refresh_not_triggered_on_failure(tmp_path, monkeypatch):
    # Setup: register_portfolio_snapshot_from_sih raises exception
    # Assert: refresh NOT triggered (exception handled in best-effort wrapper)
```

### Test file: `tests/test_pis_006_post_ingestion_trigger.py`

---

## Q8. API changes required?

**None required. Optional enhancement:**

Current: `POST /api/portfolio/analyze` returns `pis_registration` dict with `status: REGISTERED | DUPLICATE | SKIPPED | FAILED`.

Optional addition to response: include a `pis_refresh_triggered: true/false` flag to indicate whether a background refresh was started. This is informational and non-blocking.

No new endpoints are needed for PIS-006.

---

## Q9. UI changes required?

**None required. Optional enhancement:**

The PIS dashboard already shows the refresh health via `GET /api/pis/refresh/status`. After upload, the dashboard can poll this endpoint to show when artifacts catch up to the new snapshot.

Optional: add a toast notification on the upload success page showing "PIS analysis updating..." that resolves when `/api/pis/refresh/status` returns `overall_refresh_status: CURRENT` at the new date.

No UI changes are required for the trigger itself.

---

## Q10. Recommended implementation sequence?

### Step 1: Add `_trigger_pis_refresh_background()` helper to `runner.py`

A standalone helper function (4-8 lines) that imports and calls `trigger_startup_refresh()` in a daemon thread. The import is inside the function to keep the dependency lazy.

### Step 2: Add trigger call to `_register_pis_snapshot_best_effort()`

Insert after `pis_result = register_portfolio_snapshot_from_sih(...)`, guarded by `if pis_result.registered:`.

### Step 3: Write 3 tests

`tests/test_pis_006_post_ingestion_trigger.py` covering the 3 scenarios above.

### Step 4: Manual validation

1. Start server
2. Upload a new portfolio CSV
3. Observe console output: `[PIS] Startup refresh completed. Refreshed: [...]`
4. Verify `GET /api/pis/refresh/status` shows `overall_refresh_status: CURRENT` and latest dates match new upload

### Step 5: Commit

```
PIS-006: add post-ingestion refresh trigger
```

---

## Files to Modify

| File | Change | Risk |
|------|--------|------|
| `src/portfolio/runner.py` | Add `_trigger_pis_refresh_background()` + one call site | LOW |
| `tests/test_pis_006_post_ingestion_trigger.py` | New test file | ZERO |

## Files NOT Changed

| File | Reason |
|------|--------|
| `src/pis/refresh_orchestrator.py` | No changes needed — `trigger_startup_refresh()` already does exactly what's needed |
| `src/pis/artifact_freshness.py` | No changes needed |
| `scripts/run_outcome_ui.py` | No changes needed — trigger is in runner, not server |
| All business logic files | Constraint: no modification to PIS orchestration logic |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Refresh blocking API response | NONE | Background thread pattern |
| Refresh loop (repeated recomputation) | NONE | Only fires on `registered=True`; freshness gates prevent re-run |
| Concurrent refresh conflict | LOW | `_ORCHESTRATION_LOCK` queues concurrent calls |
| Exception crashing analysis | NONE | Best-effort wrapper + exception handling in `trigger_startup_refresh()` |
| Breaking existing behavior | NONE | Additive change; no existing code removed or modified |

---

## Implementation Complexity

**LOW** — estimated 8-12 lines of new code:
- 6-8 lines: `_trigger_pis_refresh_background()` function
- 2-3 lines: conditional call in `_register_pis_snapshot_best_effort()`
- 3 test functions (~30 lines each)

PIS-006 is the smallest possible closure of the refresh orchestration gap.
