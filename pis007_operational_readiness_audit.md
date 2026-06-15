# PIS-007 Operational Readiness Audit

**Date:** 2026-06-15  
**Scope:** Full production-readiness review of PIS pipeline  
**Method:** Read-only code, artifact, and API inspection

---

## 1. Refresh Reliability

### Entry Points

Three distinct entry points call the refresh chain:

| Entry Point | File | Trigger | Error Handling |
|------------|------|---------|----------------|
| Server startup | `scripts/run_outcome_ui.py:1743` | Daemon thread on `main()` | Exception swallowed by `trigger_startup_refresh()` → stderr print |
| Post-ingestion | `src/portfolio/runner.py:151` | After `pis_result.registered == True` | Exception swallowed by `_trigger_pis_refresh_background()` → silent |
| Manual API | `scripts/run_outcome_ui.py:1418` | `POST /api/pis/refresh` | Exception returned as JSON `{"error": ...}` |

### Key Finding: Silent Failure in Post-Ingestion Trigger

The `_trigger_pis_refresh_background()` helper (PIS-006) uses:

```python
except Exception:
    pass  # best-effort; never raise into caller
```

This is intentional for SIH path protection, but **no logging occurs when the background refresh fails silently**. An operator cannot determine from logs whether a post-ingestion refresh succeeded or failed.

**Startup trigger logs to stderr** (`trigger_startup_refresh` prints `[PIS] Startup refresh failed (non-fatal): {exc}`), which at least produces observable stderr output.

**Post-ingestion trigger logs nothing** on failure.

### Concurrency Controls

Three locks in the PIS pipeline:

| Lock | File | Scope | Type |
|------|------|-------|------|
| `_ORCHESTRATION_LOCK` | refresh_orchestrator.py:61 | Entire 5-stage refresh chain | `threading.Lock()` |
| `_ATTRIBUTION_REFRESH_LOCK` | performance_attribution.py:59 | Attribution load path only | `threading.Lock()` |
| `_BENCHMARK_REFRESH_LOCK` | benchmark_attribution.py:70 | Benchmark series load path only | `threading.Lock()` |

**No deadlock risk:** The orchestrator calls `compute_performance_attribution()` and `compute_benchmark_return_series()` directly (not the `_load_*` wrappers that hold the inner locks). `_ORCHESTRATION_LOCK` and the inner locks are never nested in the same call path.

**Concurrent upload behavior:** Two simultaneous uploads both trigger `_trigger_pis_refresh_background()`. Both acquire `_ORCHESTRATION_LOCK` sequentially — no race. The second refresh is idempotent (all stages already current after the first).

### Rapid Burst Behavior

Daemon threads from rapid uploads accumulate, but:
- Each thread acquires `_ORCHESTRATION_LOCK` before doing any work
- The first thread to acquire runs the refresh; all subsequent threads find everything current and skip immediately
- Threads are daemon threads — no accumulation persists after server exit

**Risk:** Under extreme burst (100+ uploads/second), thread accumulation is possible. Each thread holds minimal memory (import + lock acquire + freshness check). Practical risk is low for single-user daily operation.

---

## 2. Failure Recovery

### Per-Stage Failure Behavior

`_execute_refresh_chain()` in `refresh_orchestrator.py` calls each stage unconditionally in sequence. There is no try/except around individual stage calls within the chain.

| Stage | If it raises | Recovery |
|-------|-------------|---------|
| `refresh_canonical_daily()` | Propagates to `refresh_derived_artifacts()` → caught by `trigger_startup_refresh()` | Entire chain aborted; all downstream stages skipped; stderr logged on startup |
| `compute_all_snapshot_changes()` | Same — entire chain aborted | Downstream stages skipped |
| `compute_recommendation_lineage()` | Same | Downstream skipped |
| `compute_performance_attribution()` | Same | Downstream skipped |
| `compute_benchmark_return_series()` | Same | `compute_benchmark_recommendation_attribution()` skipped |

**Critical finding:** A single-stage failure aborts the entire chain with no partial persistence. This is fail-safe but means **a transient error in change detection (stage 2) prevents lineage, attribution, and benchmark from running**, even if they would succeed independently.

### Partial Refresh Recovery

If canonical is stale and change detection fails:
- `canonical_daily_snapshots.csv` is written (stage 1 succeeded)
- `change_records.csv` and `change_summary.csv` are NOT updated (stage 2 failed)
- Next refresh run will: skip canonical (now current), retry change detection

This is correct behavior — stages are idempotent and the next refresh will resume from the correct point.

---

## 3. Current System State

```
latest_pass_snapshot_date: 2026-06-14
latest_canonical_date:     2026-06-14   CURRENT
latest_change_date:        2026-06-14   CURRENT
latest_lineage_date:       2026-06-14   CURRENT
latest_attribution_date:   2026-06-14   CURRENT
latest_benchmark_date:     2026-06-14   CURRENT
overall_refresh_status:    CURRENT
```

All pipeline layers aligned at 2026-06-14.

---

## Summary

| Area | Assessment |
|------|-----------|
| Refresh entry points | 3 distinct, all functional |
| Lock safety | No deadlock risk; correct non-nested design |
| Concurrent uploads | Handled by lock queuing; idempotent |
| Stage failure isolation | Fail-safe but chain-aborting; no per-stage retry |
| Exception observability | Startup: stderr logging. Post-ingestion: silent. API: JSON error |
| Current state | All layers CURRENT at 2026-06-14 |
