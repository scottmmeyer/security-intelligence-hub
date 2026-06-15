# PIS-007 Refresh Failure Analysis

**Date:** 2026-06-15

---

## Chain Architecture

```
refresh_derived_artifacts()  [_ORCHESTRATION_LOCK acquired]
  │
  ├── Step 1: canonical_is_stale()? → refresh_canonical_daily()
  ├── Step 2: change_is_stale()?    → compute_all_snapshot_changes()
  ├── Step 3: lineage_is_stale()?   → compute_recommendation_lineage()
  ├── Step 4: attribution_is_stale()? → compute_performance_attribution()
  └── Step 5: benchmark_is_stale()? → compute_benchmark_return_series()
                                       + compute_benchmark_recommendation_attribution()
```

**No per-stage try/except.** Any stage failure propagates up and aborts the chain.

---

## Failure Scenarios

### Scenario A: Governance / Snapshot Index Corruption

`canonical_is_stale()` calls `latest_pass_snapshot_date()`, which reads `pis_snapshot_index.csv` and evaluates governance inline. If the index is malformed:

- `_read_csv_rows()` returns `[]` (safe: returns empty list on missing/empty file)
- `latest_pass_snapshot_date()` returns `""` → `canonical_is_stale()` returns `False`
- **System silently freezes**: canonical will not advance

**Detection:** `GET /api/pis/refresh/status` returns `canonical_status: CURRENT` even when it should be STALE because governance returns empty. No alert fired.

### Scenario B: Canonical Refresh Fails (disk write error)

`refresh_canonical_daily()` writes `canonical_daily_snapshots.csv`. If the write fails (disk full, permissions):

- Exception propagates from Step 1 up through `refresh_derived_artifacts()`
- Caught by `trigger_startup_refresh()` → stderr: `[PIS] Startup refresh failed (non-fatal): ...`
- Caught silently by `_trigger_pis_refresh_background()` → no log
- `canonical_daily_snapshots.csv` may be left in partially-written state or unchanged
- **Recovery:** Next refresh re-evaluates `canonical_is_stale()` and retries

### Scenario C: Change Detection Fails (position data missing)

`compute_all_snapshot_changes()` reads position files from snapshot partitions. If a partition directory is missing:

- `_read_csv_rows()` returns `[]` for the missing positions file
- Change is computed with 0 positions for that snapshot
- **Silent data corruption**: change records contain incorrect data
- No error is raised; the chain continues with wrong data

**This is the most critical failure scenario.** A missing partition file silently produces incorrect change detection, which then produces incorrect lineage, attribution, and benchmark.

### Scenario D: Lineage Fails (PAR files missing)

`compute_recommendation_lineage()` reads from `data/portfolio_ingestion/analysis_runs/`. If PAR directories are missing:

- `build_recommendation_candidates()` returns empty list
- All changes are matched with `confidence=NONE`
- No error; empty lineage produced
- Attribution scores zero matches

**Silent degradation**: Attribution will show no matched recommendations.

### Scenario E: Attribution Fails (schema mismatch)

`compute_performance_attribution()` reads from `change_records.csv` and `lineage_records.csv`. Schema changes would cause KeyError on row access.

- Exception propagates up
- Chain aborts at Step 4
- Benchmark not computed

### Scenario F: Benchmark Fails (SPY data stale)

`compute_benchmark_return_series()` uses `NEAREST_PRIOR_TRADING_DAY` policy. If `benchmark_returns.csv` has no data for the required date range:

- `_nearest_prior_date()` returns `(None, None)`
- Row gets `data_quality_status = "MISSING_BENCHMARK_ENTRY"` or `"MISSING_BENCHMARK_EXIT"`
- **Graceful degradation**: Row is included with quality status; `ok_interval_count` decremented
- No exception; chain completes with degraded quality

**Benchmark failure is the most graceful** — it degrades quality scores rather than aborting.

---

## Recovery Behavior Summary

| Stage Fails | Chain Aborts? | Next Refresh Retries? | Data Corruption Risk |
|------------|:---:|:---:|----|
| Canonical write error | YES | YES (stage 1 re-evaluates) | LOW (file unchanged) |
| Change detection (missing position) | NO | NO (data silently wrong) | **HIGH** |
| Lineage (missing PARs) | NO | NO (empty candidates) | MEDIUM (zero matches) |
| Attribution (schema error) | YES | YES | LOW |
| Benchmark (stale SPY data) | NO | NO (quality flag) | LOW (graceful degradation) |

---

## Critical Finding: Silent Corruption in Change Detection

If a snapshot partition directory is deleted or its `position_snapshots.csv` is empty after registration, the change detection will compute changes against 0 positions for that date. This produces:

- Incorrect `EXITED_POSITION` records for all symbols (all appear to exit)
- Cascading incorrect lineage and attribution
- No error, no warning, no alert

**This is an UNDETECTED silent corruption scenario.** Mitigation requires either:
1. Partition integrity checks in `_aggregate_positions()` before computing changes
2. A post-computation validation step comparing expected vs actual position counts

---

## Post-Ingestion Refresh Silent Failure

The `_trigger_pis_refresh_background()` function in `runner.py` swallows ALL exceptions with `pass`. When it fails:

- No log line produced
- No way to determine from any artifact or API whether the refresh attempted/succeeded
- The next upload will retry (if registered=True)
- The startup refresh will retry (if server restarts)

**Gap:** No persistent "last_refresh_attempted_at" or "last_refresh_result" metadata exists. Operators cannot tell from `GET /api/pis/refresh/status` whether an attempted refresh failed — the status just shows whatever the current artifact state is.
