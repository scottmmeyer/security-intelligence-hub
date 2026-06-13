# Canonical Recompute Assessment

## Objective
Quantify impact of replacing same-day aggregate analytics with canonical daily selection.

## Timeline Impact
Before (raw same-day sum):
- 2026-06-10: 2312650.93
- 2026-06-11: 921414.22

After (canonical daily):
- 2026-06-10: 463682.30
- 2026-06-11: 455857.04

Interpretation:
- Distortion from same-day snapshot summation is removed.
- Daily values are aligned to expected single-portfolio scale (~450K-500K).

## Change Detection Impact
Aggregated mode:
- change_summary rows: 16
- change_records rows: 1342

Canonical mode:
- change_summary rows: 16
- change_records rows: 1295

Interpretation:
- Same date coverage remains intact.
- Change detail volume is reduced by removing same-day duplicate/intraday aggregation effects.

## Lineage Impact
Aggregated mode:
- lineage_summary rows: 16
- lineage_records rows: 1248

Canonical mode:
- lineage_summary rows: 16
- lineage_records rows: 50

Interpretation:
- Lineage now tracks canonical daily changes rather than inflated same-day aggregate deltas.

## Data Integrity Boundary
Preserved:
- Immutable historical snapshots
- Full 67-row snapshot inventory visibility

Derived-only modifications:
- canonical_daily_snapshots.csv
- recomputed change_records.csv and change_summary.csv from canonical series
- recomputed lineage_records.csv and lineage_summary.csv from canonical change outputs
