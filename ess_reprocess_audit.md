# REFRESH-HEALTH-02A Part A - ESS Reprocess Verification

Date: 2026-06-17
Scope: Forensic verification only (no code changes)

## Evidence Collected

1. 2026-06-17 signal partition runs exist in signal index:
- intake-20260617 (created_at_utc 2026-06-17T11:02:42.320431+00:00, rows 313, source non-ess.csv)
- intake-20260617-060938 (created_at_utc 2026-06-17T11:09:38.940681+00:00, rows 2801, sources EquitySummaryScores-17Jun2026.csv + non-ess.csv)
- intake-20260617-060959-starmine (created_at_utc 2026-06-17T11:10:00.089175+00:00, rows 2492, source EquitySummaryScores-17Jun2026.csv)
- intake-20260617-061018-noness (created_at_utc 2026-06-17T11:10:18.579957+00:00, rows 309, source non-ess.csv)

2. Partition files and merged snapshot mtimes:
- data/history/signals/snapshot_date=2026-06-17/run_id=intake-20260617-060959-starmine/signal_snapshots.csv -> 2026-06-17 06:10:00 local
- data/history/signals/snapshot_date=2026-06-17/run_id=intake-20260617-061018-noness/signal_snapshots.csv -> 2026-06-17 06:10:18 local
- data/current/signal_snapshot.csv -> 2026-06-17 06:10:18 local

3. Source-file evidence from partition contents:
- intake-20260617-060959-starmine contains source_file=EquitySummaryScores-17Jun2026.csv
- intake-20260617-061018-noness contains source_file=non-ess.csv

4. Warning artifact mtime:
- data/current/ess_coverage_warning.json -> 2026-06-17 06:02:42 local

5. Overlay artifact evidence:
- data/portfolio_ingestion/analysis_runs/PAR-20260617-001280E0/run_metadata.json created_at_utc=2026-06-17T11:30:11.238946+00:00
- data/portfolio_ingestion/analysis_runs/PAR-20260617-001280E0/security_overlays.csv mtime=2026-06-17 06:30:39 local

## Verification Answers

1. Were the manually re-staged ESS files detected?
- Yes, at least one re-stage cycle was detected and ingested (starmine and non-ess both appear in 06:09-06:10 run set).

2. Was a new intake run created?
- Yes. New run IDs were created on 2026-06-17, including intake-20260617-060959-starmine and intake-20260617-061018-noness.

3. Was a new partition snapshot generated?
- Yes. New immutable partition files were generated under data/history/signals/snapshot_date=2026-06-17/run_id=... for those run IDs.

4. Was signal_snapshot.csv merged again?
- Yes. data/current/signal_snapshot.csv mtime aligns with the non-ess partition completion (06:10:18 local).

5. Was security_overlays.csv regenerated?
- Yes. PAR-20260617-001280E0 overlays were generated later (06:30:39 local), after the 06:10 ESS merge.

6. Was ess_coverage_warning.json regenerated?
- No. Its mtime (06:02:42 local) predates the reprocess partitions and merged snapshot.

## Re-stage Status at Time of Audit

Current intake folder state shows files present again:
- incoming/ess/starmine/EquitySummaryScores-17Jun2026.csv
- incoming/ess/non_starmine_zacks/non-ess.csv

No newer 2026-06-17 run_id appears after intake-20260617-061018-noness in signal_index.csv, so this later restage has not yet produced a new partition/merge cycle.

## Part A Conclusion

Reprocessing did occur (new runs, partitions, and merged snapshot). However, the ESS warning artifact currently served is stale and was not regenerated during that reprocess sequence. This explains why health still reports the old warning narrative/count structure.