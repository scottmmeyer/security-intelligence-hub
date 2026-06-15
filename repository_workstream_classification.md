# Repository Workstream Classification

**Date:** 2026-06-14  
**Branch:** stream/benchmark-attribution-01b  
**Total files classified:** 174

---

## Classification Key

| Workstream | Code |
|-----------|------|
| PIS-005 Refresh Orchestration | PIS-005 |
| Benchmark Attribution (01B) | BENCH |
| Performance Attribution (01B foundations) | PERF-ATTR |
| PRA-IMPL-02 / 02A | PRA |
| Signal Coverage / Refresh | SIG-COV |
| AI-003 Explainability | AI-003 |
| PIS Forensic Investigation | PIS-FORENSIC |
| Repository Governance | REPO-GOV |
| Generated Artifacts / Orphaned Docs | GEN-ART |

---

## PIS-005 — Refresh Orchestration (17 files)

### Source Code (2 new)
- `src/pis/artifact_freshness.py`
- `src/pis/refresh_orchestrator.py`

### Modified (1)
- `scripts/run_outcome_ui.py` — adds 3 PIS-005 endpoints + startup trigger

### Design + Audit Documents (8)
- `artifact_dependency_graph.md`
- `refresh_orchestration_design.md`
- `refresh_orchestration_final_verdict.md`
- `refresh_trigger_validation.md`
- `pis005_acceptance_audit.md`
- `pis005_commit_manifest.md`
- `pis005_final_verdict.md`
- `pis005_regression_surface_review.md`

### Supporting Investigation Documents (6)
- `attribution_refresh_trace.md`
- `canonical_vs_lineage_alignment.md`
- `dashboard_data_source_audit.md`
- `lineage_candidate_trace.md`
- `lineage_refresh_trigger_audit.md`
- `par_inventory_audit.md`

---

## BENCH — Benchmark Attribution 01B (48 files)

### Source Code (2 new)
- `src/pis/benchmark_attribution.py`
- `src/pis/performance_attribution.py`

### Test Files (2 new)
- `tests/test_pis_benchmark_attribution_01a.py`
- `tests/test_pis_benchmark_attribution_01b.py`
- `tests/test_pis_performance_attribution_01.py`

### UI (3 modified)
- `ui/pis_dashboard/app.js` — benchmark attribution dashboard sections added
- `ui/pis_dashboard/index.html` — benchmark dashboard HTML
- `ui/outcome_visualization/app.js` — benchmark visualization additions
- `ui/outcome_visualization/index.html` — benchmark UI additions
- `ui/pis_dashboard/README.md` — documentation

### Design Documents (26)
- `benchmark_01b_a_implementation_report.md`
- `benchmark_01b_b_validation.md`
- `benchmark_alignment_policy.md`
- `benchmark_attribution_design.md`
- `benchmark_attribution_gap_review.md`
- `benchmark_attribution_staging_manifest.md`
- `benchmark_attribution_validation.md`
- `benchmark_branch_setup_report.md`
- `benchmark_dashboard_design.md`
- `benchmark_dashboard_validation.md`
- `benchmark_engine_reuse_assessment.md`
- `benchmark_final_verdict.md`
- `benchmark_provider_audit.md`
- `benchmark_provider_trace.md`
- `benchmark_quality_final_verdict.md`
- `benchmark_quality_policy.md`
- `benchmark_quality_root_cause.md`
- `benchmark_quality_validation.md`
- `benchmark_rebuild_report.md`
- `benchmark_recommendation_attribution_model.md`
- `benchmark_recommendation_audit.md`
- `benchmark_return_series_audit.md`
- `benchmark_return_series_model.md`
- `benchmark_source_alpha_model.md`
- `benchmark_source_summary_audit.md`
- `benchmark_stream_readiness_verdict.md`
- `source_alpha_validation.md`

### Performance Attribution Foundation Documents (6)
- `docs/performance-attribution/attribution_methodology_assessment.md`
- `docs/performance-attribution/concentrated_alpha_performance_framework.md`
- `docs/performance-attribution/fidelity_performance_inventory.md`
- `docs/performance-attribution/performance_dashboard_design.md`
- `docs/performance-attribution/final_verdict.md` (modified)
- `performance_attribution_acceptance_audit.md`
- `performance_attribution_design.md`
- `recommendation_outcome_framework.md`
- `outcome_classification_model.md`
- `post_attribution_roadmap.md`

---

## PRA — PRA-IMPL-02 / 02A (24 files)

### Source Code (2 new + 5 modified)
- `src/portfolio/cra/funding_policy.py` (new)
- `src/portfolio/cra/capital_source_builder.py` (modified)
- `src/portfolio/cra/models.py` (modified)
- `src/portfolio/cra/rotation_proposal_builder.py` (modified)
- `src/portfolio/models.py` (modified)
- `src/portfolio/recommendations.py` (modified)
- `src/portfolio/runner.py` (modified)

### Test Files (5 new)
- `tests/test_pra_impl_02_funding_policy.py`
- `tests/test_pra_impl_02a_api_contract.py`
- `tests/test_pra_impl_02a_pap_rationale.py`
- `tests/test_pra_impl_02a_serialization_contracts.py`

### Design + Audit Documents (15)
- `pra_impl_02_acceptance_verdict.md`
- `pra_impl_02_behavior_delta.md`
- `pra_impl_02_current_state_audit.md`
- `pra_impl_02_explainability_audit.md`
- `pra_impl_02_funding_source_audit.md`
- `pra_impl_02_funding_trace.md`
- `pra_impl_02_reduction_audit.md`
- `pra_impl_02_test_gap_analysis.md`
- `pra_impl_02_ui_audit.md`
- `pra_impl_02_validation.md`
- `pra_impl_02a_api_contract_validation.md`
- `pra_impl_02a_contract_audit.md`
- `pra_impl_02a_final_verdict.md`
- `pra_impl_02a_funding_depletion_design.md`
- `pra_impl_02a_funding_depletion_validation.md`
- `pra_impl_02a_serialization_validation.md`
- `allocation_reduction_model.md`
- `funding_dashboard_design.md`
- `funding_explainability_model.md`
- `funding_source_policy_model.md`
- `regression_results.md` (modified)
- `refresh_execution_audit.md` (modified)

---

## SIG-COV — Signal Coverage / Refresh (22 files)

### Source Code (2 new + 3 modified)
- `src/portfolio/holdings_coverage.py` (new)
- `scripts/refresh_signals.py` (modified — adds coverage-aware refresh)
- `scripts/refresh_portfolio_signals.py` (modified)
- `src/scoring/fetch_danelfin_scores.py` (modified)
- `src/scoring/fetch_yahoo_supplemental.py` (modified)
- `src/scoring/fetch_zacks_scores.py` (modified)

### Test Files (4 new)
- `tests/test_signal_coverage_phase3.py`
- `tests/test_signal_coverage_phase5.py`
- `tests/test_signal_coverage_phase6.py`
- `tests/test_signal_coverage_phase7.py`

### Design Documents (12)
- `coverage_aware_refresh_design.md`
- `coverage_panel_design.md`
- `coverage_repair_retry_design.md`
- `coverage_ui_completion.md`
- `hardcoded_portfolio_membership_audit.md`
- `historical_coverage_analysis.md`
- `holdings_baseline_unification.md`
- `holdings_coverage_reconciliation.md`
- `operational_refresh_enforcement.md`
- `provider_applicability_model.md`
- `provider_retry_semantics.md`
- `refresh_button_trace.md`
- `refresh_eligibility_model.md`
- `refresh_execution_trace.md`
- `refresh_runtime_evidence.md`
- `refresh_status_api_design.md`
- `signal_coverage_03_completion.md`
- `signal_freshness_model_assessment.md`
- `signal_status_model_split.md`
- `spy_coverage_audit.md`
- `targeted_refresh_strategy.md`
- `ui_refresh_state_assessment.md`
- `ui_refresh_truthfulness_assessment.md`

---

## AI-003 — Allocation Explainability (2 files)

### Source Code (1 modified)
- `src/sih/allocation_explainability.py` (modified — already committed at HEAD)

### Documents
- Note: AI-003 is HEAD commit. These modifications are the committed state.

---

## PIS-FORENSIC — PIS Forensic Investigation (18 files)

- `PIS_FORENSIC_INVESTIGATION_INDEX.md`
- `attribution_freshness_audit.md`
- `attribution_readiness_assessment.md`
- `attribution_start_gate.md`
- `attribution_validation.md`
- `cash_vs_spaxx_audit.md`
- `final_verdict.md` (modified)
- `lineage_freshness_audit.md`
- `pis_attr_forensic_01_report.md`
- `pis_attr_forensic_final_verdict.md`
- `pis_closure_01_report.md`
- `pis_foundation_release_assessment.md`
- `pis_foundation_reproducibility_assessment.md`
- `portfolio_manager_history_inventory.md`
- `portfolio_manager_to_pis_mapping.md`
- `recommendation_return_trace.md`
- `reproducibility_validation.md`
- `root_cause_verdict.md`
- `snapshot_comparison_model.md`

---

## REPO-GOV — Repository Governance (13 files)

- `.gitignore` (modified)
- `docs/governance/backlog/initial_issue_backlog.md` (modified)
- `docs/governance/backlog/roadmap_recommendation.md` (modified)
- `docs/governance/governance_cleanup_report.md` (modified)
- `documentation_consolidation_plan.md`
- `foundation_release_tag_report.md`
- `generated_artifact_archive_report.md`
- `next_implementation_recommendation.md`
- `pis_backfill_design.md`
- `repository_cleanliness_audit.md`
- `repository_cleanup_plan.md`
- `repository_stabilization_actions.md`
- `repository_stabilization_inventory.md`
- `workstream_isolation_plan.md`
- `issue_50_rescope_recommendation.md`
- `migration_feasibility_assessment.md`
- `recommended_migration_strategy.md`
- `post_attribution_roadmap.md`

---

## GEN-ART — Generated Artifacts (docs/pis-001, pis-001a, pis-planning) (12 files)

- `docs/pis-001/` (directory + all contents)
- `docs/pis-001a/` (directory + all contents)
- `docs/pis-planning/` (directory)
- `pis_foundation_release_assessment.md`
- `resume_checkpoint_repair_audit.md`

---

## THIS AUDIT — Repository Stabilization (5 files)

- `repository_stabilization_inventory_v2.md` (this file's companion)
- `repository_workstream_classification.md` (this file)
- `workstream_commit_readiness.md` (to be created)
- `generated_artifact_disposition.md` (to be created)
- `documentation_consolidation_v2.md` (to be created)
- `branch_strategy_recommendation.md` (to be created)
- `repository_stabilization_final_verdict.md` (to be created)

---

## Cross-Workstream Contamination Risk

| File | Primary Workstream | Contaminates | Risk |
|------|-------------------|--------------|------|
| `scripts/run_outcome_ui.py` | PIS-005 (168 lines added) | BENCH (dashboard wiring) | MEDIUM — PIS-005 and BENCH additions are in the same file but non-overlapping |
| `ui/pis_dashboard/app.js` | BENCH | PIS-005 dashboard visibility | LOW — PIS-005 visibility relies on endpoints, not frontend |
| `tests/test_pis_ui_phase1_dashboard.py` | BENCH (modified) | PIS-005 | LOW — test expanded, not broken |
| `final_verdict.md` | PIS-FORENSIC (modified) | REPO-GOV | LOW — doc-only |

**Conclusion: No hard code-level cross-contamination. run_outcome_ui.py is the only multi-workstream modified file.**
