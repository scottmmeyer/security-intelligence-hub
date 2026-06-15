# PIS-007A Integrity Design

**Date:** 2026-06-15  
**Remediation:** R1 — Silent change-detection corruption prevention

---

## Problem

`compute_all_snapshot_changes()` calls `_aggregate_positions()` for each canonical snapshot. If `position_snapshots.csv` is missing or empty for a snapshot that has `position_count > 0` in the index, `_aggregate_positions()` returns 0 symbols. The comparison against the prior snapshot then produces EXITED_POSITION records for every prior symbol — silent data corruption with no error.

## Implementation

**File:** `src/pis/change_detection.py`  
**Function:** `compute_all_snapshot_changes()`

Added after loading positions for each pair, before change computation:

```python
integrity_warnings: list[str] = []

for group, loaded_count in ((prior, prior_positions), (current, current_positions)):
    for index_row in group.rows:
        expected = _to_int(index_row.get("position_count", 0))
        if expected > 0 and loaded_count == 0:
            sid = str(index_row.get("snapshot_id", group.snapshot_date))
            integrity_warnings.append(
                f"INTEGRITY_WARNING: snapshot {sid} ({group.snapshot_date}) "
                f"expected {expected} positions but 0 were loaded from disk. "
                "Skipping this snapshot pair to prevent silent change-detection corruption."
            )

if integrity_warnings and any(snapshot_id in w for w in integrity_warnings):
    # Skip pair; record zero-change summary
    all_summaries.append({...zero counts...})
    continue
```

Return value includes `integrity_warnings` key when any warnings were generated:
```python
result["integrity_warnings"] = integrity_warnings
```

## Behavior

| Condition | Behavior |
|-----------|---------|
| expected > 0, loaded = 0 | Warning emitted; snapshot pair skipped |
| expected = 0, loaded = 0 | No warning; normal processing |
| expected > 0, loaded > 0 | Normal processing |
| expected = 0, loaded > 0 | Normal processing (impossible in practice) |

## Constraints Preserved

- No modification to `_aggregate_positions()` signature
- No modification to any other caller
- Change records and summary are written normally for clean pairs
- Return dict structure extended (backward-compatible; `integrity_warnings` key only present when non-empty)
