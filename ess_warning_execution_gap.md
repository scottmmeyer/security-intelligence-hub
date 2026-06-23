# ESS-COVERAGE-03 Part B - Warning Execution Gap

Date: 2026-06-17
Scope: Trace where warning regeneration is skipped

## End-to-End Trace

Flow requested:
incoming file -> partition -> merge -> signal_snapshot.csv -> warning generation -> API -> UI

### A. Incoming file
Evidence indicates staged ESS files exist and were processed in prior cycle:
- starmine file: EquitySummaryScores-17Jun2026.csv
- non-ESS file: non-ess.csv

### B. Partition write
New immutable partitions were created for 2026-06-17:
- intake-20260617-060959-starmine (rows 2492; source_file EquitySummaryScores-17Jun2026.csv)
- intake-20260617-061018-noness (rows 309; source_file non-ess.csv)

### C. Merge / signal_snapshot.csv
Merged current snapshot updated:
- data/current/signal_snapshot.csv mtime: 06:10:18
- MU/FIS/VRT present in merged snapshot as STARMINE_COVERED from intake-20260617-060959-starmine.

### D. Warning generation step
Warning artifact did not update:
- data/current/ess_coverage_warning.json mtime: 06:02:42
- Content still legacy wording and stale examples.

### E. API
API reads warning artifact directly:
- scripts/run_outcome_ui.py _load_ess_coverage_warning reads file contents.
- /api/signal-status exposes warning_count/examples from that file.
- Missing new keys in stale file default to zero-count category fields.

### F. UI
UI renders API/metadata payload:
- outcome visualization renders coverage_warning_count/examples and category counts.
- portfolio alignment renders meta.ess_coverage_warning.
- No independent recalculation path in UI.

## Exact Skip Location

Skip occurs inside ESS intake stage lifecycle branch:
- append_signal_snapshots executes before persistence validation (line 219).
- validate_ess_stage_persistence runs (line 250).
- if persistence_result.errors: return FAILED (line 316).
- warning build/write (lines 324 and 331) are never reached in that failure path.

Thus, warning generation is skipped after merge when persistence validator fails.

## Why This Matches Observed Times

Observed timestamps:
- Warning artifact: 06:02
- Latest merge: 06:10
- Latest overlays: 06:30

This sequence is consistent with:
1. Later merge succeeded/was written.
2. Warning write step did not execute in that run.
3. Downstream portfolio run consumed updated snapshot but stale warning file persisted.

## Part B Conclusion

The execution gap is a lifecycle-gating gap in ESS intake stage: warning generation is downstream of a failure-return branch, while merge is upstream. Therefore merge updates can outpace warning artifact regeneration.