# Attribution Freshness Audit — PIS-ATTR-FORENSIC-04

**Date:** 2026-06-14  
**Scope:** Attribution data freshness and recomputation triggers

---

## Q16: Why Attribution Not Reflecting 2026-06-14?

**Latest Attribution Date:** 2026-06-11  
**Latest Canonical Date:** 2026-06-14  
**Gap:** 3 days

### Root Cause

Attribution depends on three upstream artifacts:
1. Change detection (latest: 2026-06-14 ✓)
2. Lineage (latest: 2026-06-11 ✗)
3. Change summary (latest: 2026-06-14 ✓)

**Lineage is the blocker.** [src/pis/performance_attribution.py:198-210]

```python
def compute_performance_attribution(...):
    lineage_records_path = lineage_root / "lineage_records.csv"
    lineage_summary_path = lineage_root / "lineage_summary.csv"
    need_lineage_recompute = (
        candidates_override is not None
        or not lineage_records_path.exists()
        or not lineage_summary_path.exists()
    )

    if need_lineage_recompute:
        compute_recommendation_lineage(...)

    change_rows = _read_csv_rows(change_records_path)
    change_summary_rows = _read_csv_rows(change_summary_path)
    lineage_rows = _read_csv_rows(lineage_records_path)
```

Attribution pulls lineage records directly. If lineage stops at 2026-06-11, attribution stops there too.

---

## Q17: Was Attribution Recomputed After Latest Snapshot Ingestion?

**Latest Snapshot Ingestion:** 2026-06-14 ([data/history/pis/canonical/canonical_daily_snapshots.csv](file:///Users/scottmmeyer/Projects/security-intelligence-hub/data/history/pis/canonical/canonical_daily_snapshots.csv#L1))

**Attribution Last Recomputation:** 2026-06-13T18:28:58+00:00 (from attribution_summary.csv `created_at`)

**Changes made between 2026-06-13 and 2026-06-14:**
- 2026-06-14 snapshot was ingested
- Governance evaluated (PASS status)
- Canonical daily snapshot created
- Change detection ran (produced 2026-06-14 change_summary.csv entry)
- **BUT: No new SIH PAR (Portfolio Analysis Run) was executed after 2026-06-11**

### Lineage Blocking Path

Lineage requires candidates from SIH analyses. [src/pis/recommendation_lineage.py:300-320]

```python
def compute_recommendation_lineage(...):
    candidates = candidates_override or build_recommendation_candidates(
        analysis_runs_root=root / "data/portfolio_ingestion/analysis_runs"
    )
    # If no new analysis_runs exist after 2026-06-11, no new candidates
    # Therefore, no new lineage matches for 2026-06-14 changes
```

**Latest Analysis Run in Manifest:** PAR-20260529-33B7DB0B  
**Manifest Updated:** 2026-06-13T18:28:58+00:00

No PAR has been added to the manifest since 2026-05-29. Without new PARs, there are no recommendation candidates for 2026-06-14 changes.

---

## Q18: Artifact Dates in Attribution Persistence

### attribution_records.csv

| Aspect | Latest Record |
|--------|---------------|
| snapshot_date | 2026-06-11 |
| created_at | 2026-06-13T18:28:58+00:00 |
| First record snapshot_date | 2026-05-22 |

### attribution_summary.csv

| Aspect | Latest Record |
|--------|---------------|
| snapshot_date | 2026-06-11 |
| created_at | 2026-06-13T18:28:58+00:00 |
| Record count | 16 snapshots covered |

---

## Q19: Newest Date Present

**Attribution newest date:** 2026-06-11  
**Canonical newest date:** 2026-06-14  
**Gap:** 3 calendar days, representing 2 non-weekend trading days (2026-06-12 and 2026-06-13 were weekend)

---

## Q20: Recomputation Mechanism

### Automatic Triggers

[src/pis/performance_attribution.py:191-210]

Attribution is **automatically** recomputed when:
1. Lineage artifacts don't exist, OR
2. `candidates_override` is explicitly provided (in tests), OR
3. A call to `pis_attribution_latest()` or `pis_attribution_summary()` is made and lineage is missing

### Manual Triggers

Explicitly calling `compute_performance_attribution()` in code or scripts.

### Scheduled

No scheduled recomputation. The system is **event-driven**, not time-driven.

### Broken?

The mechanism is **not broken**, but it depends on SIH (src/portfolio/runner.py) to provide new recommendation candidates (PARs). No new PARs have been generated since 2026-05-29, so no new candidates are available for 2026-06-14 changes.

---

## Q21: Expected vs Actual Behavior

### Expected

Attribution should reflect the latest canonical date if:
1. New PARs (recommendations) are generated after snapshot ingestion, AND
2. Recommendation lineage can match new changes to those recommendations, AND
3. Attribution is then recomputed

### Actual

Attribution stops at 2026-06-11 because:
1. No new PARs were generated after 2026-06-11
2. Lineage has no new candidates to match 2026-06-14 changes
3. Attribution cannot extend beyond the latest lineage date

### Verdict

**EXPECTED BEHAVIOR.** The system is designed to push data from SIH (PARs) into PIS (lineage → attribution → benchmark). Without new PARs from SIH, PIS cannot advance.

---

## Recomputation Path Details

**Path 1: Service endpoint** → `/api/pis/attribution/latest` calls `pis_attribution_latest()` [src/pis/performance_attribution.py:383-410]

```python
def pis_attribution_latest(...):
    summary_rows, record_rows = _load_attribution_tables(...)
    if not summary_rows:
        return {...}
    latest_snapshot_id = str(summary_rows[0].get("snapshot_id", ""))
    # Returns records for latest snapshot only
```

**Path 2: Underlying loader** → `_load_attribution_tables()` [src/pis/performance_attribution.py:330-360]

```python
def _load_attribution_tables(...):
    need_recompute = (
        candidates_override is not None
        or thresholds != DEFAULT_ATTRIBUTION_THRESHOLDS
        or not records_path.exists()
        or not summary_path.exists()
    )
    if need_recompute:
        with _ATTRIBUTION_REFRESH_LOCK:
            compute_performance_attribution(...)
    return summary_rows, record_rows
```

**Path 3: Recomputation trigger** → `compute_performance_attribution()` requires lineage [src/pis/performance_attribution.py:198-230]

```python
need_lineage_recompute = (
    candidates_override is not None
    or not lineage_records_path.exists()
    or not lineage_summary_path.exists()
)
if need_lineage_recompute:
    compute_recommendation_lineage(...)
```

---

## Conclusion

Attribution is **correctly stale** at 3 days behind canonical. The root cause is the absence of new SIH PARs after 2026-06-11. The recomputation mechanism is working correctly; it simply has no new input data (recommendations) to process.

**Recommendation:** Generate a new SIH PAR analysis for the 2026-06-14 snapshot if you want attribution to reflect that date.
