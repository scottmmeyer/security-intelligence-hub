# PIS-007 Risk Register

**Date:** 2026-06-15  
**Risk Rating:** HIGH / MEDIUM / LOW  
**Likelihood:** P1 (Certain) / P2 (Likely) / P3 (Possible) / P4 (Unlikely)

---

## Risk Register

| # | Risk | Likelihood | Severity | Rating | Mitigation Status |
|---|------|-----------|---------|--------|------------------|
| R1 | Change detection silently produces wrong data if position partition is missing or empty | P3 | HIGH | **HIGH** | None implemented |
| R2 | Post-ingestion refresh fails silently with no operator notification | P2 | MEDIUM | **HIGH** | Intentional design (best-effort); no logging |
| R3 | `lineage.latest_upload_date` on dashboard shows May 29 while system has June 14 data | P1 | MEDIUM | **MEDIUM** | Known; `latest_par` sorting by created_at not snapshot_date |
| R4 | Benchmark data (SPY prices) becomes stale without automatic refresh trigger | P2 | MEDIUM | **MEDIUM** | Manual benchmark data refresh required; no automation |
| R5 | Single-stage chain failure blocks all downstream stages | P2 | MEDIUM | **MEDIUM** | No per-stage retry; correct-by-default but disrupts full refresh |
| R6 | `duplicate_uploads_prevented` metric always shows 0 | P1 | LOW | LOW | Hardcoded; metric non-functional; no data impact |
| R7 | Lineage/attribution CSVs not written atomically; truncation risk | P4 | MEDIUM | LOW | Process kill during write leaves corrupt file; next refresh corrects |
| R8 | ESS coverage gap (55 holdings) not visible in PIS dashboard | P1 | LOW | LOW | Gap exists in `/api/signal-status` but not PIS dashboard |
| R9 | `_write_rows()` full-overwrite pattern: read-during-write can return partial data | P3 | LOW | LOW | Race condition in multi-threaded server; short write window |
| R10 | CONCENTRATED_ALPHA entries inflate `total_sih_analyses_captured` count | P1 | LOW | LOW | Cosmetic dashboard inaccuracy |
| R11 | Snapshot partition count not verified vs index | P3 | MEDIUM | LOW | No cross-check; orphaned index entries possible but not confirmed |
| R12 | Benchmark `benchmark_snapshots.csv` is empty | P1 | LOW | LOW | `CsvBenchmarkPriceProvider` falls back to `benchmark_returns.csv`; functional |

---

## R1 Detail: Silent Change Detection Corruption

**Trigger:** A snapshot partition directory is deleted, position file is missing, or position file is empty after registration.

**Effect:** `_aggregate_positions()` returns 0 positions for that snapshot. All symbols from adjacent snapshots are classified as EXITED. All downstream lineage/attribution records are incorrect.

**Detection:** None. The freshness report shows CURRENT. No warning in any artifact.

**Remediation:** Add a position-count validation in `compute_all_snapshot_changes()`:
```python
expected_count = int(index_row.get("position_count", 0))
if actual_position_count == 0 and expected_count > 0:
    warnings.append(f"Position count mismatch for {snapshot_id}: expected {expected_count}, got 0")
```

---

## R2 Detail: Silent Post-Ingestion Refresh Failure

**Trigger:** Any exception in `refresh_derived_artifacts()` called from `_trigger_pis_refresh_background()`.

**Effect:** Pipeline does not advance. `GET /api/pis/refresh/status` shows STALE (if it was stale before) or incorrectly CURRENT (if it was already current before the upload but the upload was for a new date).

**Detection:** None from logs. Only discoverable by polling `GET /api/pis/refresh/status`.

**Remediation:** Add stderr logging to the inner `_run()` function:
```python
def _run() -> None:
    try:
        trigger_startup_refresh(repo_root=repo_root)
    except Exception as exc:
        import sys
        print(f"[PIS] Post-ingestion refresh failed: {exc}", file=sys.stderr)
```

---

## R3 Detail: Dashboard Latest Upload Date Misleading

**Trigger:** A new analysis run for an old portfolio date (e.g., May 29) is created today. Its `created_at_utc` is today, so it sorts as "latest" in the manifest.

**Effect:** `lineage.latest_upload_date` shows 2026-05-29; `lineage.latest_par` shows a May PAR. An operator reviewing the dashboard thinks the most recent portfolio upload was 3+ weeks ago.

**Detection:** Comparing `health.latest_snapshot_date` (June 14) vs `lineage.latest_upload_date` (May 29) reveals the mismatch.

**Remediation:** Change `pis_sih_lineage_summary()` sort key from `created_at_utc` to `snapshot_date` as primary:
```python
latest = max(portfolios, key=lambda r: (str(r.get("snapshot_date", "")), str(r.get("created_at_utc", ""))))
```

---

## R4 Detail: Benchmark Data Staleness

**Trigger:** SPY price data in `data/current/benchmark_returns.csv` is not refreshed when new portfolio snapshots are uploaded. Currently covers through 2026-06-11.

**Effect:** The 2026-06-14 benchmark interval uses `benchmark_exit_date = 2026-06-11` (NEAREST_PRIOR_TRADING_DAY, since Jun 14 is Sunday). This is correct today, but if new snapshots for 2026-06-16+ are ingested, the benchmark will be missing exit prices for June 12, 13, 15+ (trading days).

**Detection:** `benchmark_returns.csv` has no data for those dates → `data_quality_status = "MISSING_BENCHMARK_EXIT"` in `benchmark_return_series.csv`.

**Remediation:** Run `scripts/refresh_signals.py` or the SPY data fetch workflow before (or after) portfolio upload for new dates.

---

## Priority-Ordered Remediation

| Priority | Risk | Recommended Action | Effort |
|---------|------|-------------------|--------|
| P1 | R1 (silent corruption) | Add position-count validation before change detection | LOW |
| P2 | R2 (silent failure logging) | Add stderr logging to `_trigger_pis_refresh_background._run()` | LOW |
| P3 | R3 (dashboard date misleading) | Fix `pis_sih_lineage_summary()` sort key to `snapshot_date` | LOW |
| P4 | R4 (benchmark staleness) | Document SPY refresh requirement; add benchmark data age to `/api/pis/refresh/status` | LOW |
| P5 | R6 (broken metric) | Implement `duplicate_uploads_prevented` counter in `pis_snapshot_history_health()` | MEDIUM |
