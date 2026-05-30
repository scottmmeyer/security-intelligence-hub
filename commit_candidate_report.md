# Commit Candidate Report — Phase SC-H1

**Generated:** 2026-05-30  
**Current branch:** `main`  
**Last commit:** `c8859f0` — Add scoring fetchers (Zacks/Yahoo/Danelfin), portfolio-vehicle support, and supplemental seed data  
**Test suite:** 504 passed, 0 failed (`PYTHONPATH=. pytest -q`)

---

## SAFE_TO_COMMIT (94 files)

Files that are clearly intentional, phase-owned, and directly support the feature implementation. These can be committed without further investigation.

### Core Source — New Modules

| File | Phase |
|---|---|
| `src/portfolio/__init__.py` | 6.1 |
| `src/portfolio/models.py` | 6.1 |
| `src/portfolio/ingestion.py` | 6.1 |
| `src/portfolio/enrichment.py` | 6.1 |
| `src/portfolio/alignment.py` | 7.0 |
| `src/portfolio/recommendations.py` | 7.0 |
| `src/portfolio/runner.py` | 7.0 |
| `src/portfolio/mandate.py` | 7.1 |
| `src/portfolio/scoring.py` | 7.1 |
| `src/portfolio/exposure_decomposition.py` | 7.1 |
| `src/portfolio/reconciliation.py` | 7.2 |
| `src/portfolio/archetype.py` | 7.2 |
| `src/portfolio/taxonomy.py` | 7.2 |
| `src/portfolio/trim_intelligence.py` | 7.2 |
| `src/portfolio/phase_e_synthesis.py` | 7.2 |
| `src/portfolio/optimizer.py` | 7.3A |
| `src/allocation/__init__.py` | 6.2 |
| `src/allocation/dimensions_loader.py` | 6.2 |
| `src/allocation/methodology_loader.py` | 6.2 |
| `src/allocation/models.py` | 6.2 |
| `src/allocation/recalculation_engine.py` | 6.2 |
| `src/allocation/replay_integration.py` | 6.2 |
| `src/allocation/structural_policy.py` | 6.2 |
| `src/allocation/tactical_overlay.py` | 6.2 |
| `src/allocation/validators.py` | 6.2 |
| `src/classification/__init__.py` | 6.3 |
| `src/classification/benchmark_assignment_engine.py` | 6.3 |
| `src/classification/classification_validators.py` | 6.3 |
| `src/classification/geography_resolver.py` | 6.3 |
| `src/classification/security_type_policy.py` | 6.3 |
| `src/effectiveness/__init__.py` | 6.4 |
| `src/effectiveness/composite_versioning.py` | 6.4 |
| `src/effectiveness/factor_contribution.py` | 6.4 |
| `src/history/allocation_manager.py` | 6.2 |
| `src/scoring/fetch_security_metadata.py` | 6.x |
| `src/scoring/market_cap_subtier_classifier.py` | 6.3 |
| `src/validation/market_cap_subtier_validator.py` | 6.3 |

### Tracked Source — Modified Files

| File | Phase |
|---|---|
| `src/history/analytical_universe_manager.py` | 6.x |
| `src/history/base_universe_manager.py` | 6.x |
| `src/models/analytical_models.py` | 6.x |
| `src/models/canonical_models.py` | 6.x |
| `src/normalize/ess_normalizer.py` | 6.x |
| `src/normalize/provider_normalizer.py` | 6.x |
| `src/providers/fidelity/fidelity_ess_adapter.py` | 6.x |
| `src/providers/fidelity/fidelity_schema_contract.py` | 6.x |
| `src/replay/foundation_service.py` | 6.x |
| `src/replay/replay_engine.py` | WP-05D |
| `src/replay/stock_replay_service.py` | WP-05D |
| `src/scoring/fetch_danelfin_scores.py` | 6.x |
| `src/scoring/fetch_yahoo_supplemental.py` | 6.x |
| `src/scoring/fetch_zacks_scores.py` | 6.x |
| `src/validation/replay_validator.py` | WP-05D |
| `scripts/run_outcome_ui.py` | 6.1→7.3B |

### UI

| File | Phase |
|---|---|
| `ui/portfolio_alignment/app.js` | 6.1→7.3B |
| `ui/portfolio_alignment/index.html` | 6.1→7.3B |
| `ui/allocation_intelligence/app.js` | 6.2 |
| `ui/allocation_intelligence/index.html` | 6.2 |
| `ui/outcome_visualization/app.js` | WP-05D |
| `ui/outcome_visualization/index.html` | WP-05D |

### Tests

| File | Phase |
|---|---|
| `tests/test_dynamic_subtier_classification.py` | 6.3 |
| `tests/test_signal_fetch_resume.py` | 6.x |
| `tests/test_mandate_intelligence.py` | 7.0 |
| `tests/test_vehicle_suitability.py` | 7.1 |
| `tests/test_etf_exposure_decomposition.py` | 7.1 |
| `tests/test_cash_semantics.py` | 7.x |
| `tests/test_reconciliation.py` | 7.2 |
| `tests/test_archetype.py` | 7.2 |
| `tests/test_phase_d_trim_intelligence.py` | 7.2 |
| `tests/test_phase_e_synthesis.py` | 7.2 |
| `tests/test_optimizer.py` | 7.3A |
| `tests/test_7_3b_optimizer_ui.py` | 7.3B |
| `tests/test_wp04_1_ui_prototype.py` | 7.x (adapted) |
| `tests/test_wp04_replay_foundation.py` | 7.x (adapted) |

### Config

| File | Phase |
|---|---|
| `config/allocation_dimensions.yaml` | 6.2 |
| `config/allocation_methodology.yaml` | 6.2 |
| `config/allocation_policy.yaml` | 6.2 |
| `config/allocation_models/balanced_allocation_profile.yaml` | 6.2 |
| `config/allocation_models/concentrated_alpha_profile.yaml` | 6.2 |
| `config/allocation_models/growth_allocation_profile.yaml` | 6.2 |
| `config/etf_exposure_decomposition.yaml` | 7.1 |
| `config/geography_overrides.yaml` | 6.3 |
| `config/market_cap_subtier_policy.yaml` | 6.3 |
| `config/security_type_policy.yaml` | 6.3 |
| `config/adr_domicile_policy.yaml` | 6.x |

### Documentation

| File | Phase |
|---|---|
| `docs/ALLOCATION_INTELLIGENCE_PHILOSOPHY.md` | 6.2 |
| `docs/ALLOCATION_PRIMER_WHY_THESE_NUMBERS.md` | 6.2 |
| `docs/ASSET_CLASS_FIRST_ARCHITECTURE.md` | 6.x |
| `docs/HIERARCHICAL_ALLOCATION_MODEL.md` | 6.2 |
| `docs/VEHICLE_SELECTION_RATIONALE.md` | 7.1 |
| `docs/migration_plan.md` | 6.x |
| `docs/recommendation_flow_analysis.md` | 7.x |
| `docs/security_vs_etf_decision_framework.md` | 7.1 |
| `docs/unified_optimizer_design.md` | 7.3A |
| `docs/equity-summary-score-methodology.pdf` | 6.x |
| `optimizer_ui_validation_report.md` | 7.3B |

### Operational Scripts

| File | Phase |
|---|---|
| `scripts/apply_eligibility_flags.py` | 6.x |
| `scripts/assign_geography.py` | 6.3 |
| `scripts/compare_zacks_ess_vs_internet.py` | 6.x |
| `scripts/migrate_base_universe_headers.py` | 6.x |
| `scripts/patch_universe_zacks.py` | 6.x |
| `scripts/recalculate_allocation_targets.py` | 6.2 |
| `scripts/refresh_portfolio_signals.py` | 6.x |
| `scripts/refresh_signals.py` | 6.x |
| `scripts/rescore_all_universe.py` | 6.x |
| `scripts/run_classification_audit.py` | 6.3 |
| `scripts/score_lookup.py` | 6.x |
| `scripts/diagnostics/build_wp04_foundation.py` | 6.x |
| `scripts/diagnostics/build_wp05b_replay_matrix.py` | 6.x |
| `scripts/diagnostics/merge_subtier_replays.py` | 6.3 |
| `scripts/diagnostics/partial_publish_current.py` | 6.x |
| `scripts/research/factor_effectiveness_report.py` | 6.4 |
| `scripts/research/generate_v2_scores.py` | 6.4 |
| `.gitignore` | 6.x |

**SAFE_TO_COMMIT total: 94 files**

---

## SHOULD_ARCHIVE (10 files)

Files with valid content but not appropriate to commit to the root or current location. Move before committing.

| File | Action |
|---|---|
| `data/exports/optimizer_candidate_report.md` | Move to `data/exports/archive/` or `docs/archive/` |
| `data/exports/optimizer_vs_legacy_report.md` | Move to `data/exports/archive/` or `docs/archive/` |
| `docs/conflict_graph_report.md` | Move to `docs/archive/` or `data/exports/` |
| `scripts/_generate_conviction_model_quality_report.py` | Move to `scripts/archive/` |
| `scripts/_generate_conviction_ranking_report.py` | Move to `scripts/archive/` |
| `scripts/_generate_coverage_denominator_report.py` | Move to `scripts/archive/` |
| `scripts/_generate_coverage_gap_report.py` | Move to `scripts/archive/` |
| `scripts/_generate_coverage_report.py` | Move to `scripts/archive/` |
| `scripts/_generate_phase72_audit_reports.py` | Move to `scripts/archive/` |
| `scripts/_generate_phase73a_optimizer_reports.py` | Move to `scripts/archive/` |
| `scripts/_generate_recommendation_explainability_report.py` | Move to `scripts/archive/` |
| `scripts/_generate_reconciliation_report.py` | Move to `scripts/archive/` |
| `scripts/_generate_replay_alignment_audit.py` | Move to `scripts/archive/` |
| `scripts/_generate_strategic_narrative_audit.py` | Move to `scripts/archive/` |
| `scripts/_generate_strategic_narrative_validation_report.py` | Move to `scripts/archive/` |
| `scripts/_generate_taxonomy_clean_run_report.py` | Move to `scripts/archive/` |
| `scripts/_generate_taxonomy_report.py` | Move to `scripts/archive/` |

**SHOULD_ARCHIVE total: 17 files**

---

## SHOULD_REVERT (0 files)

No files identified as requiring revert. All tracked-file modifications are attributable to integration glue for Phase 6/7 work.

**SHOULD_REVERT total: 0 files**

---

## INVESTIGATE (8 files)

Files where classification is uncertain and manual review is needed before deciding commit vs delete.

| File | Question |
|---|---|
| `xyz` | Empty file. Almost certainly accidental. Confirm and delete. |
| `scripts/refresh_signals.py` | Overlaps with `scripts/refresh_portfolio_signals.py`. Determine which is canonical; delete or rename the other. |
| `scripts/_archetype_validation.py` | Superseded by `tests/test_archetype.py`? Confirm, then delete. |
| `scripts/_portfolio_philosophy_validation.py` | Is there unique output not captured in formal tests? If not, delete. |
| `scripts/_test_pipeline.py` | Superseded by test suite? Confirm and delete. |
| `scripts/_ui_archetype_consistency_report.py` | Was this a deliverable or a diagnostic? If diagnostic only, delete. |
| `data/derived/phase7_audit_data.json` | Temporary JSON from `_phase7_build_data.py`. Confirm not needed by any current script, then gitignore/delete. |
| `navigation_state.yaml` | Should be gitignored, not committed. Add to `.gitignore` and do not stage. |

**INVESTIGATE total: 8 files**

---

## GITIGNORE ONLY (32 files — do not commit, do not delete, add to `.gitignore`)

These files should remain on disk but must not be committed. Their patterns should be added to `.gitignore` now.

| Pattern | Files Covered |
|---|---|
| 22 root `*_report.md` files (see `generated_artifact_audit.md`) | All phase-generated audit reports except `optimizer_ui_validation_report.md` |
| `navigation_state.yaml` | UI session state |
| `data/allocation/` | Runtime allocation outputs |
| `data/derived/` | Derived CSV/JSON outputs |
| `scripts/_*.py` | All diagnostic/debug/temp scripts |

---

## File Count Summary

| Section | Count |
|---|---|
| SAFE_TO_COMMIT | 94 |
| SHOULD_ARCHIVE | 17 |
| SHOULD_REVERT | 0 |
| INVESTIGATE | 8 |
| GITIGNORE ONLY | 32 |
| **Total accounted for** | **151** |
