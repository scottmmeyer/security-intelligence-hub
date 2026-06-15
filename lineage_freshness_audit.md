# Lineage Freshness Audit — PIS-ATTR-FORENSIC-05

**Date:** 2026-06-14  
**Scope:** Recommendation lineage freshness and recomputation triggers

---

## Q22: Does Lineage Contain 2026-06-14?

**Answer:** No.

**Latest Lineage Snapshot Date:** 2026-06-11 ([data/history/pis/lineage/lineage_summary.csv](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/history/pis/lineage/lineage_summary.csv))

**Latest Change Detection Date:** 2026-06-14 ([data/history/pis/changes/change_summary.csv](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/history/pis/changes/change_summary.csv))

**Gap:** 3 calendar days (2026-06-12, 06-13, 06-14 not in lineage)

---

## Q23: Why Lineage Does Not Contain 2026-06-14

### Root Cause

Lineage depends on recommendation candidates from SIH. [src/pis/recommendation_lineage.py:299-330]

```python
def compute_recommendation_lineage(...):
    candidates = candidates_override or build_recommendation_candidates(
        analysis_runs_root=root / "data/portfolio_ingestion/analysis_runs"
    )
    # candidates are built from PAR.analysis_run files
    # If no PAR was added after 2026-06-11, no new candidates exist
    # Therefore, no new changes can be matched for 2026-06-14
```

**Latest PAR (Portfolio Analysis Run):** PAR-20260529-33B7DB0B  
**Added to Manifest:** 2026-05-29

No new PARs have been added since 2026-05-29. Without new candidates, lineage cannot match 2026-06-14 changes.

---

## Q24: Was Lineage Recomputed After Latest Snapshot Ingestion?

**Latest Snapshot Ingestion:** 2026-06-14  
**Latest Lineage Recomputation:** 2026-06-13T18:28:58+00:00 (from lineage_summary.csv)

**Time between ingestion and lineage computation:** ~0 hours (lineage was computed the same day)

**But:** Lineage was computed with the same candidate set as before (no new PARs), so it didn't extend beyond 2026-06-11 changes. It recomputed, but with no new input.

---

## Q25: Recomputation Trigger Logic

[src/pis/recommendation_lineage.py:300-330]

### Automatic Recomputation

```python
def _load_lineage_tables(...):
    candidates_override = None  # no override in normal flow
    need_recompute = (
        candidates_override is not None
        or not lineage_records_path.exists()
        or not lineage_summary_path.exists()
    )
    if need_recompute:
        with _LINEAGE_REFRESH_LOCK:
            compute_recommendation_lineage(...)
    return summary_rows, record_rows
```

Lineage recomputes when:
1. CSV files don't exist, OR
2. `candidates_override` is provided (tests/manual override)

### Current State

Lineage CSV files **do exist**. Last recomputation was 2026-06-13T18:28:58. The trigger condition `not lineage_records_path.exists()` is false, so no automatic recomputation happens.

### Manual Trigger

Calling `compute_recommendation_lineage(candidates_override=None)` directly would force a recomputation, but no code path does this when a new canonical snapshot is ingested.

---

## Q26: Expected Refresh Path

### Expected Behavior

When a new canonical snapshot is ingested:
1. Change detection runs → produces new change_records.csv entries
2. **[MISSING]** Lineage refresh is triggered → reads latest candidates → matches changes
3. Attribution refresh is triggered → reads latest lineage → computes returns

### Actual Behavior

1. Change detection runs → produces new change_records.csv entries ✓
2. **[MISSING]** Lineage refresh is NOT automatically triggered
3. **[MISSING]** Attribution refresh is NOT automatically triggered

### Why?

The system assumes that if new candidates are needed, they will be provided via `candidates_override` or the CSV files will be deleted/refreshed. There is **no automatic trigger** that says "new canonical snapshot → rerun lineage."

---

## Lineage Data Freshness

### lineage_records.csv

```
Latest snapshot_date: 2026-06-11
Created at: 2026-06-13T18:28:58+00:00
Total records: 50
```

### lineage_summary.csv

```
Latest snapshot_date: 2026-06-11
Created at: 2026-06-13T18:28:58+00:00
Total records: 16 (one per snapshot date)
```

### Sample Records

```
snapshot_date: 2026-06-11
symbol: VXUS
matched_recommendation_id: DIL-PAR-20260603-0487E65C-VXUS
confidence: MEDIUM
days_between: 2

snapshot_date: 2026-06-11
symbol: FIGFX
matched_recommendation_id: DIL-PAR-20260603-0A7E6D2D-FIGFX
confidence: MEDIUM
days_between: 1
```

---

## Matching Algorithm Verification

[src/pis/recommendation_lineage.py:445-550]

```python
def _best_match(change_row, candidates, symbol_to_themes):
    # HIGH confidence: symbol_match + direction_match + days ≤ 7 (no competing)
    # MEDIUM confidence: (symbol + direction + days ≤ 30) OR (theme + direction + days ≤ 30)
    # LOW confidence: (symbol + direction + days ≤ 90) OR (theme + days ≤ 90)
    # NONE: no match or days_between < 0 or > 90
```

For 2026-06-12 and 2026-06-14 changes to be matched, candidates from PARs between 2026-04-13 and 2026-09-13 would be available. But **no PARs exist in that range** (latest is 2026-05-29).

---

## Candidate Source Verification

**Analysis Runs Root:** `/data/portfolio_ingestion/analysis_runs/`

**Contents:** [via manifest PAR lookup]
```
PAR-20260526-XXXX
PAR-20260527-XXXX
PAR-20260529-XXXX (latest)
```

**Missing:** Any PAR from 2026-06-12, 06-13, or 06-14.

---

## Expected vs Actual

### Expected

Lineage should be current to 2026-06-14 if:
1. New PARs were generated, AND
2. Lineage recomputation was triggered (automatic or manual), AND
3. New change records from 2026-06-12 to 2026-06-14 could be matched

### Actual

Lineage stops at 2026-06-11 because:
1. No new PARs were generated since 2026-05-29
2. Lineage recomputation was not triggered after 2026-06-14 snapshot ingestion
3. No candidates exist to match 2026-06-12 to 2026-06-14 changes

### Verdict

**EXPECTED DATA FRESHNESS ISSUE.** Lineage is correctly stale because:
- The system is **candidate-driven**, not date-driven
- New lineage matches require new recommendation candidates (PARs)
- No new PARs = no new lineage matches
- No automatic trigger connects snapshot ingestion to lineage refresh

---

## Governance Gap

There should be an **automatic trigger** that:
1. Detects new canonical snapshots
2. Initiates lineage recomputation if no new candidates are available
3. Or requires the SIH workflow to generate a new PAR when a new canonical snapshot is ready

Currently, neither exists. Lineage refresh is **manual** or depends on file deletion/override.

---

## Conclusion

Lineage is **correctly stale** at 3 days behind canonical, mirroring the attribution staleness. Both depend on new SIH recommendations (PARs) to advance. Without new PARs, neither artifact extends beyond 2026-06-11.

**Recommendation:** Implement automatic trigger to refresh lineage when new canonical snapshots are detected, or require SIH to generate new PARs as part of the ingestion workflow.
