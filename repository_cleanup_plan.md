# Repository Cleanup Plan

## Scope

Repository stabilization and release preparation for PIS Foundation before `PERFORMANCE-ATTRIBUTION-01`.

## Phase A - Hygiene Cleanup Results

- Removed temporary scratch artifacts:
  - `.pra_impl_01_body.md`
  - `.pra_impl_02_body.md`
  - `.pra_impl_03_body.md`
  - `.pra_impl_04_body.md`
  - `.pra_impl_05_body.md`
  - `.pra_impl_06_body.md`
- Added `.gitignore` rules:
  - `.pra_impl_*body.md`
  - `.pra_impl*.md`
- Verified no additional temporary/cache artifacts are currently present in dirty status.

## Post-Cleanup Dirty Totals

- Total dirty files: `126`
- Modified: `17`
- Untracked: `109`

Inventory note:
- The categorized inventory below is the post-cleanup baseline captured before creating this release-preparation document set.
- This pass adds four planning docs (`repository_cleanup_plan.md`, `commit_staging_plan.md`, `documentation_consolidation_plan.md`, `pis_foundation_release_assessment.md`) and updates `final_verdict.md`, so live dirty count increases afterward.

## Phase B - Final Categorized Inventory

Classification buckets:
1. PIS Foundation
2. Signal Coverage / Refresh
3. Generated Artifact
4. Documentation Draft
5. Temporary / Ignore

### 1) PIS Foundation (75)

- `M` | `.gitignore`
- `M` | `scripts/run_outcome_ui.py`
- `??` | `canonical_recompute_assessment.md`
- `??` | `canonical_selection_algorithm.md`
- `??` | `canonical_validation.md`
- `??` | `change_detection_algorithm.md`
- `??` | `change_detection_validation.md`
- `??` | `dashboard_kpi_model.md`
- `??` | `dashboard_status_model.md`
- `??` | `docs/pis-001/benchmark_integration_assessment.md`
- `??` | `docs/pis-001/change_detection_design.md`
- `??` | `docs/pis-001/decision_lineage_framework.md`
- `??` | `docs/pis-001/fidelity_portfolio_file_inventory.md`
- `??` | `docs/pis-001/final_verdict.md`
- `??` | `docs/pis-001/missing_information_queue_design.md`
- `??` | `docs/pis-001/phased_implementation_roadmap.md`
- `??` | `docs/pis-001/pis_api_contract.md`
- `??` | `docs/pis-001/pis_architecture_overview.md`
- `??` | `docs/pis-001/pis_dashboard_design.md`
- `??` | `docs/pis-001/pis_ui_phase1_completion.md`
- `??` | `docs/pis-001/portfolio_snapshot_schema.md`
- `??` | `docs/pis-001/screenshots/pis_dashboard_phase1.png`
- `??` | `docs/pis-001/screenshots/sih_to_pis_navigation.png`
- `??` | `docs/pis-001a/completion_report.md`
- `??` | `docs/pis-001a/failure_isolation_assessment.md`
- `??` | `docs/pis-001a/idempotency_assessment.md`
- `??` | `docs/pis-001a/pis_snapshot_registration_design.md`
- `??` | `docs/pis-001a/upload_lifecycle_trace.md`
- `??` | `docs/pis-planning/pis_data_ownership_model.md`
- `??` | `docs/pis-planning/pis_final_architecture_recommendation.md`
- `??` | `docs/pis-planning/pis_navigation_and_ui_model.md`
- `??` | `docs/pis-planning/pis_phase1_implementation_plan.md`
- `??` | `docs/pis-planning/pis_phase_validation.md`
- `??` | `docs/pis-planning/pis_repository_architecture.md`
- `??` | `docs/pis-planning/pis_risk_assessment.md`
- `??` | `docs/pis-planning/pis_storage_strategy.md`
- `??` | `governance_validation.md`
- `??` | `lineage_confidence_model.md`
- `??` | `lineage_matching_algorithm.md`
- `??` | `lineage_validation.md`
- `??` | `loading_state_validation.md`
- `??` | `migration_feasibility_assessment.md`
- `??` | `pis_004a_governance_design.md`
- `??` | `pis_004b_canonical_selection_design.md`
- `??` | `pis_backfill_design.md`
- `??` | `pis_change_detection_design.md`
- `??` | `pis_ui_02_loading_states_design.md`
- `??` | `pis_ui_03_executive_dashboard_design.md`
- `??` | `portfolio_manager_history_inventory.md`
- `??` | `portfolio_manager_to_pis_mapping.md`
- `??` | `progressive_rendering_strategy.md`
- `??` | `recommendation_lineage_design.md`
- `??` | `scripts/backfill_pis_snapshots.py`
- `??` | `snapshot_governance_rules.md`
- `??` | `src/pis/__init__.py`
- `??` | `src/pis/canonical_daily.py`
- `??` | `src/pis/change_detection.py`
- `??` | `src/pis/governance.py`
- `??` | `src/pis/ingestion.py`
- `??` | `src/pis/models.py`
- `??` | `src/pis/recommendation_lineage.py`
- `??` | `src/pis/service.py`
- `??` | `src/pis/storage.py`
- `??` | `summary_card_specification.md`
- `??` | `tests/test_pis_backfill_01.py`
- `??` | `tests/test_pis_canonical_daily_004b.py`
- `??` | `tests/test_pis_change_detection_phase1.py`
- `??` | `tests/test_pis_governance_stage_a.py`
- `??` | `tests/test_pis_phase1.py`
- `??` | `tests/test_pis_recommendation_lineage_01.py`
- `??` | `tests/test_pis_ui_phase1_dashboard.py`
- `??` | `ui/pis_dashboard/README.md`
- `??` | `ui/pis_dashboard/app.js`
- `??` | `ui/pis_dashboard/index.html`
- `??` | `ux_validation.md`

### 2) Signal Coverage / Refresh (28)

- `M` | `scripts/refresh_portfolio_signals.py`
- `M` | `scripts/refresh_signals.py`
- `M` | `src/portfolio/runner.py`
- `M` | `src/scoring/fetch_danelfin_scores.py`
- `M` | `src/scoring/fetch_yahoo_supplemental.py`
- `M` | `src/scoring/fetch_zacks_scores.py`
- `??` | `coverage_aware_refresh_design.md`
- `??` | `coverage_panel_design.md`
- `??` | `coverage_repair_retry_design.md`
- `??` | `coverage_ui_completion.md`
- `??` | `historical_coverage_analysis.md`
- `??` | `holdings_baseline_unification.md`
- `??` | `holdings_coverage_reconciliation.md`
- `??` | `operational_refresh_enforcement.md`
- `??` | `provider_applicability_model.md`
- `??` | `provider_retry_semantics.md`
- `??` | `refresh_eligibility_model.md`
- `??` | `refresh_status_api_design.md`
- `??` | `resume_checkpoint_repair_audit.md`
- `??` | `signal_coverage_03_completion.md`
- `??` | `signal_freshness_model_assessment.md`
- `??` | `signal_status_model_split.md`
- `??` | `src/portfolio/holdings_coverage.py`
- `??` | `targeted_refresh_strategy.md`
- `??` | `tests/test_signal_coverage_phase3.py`
- `??` | `tests/test_signal_coverage_phase5.py`
- `??` | `tests/test_signal_coverage_phase6.py`
- `??` | `tests/test_signal_coverage_phase7.py`

### 3) Generated Artifact (9)

- `M` | `docs/performance-attribution/final_verdict.md`
- `M` | `refresh_execution_audit.md`
- `??` | `final_verdict.md`
- `??` | `refresh_button_trace.md`
- `??` | `refresh_execution_trace.md`
- `??` | `refresh_runtime_evidence.md`
- `??` | `regression_results.md`
- `??` | `ui_refresh_state_assessment.md`
- `??` | `ui_refresh_truthfulness_assessment.md`

### 4) Documentation Draft (14)

- `M` | `docs/governance/backlog/initial_issue_backlog.md`
- `M` | `docs/governance/backlog/roadmap_recommendation.md`
- `M` | `docs/governance/governance_cleanup_report.md`
- `M` | `ui/outcome_visualization/app.js`
- `M` | `ui/outcome_visualization/index.html`
- `M` | `ui/portfolio_alignment/app.js`
- `M` | `ui/portfolio_alignment/index.html`
- `??` | `docs/performance-attribution/attribution_methodology_assessment.md`
- `??` | `docs/performance-attribution/concentrated_alpha_performance_framework.md`
- `??` | `docs/performance-attribution/fidelity_performance_inventory.md`
- `??` | `docs/performance-attribution/performance_dashboard_design.md`
- `??` | `hardcoded_portfolio_membership_audit.md`
- `??` | `recommended_migration_strategy.md`
- `??` | `snapshot_comparison_model.md`

### 5) Temporary / Ignore (0)

- none

## Files That Should Not Be Committed in PIS Foundation Baseline

- Entire `Signal Coverage / Refresh` bucket.
- Entire `Documentation Draft` bucket unrelated to PIS foundation scope.
- `Generated Artifact` bucket unless intentionally publishing evidence snapshots.

## Generated Outputs Recommended for Regeneration (Not Versioned)

- `refresh_execution_audit.md`
- `refresh_button_trace.md`
- `refresh_execution_trace.md`
- `refresh_runtime_evidence.md`
- `ui_refresh_state_assessment.md`
- `ui_refresh_truthfulness_assessment.md`
- `regression_results.md` (if CI/reporting pipeline can regenerate)
- `docs/pis-001/screenshots/pis_dashboard_phase1.png`
- `docs/pis-001/screenshots/sih_to_pis_navigation.png`
