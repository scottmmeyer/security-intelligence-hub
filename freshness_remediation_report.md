# Freshness Remediation Report
**Phase:** 22D.2 — Workstream D  
**Reference Date:** 2026-06-01  
**Status:** COMPLETE  

---

## Finding Addressed

**Phase 22D.1 Finding:** `_sourced_date()` in `scripts/run_outcome_ui.py` returned
the **first** non-empty `sourced_date` value from a CSV, not the most recent.
For files where the oldest rows appear first, this would report a stale date
to the `/api/signal-status` endpoint, causing the UI freshness indicators to
show an older (potentially STALE or CRITICAL) status when the actual data is
more recent.

**Confirmed Provider Freshness (reference date 2026-06-01):**

| Provider | sourced_date | Age | Status |
|----------|-------------|-----|--------|
| ESS | 2026-06-01 | 0d | FRESH |
| Zacks | 2026-06-01 | 0d | FRESH |
| Danelfin | 2026-05-29 | 3d | WARNING |
| Yahoo | 2026-05-29 | 3d | WARNING |

The latent bug was confirmed but not actively causing wrong output for Danelfin
and Yahoo (single-sourced_date files) or ESS/Zacks (correctly handled by
`runner.py` using `max(dates)` separately). However, the bug was a correctness
defect that would surface for any multi-row signal file where rows are not
date-sorted descending.

---

## Change Made

### `scripts/run_outcome_ui.py` — `_sourced_date()`

**Before:**
```python
def _sourced_date(csv_path: Path) -> str | None:
    """Return the first sourced_date value found in csv_path, or None."""
    if not csv_path.exists():
        return None
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                val = str(row.get("sourced_date", "")).strip()
                if val:
                    return val   # ← returned first non-empty, not max
    except Exception:
        pass
    return None
```

**After:**
```python
def _sourced_date(csv_path: Path) -> str | None:
    """Return the maximum sourced_date value found in csv_path, or None."""
    if not csv_path.exists():
        return None
    try:
        latest: str | None = None
        with csv_path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                val = str(row.get("sourced_date", "")).strip()
                if val and (latest is None or val > latest):
                    latest = val
        return latest
    except Exception:
        pass
    return None
```

String comparison of ISO-8601 dates (YYYY-MM-DD) is lexicographically equivalent
to chronological comparison — no datetime parsing required.

---

## Acceptance Criteria Verification

| ID | Criterion | Result |
|----|-----------|--------|
| AC-D1 | `_sourced_date()` returns max date for unsorted CSV | PASS — smoke test verified with rows ordered 2026-05-25, 2026-05-29, 2026-05-27 → returns 2026-05-29 |
| AC-D2 | No change to UI freshness thresholds | PASS — thresholds (≤2d FRESH / ≤5d WARNING / ≤10d STALE / >10d CRITICAL) unchanged |
| AC-D3 | `runner.py` `_build_signal_source_metadata()` unaffected | PASS — that function already used `max(dates)`; no change needed |

---

## Design Notes

- The function reads all rows before returning, a slight change from the original early-return pattern. For signal CSV files (hundreds to low thousands of rows) this is negligible.
- No change to the `/api/signal-status` endpoint logic or response schema.
