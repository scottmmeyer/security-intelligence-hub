# REFRESH-HEALTH-02A Part F - Refresh Timeline Reconstruction

Date: 2026-06-17
Timezone basis: local filesystem times + UTC run metadata where present

## ESS Timeline

1. File staged (source presence)
- incoming/ess/starmine/EquitySummaryScores-17Jun2026.csv mtime: 05:54:37
- incoming/ess/non_starmine_zacks/non-ess.csv mtime: 07:04:22 (current file instance)

2. Intake started / partitions written
- intake-20260617-060959-starmine -> partition mtime 06:10:00 (source_file EquitySummaryScores-17Jun2026.csv, rows 2492)
- intake-20260617-061018-noness -> partition mtime 06:10:18 (source_file non-ess.csv, rows 309)

3. Merge completed
- data/current/signal_snapshot.csv mtime 06:10:18

4. Warning generated
- data/current/ess_coverage_warning.json mtime 06:02:42
- This predates the 06:10 ESS merge sequence; warning is stale relative to latest merged signal state.

5. Overlays regenerated
- PAR-20260617-001280E0/security_overlays.csv mtime 06:30:39
- PAR-20260617-001280E0/run_metadata.json created_at_utc 2026-06-17T11:30:11.238946+00:00

6. API payload generated
- run_outcome_ui computes /api/signal-status dynamically from current files at request time.
- last_signal_refresh_report.json mtime 06:39:18 indicates refresh-report update event (provider-level).

7. Dashboard loaded
- UI consumes /api/signal-status and render logic in ui/outcome_visualization/app.js; rendered values follow artifact/API state.

## Zacks Timeline

1. Latest provider artifact
- data/signals/zacks/latest_zacks.csv mtime 2026-06-16 16:34:09
- top-of-file sourced_date values are 2026-06-16

2. Refresh orchestration report
- data/current/last_signal_refresh_report.json mtime 2026-06-17 06:39:18
- zacks triggered=false, state=RESEARCH_FRESH_COMPLIANT, covered_today=0, covered_within_threshold=24

3. API payload generation
- /api/signal-status sets zacks sourced_date from latest_zacks.csv and stale boolean vs today.
- holdings coverage metrics computed separately from summarize_holdings_coverage(threshold_days=2).

4. Dashboard render
- Top pill shows stale from sourced_date day mismatch.
- Coverage panel shows COMPLIANT due to within-threshold holdings coverage.

## Reprocess Move/Archive Events (Operational)

- incoming/ess/_holding created: 06:09:59
- incoming/ess/processed created: 06:10:37
- incoming/ess/processed/20260617-061037 created: 06:10:37
- Transcript evidence shows manual mkdir/mv command created archive layout and moved files.

## Timeline Conclusion

ESS processing and merge occurred at ~06:10, overlays at ~06:30, and refresh report at ~06:39. The ESS warning file remained at ~06:02 and therefore did not track later merged-state updates. Zacks stale/compliant split is timeline-consistent with no 06-17 zacks file update.