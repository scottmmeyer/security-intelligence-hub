# ESS-COVERAGE-02 - MU Lineage Trace

Date: 2026-06-17  
Scope: Full lineage trace across ESS pipeline stages without code changes

## Part A - MU Stage Trace

| Stage | Evidence | MU Status | Notes |
|---|---|---|---|
| 1. Raw incoming ESS file | incoming/ess/processed/20260617-061037/starmine/EquitySummaryScores-17Jun2026.csv (row 2412) and incoming/ess/processed/20260617-061037/non_starmine_zacks/non-ess.csv (row 82) | PRESENT | MU exists in both StarMine and non-ESS source files for this cycle. |
| 2. ESS parser | src/pipeline/stages/ess_intake_stage.py and src/normalize/provider_normalizer.py call chain | PRESENT | No parser rejection observed for MU; row persisted downstream. |
| 3. ESS normalized records | data/history/signals/snapshot_date=2026-06-17/run_id=intake-20260617-060959-starmine/signal_snapshots.csv (MU row) and .../run_id=intake-20260617-061018-noness/signal_snapshots.csv (MU row) | PRESENT (MODIFIED by domain) | StarMine row is STARMINE_COVERED with ESS text; non-ESS row is NON_STARMINE_ANALYST with empty starmine_ess_text. |
| 4. signal_snapshot.csv generation | data/history/signals/.../run_id=intake-20260617-060959-starmine/signal_snapshots.csv | PRESENT | MU written in immutable partition output. |
| 5. signal_snapshot_manager merge logic | data/current/signal_snapshot.csv (MU row, run_id intake-20260617-060959-starmine) | PRESENT | Merge keeps highest-quality symbol row (StarMine-covered with ESS text). MU not lost. |
| 6. security_overlays.csv | data/portfolio_ingestion/analysis_runs/PAR-20260617-001280E0/security_overlays.csv | PRESENT | MU has ess_score_text=VERY_BULLISH and composite score populated. |
| 7. API payload generation | scripts/run_outcome_ui.py: _signal_status() and /api/security-metadata handlers | PRESENT in signal state; WARNING payload still lists MU | API reads ess_coverage_warning.json directly for health panel. |
| 8. Refresh health coverage validator | src/portfolio/ess_coverage.py: build_ess_coverage_gap_warning() | FLAGGED AS MISSING | MU is excluded from incoming_ess_symbols because validator only counts STARMINE_COVERED rows with non-empty starmine_ess_text from current intake run context. |
| 9. Dashboard response | ui/outcome_visualization/app.js and ui/portfolio_alignment/app.js | DISPLAYED AS MISSING | UI faithfully renders warning_count/examples from API payload; no independent symbol loss in UI layer. |

## Key MU Finding

MU does not disappear in ingestion, normalization, partition persistence, merge, or overlay stages.  
MU is present end-to-end in data artifacts, but coverage validator logic still reports MU as absent in the ESS warning payload.

## Part E - FIS / VRT Comparison

| Symbol | Incoming File | Parsed/Partition | Merged Snapshot | Overlays/API Working Set | Validator Warning | Root-Cause Class |
|---|---|---|---|---|---|---|
| MU | Present (StarMine + non-ESS) | Present | Present | Present | Missing | Validator logic false positive |
| VRT | Present (StarMine + non-ESS) | Present | Present | Present | Missing | Validator logic false positive |
| FIS | Present (StarMine) | Present | Present | Not in latest PAR-20260617-001280E0 overlays | Missing | Mixed: validator false positive + current API working-set mismatch |

Conclusion:
- MU and VRT share the same primary root cause (validator comparison logic).
- FIS adds a secondary context mismatch: it appears in warning payload but is not in latest overlay working set currently loaded from PAR-20260617-001280E0.
