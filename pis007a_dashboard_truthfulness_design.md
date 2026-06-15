# PIS-007A Dashboard Truthfulness Design

**Date:** 2026-06-15  
**Remediation:** R3 — Dashboard latest upload date reflects actual portfolio data

---

## Problem

`pis_sih_lineage_summary()` in `src/pis/storage.py` sorted portfolios by `(created_at_utc, snapshot_date)`. When a PAR for an older portfolio date (e.g., 2026-05-29) is re-analyzed today (created_at_utc=2026-06-15), it sorts as "latest" — making the dashboard show `latest_upload_date: 2026-05-29` when the system actually has 2026-06-14 data.

A secondary issue: `CONCENTRATED_ALPHA` entries have a non-date `snapshot_date` field that sorts lexicographically after numeric dates (e.g., "CONCENTRATED_ALPHA" > "2026-06-14" in ASCII).

## Implementation

**File:** `src/pis/storage.py`  
**Function:** `pis_sih_lineage_summary()`

Change 1 — sort key reversal:
```python
# Before:
latest = max(portfolios, key=lambda r: (str(r.get("created_at_utc", "")), str(r.get("snapshot_date", ""))))

# After:
latest = max(dated_portfolios, key=lambda r: (str(r.get("snapshot_date", "")), str(r.get("created_at_utc", ""))))
```

Change 2 — filter non-date entries before sorting:
```python
dated_portfolios = [
    p for p in portfolios
    if len(str(p.get("snapshot_date", "")).strip()) == 10
    and str(p.get("snapshot_date", "")).strip()[4:5] == "-"
]
if not dated_portfolios:
    dated_portfolios = portfolios
```

## Behavior

| Scenario | Before | After |
|----------|--------|-------|
| PAR for 2026-05-29 created today | `latest_upload_date: 2026-05-29` | `latest_upload_date: 2026-06-14` |
| CONCENTRATED_ALPHA entry present | `latest_upload_date: CONCENTRATED_ALPHA` | `latest_upload_date: 2026-06-14` |
| Two PARs same date, different created_at | First created wins | Latest created wins (correct tiebreaker) |

## Live Verification

```
Before fix: latest_upload_date = 2026-05-29 (or CONCENTRATED_ALPHA)
After fix:  latest_upload_date = 2026-06-14  ✓
            latest_par         = PAR-20260614-3A8B91DB  ✓
```

## Constraints

- No API contract change: field names and structure unchanged
- `total_sih_analyses_captured` still includes all 242 PARs (CONCENTRATED_ALPHA counted but not used for date selection)
- `latest_mandate` still reads from the selected PAR's `run_metadata.json`
