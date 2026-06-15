# Artifact Dependency Graph — PIS-005

**Created:** 2026-06-14  
**Scope:** Complete producer/consumer/freshness mapping for all PIS derived artifacts

---

## Dependency Hierarchy

```
pis_snapshot_index.csv  ← Input (immutable, written by ingestion only)
        │
        ▼  evaluate_snapshot_governance() — read-only, no persist
Governance (virtual: no separate CSV required)
        │
        ▼  refresh_canonical_daily()
canonical_daily_snapshots.csv
        │
        ▼  compute_all_snapshot_changes()
change_records.csv
change_summary.csv
        │
        ▼  compute_recommendation_lineage()
lineage_records.csv
lineage_summary.csv
        │
        ▼  compute_performance_attribution()
attribution_records.csv
attribution_summary.csv
        │
        ▼  compute_benchmark_return_series()
benchmark_return_series.csv
        │
        ▼  compute_benchmark_recommendation_attribution()
recommendation_benchmark_records.csv
source_benchmark_summary.csv
```

---

## Artifact Inventory

### Tier 0 — Source of Truth (Immutable)

| Artifact | Path | Producer | Consumer |
|----------|------|----------|----------|
| Snapshot Index | `data/history/pis/pis_snapshot_index.csv` | `storage.append_portfolio_history()` via ingestion | All downstream tiers |

### Tier 1 — Canonical Selection

| Artifact | Path | Producer | Consumer |
|----------|------|----------|----------|
| Canonical Daily Snapshots | `data/history/pis/canonical/canonical_daily_snapshots.csv` | `canonical_daily.refresh_canonical_daily()` | `change_detection._snapshot_groups()`, `benchmark_attribution._canonical_selected_rows()` |

**Producer function:** `src/pis/canonical_daily.py:refresh_canonical_daily()`  
**Selection policy:** PASS_THEN_LATEST_INGESTION (most recent PASS snapshot per date)  
**Governance source:** inline via `evaluate_snapshot_governance()` from index  
**Freshness trigger:** governance_latest_PASS_date > canonical_latest_date

### Tier 2 — Change Detection

| Artifact | Path | Producer | Consumer |
|----------|------|----------|----------|
| Change Records | `data/history/pis/changes/change_records.csv` | `change_detection.compute_all_snapshot_changes()` | `recommendation_lineage.compute_recommendation_lineage()`, `performance_attribution.compute_performance_attribution()` |
| Change Summary | `data/history/pis/changes/change_summary.csv` | `change_detection.compute_all_snapshot_changes()` | `recommendation_lineage.compute_recommendation_lineage()`, `performance_attribution.compute_performance_attribution()` |

**Producer function:** `src/pis/change_detection.py:compute_all_snapshot_changes()`  
**Dependency:** Reads canonical snapshot positions files (partition directories)  
**Freshness trigger:** canonical_latest > change_latest

### Tier 3 — Recommendation Lineage

| Artifact | Path | Producer | Consumer |
|----------|------|----------|----------|
| Lineage Records | `data/history/pis/lineage/lineage_records.csv` | `recommendation_lineage.compute_recommendation_lineage()` | `performance_attribution.compute_performance_attribution()` |
| Lineage Summary | `data/history/pis/lineage/lineage_summary.csv` | `recommendation_lineage.compute_recommendation_lineage()` | `performance_attribution.compute_performance_attribution()` |

**Producer function:** `src/pis/recommendation_lineage.py:compute_recommendation_lineage()`  
**Dependency:** change_records.csv, change_summary.csv, PAR analysis_runs directories  
**Freshness trigger:** change_latest > lineage_latest

### Tier 4 — Performance Attribution

| Artifact | Path | Producer | Consumer |
|----------|------|----------|----------|
| Attribution Records | `data/history/pis/attribution/attribution_records.csv` | `performance_attribution.compute_performance_attribution()` | `benchmark_attribution.compute_benchmark_recommendation_attribution()` |
| Attribution Summary | `data/history/pis/attribution/attribution_summary.csv` | `performance_attribution.compute_performance_attribution()` | Dashboard `/api/pis/attribution/history` |

**Producer function:** `src/pis/performance_attribution.py:compute_performance_attribution()`  
**Dependency:** change_records.csv, change_summary.csv, lineage_records.csv, lineage_summary.csv  
**Freshness trigger:** lineage_latest > attribution_latest

### Tier 5 — Benchmark Attribution

| Artifact | Path | Producer | Consumer |
|----------|------|----------|----------|
| Benchmark Return Series | `data/history/pis/benchmark_attribution/benchmark_return_series.csv` | `benchmark_attribution.compute_benchmark_return_series()` | `benchmark_attribution.compute_benchmark_recommendation_attribution()` |
| Recommendation Benchmark Records | `data/history/pis/benchmark_attribution/recommendation_benchmark_records.csv` | `benchmark_attribution.compute_benchmark_recommendation_attribution()` | Dashboard benchmark endpoints |
| Source Benchmark Summary | `data/history/pis/benchmark_attribution/source_benchmark_summary.csv` | `benchmark_attribution.compute_benchmark_recommendation_attribution()` | Dashboard benchmark endpoints |

**Producer functions:**  
- `src/pis/benchmark_attribution.py:compute_benchmark_return_series()` (SPY interval returns)  
- `src/pis/benchmark_attribution.py:compute_benchmark_recommendation_attribution()` (recommendation vs benchmark)  
**Dependency:** canonical_daily_snapshots.csv, benchmark price data, attribution_records.csv, change_records.csv  
**Freshness trigger:** attribution_latest > benchmark_latest

---

## Recompute Order

| Order | Stage | Function | Trigger Rule |
|-------|-------|----------|-------------|
| 1 | Canonical | `refresh_canonical_daily()` | gov_latest_PASS > canonical_latest |
| 2 | Change Detection | `compute_all_snapshot_changes()` | canonical_latest > change_latest |
| 3 | Lineage | `compute_recommendation_lineage()` | change_latest > lineage_latest |
| 4 | Attribution | `compute_performance_attribution()` | lineage_latest > attribution_latest |
| 5 | Benchmark Series | `compute_benchmark_return_series()` | attribution_latest > benchmark_latest |
| 5b | Benchmark Recommendations | `compute_benchmark_recommendation_attribution()` | (same trigger as 5) |

---

## What Was NOT in the Dependency Graph (Pre-PIS-005)

The following critical link was missing from the prior architecture:

```
governance approval → canonical refresh → (chain trigger)
```

The individual stages existed and worked correctly when called.  
The **missing piece** was the orchestration layer that connects them.

**PIS-005 adds:**

```
artifact_freshness.py  — deterministic staleness detection
refresh_orchestrator.py — ordered, lock-protected chain execution
/api/pis/refresh        — on-demand trigger endpoint
/api/pis/refresh/status — freshness visibility endpoint
startup trigger         — automatic refresh at server start
```
