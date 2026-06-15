# ESS Intake Ordering — Implementation Notes

**Date:** 2026-06-15  
**Commit:** `bed805a`

---

## Summary

Implemented Option A: merged canonical current-state artifact.

---

## Files Changed

| File | Change |
|------|--------|
| `src/history/signal_snapshot_manager.py` | Added `_build_merged_snapshot()` helper (46 lines); replaced last-write-wins `_write_csv_rows` call with merge-and-write |

---

## Implementation Details

### `_coverage_rank()` helper

Assigns quality rank 3/2/1 to signal rows:
- 3: `coverage_domain == STARMINE_COVERED` AND non-empty `starmine_ess_text`
- 2: non-empty `starmine_ess_text` in any domain
- 1: no ESS text

### `_build_merged_snapshot()` logic

1. Start with `extra_rows` (rows from the current intake call, not yet written to disk)
2. Scan `history_root/snapshot_date={date}/*/signal_snapshots.csv` for all existing partitions
3. For each symbol, keep the highest-rank row (tiebreak: latest `created_at_utc`)
4. Sort output by symbol for deterministic file contents

### Backward Compatibility

- All existing partition write logic unchanged (immutability preserved)
- Signal index unchanged
- All downstream callers of `load_fidelity_signals()` automatically benefit — no callers changed
- ESS coverage gap warning will naturally report fewer false positives once StarMine data is in the merged snapshot

---

## Operational Note

The Jun 15 false coverage warning was caused by the StarMine intake running first (producing `signal_snapshot.csv` with StarMine data) and then the non-StarMine Zacks intake running second (overwriting with non-StarMine only). 

After this fix: if both intakes had run on the same day, the second `append_signal_snapshots()` call would call `_build_merged_snapshot()`, which would scan both partitions and produce a merged artifact containing both StarMine and non-StarMine rows.

**Going forward:** MU, VRT, and NVDA will remain in `signal_snapshot.csv` after non-StarMine Zacks runs.
