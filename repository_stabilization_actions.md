# Repository Stabilization Actions

## Action Summary

- ARCHIVE: 2
- DEFER: 100
- DELETE: 11

## Per-File Actions

| File | Classification | Action | Rationale |
|---|---|---|---|
| .gitignore | Future Work | DEFER | Cross-stream repository policy update; decide in dedicated cleanup commit. |
| docs/governance/backlog/initial_issue_backlog.md | Documentation Draft | DEFER | Documentation/process draft for consolidation stream. |
| docs/governance/backlog/roadmap_recommendation.md | Documentation Draft | DEFER | Documentation/process draft for consolidation stream. |
| docs/governance/governance_cleanup_report.md | Documentation Draft | DEFER | Documentation/process draft for consolidation stream. |
| docs/performance-attribution/final_verdict.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| refresh_execution_audit.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| scripts/refresh_portfolio_signals.py | Signal Coverage / Refresh | DEFER | Implementation code/tests for refresh stream; isolate and commit separately. |
| scripts/refresh_signals.py | Signal Coverage / Refresh | DEFER | Implementation code/tests for refresh stream; isolate and commit separately. |
| src/scoring/fetch_danelfin_scores.py | Signal Coverage / Refresh | DEFER | Implementation code/tests for refresh stream; isolate and commit separately. |
| src/scoring/fetch_yahoo_supplemental.py | Signal Coverage / Refresh | DEFER | Implementation code/tests for refresh stream; isolate and commit separately. |
| src/scoring/fetch_zacks_scores.py | Signal Coverage / Refresh | DEFER | Implementation code/tests for refresh stream; isolate and commit separately. |
| tests/test_pis_ui_phase1_dashboard.py | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| ui/outcome_visualization/app.js | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| ui/outcome_visualization/index.html | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| ui/pis_dashboard/app.js | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| ui/pis_dashboard/index.html | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| ai003_commit_report.md | Temporary | DELETE | Process/checkpoint artifact; safe to remove after summary extraction. |
| ai003_commit_validation.md | Temporary | DELETE | Process/checkpoint artifact; safe to remove after summary extraction. |
| ai003_regression_report.md | Temporary | DELETE | Process/checkpoint artifact; safe to remove after summary extraction. |
| ai003_staging_report.md | Temporary | DELETE | Process/checkpoint artifact; safe to remove after summary extraction. |
| attribution_readiness_assessment.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| attribution_start_gate.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| attribution_validation.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| benchmark_engine_reuse_assessment.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| closure_commit_report.md | Temporary | DELETE | Process/checkpoint artifact; safe to remove after summary extraction. |
| closure_inventory_validation.md | Temporary | DELETE | Process/checkpoint artifact; safe to remove after summary extraction. |
| closure_test_results.md | Temporary | DELETE | Process/checkpoint artifact; safe to remove after summary extraction. |
| commit_execution_report.md | Temporary | DELETE | Process/checkpoint artifact; safe to remove after summary extraction. |
| commit_staging_plan.md | Temporary | DELETE | Process/checkpoint artifact; safe to remove after summary extraction. |
| coverage_aware_refresh_design.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| coverage_panel_design.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| coverage_repair_retry_design.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| coverage_ui_completion.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| docs/performance-attribution/attribution_methodology_assessment.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| docs/performance-attribution/concentrated_alpha_performance_framework.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| docs/performance-attribution/fidelity_performance_inventory.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| docs/performance-attribution/performance_dashboard_design.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| docs/pis-001/benchmark_integration_assessment.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001/change_detection_design.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001/decision_lineage_framework.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001/fidelity_portfolio_file_inventory.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001/final_verdict.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001/missing_information_queue_design.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001/phased_implementation_roadmap.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001/pis_api_contract.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001/pis_architecture_overview.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001/pis_dashboard_design.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001/pis_ui_phase1_completion.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001/portfolio_snapshot_schema.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001/screenshots/pis_dashboard_phase1.png | Generated Artifact | ARCHIVE | Binary validation artifact; move to archive/LFS and exclude from active dev diff. |
| docs/pis-001/screenshots/sih_to_pis_navigation.png | Generated Artifact | ARCHIVE | Binary validation artifact; move to archive/LFS and exclude from active dev diff. |
| docs/pis-001a/completion_report.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001a/failure_isolation_assessment.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001a/idempotency_assessment.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001a/pis_snapshot_registration_design.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-001a/upload_lifecycle_trace.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-planning/pis_data_ownership_model.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-planning/pis_final_architecture_recommendation.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-planning/pis_navigation_and_ui_model.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-planning/pis_phase1_implementation_plan.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-planning/pis_phase_validation.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-planning/pis_repository_architecture.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-planning/pis_risk_assessment.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| docs/pis-planning/pis_storage_strategy.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| documentation_consolidation_plan.md | Documentation Draft | DEFER | Documentation/process draft for consolidation stream. |
| foundation_release_tag_report.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| hardcoded_portfolio_membership_audit.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| historical_coverage_analysis.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| holdings_baseline_unification.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| holdings_coverage_reconciliation.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| issue_50_rescope_recommendation.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| migration_feasibility_assessment.md | Documentation Draft | DEFER | Documentation/process draft for consolidation stream. |
| operational_refresh_enforcement.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| outcome_classification_model.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| performance_attribution_acceptance_audit.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| performance_attribution_design.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| pis_backfill_design.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| pis_closure_01_report.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| pis_foundation_release_assessment.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| pis_foundation_reproducibility_assessment.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| portfolio_manager_history_inventory.md | Documentation Draft | DEFER | Documentation/process draft for consolidation stream. |
| portfolio_manager_to_pis_mapping.md | Documentation Draft | DEFER | Documentation/process draft for consolidation stream. |
| post_attribution_roadmap.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| post_commit_audit.md | Temporary | DELETE | Process/checkpoint artifact; safe to remove after summary extraction. |
| pre_commit_validation.md | Temporary | DELETE | Process/checkpoint artifact; safe to remove after summary extraction. |
| provider_applicability_model.md | PRA-IMPL-02 | DEFER | PRA-IMPL-02 planning artifacts pending implementation scope finalization. |
| provider_retry_semantics.md | PRA-IMPL-02 | DEFER | PRA-IMPL-02 planning artifacts pending implementation scope finalization. |
| recommendation_outcome_framework.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| recommended_migration_strategy.md | Documentation Draft | DEFER | Documentation/process draft for consolidation stream. |
| refresh_button_trace.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| refresh_eligibility_model.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| refresh_execution_trace.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| refresh_runtime_evidence.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| refresh_status_api_design.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| repository_cleanliness_audit.md | Documentation Draft | DEFER | Documentation/process draft for consolidation stream. |
| repository_cleanup_plan.md | Documentation Draft | DEFER | Documentation/process draft for consolidation stream. |
| reproducibility_validation.md | Documentation Draft | DEFER | Documentation/process draft for consolidation stream. |
| resume_checkpoint_repair_audit.md | PIS Foundation | DEFER | PIS foundation architecture/validation material; keep grouped as foundation stream. |
| signal_coverage_03_completion.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| signal_freshness_model_assessment.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| signal_status_model_split.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| snapshot_comparison_model.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| src/pis/performance_attribution.py | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| src/portfolio/holdings_coverage.py | Signal Coverage / Refresh | DEFER | Implementation code/tests for refresh stream; isolate and commit separately. |
| targeted_refresh_strategy.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| tests/test_pis_performance_attribution_01.py | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| tests/test_signal_coverage_phase3.py | Signal Coverage / Refresh | DEFER | Implementation code/tests for refresh stream; isolate and commit separately. |
| tests/test_signal_coverage_phase5.py | Signal Coverage / Refresh | DEFER | Implementation code/tests for refresh stream; isolate and commit separately. |
| tests/test_signal_coverage_phase6.py | Signal Coverage / Refresh | DEFER | Implementation code/tests for refresh stream; isolate and commit separately. |
| tests/test_signal_coverage_phase7.py | Signal Coverage / Refresh | DEFER | Implementation code/tests for refresh stream; isolate and commit separately. |
| ui/pis_dashboard/README.md | Benchmark Attribution | DEFER | Benchmark-attribution stream artifacts; keep isolated until scope-complete pass. |
| ui_refresh_state_assessment.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |
| ui_refresh_truthfulness_assessment.md | Signal Coverage / Refresh | DEFER | Design/evidence docs tied to the refresh stream. |

## Action Semantics

- COMMIT: ready as-is for immediate stream-specific commit.
- DEFER: keep in working tree for planned stream execution.
- ARCHIVE: move out of active stream (archive/LFS/docs archive).
- DELETE: remove low-value temporary artifact.
- IGNORE: leave unmodified and intentionally out of stream scope.
