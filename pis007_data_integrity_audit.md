# PIS-007 Data Integrity Audit

**Date:** 2026-06-15

---

## Snapshot Registration Consistency

### Duplicate Protection: STRONG

Two layers of protection:

**Layer 1 — `append_portfolio_history()` (storage.py:499)**
```python
if any(str(row.get("snapshot_id", "")) == snapshot.snapshot_id for row in existing_index_rows):
    raise ValueError(
        f"PIS index append blocked: snapshot_id {snapshot.snapshot_id} is already registered in the index."
    )
```
Checks the index before writing. Raises an exception (does not silently skip).

**Layer 2 — `register_portfolio_snapshot_from_sih()` (service.py)**
```python
already_registered = pis_snapshot.snapshot_id in set(summary_before.get("snapshot_ids", []))
if already_registered:
    return PortfolioRegistrationResult(... duplicate=True ...)
```
Checks the snapshot ID before calling `append_portfolio_history`. Returns `duplicate=True` to caller.

**Layer 3 — Partition directory protection (storage.py)**
```python
if storage_paths.partition_dir.exists():
    # Compares existing content; raises if different
    raise ValueError("Immutable PIS partition protection triggered: ...")
```

**Verdict:** Duplicate protection is robust. Three independent checks prevent double-registration.

**Note:** `duplicate_uploads_prevented` in `pis_snapshot_history_health()` is hardcoded to 0. This metric is non-functional but does not affect data integrity.

---

## Snapshot Index Consistency

Current index state:
- **68 entries** in `pis_snapshot_index.csv`
- Dates range: 2026-05-21 through 2026-06-14
- 10 snapshots for May 21/29 (multiple from backfill + new uploads)
- Governance evaluation runs inline from index (not from a separate governance CSV)

**Governance CSV (snapshot_governance.csv)** exists but is NOT the authoritative source for freshness checks. `artifact_freshness.py` evaluates governance inline from `pis_snapshot_index.csv`. This eliminates a stale-governance-file risk class.

---

## Lineage Persistence Consistency

`lineage_records.csv` — last modified 2026-06-14 20:33.

**Write pattern:** `compute_recommendation_lineage()` writes the full lineage output atomically using `_write_rows()` which opens with `mode="w"` (full overwrite). No append. No partial write accumulation.

**Risk:** If the process is killed during a lineage write, the file may be truncated. Next refresh will detect `lineage_is_stale()` and recompute, but the corrupted file will be read by any API calls before the next refresh.

**Mitigation not present:** No temp-file-then-rename atomic write pattern in `_write_rows()`. The function opens directly with `mode="w"`:
```python
with path.open("w", encoding="utf-8", newline="") as handle:
    writer.writeheader()
    writer.writerows(rows)
```

This is a known limitation documented in the codebase patterns.

---

## Attribution Persistence Consistency

Same `_write_rows()` pattern as lineage. Same atomicity concern.

Current state: `attribution_records.csv` last modified 2026-06-14 20:33, consistent with lineage (both from same refresh run).

Attribution has 2 artifacts (`attribution_records.csv`, `attribution_summary.csv`). Both written in the same `compute_performance_attribution()` call. If the call is interrupted between the two writes, the summary would be out of sync with records. Next refresh corrects this.

---

## Historical Data Integrity

### Snapshot Partition Directories

All registered snapshots have corresponding partition directories:
```
data/history/pis/snapshot_date={date}/account_id=PORTFOLIO/snapshot_id={id}/
  portfolio_snapshot.csv
  position_snapshots.csv
```

**Not verified in this audit**: Whether all 68 index entries have physically intact partition directories. A forensic check would require listing all partition dirs and cross-referencing with the index.

### Change Detection Integrity Risk

**Critical finding from refresh failure analysis:** `compute_all_snapshot_changes()` calls `_aggregate_positions()` for each snapshot, which reads `position_snapshots.csv` from the partition directory. If this file is missing or empty:

- `_read_csv_rows()` returns `[]`
- `_aggregate_positions()` returns `({}, 0.0, 0)`
- Change detection treats all prior positions as EXITED
- No error raised

This means a corrupt partition can silently corrupt the entire change detection history. No integrity check exists in the change detection pipeline.

---

## Summary

| Integrity Area | Status | Risk |
|---------------|--------|------|
| Duplicate snapshot protection | STRONG (3 layers) | LOW |
| Snapshot index consistency | GOOD (68 entries, correct dates) | LOW |
| Governance source reliability | GOOD (inline eval, not cached) | LOW |
| Lineage write atomicity | WEAK (direct write, no rename) | MEDIUM |
| Attribution write atomicity | WEAK (direct write, no rename) | MEDIUM |
| Position partition integrity | NOT VERIFIED | MEDIUM |
| Change detection silent corruption | UNMITIGATED | **HIGH** |
| `duplicate_uploads_prevented` metric | BROKEN (always 0) | LOW (metric only, no data impact) |
