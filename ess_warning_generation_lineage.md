# ESS-COVERAGE-03 Part A - Warning Generation Lineage

Date: 2026-06-17
Scope: Ownership and lifecycle of ess_coverage_warning.json generation

## 1) Component Ownership

The warning artifact is owned by the ESS intake stage.

Primary code path:
- src/pipeline/stages/ess_intake_stage.py imports warning builder/writer at line 23.
- src/pipeline/stages/ess_intake_stage.py invokes build_ess_coverage_gap_warning at line 324.
- src/pipeline/stages/ess_intake_stage.py invokes write_ess_coverage_warning at line 331.

Artifact writer function:
- src/portfolio/ess_coverage.py defines write_ess_coverage_warning at line 167.

## 2) When It Is Expected to Run

Expected runtime event: during execute_ess_intake_stage after successful persistence validation.

Observed stage ordering (current):
1. append_signal_snapshots runs (merge may already be updated) at line 219.
2. validate_ess_stage_persistence runs at line 250.
3. If persistence_result.errors is true, stage returns FAILED at line 316.
4. Warning build/write happens only after that branch, at lines 324 and 331.

Therefore, warning generation is not attached to "merge completed"; it is attached to "stage passed persistence gate".

## 3) Invoker Code Path

Only runtime owner in pipeline stage:
- src/pipeline/stages/ess_intake_stage.py

Consumers (read-only):
- scripts/run_outcome_ui.py reads data/current/ess_coverage_warning.json via _load_ess_coverage_warning (lines 101-105), then maps to /api/signal-status fields (line 412 and line 418).
- src/portfolio/runner.py injects ess_coverage_warning into portfolio metadata at line 1754.
- ui/outcome_visualization/app.js and ui/portfolio_alignment/app.js render warning fields supplied by API/metadata.

## 4) Recent Changes That Altered Execution Order

Historical introduction (SIGNAL-COVERAGE-02):
- Commit 286d6dd introduced warning generation and persisted ess_coverage_warning.json inside ESS intake success path.
- In that commit, warning generation was already coupled to successful intake completion (not independent of persistence errors).

Recent local ESS-COVERAGE-02 semantic changes:
- Warning computation moved from pre-merge to post-merge, but still remains after persistence error gate.
- Uncommitted diff shows build/write shifted to later location in stage; early return on persistence errors remains before warning generation.

Impact:
- Merge can complete, but warning can still remain stale whenever persistence validator fails and triggers early return.

## Part A Conclusion

ess_coverage_warning.json generation is owned by ESS intake stage success flow, not by merge completion. This lifecycle coupling is the direct structural reason stale warning artifacts can persist after successful merged snapshot updates.