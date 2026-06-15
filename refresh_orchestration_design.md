# Refresh Orchestration Design — PIS-005

**Created:** 2026-06-14  
**Scope:** Architecture design for PIS derived artifact refresh orchestration

---

## Problem Statement

The PIS pipeline has five derived artifact layers (canonical, change, lineage, attribution, benchmark). Each layer depends on the previous. Individual compute functions work correctly, but no mechanism existed to:

1. Detect when an artifact layer is behind its upstream source
2. Trigger recomputation in the correct order
3. Prevent duplicate/concurrent computation
4. Expose freshness state to operators

**Root cause confirmed by forensic investigation (PIS-LINEAGE-ATTR-REFRESH-07):**

> "The PIS refresh architecture lacks an orchestration trigger connecting governance approval of new canonical snapshots to automatic recomputation of downstream artifacts."

---

## Design Principles

1. **No business logic changes** — governance, selection policy, matching algorithms, scoring, and benchmark math are untouched.
2. **Deterministic order** — stages execute in exactly the dependency order every time.
3. **Minimal recomputation** — each stage skips itself if already current.
4. **Lock-protected** — single threading lock prevents concurrent refresh races.
5. **Idempotent** — calling refresh on a fully-current system produces zero writes.
6. **Observable** — freshness state exposed via API and dashboard.

---

## Architecture

### New Modules

#### `src/pis/artifact_freshness.py`

Provides freshness detection without side effects.

**Key functions:**

```python
latest_pass_snapshot_date(index_path)    # inline governance eval from index
latest_canonical_date(canonical_path)
latest_change_date(change_summary_path)
latest_lineage_date(lineage_summary_path)
latest_attribution_date(attribution_summary_path)
latest_benchmark_date(benchmark_series_path)

canonical_is_stale(...)   # gov_latest > canonical_latest
change_is_stale(...)      # canonical_latest > change_latest
lineage_is_stale(...)     # change_latest > lineage_latest
attribution_is_stale(...) # lineage_latest > attribution_latest
benchmark_is_stale(...)   # attribution_latest > benchmark_latest

artifact_freshness_report(...) -> dict  # all layers, for dashboard
```

**Returns `Freshness = Literal["CURRENT", "STALE", "MISSING"]` per layer.**

No heuristics. Only date comparisons against persisted CSV files.

#### `src/pis/refresh_orchestrator.py`

Executes the ordered, lock-protected refresh chain.

**Key function:**

```python
refresh_derived_artifacts(
    *,
    repo_root=".",
    index_path=...,
    canonical_path=...,
    changes_root=...,
    lineage_root=...,
    attribution_root=...,
    benchmark_root=...,
    governance_config=DEFAULT_GOVERNANCE_CONFIG,
    benchmark_config=DEFAULT_BENCHMARK_ATTRIBUTION_CONFIG,
    price_provider=None,
    allow_online_fallback=False,
    dry_run=False,
) -> dict
```

Returns `{refreshed, skipped, dry_run, started_at, completed_at, freshness}`.

Also exports `trigger_startup_refresh()` for background thread use.

---

## Refresh Chain Execution

```
LOCK(_ORCHESTRATION_LOCK)
│
├─ Step 1: canonical_is_stale()?
│     YES → refresh_canonical_daily() → writes canonical_daily_snapshots.csv
│     NO  → skip
│
├─ Step 2: change_is_stale()?
│     YES → compute_all_snapshot_changes() → writes change_records.csv, change_summary.csv
│     NO  → skip
│
├─ Step 3: lineage_is_stale()?
│     YES → compute_recommendation_lineage() → writes lineage_records.csv, lineage_summary.csv
│     NO  → skip
│
├─ Step 4: attribution_is_stale()?
│     YES → compute_performance_attribution() → writes attribution_records.csv, attribution_summary.csv
│     NO  → skip
│
└─ Step 5: benchmark_is_stale()?
      YES → compute_benchmark_return_series() → writes benchmark_return_series.csv
            compute_benchmark_recommendation_attribution() → writes recommendation_benchmark_records.csv, source_benchmark_summary.csv
      NO  → skip

RELEASE(_ORCHESTRATION_LOCK)
```

---

## Trigger Points

### Trigger 1: Server Startup (Recommended — Implemented)

```python
# In main() of scripts/run_outcome_ui.py
_pis_startup_thread = threading.Thread(
    target=trigger_startup_refresh,
    kwargs={"repo_root": _REPO_ROOT},
    daemon=True,
    name="pis-startup-refresh",
)
_pis_startup_thread.start()
```

**Properties:**
- Runs once at startup in a daemon thread
- Does not block the HTTP listener
- Idempotent (no-op if all current)
- Thread safety: protected by `_ORCHESTRATION_LOCK`

**Why chosen:**
- Least invasive integration point
- Covers the most common scenario (server restarted after new ingestion)
- No risk of refresh loops (fires once, then never again until restart)
- Existing lock patterns in `performance_attribution.py` honored at the calling layer

### Trigger 2: On-Demand API (Implemented)

```
POST /api/pis/refresh
```

Allows operators to manually trigger refresh without restarting the server.

Returns full orchestration result including per-stage status and final freshness report.

### Trigger 3: Freshness Status API (Implemented)

```
GET /api/pis/refresh/status
```

Returns `artifact_freshness_report()` without triggering any recomputation.

Operators can check staleness state without side effects.

---

## Dashboard Integration (Phase D)

### New Endpoint

`GET /api/pis/refresh/status` returns:

```json
{
  "latest_pass_snapshot_date": "2026-06-14",
  "latest_canonical_date": "2026-06-14",
  "latest_change_date": "2026-06-14",
  "latest_lineage_date": "2026-06-14",
  "latest_attribution_date": "2026-06-14",
  "latest_benchmark_date": "2026-06-14",
  "canonical_status": "CURRENT",
  "change_status": "CURRENT",
  "lineage_status": "CURRENT",
  "attribution_status": "CURRENT",
  "benchmark_status": "CURRENT",
  "overall_refresh_status": "CURRENT"
}
```

When stale, `overall_refresh_status` will be `"STALE"` and the individual layer showing `"STALE"` pinpoints the bottleneck.

### Refresh Health Section

The dashboard can now show a "Refresh Health" table with:
- Latest governance PASS date (the watermark)
- Per-layer status (CURRENT / STALE / MISSING)
- Overall health indicator
- Trigger button → POST `/api/pis/refresh`

---

## Concurrency Safety

Single `threading.Lock` (`_ORCHESTRATION_LOCK`) in `refresh_orchestrator.py`.

- Concurrent API calls or background threads queue rather than race
- Uses standard `threading.Lock` (not `RLock`) — reentrancy raises rather than silently double-writes
- Existing `_ATTRIBUTION_REFRESH_LOCK` in `performance_attribution.py` is not needed for the orchestrated path since the orchestrator owns the entire chain; individual component locks remain intact for direct callers

---

## What Is NOT Changed

| Component | Status |
|-----------|--------|
| Governance evaluation logic | Unchanged |
| Canonical selection policy | Unchanged |
| Change detection algorithms | Unchanged |
| Lineage matching logic | Unchanged |
| Attribution scoring formulas | Unchanged |
| Benchmark math | Unchanged |
| Existing API endpoints | Unchanged (additive only) |
| Data file formats | Unchanged |
| Existing tests | Unchanged |

---

## Files Created

| File | Purpose |
|------|---------|
| `src/pis/artifact_freshness.py` | Freshness detection module |
| `src/pis/refresh_orchestrator.py` | Refresh chain execution |

## Files Modified

| File | Change |
|------|--------|
| `scripts/run_outcome_ui.py` | Added GET `/api/pis/refresh/status`, POST `/api/pis/refresh`, startup trigger in `main()` |
