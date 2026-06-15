# Attribution Refresh Trace — PIS-LINEAGE-ATTR-REFRESH-04

**Investigation Date:** 2026-06-14  
**Scope:** Trace attribution advancement dependency chain

---

## Summary

**Attribution advancement is blocked at the canonical snapshot stage.** The chain is: canonical → change detection → lineage → attribution. Since canonical stops at June 11, so does everything downstream.

---

## The Dependency Chain

```
Canonical Daily Snapshot (2026-06-14)
    ↓ (if exists)
Change Detection (compares consecutive canonicals)
    ↓
Lineage (matches changes to recommendations)
    ↓
Attribution (computes returns for matched changes)
    ↓
Benchmark Attribution (computes excess returns vs SPY)
```

---

## Current State by Date

### 2026-06-11 (LAST COMPLETE ROW)

✓ **Canonical:** PSNAP-20260611-B39EFA0A6C95 (PASS)  
✓ **Changes:** Computed (compared 2026-06-11 vs 2026-06-10)  
✓ **Lineage:** Matched (3 changes matched to recommendations)  
✓ **Attribution:** Computed (outcome scores calculated)  
✓ **Benchmark:** Computed (excess returns calculated)

### 2026-06-12 (GAP STARTS HERE)

✗ **Canonical:** NOT IN canonical_daily_snapshots.csv  
✗ **Changes:** NOT computed (no canonical for 2026-06-12)  
✗ **Lineage:** NOT matched (no changes to match)  
✗ **Attribution:** NOT computed (no lineage data)  
✗ **Benchmark:** NOT computed (no attribution data)

### 2026-06-13 (NO DATA)

✗ **Canonical:** NOT IN canonical_daily_snapshots.csv  
✗ **Changes:** NOT computed  
✗ **Lineage:** NOT computed (last updated 2026-06-13T18:26:36, but with data through 2026-06-11)  
✗ **Attribution:** NOT computed  
✗ **Benchmark:** NOT computed  

### 2026-06-14 (NEWEST INGESTION)

✗ **Canonical:** EXISTS IN GOVERNANCE (PASS status) but NOT in canonical_daily_snapshots.csv  
✗ **Changes:** NOT computed (no canonical comparison)  
✗ **Lineage:** NOT computed (no changes to match)  
✗ **Attribution:** NOT computed (no lineage data)  
✗ **Benchmark:** NOT computed (no attribution data)

---

## Q11: What exact dependency prevented attribution from advancing?

**Answer:** Canonical snapshot persistence

**Evidence:**

```
┌─────────────────────────────────────────────────────────────┐
│ Attribution Computation Flow                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ compute_performance_attribution(...)                       │
│   ├─ Reads: change_records.csv                            │
│   ├─ Reads: change_summary.csv                            │
│   ├─ Reads: lineage_records.csv                           │
│   └─ Requires: NEW changes to compute NEW attribution     │
│                                                             │
│ But:                                                        │
│   → change_detection depends on canonical snapshots       │
│   → Canonical stops at 2026-06-11                          │
│   → No changes computed for 2026-06-12+                    │
│   → No lineage matches for 2026-06-12+                     │
│   → No attribution for 2026-06-12+                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

[src/pis/performance_attribution.py:compute_performance_attribution()](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/performance_attribution.py#L198)

```python
def compute_performance_attribution(...):
    change_rows = _read_csv_rows(change_records_path)
    lineage_rows = _read_csv_rows(lineage_records_path)
    # These CSVs only have data through 2026-06-11
    # because canonical snapshots only go to 2026-06-11
```

---

## Q12: Is lineage the blocker?

**Answer:** NO - Lineage is a symptom, not the root cause

Lineage depends on change detection, which depends on canonical:

```
Change Detection:
  ├─ Needs: canonical snapshot 2026-06-11
  ├─ Needs: canonical snapshot 2026-06-12 (to compare)
  └─ Produces: changes by comparing the two
  
But canonical only has 2026-06-11, so:
  → No changes can be detected for 2026-06-12
  → No lineage can match 2026-06-12 changes
  → No attribution can be computed for 2026-06-12
```

**Lineage is blocked because it has no input data (changes), not because of lineage itself.**

---

## Q13: Is candidate generation the blocker?

**Answer:** NO - Candidates are available

Candidates exist for 2026-06-14 (230 candidates extracted).

The problem is not "no candidates"; it's "no changes to match them to".

**Proof:**
```
Candidates from June 14 PAR: 230 (available)
Changes from June 14: 0 (blocked by canonical)
Lineage matches: 0 (can't match 0 changes to any candidates)
```

---

## Q14: Is refresh logic the blocker?

**Answer:** YES - Primary root cause

No automatic trigger exists to:
1. Refresh canonical_daily_snapshots.csv when new canonical is approved
2. Trigger change detection when canonical is refreshed
3. Trigger lineage when changes are detected
4. Trigger attribution when lineage is computed

[src/pis/canonical_daily.py](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/canonical_daily.py#L80) has a `select_canonical_daily_rows()` function that CAN include June 12-14, but:

- This function is never called after June 14 ingestion
- The persisted CSV (`canonical_daily_snapshots.csv`) is never refreshed with the new selection

**Missing trigger:** `compute_performance_attribution()` should call `select_canonical_daily_rows()` and update the canonical CSV before proceeding with change detection.

---

## Canonical Selection Capability Verification

Testing what canonical WOULD include if it were refreshed:

```python
from src.pis.canonical_daily import select_canonical_daily_rows

canonical = select_canonical_daily_rows()
# Returns 18 daily snapshots including:
{
  'snapshot_date': '2026-06-14',
  'canonical_snapshot_id': 'PSNAP-20260614-A10360707326',
  'governance_status': 'PASS',
  'portfolio_value': 473874.84,
  'position_count': 81
}
```

**The canonical_daily.py code WORKS correctly and WOULD include June 14.**

The issue is that `select_canonical_daily_rows()` is never called to regenerate the CSV.

---

## Dependency Trace for 2026-06-12 Scenario

If canonical WERE refreshed to include 2026-06-12:

```
Step 1: Canonical refresh
  → canonical_daily_snapshots.csv updated with 2026-06-12

Step 2: Change detection triggered
  → compute_all_snapshot_changes(canonical_2026-06-11, canonical_2026-06-12)
  → Detects changes: position_value_changes, new/exited positions
  → Writes change_records.csv with 2026-06-12 changes
  
Step 3: Lineage triggered
  → compute_recommendation_lineage() reads new change_records.csv
  → Matches 2026-06-12 changes to candidates from PAR-20260612-*
  → Finds HIGH/MEDIUM/LOW confidence matches
  → Writes lineage_records.csv with 2026-06-12 matches
  
Step 4: Attribution triggered
  → compute_performance_attribution() reads new lineage_records.csv
  → Calculates directional_return_pct for each matched recommendation
  → Classifies outcomes (WINNER/NEUTRAL/LOSER)
  → Writes attribution_records.csv with 2026-06-12 data
  
Step 5: Benchmark triggered
  → Computes excess returns vs SPY
  → Calculates source alpha
  → Writes benchmark_attribution_records.csv with 2026-06-12 data
```

**This pipeline could execute, but the first step (canonical refresh) is not triggered.**

---

## Conclusion

Q11: Canonical snapshot persistence is the dependency blocker  
Q12: NO - Lineage is dependent on canonical, not a blocker  
Q13: NO - Candidates are available; not the blocker  
Q14: YES - Refresh logic defect is the primary root cause

**Primary Root Cause:** No automatic trigger to refresh canonical_daily_snapshots.csv when new canonical snapshots are approved by governance.

**Downstream Effects:**
- Change detection blocked (no new canonical pairs to compare)
- Lineage blocked (no new changes to match)
- Attribution blocked (no new lineage data)
- Benchmark blocked (no new attribution data)

**All artifacts stop at 2026-06-11 because canonical stops there.**
