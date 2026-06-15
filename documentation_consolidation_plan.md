# Documentation Consolidation Plan

## Objective

Rationalize PIS documentation into a durable reference set under `docs/pis/` and reduce draft duplication.

Target structure:
- `docs/pis/architecture.md`
- `docs/pis/apis.md`
- `docs/pis/governance.md`
- `docs/pis/canonical-selection.md`
- `docs/pis/change-detection.md`
- `docs/pis/lineage.md`
- `docs/pis/dashboard.md`
- `docs/pis/history.md`

## Consolidation Rules

1. `Keep`
- canonical source references and high-signal specs needed for ongoing maintenance.

2. `Archive`
- milestone completion logs, verdict snapshots, and planning-era docs still useful for traceability.

3. `Delete`
- superseded duplicates after content is merged into final `docs/pis/*.md` files.

## Existing PIS Docs - Keep / Archive / Delete

### docs/pis-001

- `docs/pis-001/pis_architecture_overview.md` -> Keep (merge into `docs/pis/architecture.md`)
- `docs/pis-001/pis_api_contract.md` -> Keep (merge into `docs/pis/apis.md`)
- `docs/pis-001/portfolio_snapshot_schema.md` -> Keep (merge into `docs/pis/history.md`)
- `docs/pis-001/fidelity_portfolio_file_inventory.md` -> Archive
- `docs/pis-001/benchmark_integration_assessment.md` -> Archive
- `docs/pis-001/missing_information_queue_design.md` -> Archive
- `docs/pis-001/phased_implementation_roadmap.md` -> Archive
- `docs/pis-001/pis_dashboard_design.md` -> Keep (merge into `docs/pis/dashboard.md`)
- `docs/pis-001/pis_ui_phase1_completion.md` -> Archive
- `docs/pis-001/change_detection_design.md` -> Keep (merge into `docs/pis/change-detection.md`)
- `docs/pis-001/decision_lineage_framework.md` -> Keep (merge into `docs/pis/lineage.md`)
- `docs/pis-001/final_verdict.md` -> Archive
- `docs/pis-001/screenshots/pis_dashboard_phase1.png` -> Archive
- `docs/pis-001/screenshots/sih_to_pis_navigation.png` -> Archive

### docs/pis-001a

- `docs/pis-001a/pis_snapshot_registration_design.md` -> Keep (merge into `docs/pis/history.md`)
- `docs/pis-001a/failure_isolation_assessment.md` -> Archive
- `docs/pis-001a/idempotency_assessment.md` -> Archive
- `docs/pis-001a/upload_lifecycle_trace.md` -> Archive
- `docs/pis-001a/completion_report.md` -> Archive

### docs/pis-planning

- `docs/pis-planning/pis_repository_architecture.md` -> Keep (merge into `docs/pis/architecture.md`)
- `docs/pis-planning/pis_data_ownership_model.md` -> Keep (merge into `docs/pis/architecture.md`)
- `docs/pis-planning/pis_storage_strategy.md` -> Keep (merge into `docs/pis/history.md`)
- `docs/pis-planning/pis_navigation_and_ui_model.md` -> Keep (merge into `docs/pis/dashboard.md`)
- `docs/pis-planning/pis_risk_assessment.md` -> Archive
- `docs/pis-planning/pis_phase1_implementation_plan.md` -> Archive
- `docs/pis-planning/pis_phase_validation.md` -> Archive
- `docs/pis-planning/pis_final_architecture_recommendation.md` -> Keep (merge into `docs/pis/architecture.md`)

### Root-level PIS design and validation docs

- `pis_004a_governance_design.md` -> Keep (merge into `docs/pis/governance.md`)
- `snapshot_governance_rules.md` -> Keep (merge into `docs/pis/governance.md`)
- `governance_validation.md` -> Keep (append validation section in `docs/pis/governance.md`)
- `pis_004b_canonical_selection_design.md` -> Keep (merge into `docs/pis/canonical-selection.md`)
- `canonical_selection_algorithm.md` -> Keep (merge into `docs/pis/canonical-selection.md`)
- `canonical_recompute_assessment.md` -> Archive
- `canonical_validation.md` -> Keep (validation section in `docs/pis/canonical-selection.md`)
- `pis_change_detection_design.md` -> Keep (merge into `docs/pis/change-detection.md`)
- `change_detection_algorithm.md` -> Keep (merge into `docs/pis/change-detection.md`)
- `change_detection_validation.md` -> Keep (validation section in `docs/pis/change-detection.md`)
- `recommendation_lineage_design.md` -> Keep (merge into `docs/pis/lineage.md`)
- `lineage_matching_algorithm.md` -> Keep (merge into `docs/pis/lineage.md`)
- `lineage_confidence_model.md` -> Keep (merge into `docs/pis/lineage.md`)
- `lineage_validation.md` -> Keep (validation section in `docs/pis/lineage.md`)
- `pis_ui_02_loading_states_design.md` -> Keep (merge into `docs/pis/dashboard.md`)
- `progressive_rendering_strategy.md` -> Keep (merge into `docs/pis/dashboard.md`)
- `dashboard_status_model.md` -> Keep (merge into `docs/pis/dashboard.md`)
- `loading_state_validation.md` -> Keep (validation section in `docs/pis/dashboard.md`)
- `pis_ui_03_executive_dashboard_design.md` -> Keep (merge into `docs/pis/dashboard.md`)
- `dashboard_kpi_model.md` -> Keep (merge into `docs/pis/dashboard.md`)
- `summary_card_specification.md` -> Keep (merge into `docs/pis/dashboard.md`)
- `ux_validation.md` -> Keep (validation section in `docs/pis/dashboard.md`)
- `pis_backfill_design.md` -> Keep (merge into `docs/pis/history.md`)
- `portfolio_manager_history_inventory.md` -> Archive
- `portfolio_manager_to_pis_mapping.md` -> Keep (merge into `docs/pis/history.md`)
- `migration_feasibility_assessment.md` -> Archive

## Duplicate/Superseded Patterns

1. `dashboard` documentation is currently split across multiple root docs plus `docs/pis-001/*`.
2. `change-detection` exists in both planning and implementation docs.
3. `lineage` has separate framework/design/algorithm/confidence/validation files.
4. `history` and migration narratives are spread across planning, backfill, and inventory files.

## Recommended Consolidation Steps

1. Create `docs/pis/` with the eight canonical files.
2. Migrate `Keep` content into those files.
3. Move all `Archive` docs into `docs/pis/archive/` retaining original filenames.
4. Delete superseded root-level drafts only after content merge is complete and reviewed.
5. Keep screenshots only in archive unless needed in the canonical dashboard doc.

## Delete Candidates After Merge Confirmation

- `pis_ui_02_loading_states_design.md`
- `pis_ui_03_executive_dashboard_design.md`
- `dashboard_status_model.md`
- `dashboard_kpi_model.md`
- `summary_card_specification.md`
- `change_detection_algorithm.md`
- `lineage_matching_algorithm.md`
- `canonical_selection_algorithm.md`

(Delete only after their content is fully absorbed into `docs/pis/*.md`.)
