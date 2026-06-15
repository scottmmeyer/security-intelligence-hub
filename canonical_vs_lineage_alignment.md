# Canonical vs Lineage Alignment — PIS-LINEAGE-ATTR-REFRESH-06

**Investigation Date:** 2026-06-14  
**Scope:** Compare canonical snapshot advancement vs lineage advancement; identify sync points

---

## Summary

Canonical and lineage are perfectly aligned because lineage depends on canonical. Both stop at 2026-06-11 because the canonical CSV hasn't been refreshed to include June 12-14.

---

## Alignment Table

| Date | Canonical CSV | Lineage CSV | Change CSV | Attribution CSV | Alignment | Notes |
|------|---------------|-------------|------------|-----------------|-----------|-------|
| 2026-05-21 | ✓ PASS | ✓ Matched | ✓ Detected | ✓ Computed | SYNC | All layers complete |
| 2026-05-22 | ✓ PASS | ✓ Matched | ✓ Detected | ✓ Computed | SYNC | All layers complete |
| ... | ... | ... | ... | ... | ... | ... |
| 2026-06-11 | ✓ PASS | ✓ Matched | ✓ Detected | ✓ Computed | SYNC | All layers complete |
| 2026-06-12 | ✗ MISSING | ✗ MISSING | ✗ MISSING | ✗ MISSING | OUT-OF-SYNC | Canonical not in CSV |
| 2026-06-13 | ✗ MISSING | ✗ MISSING | ✗ MISSING | ✗ MISSING | OUT-OF-SYNC | Canonical not in CSV |
| 2026-06-14 | ✗ MISSING | ✗ MISSING | ✗ MISSING | ✗ MISSING | OUT-OF-SYNC | Canonical not in CSV |

---

## Canonical CSV Status

[data/history/pis/canonical/canonical_daily_snapshots.csv](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/history/pis/canonical/canonical_daily_snapshots.csv)

```
Last row: 2026-06-11, PSNAP-20260611-B39EFA0A6C95, PASS, portfolio_value=455857.04, position_count=77
```

**Snapshot for 2026-06-14 Exists in Index:**
```
PSNAP-20260614-A10360707326, PASS, portfolio_value=473874.84, position_count=81
```

**But it's NOT in the canonical_daily_snapshots.csv file.**

---

## Why Canonical Halts at June 11

### Hypothesis A: CSV Never Refreshed After June 14 Ingestion ✓ CONFIRMED

**Evidence:**
- canonical_daily_snapshots.csv last modified: 2026-06-14 10:21
- June 14 snapshot ingested: 2026-06-14 15:10:36
- June 14 snapshot governance approved: After ingestion (based on governance CSV timestamp)
- Canonical refresh triggered after June 14: NO

**Verdict:** Canonical selection should have been triggered AFTER June 14 governance approval to include June 14 in the CSV. It was not.

### Hypothesis B: select_canonical_daily_rows() Is Broken ✗ REJECTED

**Evidence:**
- Code review shows correct logic (PASS_THEN_LATEST_INGESTION policy)
- When executed manually, returns 18 daily snapshots INCLUDING 2026-06-14
- No date filters, no hard-coded cutoffs

**Verdict:** Logic is correct; the function is just never called for refresh.

### Hypothesis C: Governance Approval Failed ✗ REJECTED

**Evidence:**
- governance/snapshot_governance.csv contains: `PSNAP-20260614-A10360707326,2026-06-14,PASS,`
- June 14 passed all checks: scope_valid=true, value_valid=true, source_valid=true

**Verdict:** Governance approval succeeded; artifact shows PASS status.

### Hypothesis D: Canonical Refresh Was Triggered But Excluded June 14 ✗ REJECTED

**Evidence:**
- Manual execution of select_canonical_daily_rows() returns June 14
- Code path has no conditional that would exclude June 14

**Verdict:** If run, function would include June 14. But function was not run.

---

## Lineage Dependency Chain

```
Canonical CSV (2026-06-11 latest)
    ↓ provides snapshot pairs for comparison
Change Detection (compares 2026-06-10 → 2026-06-11)
    ↓ produces detected changes
Lineage Matching (matches changes to recommendations)
    ↓
Lineage CSV (2026-06-11 latest)
```

**For lineage to advance to 2026-06-12:**

```
Requirement: Canonical must have both 2026-06-11 AND 2026-06-12
Current state: Canonical only has 2026-06-11
Result: No 2026-06-12 snapshot pair to compare
Result: No 2026-06-12 changes detected
Result: No 2026-06-12 lineage matches
Result: Lineage cannot advance past 2026-06-11
```

---

## Artifact Freshness Analysis

### Canonical Daily Snapshots CSV

**File:** [data/history/pis/canonical/canonical_daily_snapshots.csv](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/history/pis/canonical/canonical_daily_snapshots.csv)

**Last Modified:** 2026-06-14 10:21 UTC

**Contents:** 18 daily snapshots from 2026-05-21 through 2026-06-11

**Expected Contents:** 18+ daily snapshots from 2026-05-21 through 2026-06-14 (if June 14 is PASS)

**Actual Latest:** 2026-06-11

**Gap:** June 12, 13, 14 (3 days missing)

### Change Records CSV

**File:** [data/history/pis/change/change_records.csv](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/history/pis/change/change_records.csv)

**Last Modified:** Computed when canonical is refreshed

**Contents:** Changes detected from consecutive canonical snapshots

**Latest Date:** 2026-06-11

**Explanation:** Depends on canonical having both 2026-06-10 and 2026-06-11 to detect changes. Can't detect 2026-06-12 changes without 2026-06-12 canonical snapshot.

### Lineage Records CSV

**File:** [data/history/pis/lineage/lineage_records.csv](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/history/pis/lineage/lineage_records.csv)

**Last Modified:** 2026-06-13 18:26:36 UTC

**Contents:** Recommendation-to-change matches

**Latest Date:** 2026-06-11

**Explanation:** Last recomputed on 2026-06-13. At that time, canonical had data through 2026-06-11. After June 14 ingestion, canonical was not refreshed, so lineage has no new data to match.

### Attribution Records CSV

**File:** [data/history/pis/attribution/attribution_records.csv](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/history/pis/attribution/attribution_records.csv)

**Last Modified:** 2026-06-13 18:26:36 UTC

**Contents:** Outcome classifications and returns

**Latest Date:** 2026-06-11

**Explanation:** Depends on lineage having new matches. Since lineage doesn't have June 12+ data, attribution doesn't either.

---

## Cascade Failure Pattern

```
TRIGGER: June 14 snapshot ingested (2026-06-14T15:10:36)
           ↓
NEED: Canonical refresh to include June 14
           ↓
MISSING: No automatic refresh trigger called
           ↓
RESULT: canonical_daily_snapshots.csv stays at 2026-06-11
           ↓
CASCADE: Since canonical hasn't advanced...
           ├─ Change detection has no new snapshot pair
           ├─ Lineage matching has no new changes
           ├─ Attribution scoring has no new lineage
           └─ All downstream systems cascade fail
```

---

## Sync Point Analysis

### Sync Point 1: Canonical-to-Change

**Location:** [src/pis/change_detection.py](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/change_detection.py)

**Requirement:** `canonical_daily_snapshots.csv` must have consecutive daily pairs

**Current State:** Only has through 2026-06-11

**Result:** Can only compute changes through 2026-06-11

**Fix Required:** Refresh canonical to include 2026-06-12, 2026-06-13, 2026-06-14

### Sync Point 2: Change-to-Lineage

**Location:** [src/pis/recommendation_lineage.py](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/recommendation_lineage.py)

**Requirement:** `change_records.csv` must have changes to match

**Current State:** Only has through 2026-06-11

**Result:** Can only match changes through 2026-06-11

**Fix Required:** Refresh change detection with new canonical pairs

### Sync Point 3: Lineage-to-Attribution

**Location:** [src/pis/performance_attribution.py](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/performance_attribution.py)

**Requirement:** `lineage_records.csv` must have matches to score

**Current State:** Only has through 2026-06-11

**Result:** Can only compute attribution through 2026-06-11

**Fix Required:** Refresh lineage with new change matches

### Sync Point 4: Attribution-to-Benchmark

**Location:** [src/pis/benchmark_attribution.py](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/benchmark_attribution.py)

**Requirement:** `attribution_records.csv` must have outcome scores

**Current State:** Only has through 2026-06-11

**Result:** Can only compute benchmark through 2026-06-11

**Fix Required:** Refresh attribution with new lineage data

---

## Q18: When exactly did canonical diverge from manifest?

**Answer:** After 2026-06-13T18:26:36 UTC (last lineage recomputation)

**Timeline:**

```
2026-06-13T18:26:36: Last lineage recomputation
   → Canonical had data through 2026-06-11
   → Lineage computed with that data
   → Both frozen at 2026-06-11

2026-06-14T10:21: canonical_daily_snapshots.csv last touched
   → File modified but not updated with June 14

2026-06-14T15:10:36: June 14 snapshot ingested
   → New PSNAP-20260614-A10360707326 created
   → Governance evaluation runs

AFTER 2026-06-14T15:10:36: Missing trigger
   → Canonical refresh never triggered
   → June 14 never added to canonical_daily_snapshots.csv
   → Lineage recomputation never triggered
   → Attribution recomputation never triggered

RESULT: Divergence begins
   Manifest: 236 PARs, latest 2026-06-14 ✓
   Canonical CSV: 18 snapshots, latest 2026-06-11 ✗
   Lineage CSV: matches through 2026-06-11 ✗
   Attribution CSV: scores through 2026-06-11 ✗
```

---

## Q19: Is there a blocker preventing canonical from INCLUDING June 14?

**Answer:** NO - No technical blocker

**Evidence:**
- June 14 snapshot exists: PSNAP-20260614-A10360707326 ✓
- June 14 governance approved: governance_status=PASS ✓
- June 14 portfolio value passes threshold: 473,874.84 < 600,000 ✓
- June 14 account scope valid: Contains ("General Brokerage", "Joint WROS - TOD", "Individual - TOD") ✓
- June 14 source file valid: Portfolio_Positions_Jun-14-2026.csv (not test artifact) ✓

**Conclusion:** No blocker. The canonical selection logic WOULD include June 14 if executed.

---

## Q20: Is there a blocker preventing lineage from MATCHING June 14 changes?

**Answer:** YES - Indirect blocker (canonical not advanced)

**Blockers:**
1. No canonical snapshot pair for 2026-06-13 → 2026-06-14 comparison
2. Therefore no changes detected for 2026-06-14
3. Therefore no changes available for lineage to match

**Root cause:** Canonical selection not triggered after June 14 ingestion.

---

## Conclusion

**Canonical and Lineage are synchronized at 2026-06-11 because lineage depends on canonical. Neither has advanced past June 11 because canonical hasn't been refreshed to include June 12-14.**

**The issue is NOT misalignment; it's unified staleness caused by a missing refresh trigger at the canonical layer.**

**Fix:** Implement trigger to refresh canonical → change detection → lineage → attribution when new canonical snapshot is approved by governance.

When that's done, both canonical and lineage will advance together to 2026-06-14, becoming synchronized with the manifest.
