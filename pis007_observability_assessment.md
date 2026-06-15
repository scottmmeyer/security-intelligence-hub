# PIS-007 Observability Assessment

**Date:** 2026-06-15

---

## Logging Inventory

### What Gets Logged

| Location | Event | Output | Level |
|---------|-------|--------|-------|
| `refresh_orchestrator.py:337` | Startup refresh completed with refreshed stages | `[PIS] Startup refresh completed. Refreshed: [...]. Status: CURRENT` | stdout |
| `refresh_orchestrator.py:339` | Startup refresh — all stages current | `[PIS] Startup refresh: all artifacts current ([...]). Status: CURRENT` | stdout |
| `refresh_orchestrator.py:341` | Startup refresh exception | `[PIS] Startup refresh failed (non-fatal): {exc}` | stderr |

### What Does NOT Get Logged

| Event | Gap |
|-------|-----|
| Post-ingestion refresh triggered | No log |
| Post-ingestion refresh succeeded | No log |
| Post-ingestion refresh failed | No log (silent pass) |
| Manual `POST /api/pis/refresh` triggered | No log |
| Individual stage start/complete | No log |
| Individual stage skip (already current) | No log |
| Change detection found N position changes | No log |
| Lineage found N matches | No log |

**The post-ingestion refresh path (PIS-006) is completely invisible to operators via logs.**

---

## Refresh Status APIs

### Available

| Endpoint | Function | Returns |
|---------|---------|---------|
| `GET /api/pis/refresh/status` | `artifact_freshness_report()` | 6 latest dates + 5 layer statuses + overall |
| `POST /api/pis/refresh` | `refresh_derived_artifacts()` | refreshed/skipped lists + freshness + timestamps |

### Not Available

| Missing Endpoint | Purpose | Risk |
|----------------|---------|------|
| `GET /api/pis/refresh/history` | Last N refresh events | Cannot audit when refresh last ran |
| `GET /api/pis/refresh/last-result` | Most recent refresh outcome | Cannot tell if last refresh succeeded |
| Webhook/callback on refresh complete | Notify external systems | Manual polling required |

---

## Diagnostic Endpoints

### Available

| Endpoint | Source | Freshness |
|---------|--------|---------|
| `GET /api/pis/summary` | `pis_dashboard_summary()` | manifest.json (live) |
| `GET /api/pis/governance/latest` | `pis_governance_latest()` | snapshot index (live) |
| `GET /api/pis/canonical/latest` | `pis_canonical_latest()` | canonical CSV |
| `GET /api/pis/canonical/history` | `pis_canonical_history()` | canonical CSV |
| `GET /api/pis/changes/latest` | `pis_changes_latest()` | change CSVs |
| `GET /api/pis/lineage/latest` | `pis_lineage_latest()` | lineage CSVs |
| `GET /api/pis/attribution/latest` | `pis_attribution_latest()` | attribution CSVs |
| `GET /api/pis/benchmark-attribution/returns` | `pis_benchmark_returns()` | benchmark CSVs |
| `GET /api/pis/refresh/status` | `artifact_freshness_report()` | all artifact CSVs |

### Missing Diagnostics

| Diagnostic | Purpose |
|-----------|---------|
| `GET /api/pis/integrity/snapshot-count` | Verify snapshot partition dirs match index count |
| `GET /api/pis/integrity/position-coverage` | Verify position files exist for all indexed snapshots |
| `GET /api/pis/refresh/log` | Last N refresh events with timestamps |
| `GET /api/pis/benchmarks/data-coverage` | SPY price data latest date vs portfolio snapshot latest date |

---

## Missing Operator Visibility

### Critical Gaps

1. **No refresh history**: No persistent record of when refresh was last triggered or completed. `GET /api/pis/refresh/status` shows artifact state, not refresh history.

2. **No failure notifications**: When `_trigger_pis_refresh_background()` fails silently, there is no way for an operator to know. The freshness report will still show the pre-refresh state (possibly STALE), but there's no indication that a refresh was attempted and failed vs. simply never triggered.

3. **`duplicate_uploads_prevented` metric hardcoded to 0**: `pis_snapshot_history_health()` always returns `"duplicate_uploads_prevented": 0`. Duplicate suppression does happen (in `append_portfolio_history()` and `register_portfolio_snapshot_from_sih()`), but the metric is never populated. Operators cannot see how many duplicate uploads occurred.

4. **ESS coverage gap not surfaced in dashboard**: The ESS coverage gap warning (`data/current/ess_coverage_warning.json`) is written by the intake stage but is only surfaced via the `/api/signal-status` endpoint, not the PIS dashboard. Holdings with missing ESS scores affect recommendation quality invisibly.

5. **No benchmark data freshness indicator**: `GET /api/pis/refresh/status` does not indicate when `benchmark_returns.csv` was last updated or whether SPY data is current. The benchmark can show `benchmark_status: CURRENT` while the underlying SPY price data is weeks old (because the benchmark was computed correctly from stale data).

---

## Summary

| Observability Area | Status |
|-------------------|--------|
| Startup refresh logging | ADEQUATE (stdout/stderr) |
| Post-ingestion refresh logging | MISSING (silent) |
| Manual refresh API | ADEQUATE (returns result) |
| Freshness status endpoint | ADEQUATE |
| Refresh history | MISSING |
| Stage-level visibility | MISSING |
| Benchmark data freshness | MISSING |
| Duplicate detection metrics | BROKEN (hardcoded 0) |
