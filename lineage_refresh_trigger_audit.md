# Lineage Refresh Trigger Audit — PIS-LINEAGE-ATTR-REFRESH-03

**Investigation Date:** 2026-06-14  
**Scope:** Trace lineage refresh triggers and canonical snapshot dependency

---

## Summary

**Lineage was NOT recomputed after 2026-06-14 because canonical snapshots for June 12-14 were never written to the canonical_daily_snapshots.csv file.** The canonical selection logic CAN include June 14, but the persisted file is stale.

---

## Q7: Was lineage recomputed after 2026-06-14 ingestion?

**Answer:** NO

**Evidence:**

**Lineage Latest Date:** 2026-06-11 ([data/history/pis/lineage/lineage_summary.csv](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/history/pis/lineage/lineage_summary.csv))

```
snapshot_date,created_at
...
2026-06-11,2026-06-13T18:26:36+00:00
```

**Last Recomputation:** 2026-06-13T18:26:36+00:00  
**Ingestion of 2026-06-14 Snapshot:** 2026-06-14T15:10:36+00:00

**Timeline:**
1. 2026-06-13T18:26:36 - Lineage recomputed (contains up to 2026-06-11)
2. 2026-06-14T15:10:36 - New portfolio snapshot for 2026-06-14 ingested
3. No lineage recomputation after 2026-06-14T15:10:36

---

## Q8: If not, why not?

**Answer:** The recomputation trigger condition was never met after June 14 ingestion.

**Trigger Logic:** [src/pis/performance_attribution.py:_load_attribution_tables()](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/performance_attribution.py#L330)

Attribution (which triggers lineage) only recomputes if:

```python
need_lineage_recompute = (
    candidates_override is not None
    or not lineage_records_path.exists()
    or not lineage_summary_path.exists()
)

if need_lineage_recompute:
    compute_recommendation_lineage(...)
```

**Since June 14 ingestion:**
- `candidates_override`: None (no manual override provided)
- Lineage files exist (last written 2026-06-13)
- Recomputation condition: FALSE

**No automatic trigger connects:**
1. New canonical snapshot → lineage recomputation

---

## Q9: Should it have been?

**Answer:** YES - Architectural defect

When a new canonical snapshot is ingested and approved (PASS governance status), lineage should be recomputed to match changes in that snapshot.

**Current Behavior:** Attribution/lineage only recompute on manual override or file deletion.

**Expected Behavior:** On canonical refresh, trigger lineage refresh.

---

## Critical Dependency: Canonical Snapshots

### Canonical Selection Logic

The canonical selection function **CAN** include June 14:

```python
from src.pis.canonical_daily import select_canonical_daily_rows
canonical = select_canonical_daily_rows()

# Result includes:
# Date: 2026-06-14, ID: PSNAP-20260614-A10360707326, Status: PASS
```

### Canonical Persisted File

But the persisted file [data/history/pis/canonical/canonical_daily_snapshots.csv](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/history/pis/canonical/canonical_daily_snapshots.csv) does NOT include June 12-14:

```
Last row: 2026-06-11, PSNAP-20260611-B39EFA0A6C95, PASS
```

### Root Cause

The canonical CSV file was last written on 2026-06-14 10:21 (before governance approval of 2026-06-14 snapshot was complete or before refresh was triggered).

**Two Possibilities:**
1. Canonical refresh never ran after June 14 governance approval
2. Canonical refresh ran but didn't include June 14

---

## Lineage Refresh Path Analysis

### Path 1: Automatic Refresh (Missing Trigger)

No automatic trigger calls `compute_recommendation_lineage()` after canonical snapshot ingestion.

**Missing Code:**
```
# Doesn't exist:
when new_canonical_snapshot_ingested:
    call compute_recommendation_lineage()
```

### Path 2: API-Triggered Refresh

When `/api/pis/attribution/latest` is called:
```python
def pis_attribution_latest(...):
    summary_rows, record_rows = _load_attribution_tables(...)
    # IF lineage files don't exist, re-triggers computation
```

But lineage files DO exist, so no refresh is triggered.

### Path 3: Startup Refresh

On server startup, `_load_attribution_tables()` is called, but only refreshes if files missing.

**Current state:** Files exist, so no refresh.

### Path 4: Manual Override

`compute_recommendation_lineage(candidates_override=None)` can be called directly, but no code path does this after canonical ingestion.

---

## Governance Approval Timeline

### Governance Status File

[data/history/pis/governance/snapshot_governance.csv](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/history/pis/governance/snapshot_governance.csv)

```
PSNAP-20260614-A10360707326,2026-06-14,PASS,,true,true,true
```

2026-06-14 snapshot IS marked as PASS in governance.

**But:** The canonical_daily_snapshots.csv doesn't reflect this approval.

---

## Lock and Concurrency Check

[src/pis/performance_attribution.py](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/performance_attribution.py#L330)

```python
_ATTRIBUTION_REFRESH_LOCK = threading.Lock()

def _load_attribution_tables(...):
    ...
    if need_recompute:
        with _ATTRIBUTION_REFRESH_LOCK:
            compute_performance_attribution(...)
```

Lock is present and used correctly. No concurrency issue evident.

---

## Artifact Freshness Comparison

| Artifact | Latest Date | Last Updated | Days Behind |
|----------|------------|--------------|------------|
| PAR Manifest | 2026-06-14 | ✓ Current | 0 |
| Candidates | 2026-06-14 | ✓ Current | 0 |
| Governance | 2026-06-14 | ✓ Current | 0 |
| Canonical CSV | 2026-06-11 | 2026-06-14 10:21 | 3 days |
| Lineage CSV | 2026-06-11 | 2026-06-13 18:26 | 3 days |
| Attribution CSV | 2026-06-11 | 2026-06-13 18:26 | 3 days |

**Pattern:** Canonical, Lineage, and Attribution all stop at 2026-06-11, suggesting canonical is the blocker.

---

## Conclusion

Q7: NO - Lineage was NOT recomputed after 2026-06-14  
Q8: Missing automatic trigger to refresh lineage/canonical when new canonical snapshot is approved  
Q9: YES - Should have been recomputed; architectural defect exists

**The defect:** No mechanism connects:
1. Canonical snapshot ingestion → governance approval → canonical CSV refresh → lineage recomputation

**Manual workaround:** Delete `canonical_daily_snapshots.csv` and call `select_canonical_daily_rows()` to regenerate with June 14 included.

---

## Recommendation

Implement automatic trigger:

```python
# After governance approval of new snapshot:
if snapshot_approved_and_not_in_canonical:
    refresh_canonical_daily()  # Regenerates CSV
    compute_recommendation_lineage()  # Re-matches changes
    compute_performance_attribution()  # Recomputes returns
```

Current state is **NOT a defect in candidate extraction** (that works fine), but a **defect in triggering the refresh pipeline**.
