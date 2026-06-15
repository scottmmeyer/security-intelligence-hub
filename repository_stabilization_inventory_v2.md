# Repository Stabilization Inventory v2

**Date:** 2026-06-14  
**Branch:** stream/benchmark-attribution-01b  
**HEAD commit:** 18fbbd8 (AI-003: implement deterministic allocation philosophy explainability)  
**Total dirty files:** 174

---

## Counts by Status

| Status | Count |
|--------|-------|
| Modified (` M`) | 27 |
| Untracked (`??`) | 147 |
| Staged modified (`M `) | 0 |
| Deleted | 0 |
| **Total** | **174** |

---

## Modified Files (27)

| # | File | Status |
|---|------|--------|
| 1 | `.gitignore` | ` M` |
| 2 | `docs/governance/backlog/initial_issue_backlog.md` | ` M` |
| 3 | `docs/governance/backlog/roadmap_recommendation.md` | ` M` |
| 4 | `docs/governance/governance_cleanup_report.md` | ` M` |
| 5 | `docs/performance-attribution/final_verdict.md` | ` M` |
| 6 | `final_verdict.md` | ` M` |
| 7 | `refresh_execution_audit.md` | ` M` |
| 8 | `regression_results.md` | ` M` |
| 9 | `scripts/refresh_portfolio_signals.py` | ` M` |
| 10 | `scripts/refresh_signals.py` | ` M` |
| 11 | `scripts/run_outcome_ui.py` | ` M` |
| 12 | `src/portfolio/cra/capital_source_builder.py` | ` M` |
| 13 | `src/portfolio/cra/models.py` | ` M` |
| 14 | `src/portfolio/cra/rotation_proposal_builder.py` | ` M` |
| 15 | `src/portfolio/models.py` | ` M` |
| 16 | `src/portfolio/recommendations.py` | ` M` |
| 17 | `src/portfolio/runner.py` | ` M` |
| 18 | `src/scoring/fetch_danelfin_scores.py` | ` M` |
| 19 | `src/scoring/fetch_yahoo_supplemental.py` | ` M` |
| 20 | `src/scoring/fetch_zacks_scores.py` | ` M` |
| 21 | `src/sih/allocation_explainability.py` | ` M` |
| 22 | `tests/test_pis_ui_phase1_dashboard.py` | ` M` |
| 23 | `ui/outcome_visualization/app.js` | ` M` |
| 24 | `ui/outcome_visualization/index.html` | ` M` |
| 25 | `ui/pis_dashboard/app.js` | ` M` |
| 26 | `ui/pis_dashboard/index.html` | ` M` |
| 27 | `ui/portfolio_alignment/app.js` | ` M` |

---

## Untracked Files (147)

### Root-Level Documents (95)

| # | File |
|---|------|
| 1 | `PIS_FORENSIC_INVESTIGATION_INDEX.md` |
| 2 | `allocation_reduction_model.md` |
| 3 | `artifact_dependency_graph.md` |
| 4 | `attribution_freshness_audit.md` |
| 5 | `attribution_readiness_assessment.md` |
| 6 | `attribution_refresh_trace.md` |
| 7 | `attribution_start_gate.md` |
| 8 | `attribution_validation.md` |
| 9 | `benchmark_01b_a_implementation_report.md` |
| 10 | `benchmark_01b_b_validation.md` |
| 11 | `benchmark_alignment_policy.md` |
| 12 | `benchmark_attribution_design.md` |
| 13 | `benchmark_attribution_gap_review.md` |
| 14 | `benchmark_attribution_staging_manifest.md` |
| 15 | `benchmark_attribution_validation.md` |
| 16 | `benchmark_branch_setup_report.md` |
| 17 | `benchmark_dashboard_design.md` |
| 18 | `benchmark_dashboard_validation.md` |
| 19 | `benchmark_engine_reuse_assessment.md` |
| 20 | `benchmark_final_verdict.md` |
| 21 | `benchmark_provider_audit.md` |
| 22 | `benchmark_provider_trace.md` |
| 23 | `benchmark_quality_final_verdict.md` |
| 24 | `benchmark_quality_policy.md` |
| 25 | `benchmark_quality_root_cause.md` |
| 26 | `benchmark_quality_validation.md` |
| 27 | `benchmark_rebuild_report.md` |
| 28 | `benchmark_recommendation_attribution_model.md` |
| 29 | `benchmark_recommendation_audit.md` |
| 30 | `benchmark_return_series_audit.md` |
| 31 | `benchmark_return_series_model.md` |
| 32 | `benchmark_source_alpha_model.md` |
| 33 | `benchmark_source_summary_audit.md` |
| 34 | `benchmark_stream_readiness_verdict.md` |
| 35 | `canonical_vs_lineage_alignment.md` |
| 36 | `cash_vs_spaxx_audit.md` |
| 37 | `coverage_aware_refresh_design.md` |
| 38 | `coverage_panel_design.md` |
| 39 | `coverage_repair_retry_design.md` |
| 40 | `coverage_ui_completion.md` |
| 41 | `dashboard_data_source_audit.md` |
| 42 | `documentation_consolidation_plan.md` |
| 43 | `foundation_release_tag_report.md` |
| 44 | `funding_dashboard_design.md` |
| 45 | `funding_explainability_model.md` |
| 46 | `funding_source_policy_model.md` |
| 47 | `generated_artifact_archive_report.md` |
| 48 | `hardcoded_portfolio_membership_audit.md` |
| 49 | `historical_coverage_analysis.md` |
| 50 | `holdings_baseline_unification.md` |
| 51 | `holdings_coverage_reconciliation.md` |
| 52 | `issue_50_rescope_recommendation.md` |
| 53 | `lineage_candidate_trace.md` |
| 54 | `lineage_freshness_audit.md` |
| 55 | `lineage_refresh_trigger_audit.md` |
| 56 | `migration_feasibility_assessment.md` |
| 57 | `next_implementation_recommendation.md` |
| 58 | `operational_refresh_enforcement.md` |
| 59 | `outcome_classification_model.md` |
| 60 | `par_inventory_audit.md` |
| 61 | `pending_activity_audit.md` |
| 62 | `performance_attribution_acceptance_audit.md` |
| 63 | `performance_attribution_design.md` |
| 64 | `pis005_acceptance_audit.md` |
| 65 | `pis005_commit_manifest.md` |
| 66 | `pis005_final_verdict.md` |
| 67 | `pis005_regression_surface_review.md` |
| 68 | `pis_attr_forensic_01_report.md` |
| 69 | `pis_attr_forensic_final_verdict.md` |
| 70 | `pis_backfill_design.md` |
| 71 | `pis_closure_01_report.md` |
| 72 | `pis_foundation_release_assessment.md` |
| 73 | `pis_foundation_reproducibility_assessment.md` |
| 74 | `portfolio_manager_history_inventory.md` |
| 75 | `portfolio_manager_to_pis_mapping.md` |
| 76 | `post_attribution_roadmap.md` |
| 77 | `pra_impl_02_acceptance_verdict.md` |
| 78 | `pra_impl_02_behavior_delta.md` |
| 79 | `pra_impl_02_current_state_audit.md` |
| 80 | `pra_impl_02_explainability_audit.md` |
| 81 | `pra_impl_02_funding_source_audit.md` |
| 82 | `pra_impl_02_funding_trace.md` |
| 83 | `pra_impl_02_reduction_audit.md` |
| 84 | `pra_impl_02_test_gap_analysis.md` |
| 85 | `pra_impl_02_ui_audit.md` |
| 86 | `pra_impl_02_validation.md` |
| 87 | `pra_impl_02a_api_contract_validation.md` |
| 88 | `pra_impl_02a_contract_audit.md` |
| 89 | `pra_impl_02a_final_verdict.md` |
| 90 | `pra_impl_02a_funding_depletion_design.md` |
| 91 | `pra_impl_02a_funding_depletion_validation.md` |
| 92 | `pra_impl_02a_serialization_validation.md` |
| 93 | `provider_applicability_model.md` |
| 94 | `provider_retry_semantics.md` |
| 95 | `recommendation_outcome_framework.md` |
| 96 | `recommendation_return_trace.md` |
| 97 | `recommended_migration_strategy.md` |
| 98 | `refresh_button_trace.md` |
| 99 | `refresh_eligibility_model.md` |
| 100 | `refresh_execution_trace.md` |
| 101 | `refresh_orchestration_design.md` |
| 102 | `refresh_orchestration_final_verdict.md` |
| 103 | `refresh_runtime_evidence.md` |
| 104 | `refresh_status_api_design.md` |
| 105 | `refresh_trigger_validation.md` |
| 106 | `repository_cleanliness_audit.md` |
| 107 | `repository_cleanup_plan.md` |
| 108 | `repository_stabilization_actions.md` |
| 109 | `repository_stabilization_inventory.md` |
| 110 | `reproducibility_validation.md` |
| 111 | `resume_checkpoint_repair_audit.md` |
| 112 | `root_cause_verdict.md` |
| 113 | `signal_coverage_03_completion.md` |
| 114 | `signal_freshness_model_assessment.md` |
| 115 | `signal_status_model_split.md` |
| 116 | `snapshot_comparison_model.md` |
| 117 | `source_alpha_validation.md` |
| 118 | `spy_coverage_audit.md` |
| 119 | `targeted_refresh_strategy.md` |
| 120 | `ui_refresh_state_assessment.md` |
| 121 | `ui_refresh_truthfulness_assessment.md` |
| 122 | `workstream_isolation_plan.md` |

### docs/ Subdirectories (3 new dirs)

| # | Path |
|---|------|
| 123 | `docs/pis-001/` (dir — contains 10+ files) |
| 124 | `docs/pis-001a/` (dir — contains 4 files) |
| 125 | `docs/pis-planning/` (dir) |
| 126 | `docs/performance-attribution/attribution_methodology_assessment.md` |
| 127 | `docs/performance-attribution/concentrated_alpha_performance_framework.md` |
| 128 | `docs/performance-attribution/fidelity_performance_inventory.md` |
| 129 | `docs/performance-attribution/performance_dashboard_design.md` |

### Source Files (4 new)

| # | File |
|---|------|
| 130 | `src/pis/artifact_freshness.py` |
| 131 | `src/pis/benchmark_attribution.py` |
| 132 | `src/pis/performance_attribution.py` |
| 133 | `src/pis/refresh_orchestrator.py` |
| 134 | `src/portfolio/cra/funding_policy.py` |
| 135 | `src/portfolio/holdings_coverage.py` |

### Test Files (12 new)

| # | File |
|---|------|
| 136 | `tests/test_pis_benchmark_attribution_01a.py` |
| 137 | `tests/test_pis_benchmark_attribution_01b.py` |
| 138 | `tests/test_pis_performance_attribution_01.py` |
| 139 | `tests/test_pra_impl_02_funding_policy.py` |
| 140 | `tests/test_pra_impl_02a_api_contract.py` |
| 141 | `tests/test_pra_impl_02a_pap_rationale.py` |
| 142 | `tests/test_pra_impl_02a_serialization_contracts.py` |
| 143 | `tests/test_signal_coverage_phase3.py` |
| 144 | `tests/test_signal_coverage_phase5.py` |
| 145 | `tests/test_signal_coverage_phase6.py` |
| 146 | `tests/test_signal_coverage_phase7.py` |

### UI Files (1 new)

| # | File |
|---|------|
| 147 | `ui/pis_dashboard/README.md` |
