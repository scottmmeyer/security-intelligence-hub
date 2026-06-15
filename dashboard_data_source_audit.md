# Dashboard Data Source Audit — PIS-LINEAGE-ATTR-REFRESH-05

**Investigation Date:** 2026-06-14  
**Scope:** Verify dashboard data sources and why dashboard reports June 14 while other systems show June 11

---

## Summary

The dashboard is reading from the manifest directly and is correct. All other systems are reading from computed artifacts that depend on canonical snapshots (which are stale).

---

## Dashboard Data Source

### Endpoint: `/api/pis/summary`

[scripts/run_outcome_ui.py:429-451](file:///Users/scottmmeyer/Projects/security-intelligence-hub/scripts/run_outcome_ui.py#L429)

```python
@app.route("/api/pis/summary", methods=["GET"])
def get_pis_summary():
    summary = pis_dashboard_summary(repo_root=_REPO_ROOT)
    return jsonify(summary)
```

---

## pis_dashboard_summary() Data Flow

[src/pis/storage.py:298-336](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/storage.py#L298)

```python
def pis_dashboard_summary(repo_root):
    lineage_summary = pis_sih_lineage_summary(repo_root)
    # lineage_summary contains:
    # {
    #   'total_sih_analyses_captured': 236,
    #   'latest_par': 'PAR-20260614-3A8B91DB',
    #   'latest_upload_date': '2026-06-14'
    # }
    
    health = pis_health_metrics(...)
    # health contains: snapshot counts, ingestion metrics
    
    return {
        'health': health,
        'lineage': lineage_summary,
        ...
    }
```

### Data Source for "latest_par"

[src/pis/storage.py:pis_sih_lineage_summary()](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/storage.py#L298)

```python
def pis_sih_lineage_summary(repo_root):
    manifest_path = os.path.join(repo_root, 'data/portfolio_ingestion/manifest.json')
    
    with open(manifest_path) as f:
        manifest_data = json.load(f)
    
    portfolios = manifest_data.get('portfolios', [])
    
    if not portfolios:
        return {'total_sih_analyses_captured': 0, 'latest_par': '', ...}
    
    # Sort by (created_at_utc DESC, snapshot_date DESC)
    latest_par = max(
        portfolios,
        key=lambda p: (p.get('created_at_utc', ''), p.get('snapshot_date', ''))
    )
    
    return {
        'total_sih_analyses_captured': len(portfolios),
        'latest_par': latest_par.get('run_id', ''),
        'latest_upload_date': latest_par.get('snapshot_date', '')
    }
```

**Source:** [data/portfolio_ingestion/manifest.json](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/portfolio_ingestion/manifest.json) (authoritative PAR registry, 236 entries, latest=PAR-20260614-3A8B91DB)

---

## Dashboard Response (Actual)

When `/api/pis/summary` is queried:

```json
{
  "health": {
    "total_snapshots_ingested": 31,
    "pass_snapshots": 18,
    "warning_snapshots": 9,
    "reject_snapshots": 4,
    ...
  },
  "lineage": {
    "total_sih_analyses_captured": 236,
    "latest_par": "PAR-20260614-3A8B91DB",
    "latest_upload_date": "2026-06-14",
    ...
  }
}
```

**Status:** CORRECT - Reflects manifest state

---

## Attribution API Data Source

### Endpoint: `/api/pis/attribution/latest`

[scripts/run_outcome_ui.py:452-470](file:///Users/scottmmeyer/Projects/security-intelligence-hub/scripts/run_outcome_ui.py#L452)

```python
@app.route("/api/pis/attribution/latest", methods=["GET"])
def get_pis_attribution_latest():
    summary_rows, record_rows = pis_attribution_latest(repo_root=_REPO_ROOT)
    return jsonify({'summary': summary_rows, 'records': record_rows})
```

**Data Sources:**
- [data/history/pis/attribution/attribution_summary.csv](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/history/pis/attribution/attribution_summary.csv) (latest date: 2026-06-11)
- [data/history/pis/attribution/attribution_records.csv](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/history/pis/attribution/attribution_records.csv) (latest date: 2026-06-11)

**Status:** STALE - Stops at 2026-06-11

---

## Why Different Data?

| Data Source | System | Latest Date | Why |
|-------------|--------|-------------|-----|
| manifest.json | Dashboard (lineage tab) | 2026-06-14 ✓ | Direct query; not computed |
| attribution_records.csv | Attribution API | 2026-06-11 ✗ | Depends on canonical snapshots → change detection → lineage → attribution (chain blocked at canonical) |
| lineage_records.csv | Lineage API | 2026-06-11 ✗ | Depends on canonical → change detection → lineage (chain blocked at canonical) |
| change_records.csv | Change Detection API | 2026-06-11 ✗ | Depends on canonical snapshots (chain blocked at canonical) |
| canonical_daily_snapshots.csv | Portfolio Data API | 2026-06-11 ✗ | Last persisted refresh at 2026-06-14 10:21, but before June 14 was added to canonical |

---

## Manifest vs Artifact Discrepancy

### Dashboard Layer (Fresh)

```
manifest.json (236 PARs)
  ↓
pis_sih_lineage_summary()
  ↓
Dashboard: "Latest PAR: PAR-20260614-3A8B91DB" ✓ CORRECT
```

### Computed Artifact Layers (Stale)

```
canonical_daily_snapshots.csv (stops at 2026-06-11)
  ↓
change_records.csv (stops at 2026-06-11)
  ↓
lineage_records.csv (stops at 2026-06-11)
  ↓
attribution_records.csv (stops at 2026-06-11)
  ↓
Attribution API: "Latest: 2026-06-11" ✗ STALE
```

---

## Q15: Is dashboard correct?

**Answer:** YES

**Evidence:**
- Dashboard reads manifest.json
- manifest.json contains 236 PARs
- Latest PAR = PAR-20260614-3A8B91DB (verified: directory exists, files present)
- Dashboard displays this correctly

---

## Q16: Is dashboard misleading?

**Answer:** YES - Partial picture

**Issue:** Dashboard shows latest PAR ingested (manifested) but not latest PAR analyzed (attributed).

```
Dashboard says: "236 SIH analyses captured"
But means: "236 PARs exist in manifest"
Not: "236 PARs have complete attribution computed"

Actually computed through: 2026-06-11
PARs total: 236
PARs with attribution: ~145 (through 2026-06-11)
PARs without attribution: ~91 (June 12-14 and others)
```

**This is NOT a dashboard bug, but an architectural pattern:** The dashboard layer reads from manifest (canonical source), while computed metrics depend on downstream artifact freshness.

---

## Q17: Should they match?

**Answer:** YES - They should match, but don't due to refresh trigger defect

**What SHOULD happen:**
1. New PAR ingested → manifest updated with 236 entries
2. Canonical refresh triggered → canonical_daily_snapshots.csv updated
3. Change detection triggered → change_records.csv updated
4. Lineage triggered → lineage_records.csv updated
5. Attribution triggered → attribution_records.csv updated
6. Dashboard says: "Latest analysis: 2026-06-14" (matching manifest)

**What ACTUALLY happens:**
1. New PAR ingested → manifest updated with 236 entries
2. Canonical refresh NOT triggered → canonical_daily_snapshots.csv NOT updated
3. Change detection NOT triggered → change_records.csv NOT updated
4. Lineage NOT triggered → lineage_records.csv NOT updated
5. Attribution NOT triggered → attribution_records.csv NOT updated
6. Dashboard still says: "Latest PAR: 2026-06-14" but attribution shows "Latest: 2026-06-11"

---

## Data Source Consistency Table

| Subsystem | Data Source | Query Type | Latest Date | Status |
|-----------|------------|-----------|------------|--------|
| Dashboard Lineage | manifest.json | Direct read | 2026-06-14 | ✓ Fresh |
| Portfolio Stats | canonical_daily_snapshots.csv | Computed, persisted | 2026-06-11 | ✗ Stale |
| Changes | change_records.csv | Computed, persisted | 2026-06-11 | ✗ Stale |
| Lineage Matches | lineage_records.csv | Computed, persisted | 2026-06-11 | ✗ Stale |
| Attribution Scores | attribution_records.csv | Computed, persisted | 2026-06-11 | ✗ Stale |
| Benchmark Returns | benchmark_attribution_records.csv | Computed, persisted | 2026-06-11 | ✗ Stale |

---

## Conclusion

Q15: YES - Dashboard is reporting accurately from manifest  
Q16: YES - Dashboard is misleading because it doesn't match downstream computed metrics  
Q17: YES - They should match after refresh trigger is implemented

**Current state is a **consistency problem**, not a correctness problem at the dashboard layer.**

The dashboard correctly reports what's in the manifest. The problem is that computed artifacts haven't caught up because the refresh trigger doesn't exist.

**Fix required:** Implement automatic trigger to refresh canonical → change detection → lineage → attribution when new canonical is approved.
