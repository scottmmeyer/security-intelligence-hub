# REFRESH-HEALTH-02A Part D - ESS Warning Post-Reprocess Audit

Date: 2026-06-17
Scope: Artifact vs API vs UI consistency after reprocess

## Evidence

1. Warning artifact metadata:
- data/current/ess_coverage_warning.json mtime: 2026-06-17 06:02:42 local
- Content includes legacy fields/wording:
  - warning_count: 55
  - summary_message: "ESS Coverage Warning - 55 holdings absent from latest ESS file. Examples: MU, FIS, VRT"
  - No true_missing_count/stale_coverage_count/no_fresh_starmine_count keys present

2. Reprocess event timings:
- intake-20260617-060959-starmine partition mtime: 06:10:00
- intake-20260617-061018-noness partition mtime: 06:10:18
- data/current/signal_snapshot.csv mtime: 06:10:18

3. Merged state content contradicts warning examples:
- data/current/signal_snapshot.csv contains MU/FIS/VRT as STARMINE_COVERED from intake-20260617-060959-starmine.

4. API behavior:
- scripts/run_outcome_ui.py reads ess_coverage_warning.json directly.
- API payload from _signal_status() reports:
  - coverage_warning_count: 55
  - coverage_warning_examples: MU,FIS,VRT
  - coverage_true_missing_count: 0
  - coverage_stale_count: 0
  - coverage_no_fresh_starmine_count: 0
  - coverage_warning_message: legacy "holdings absent" string
- The zero category counts occur because new keys are missing in stale artifact and default to 0 in API mapping.

5. UI behavior:
- ui/outcome_visualization/app.js renders ESS warning from API fields (new wording template).
- ui/portfolio_alignment/app.js renders meta.ess_coverage_warning directly and would display category counts from payload if present.
- No evidence UI is independently calculating warnings; UI is rendering stale API/artifact state.

## Artifact/API/UI Comparison

| Layer | Observed State | Semantic Version | Stale? |
|---|---|---|---|
| Artifact (ess_coverage_warning.json) | 55 warnings, legacy "holdings absent" wording, no new category keys | Legacy | Yes |
| API (/api/signal-status via run_outcome_ui) | Returns warning_count/examples from stale artifact; new category fields default to 0 | Mixed/derived from stale artifact | Yes |
| UI (outcome/portfolio alignment) | Renders what API/artifact provide; does not recompute | Current renderer over stale payload | Not source of staleness |

## Direct Answers

1. Was ess_coverage_warning.json regenerated after reprocessing?
- No. Its mtime predates reprocess partitions and merged snapshot.

2. Does it contain the new semantic structure?
- No.

3. Does it still contain legacy "holdings absent" wording?
- Yes.

4. Is API returning new data?
- Partially only in schema projection, but values are stale because source artifact is stale.

5. Is UI rendering old data?
- Yes, because API/artifact are stale. UI logic itself is not the root cause.

## Part D Conclusion

Stale state is at the artifact generation layer (ess_coverage_warning.json), propagating into API and then UI. This is not a front-end recomputation defect.