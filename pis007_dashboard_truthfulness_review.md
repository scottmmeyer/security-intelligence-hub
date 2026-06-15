# PIS-007 Dashboard Truthfulness Review

**Date:** 2026-06-15

---

## KPI Inventory

### `/api/pis/summary` (Dashboard Header)

Source: `pis_dashboard_summary()` in `storage.py`

| KPI | Source | Truth | Issue |
|----|--------|-------|-------|
| `health.latest_snapshot_date` | `pis_snapshot_index.csv` | **2026-06-14** ✓ | None — correct |
| `health.snapshot_count` | `pis_snapshot_index.csv` | **68** ✓ | None — correct |
| `health.missing_days` | Computed from snapshot dates | Potentially misleading | Counts calendar days without snapshots, not trading days |
| `health.duplicate_uploads_prevented` | Hardcoded `0` | **WRONG** ✗ | Always shows 0 regardless of actual duplicates detected |
| `lineage.total_sih_analyses_captured` | `manifest.json` portfolio count | **242** | Includes `CONCENTRATED_ALPHA` entries (non-dated PARs); inflates count slightly |
| `lineage.latest_par` | `max(manifest.portfolios, key=created_at+snapshot_date)` | **PAR-20260529-311C47DA** | **MISLEADING** — shows a May 29 PAR as "latest" even though the system has June 14 data |
| `lineage.latest_upload_date` | Same max PAR's `snapshot_date` | **2026-05-29** | **MISLEADING** — dashboard shows May 29 as latest upload while portfolio snapshots go to June 14 |

### The `latest_par` Misleading Date Issue

The manifest's `max()` sorting uses `(created_at_utc, snapshot_date)`. The PAR `PAR-20260529-311C47DA` has `created_at_utc = 2026-06-15T11:00:43` (created today), while June 14 PARs were created earlier. Because `created_at_utc` is the primary sort key, this May 29 PAR sorts as "latest" even though its portfolio data is from May 29.

**The dashboard shows "Latest Upload: 2026-05-29" when the system actually has June 14 data.**

This is a pre-existing issue unrelated to the PIS-005/006 refresh work. The forensic investigation noted it earlier. It should be addressed by sorting on `snapshot_date` as the primary key (most recent portfolio data), not `created_at_utc` (analysis run creation time).

---

## Attribution and Benchmark KPIs

### `/api/pis/attribution/latest`

Source: `attribution_records.csv`, `attribution_summary.csv`

| KPI | Source | Current Truth |
|----|--------|--------------|
| Latest attribution date | `attribution_summary.csv` | **2026-06-14** ✓ |
| Winner/Loser/Neutral counts | `attribution_records.csv` | Current ✓ |
| `directional_return_pct` | Computed from change data | Correct formula ✓ |

### `/api/pis/benchmark-attribution/returns`

Source: `benchmark_return_series.csv`

| KPI | Source | Current Truth |
|----|--------|--------------|
| Latest benchmark interval | `benchmark_return_series.csv` | `2026-06-14 <- 2026-06-11` ✓ |
| `data_quality_status` | Per-row quality flag | All `OK` ✓ |
| `benchmark_exit_date` | NEAREST_PRIOR_TRADING_DAY | `2026-06-11` (correct: Jun 14 = Sunday) ✓ |
| `benchmark_exit_price` | `data/current/benchmark_returns.csv` | Last available: 2026-06-11 ✓ |

**Benchmark exit date is 2026-06-11 for the June 14 interval.** This is correct behavior (NEAREST_PRIOR_TRADING_DAY policy; June 14 is a Sunday). Not a truthfulness issue.

---

## Freshness Status Dashboard (`/api/pis/refresh/status`)

Source: `artifact_freshness_report()`

| Field | Value | Truthful? |
|-------|-------|----------|
| `latest_pass_snapshot_date` | 2026-06-14 | ✓ |
| `latest_canonical_date` | 2026-06-14 | ✓ |
| `latest_change_date` | 2026-06-14 | ✓ |
| `latest_lineage_date` | 2026-06-14 | ✓ |
| `latest_attribution_date` | 2026-06-14 | ✓ |
| `latest_benchmark_date` | 2026-06-14 | ✓ |
| `overall_refresh_status` | CURRENT | ✓ |

The freshness endpoint is fully truthful and aligned.

---

## Stale Visualization Risk

### Missing Refresh History Visualization

The dashboard has no panel showing "Last refreshed at: [timestamp]" or "Last refresh triggered by: [upload/startup/manual]". Operators cannot see when the last refresh ran.

### ESS Coverage Gap Not Visible

`data/current/ess_coverage_warning.json` contains an ESS coverage gap warning (55 holdings without ESS scores). This warning:
- Is accessible via `/api/signal-status`
- Is NOT surfaced in the PIS dashboard
- Holdings without ESS scores receive lower recommendation scores

An operator looking at the PIS dashboard cannot tell that 55 portfolio holdings lack ESS data.

---

## Summary

| KPI | Truthful | Severity |
|----|---------|---------|
| `health.latest_snapshot_date` | ✓ | — |
| `health.snapshot_count` | ✓ | — |
| `health.duplicate_uploads_prevented` | ✗ (always 0) | LOW |
| `lineage.latest_par` | ✗ (shows PAR by creation date, not portfolio date) | **MEDIUM** |
| `lineage.latest_upload_date` | ✗ (shows 2026-05-29, not 2026-06-14) | **MEDIUM** |
| `lineage.total_sih_analyses_captured` | Slightly inflated (CONCENTRATED_ALPHA entries) | LOW |
| Attribution latest date | ✓ | — |
| Benchmark return quality | ✓ | — |
| Freshness status endpoint | ✓ | — |
