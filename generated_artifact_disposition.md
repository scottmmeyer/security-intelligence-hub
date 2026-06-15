# Generated Artifact Disposition

**Date:** 2026-06-14  
**Scope:** Classify all untracked root-level documents and determine versioning disposition

---

## Disposition Key

| Code | Meaning |
|------|---------|
| COMMIT | Version-control as part of the associated workstream commit |
| IGNORE | Add to .gitignore; do not version |
| ARCHIVE | Move to docs/ subdirectory before commit |
| DELETE | Not needed; can be removed safely |

---

## PIS-005 Documents — COMMIT

These are specification, design, validation, and audit documents for PIS-005 and should be committed with the implementation.

| File | Disposition | Reason |
|------|------------|--------|
| `artifact_dependency_graph.md` | COMMIT | PIS-005 design spec |
| `refresh_orchestration_design.md` | COMMIT | PIS-005 design spec |
| `refresh_orchestration_final_verdict.md` | COMMIT | PIS-005 delivery record |
| `refresh_trigger_validation.md` | COMMIT | PIS-005 validation evidence |
| `pis005_acceptance_audit.md` | COMMIT | Acceptance audit record |
| `pis005_commit_manifest.md` | COMMIT | Commit manifest |
| `pis005_final_verdict.md` | COMMIT | Final decision record |
| `pis005_regression_surface_review.md` | COMMIT | Regression audit |
| `attribution_refresh_trace.md` | COMMIT | PIS-005 forensic evidence |
| `canonical_vs_lineage_alignment.md` | COMMIT | PIS-005 forensic evidence |
| `dashboard_data_source_audit.md` | COMMIT | PIS-005 forensic evidence |
| `lineage_candidate_trace.md` | COMMIT | PIS-005 forensic evidence |
| `lineage_refresh_trigger_audit.md` | COMMIT | PIS-005 forensic evidence |
| `par_inventory_audit.md` | COMMIT | PIS-005 forensic evidence |

---

## Benchmark Attribution Documents — COMMIT

| File | Disposition | Reason |
|------|------------|--------|
| `benchmark_01b_a_implementation_report.md` | COMMIT | BENCH delivery record |
| `benchmark_01b_b_validation.md` | COMMIT | BENCH validation |
| `benchmark_alignment_policy.md` | COMMIT | BENCH design policy |
| `benchmark_attribution_design.md` | COMMIT | BENCH design spec |
| `benchmark_attribution_gap_review.md` | COMMIT | BENCH gap analysis |
| `benchmark_attribution_staging_manifest.md` | COMMIT | BENCH staging record |
| `benchmark_attribution_validation.md` | COMMIT | BENCH validation |
| `benchmark_branch_setup_report.md` | COMMIT | BENCH setup record |
| `benchmark_dashboard_design.md` | COMMIT | BENCH UI design |
| `benchmark_dashboard_validation.md` | COMMIT | BENCH UI validation |
| `benchmark_engine_reuse_assessment.md` | COMMIT | BENCH design decision |
| `benchmark_final_verdict.md` | COMMIT | BENCH delivery record |
| `benchmark_provider_audit.md` | COMMIT | BENCH data source audit |
| `benchmark_provider_trace.md` | COMMIT | BENCH data source trace |
| `benchmark_quality_final_verdict.md` | COMMIT | BENCH quality record |
| `benchmark_quality_policy.md` | COMMIT | BENCH quality policy |
| `benchmark_quality_root_cause.md` | COMMIT | BENCH quality analysis |
| `benchmark_quality_validation.md` | COMMIT | BENCH quality validation |
| `benchmark_rebuild_report.md` | COMMIT | BENCH rebuild record |
| `benchmark_recommendation_attribution_model.md` | COMMIT | BENCH model spec |
| `benchmark_recommendation_audit.md` | COMMIT | BENCH audit |
| `benchmark_return_series_audit.md` | COMMIT | BENCH return series audit |
| `benchmark_return_series_model.md` | COMMIT | BENCH return series model |
| `benchmark_source_alpha_model.md` | COMMIT | BENCH alpha model |
| `benchmark_source_summary_audit.md` | COMMIT | BENCH summary audit |
| `benchmark_stream_readiness_verdict.md` | COMMIT | BENCH readiness verdict |
| `source_alpha_validation.md` | COMMIT | BENCH alpha validation |
| `performance_attribution_acceptance_audit.md` | COMMIT | BENCH acceptance audit |
| `performance_attribution_design.md` | COMMIT | BENCH/PERF-ATTR design |
| `recommendation_outcome_framework.md` | COMMIT | BENCH/PERF-ATTR framework |
| `outcome_classification_model.md` | COMMIT | BENCH model spec |
| `post_attribution_roadmap.md` | COMMIT | BENCH roadmap |

---

## PRA-IMPL-02 / 02A Documents — COMMIT

| File | Disposition | Reason |
|------|------------|--------|
| `pra_impl_02_acceptance_verdict.md` | COMMIT | PRA acceptance record |
| `pra_impl_02_behavior_delta.md` | COMMIT | PRA behavior analysis |
| `pra_impl_02_current_state_audit.md` | COMMIT | PRA audit |
| `pra_impl_02_explainability_audit.md` | COMMIT | PRA explainability audit |
| `pra_impl_02_funding_source_audit.md` | COMMIT | PRA funding audit |
| `pra_impl_02_funding_trace.md` | COMMIT | PRA trace |
| `pra_impl_02_reduction_audit.md` | COMMIT | PRA reduction audit |
| `pra_impl_02_test_gap_analysis.md` | COMMIT | PRA gap analysis |
| `pra_impl_02_ui_audit.md` | COMMIT | PRA UI audit |
| `pra_impl_02_validation.md` | COMMIT | PRA validation |
| `pra_impl_02a_api_contract_validation.md` | COMMIT | PRA-02A contract validation |
| `pra_impl_02a_contract_audit.md` | COMMIT | PRA-02A audit |
| `pra_impl_02a_final_verdict.md` | COMMIT | PRA-02A verdict |
| `pra_impl_02a_funding_depletion_design.md` | COMMIT | PRA-02A design |
| `pra_impl_02a_funding_depletion_validation.md` | COMMIT | PRA-02A validation |
| `pra_impl_02a_serialization_validation.md` | COMMIT | PRA-02A validation |
| `allocation_reduction_model.md` | COMMIT | PRA model spec |
| `funding_dashboard_design.md` | COMMIT | PRA dashboard design |
| `funding_explainability_model.md` | COMMIT | PRA explainability model |
| `funding_source_policy_model.md` | COMMIT | PRA policy model |

---

## Signal Coverage Documents — COMMIT (with SIG-COV code)

| File | Disposition | Reason |
|------|------------|--------|
| `coverage_aware_refresh_design.md` | COMMIT | SIG-COV design |
| `coverage_panel_design.md` | COMMIT | SIG-COV UI design |
| `coverage_repair_retry_design.md` | COMMIT | SIG-COV design |
| `coverage_ui_completion.md` | COMMIT | SIG-COV completion record |
| `hardcoded_portfolio_membership_audit.md` | COMMIT | SIG-COV audit |
| `historical_coverage_analysis.md` | COMMIT | SIG-COV analysis |
| `holdings_baseline_unification.md` | COMMIT | SIG-COV design |
| `holdings_coverage_reconciliation.md` | COMMIT | SIG-COV reconciliation |
| `operational_refresh_enforcement.md` | COMMIT | SIG-COV policy |
| `provider_applicability_model.md` | COMMIT | SIG-COV model |
| `provider_retry_semantics.md` | COMMIT | SIG-COV semantics |
| `refresh_button_trace.md` | COMMIT | SIG-COV trace |
| `refresh_eligibility_model.md` | COMMIT | SIG-COV model |
| `refresh_execution_trace.md` | COMMIT | SIG-COV trace |
| `refresh_runtime_evidence.md` | COMMIT | SIG-COV evidence |
| `refresh_status_api_design.md` | COMMIT | SIG-COV API design |
| `signal_coverage_03_completion.md` | COMMIT | SIG-COV completion |
| `signal_freshness_model_assessment.md` | COMMIT | SIG-COV assessment |
| `signal_status_model_split.md` | COMMIT | SIG-COV design |
| `spy_coverage_audit.md` | COMMIT | SIG-COV audit |
| `targeted_refresh_strategy.md` | COMMIT | SIG-COV strategy |
| `ui_refresh_state_assessment.md` | COMMIT | SIG-COV UI assessment |
| `ui_refresh_truthfulness_assessment.md` | COMMIT | SIG-COV UI assessment |

---

## PIS Forensic Investigation Documents — COMMIT (with PIS-005)

| File | Disposition | Reason |
|------|------------|--------|
| `PIS_FORENSIC_INVESTIGATION_INDEX.md` | COMMIT | Investigation index |
| `attribution_freshness_audit.md` | COMMIT | Forensic audit |
| `attribution_readiness_assessment.md` | COMMIT | Forensic assessment |
| `attribution_start_gate.md` | COMMIT | Forensic gate |
| `attribution_validation.md` | COMMIT | Forensic validation |
| `cash_vs_spaxx_audit.md` | COMMIT | Forensic audit |
| `lineage_freshness_audit.md` | COMMIT | Forensic audit |
| `pis_attr_forensic_01_report.md` | COMMIT | Forensic report |
| `pis_attr_forensic_final_verdict.md` | COMMIT | Forensic verdict |
| `pis_closure_01_report.md` | COMMIT | PIS closure report |
| `pis_foundation_release_assessment.md` | COMMIT | PIS foundation |
| `pis_foundation_reproducibility_assessment.md` | COMMIT | PIS reproducibility |
| `portfolio_manager_history_inventory.md` | COMMIT | PIS inventory |
| `portfolio_manager_to_pis_mapping.md` | COMMIT | PIS mapping |
| `recommendation_return_trace.md` | COMMIT | Forensic trace |
| `reproducibility_validation.md` | COMMIT | Forensic validation |
| `root_cause_verdict.md` | COMMIT | Root cause record |
| `snapshot_comparison_model.md` | COMMIT | Forensic model |

---

## Repository Governance Documents — COMMIT

| File | Disposition | Reason |
|------|------------|--------|
| `documentation_consolidation_plan.md` | COMMIT | Governance plan |
| `foundation_release_tag_report.md` | COMMIT | Release tag record |
| `generated_artifact_archive_report.md` | COMMIT | Archive record |
| `next_implementation_recommendation.md` | COMMIT | Governance recommendation |
| `pis_backfill_design.md` | COMMIT | PIS backfill design |
| `repository_cleanliness_audit.md` | COMMIT | Prior cleanup audit |
| `repository_cleanup_plan.md` | COMMIT | Cleanup plan |
| `repository_stabilization_actions.md` | COMMIT | Stabilization actions |
| `repository_stabilization_inventory.md` | COMMIT | Prior inventory |
| `workstream_isolation_plan.md` | COMMIT | Isolation plan |
| `issue_50_rescope_recommendation.md` | COMMIT | Issue recommendation |
| `migration_feasibility_assessment.md` | COMMIT | Migration analysis |
| `recommended_migration_strategy.md` | COMMIT | Migration strategy |

---

## This Audit — COMMIT

| File | Disposition | Reason |
|------|------------|--------|
| `repository_stabilization_inventory_v2.md` | COMMIT | This audit's inventory |
| `repository_workstream_classification.md` | COMMIT | This audit's classification |
| `workstream_commit_readiness.md` | COMMIT | This audit's readiness |
| `generated_artifact_disposition.md` | COMMIT | This file |
| `documentation_consolidation_v2.md` | COMMIT | This audit's doc consolidation |
| `branch_strategy_recommendation.md` | COMMIT | This audit's branch strategy |
| `repository_stabilization_final_verdict.md` | COMMIT | This audit's verdict |

---

## Docs Subdirectories — COMMIT

| Path | Disposition | Reason |
|------|------------|--------|
| `docs/pis-001/` | COMMIT | PIS-001 documentation |
| `docs/pis-001a/` | COMMIT | PIS-001A documentation |
| `docs/pis-planning/` | COMMIT | PIS planning docs |
| `docs/performance-attribution/*.md` (4 new files) | COMMIT | BENCH documentation |

---

## Files with No Clear Workstream — ARCHIVE/DELETE

| File | Disposition | Reason |
|------|------------|--------|
| `resume_checkpoint_repair_audit.md` | ARCHIVE | Prior session management artifact; not part of any active workstream |

---

## Summary

| Disposition | Count |
|------------|-------|
| COMMIT | ~170 |
| ARCHIVE | 1 |
| IGNORE | 0 |
| DELETE | 0 |

**Finding:** Nearly all dirty files represent genuine implementation and investigation artifacts that belong in version control. There are no generated throwaway files. The repository root has become a large workspace for document-heavy development — this is intentional given the forensic/design methodology.
