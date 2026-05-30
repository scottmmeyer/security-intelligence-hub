# Repository Dirty File Inventory — Phase SC-H1

**Generated:** 2026-05-30  
**Command:** `git status --short`  
**Last commit:** `c8859f0` — Add scoring fetchers (Zacks/Yahoo/Danelfin), portfolio-vehicle support, and supplemental seed data  
**Total dirty entries:** 142 (25 modified tracked + 117 untracked entries; directories expand to ~185 total files)

---

## Classification Key

| Code | Meaning |
|---|---|
| EXPECTED_CODE_CHANGE | Intentional code change from a defined phase |
| GENERATED_ARTIFACT | Output produced by running code (reports, data, run outputs) |
| TEST_CHANGE | New or modified test file from a defined phase |
| CONFIG_CHANGE | Intentional config/policy file change |
| DOCUMENTATION_CHANGE | Intentional documentation added as part of a phase |
| ACCIDENTAL_CHANGE | Modified file with no clear intent or phase owner |
| UNKNOWN | Cannot classify without further investigation |

---

## MODIFIED TRACKED FILES (25)

| File | Δ Lines | Classification | Phase | Notes |
|---|---|---|---|---|
| `.gitignore` | +28 | CONFIG_CHANGE | 6.x | Added ignores for runtime data, venv, caches |
| `navigation_state.yaml` | +34 | GENERATED_ARTIFACT | auto | Auto-updated UI navigation state; not code |
| `scripts/diagnostics/build_wp04_foundation.py` | +6 | EXPECTED_CODE_CHANGE | 6.x | Portfolio ingestion diagnostic adaptation |
| `scripts/diagnostics/build_wp05b_replay_matrix.py` | +26 | EXPECTED_CODE_CHANGE | 6.x | Replay matrix diagnostic adaptation |
| `scripts/run_outcome_ui.py` | +414 | EXPECTED_CODE_CHANGE | 6.1→7.3B | Portfolio alignment API routes added (POST analyze, GET runs) |
| `scripts/score_lookup.py` | +13 | EXPECTED_CODE_CHANGE | 6.x | Scoring utility extension |
| `src/history/analytical_universe_manager.py` | +364 | EXPECTED_CODE_CHANGE | 6.x | Allocation manager integration extensions |
| `src/history/base_universe_manager.py` | +1 | EXPECTED_CODE_CHANGE | 6.x | Minor field addition |
| `src/models/analytical_models.py` | +43 | EXPECTED_CODE_CHANGE | 6.x | New analytical model fields |
| `src/models/canonical_models.py` | +3 | EXPECTED_CODE_CHANGE | 6.x | Minor canonical model extension |
| `src/normalize/ess_normalizer.py` | +13 | EXPECTED_CODE_CHANGE | 6.x | ESS normalizer extension |
| `src/normalize/provider_normalizer.py` | +1 | EXPECTED_CODE_CHANGE | 6.x | Minor normalizer fix |
| `src/providers/fidelity/fidelity_ess_adapter.py` | +60 | EXPECTED_CODE_CHANGE | 6.x | Fidelity adapter enhancements |
| `src/providers/fidelity/fidelity_schema_contract.py` | +15 | EXPECTED_CODE_CHANGE | 6.x | Schema contract extensions |
| `src/replay/foundation_service.py` | +92 | EXPECTED_CODE_CHANGE | 6.x | Replay foundation extensions |
| `src/replay/replay_engine.py` | +39 | EXPECTED_CODE_CHANGE | WP-05D | Replay engine extensions |
| `src/replay/stock_replay_service.py` | +2 | EXPECTED_CODE_CHANGE | WP-05D | Minor stock replay fix |
| `src/scoring/fetch_danelfin_scores.py` | +52 | EXPECTED_CODE_CHANGE | 6.x | Danelfin scorer extension |
| `src/scoring/fetch_yahoo_supplemental.py` | +50 | EXPECTED_CODE_CHANGE | 6.x | Yahoo supplemental extension |
| `src/scoring/fetch_zacks_scores.py` | +59 | EXPECTED_CODE_CHANGE | 6.x | Zacks scorer extension |
| `src/validation/replay_validator.py` | +17 | EXPECTED_CODE_CHANGE | WP-05D/6.x | Replay validator extension |
| `tests/test_wp04_1_ui_prototype.py` | +10 | TEST_CHANGE | 7.x | Test adaptation for new API contract |
| `tests/test_wp04_replay_foundation.py` | +6 | TEST_CHANGE | 7.x | Test adaptation for new API contract |
| `ui/outcome_visualization/app.js` | +784 | EXPECTED_CODE_CHANGE | WP-05D | Stock replay curves + return comparison UI (WP-05D Phase H) |
| `ui/outcome_visualization/index.html` | +396 | EXPECTED_CODE_CHANGE | WP-05D | Stock coverage panel + return comparison table (WP-05D Phase H) |

---

## UNTRACKED FILES — NEW SOURCE MODULES (Phase 6.x–7.3B)

| File / Directory | Classification | Phase | Notes |
|---|---|---|---|
| `src/portfolio/` (17 files) | EXPECTED_CODE_CHANGE | 6.1→7.3B | Core portfolio analysis module — entire Phase 6/7 implementation |
| `src/portfolio/__init__.py` | EXPECTED_CODE_CHANGE | 6.1 | |
| `src/portfolio/alignment.py` | EXPECTED_CODE_CHANGE | 7.0 | Allocation alignment engine |
| `src/portfolio/archetype.py` | EXPECTED_CODE_CHANGE | 7.2 | Portfolio archetype classifier |
| `src/portfolio/enrichment.py` | EXPECTED_CODE_CHANGE | 6.1 | Holdings enrichment |
| `src/portfolio/exposure_decomposition.py` | EXPECTED_CODE_CHANGE | 7.1 | ETF exposure decomposition |
| `src/portfolio/ingestion.py` | EXPECTED_CODE_CHANGE | 6.1 | Portfolio CSV ingestion |
| `src/portfolio/mandate.py` | EXPECTED_CODE_CHANGE | 7.1 | PMI mandate intelligence |
| `src/portfolio/models.py` | EXPECTED_CODE_CHANGE | 6.1 | Portfolio domain models (frozen dataclasses) |
| `src/portfolio/optimizer.py` | EXPECTED_CODE_CHANGE | 7.3A | Parallel optimizer — Phase 7.3A |
| `src/portfolio/phase_e_synthesis.py` | EXPECTED_CODE_CHANGE | 7.2 | Phase E recommendation synthesis |
| `src/portfolio/recommendations.py` | EXPECTED_CODE_CHANGE | 7.0 | Recommendation engine |
| `src/portfolio/reconciliation.py` | EXPECTED_CODE_CHANGE | 7.2 | Portfolio reconciliation |
| `src/portfolio/runner.py` | EXPECTED_CODE_CHANGE | 7.0→7.3A | Full analysis orchestrator |
| `src/portfolio/scoring.py` | EXPECTED_CODE_CHANGE | 7.1 | Vehicle suitability scoring |
| `src/portfolio/taxonomy.py` | EXPECTED_CODE_CHANGE | 7.2 | Taxonomy classification |
| `src/portfolio/trim_intelligence.py` | EXPECTED_CODE_CHANGE | 7.2 | Phase D trim intelligence |
| `src/allocation/` (8 files) | EXPECTED_CODE_CHANGE | 6.2 | Allocation intelligence module |
| `src/classification/` (6 files) | EXPECTED_CODE_CHANGE | 6.3 | Geography/security-type classification module |
| `src/effectiveness/__init__.py` | EXPECTED_CODE_CHANGE | 6.4 | Effectiveness module init |
| `src/effectiveness/composite_versioning.py` | EXPECTED_CODE_CHANGE | 6.4 | Composite score versioning |
| `src/effectiveness/factor_contribution.py` | EXPECTED_CODE_CHANGE | 6.4 | Factor contribution analysis |
| `src/history/allocation_manager.py` | EXPECTED_CODE_CHANGE | 6.2 | Allocation history persistence |
| `src/scoring/fetch_security_metadata.py` | EXPECTED_CODE_CHANGE | 6.x | Security metadata fetcher |
| `src/scoring/market_cap_subtier_classifier.py` | EXPECTED_CODE_CHANGE | 6.3 | Market cap subtier classifier |
| `src/validation/market_cap_subtier_validator.py` | EXPECTED_CODE_CHANGE | 6.3 | Market cap subtier validator |

---

## UNTRACKED FILES — NEW UI MODULES

| File | Classification | Phase | Notes |
|---|---|---|---|
| `ui/portfolio_alignment/app.js` | EXPECTED_CODE_CHANGE | 6.1→7.3B | Main portfolio alignment JS app |
| `ui/portfolio_alignment/index.html` | EXPECTED_CODE_CHANGE | 6.1→7.3B | Portfolio alignment HTML shell |
| `ui/allocation_intelligence/app.js` | EXPECTED_CODE_CHANGE | 6.2 | Allocation intelligence UI app |
| `ui/allocation_intelligence/index.html` | EXPECTED_CODE_CHANGE | 6.2 | Allocation intelligence HTML shell |

---

## UNTRACKED FILES — CONFIG

| File | Classification | Phase | Notes |
|---|---|---|---|
| `config/adr_domicile_policy.yaml` | CONFIG_CHANGE | 6.x | ADR/domicile classification policy |
| `config/allocation_dimensions.yaml` | CONFIG_CHANGE | 6.2 | Allocation dimension definitions |
| `config/allocation_methodology.yaml` | CONFIG_CHANGE | 6.2 | Allocation methodology rules |
| `config/allocation_models/balanced_allocation_profile.yaml` | CONFIG_CHANGE | 6.2 | Balanced mandate profile |
| `config/allocation_models/concentrated_alpha_profile.yaml` | CONFIG_CHANGE | 6.2 | Concentrated Alpha mandate profile |
| `config/allocation_models/growth_allocation_profile.yaml` | CONFIG_CHANGE | 6.2 | Growth mandate profile |
| `config/allocation_policy.yaml` | CONFIG_CHANGE | 6.2 | Allocation policy rules |
| `config/etf_exposure_decomposition.yaml` | CONFIG_CHANGE | 7.1 | ETF exposure decomposition registry |
| `config/geography_overrides.yaml` | CONFIG_CHANGE | 6.3 | Geography override mappings |
| `config/market_cap_subtier_policy.yaml` | CONFIG_CHANGE | 6.3 | Market cap subtier policy |
| `config/security_type_policy.yaml` | CONFIG_CHANGE | 6.3 | Security type classification policy |

---

## UNTRACKED FILES — NEW TESTS

| File | Classification | Phase | Notes |
|---|---|---|---|
| `tests/test_7_3b_optimizer_ui.py` | TEST_CHANGE | 7.3B | 15 optimizer UI validation tests |
| `tests/test_archetype.py` | TEST_CHANGE | 7.2 | Archetype classifier tests |
| `tests/test_cash_semantics.py` | TEST_CHANGE | 7.x | Cash semantic validation tests |
| `tests/test_dynamic_subtier_classification.py` | TEST_CHANGE | 6.3 | Market cap subtier tests |
| `tests/test_etf_exposure_decomposition.py` | TEST_CHANGE | 7.1 | ETF decomposition tests |
| `tests/test_mandate_intelligence.py` | TEST_CHANGE | 7.0/7.1 | PMI mandate intelligence tests |
| `tests/test_optimizer.py` | TEST_CHANGE | 7.3A | 11 parallel optimizer tests |
| `tests/test_phase_d_trim_intelligence.py` | TEST_CHANGE | 7.2 | Phase D trim tests |
| `tests/test_phase_e_synthesis.py` | TEST_CHANGE | 7.2 | Phase E synthesis tests |
| `tests/test_reconciliation.py` | TEST_CHANGE | 7.2 | Portfolio reconciliation tests |
| `tests/test_signal_fetch_resume.py` | TEST_CHANGE | 6.x | Signal fetch resume tests |
| `tests/test_vehicle_suitability.py` | TEST_CHANGE | 7.1 | Vehicle suitability scoring tests |

---

## UNTRACKED FILES — DOCUMENTATION

| File | Classification | Phase | Notes |
|---|---|---|---|
| `docs/ALLOCATION_INTELLIGENCE_PHILOSOPHY.md` | DOCUMENTATION_CHANGE | 6.2 | Allocation intelligence design doc |
| `docs/ALLOCATION_PRIMER_WHY_THESE_NUMBERS.md` | DOCUMENTATION_CHANGE | 6.2 | Allocation primer |
| `docs/ASSET_CLASS_FIRST_ARCHITECTURE.md` | DOCUMENTATION_CHANGE | 6.x | Architecture philosophy |
| `docs/HIERARCHICAL_ALLOCATION_MODEL.md` | DOCUMENTATION_CHANGE | 6.2 | Hierarchical allocation model doc |
| `docs/VEHICLE_SELECTION_RATIONALE.md` | DOCUMENTATION_CHANGE | 7.1 | Vehicle selection rationale |
| `docs/conflict_graph_report.md` | GENERATED_ARTIFACT | 7.2 | Conflict graph generated by Phase 7.2 |
| `docs/equity-summary-score-methodology.pdf` | DOCUMENTATION_CHANGE | 6.x | Reference PDF (provider methodology) |
| `docs/migration_plan.md` | DOCUMENTATION_CHANGE | 6.x | Data migration design doc |
| `docs/recommendation_flow_analysis.md` | DOCUMENTATION_CHANGE | 7.x | Recommendation flow analysis |
| `docs/security_vs_etf_decision_framework.md` | DOCUMENTATION_CHANGE | 7.1 | Security vs ETF decision framework |
| `docs/unified_optimizer_design.md` | DOCUMENTATION_CHANGE | 7.3A | Optimizer design document |

---

## UNTRACKED FILES — GENERATED ARTIFACTS (Root-level reports)

| File | Classification | Phase | Notes |
|---|---|---|---|
| `archetype_validation_report.md` | GENERATED_ARTIFACT | 7.2 | Generated by `_archetype_validation.py` |
| `cash_deployment_report.md` | GENERATED_ARTIFACT | 7.x | Generated cash deployment analysis |
| `cash_reconciliation_report.md` | GENERATED_ARTIFACT | 7.x | Generated cash reconciliation |
| `conviction_deployment_report.md` | GENERATED_ARTIFACT | 7.x | Generated conviction deployment |
| `conviction_model_quality_report.md` | GENERATED_ARTIFACT | 7.x | Generated conviction quality |
| `conviction_ranking_report.md` | GENERATED_ARTIFACT | 7.x | Generated conviction ranking |
| `coverage_denominator_report.md` | GENERATED_ARTIFACT | 7.x | Generated coverage denominator |
| `coverage_gap_report.md` | GENERATED_ARTIFACT | 7.x | Generated coverage gap |
| `coverage_reconciliation_report.md` | GENERATED_ARTIFACT | 7.x | Generated coverage reconciliation |
| `l1_allocation_gap_report.md` | GENERATED_ARTIFACT | 7.x | Generated L1 allocation gap |
| `optimizer_ui_validation_report.md` | GENERATED_ARTIFACT | 7.3B | Generated by Phase 7.3B implementation |
| `overlap_analysis_report.md` | GENERATED_ARTIFACT | 7.x | Generated overlap analysis |
| `portfolio_philosophy_validation_report.md` | GENERATED_ARTIFACT | 7.x | Generated validation report |
| `portfolio_reconciliation_report.md` | GENERATED_ARTIFACT | 7.x | Generated portfolio reconciliation |
| `recommendation_conflict_report.md` | GENERATED_ARTIFACT | 7.2 | Generated by `_generate_phase72_audit_reports.py` |
| `recommendation_explainability_report.md` | GENERATED_ARTIFACT | 7.x | Generated explainability report |
| `replay_alignment_audit.md` | GENERATED_ARTIFACT | 7.x | Generated replay alignment audit |
| `security_vs_etf_report.md` | GENERATED_ARTIFACT | 7.1 | Generated security vs ETF analysis |
| `strategic_narrative_audit.md` | GENERATED_ARTIFACT | 7.x | Generated narrative audit |
| `strategic_narrative_validation_report.md` | GENERATED_ARTIFACT | 7.x | Generated narrative validation |
| `taxonomy_clean_run_report.md` | GENERATED_ARTIFACT | 7.2 | Generated taxonomy clean run |
| `taxonomy_reconciliation_report.md` | GENERATED_ARTIFACT | 7.2 | Generated taxonomy reconciliation |
| `ui_archetype_consistency_report.md` | GENERATED_ARTIFACT | 7.2 | Generated UI archetype consistency |

---

## UNTRACKED FILES — GENERATED ARTIFACTS (Data)

| File / Directory | Classification | Phase | Notes |
|---|---|---|---|
| `data/allocation/` (6 files) | GENERATED_ARTIFACT | 6.2 | Allocation run outputs (evidence, overlay, manifest) |
| `data/derived/coverage_history.csv` | GENERATED_ARTIFACT | 7.x | Coverage history CSV |
| `data/derived/phase7_audit_data.json` | GENERATED_ARTIFACT | 7.x | Phase 7 audit data JSON |
| `data/exports/optimizer_candidate_report.md` | GENERATED_ARTIFACT | 7.3A | Optimizer candidate output |
| `data/exports/optimizer_vs_legacy_report.md` | GENERATED_ARTIFACT | 7.3A | Optimizer vs legacy comparison |

---

## UNTRACKED FILES — UTILITY SCRIPTS (operational tools)

| File | Classification | Phase | Notes |
|---|---|---|---|
| `scripts/apply_eligibility_flags.py` | EXPECTED_CODE_CHANGE | 6.x | Universe eligibility flag application |
| `scripts/assign_geography.py` | EXPECTED_CODE_CHANGE | 6.3 | Geography assignment utility |
| `scripts/compare_zacks_ess_vs_internet.py` | EXPECTED_CODE_CHANGE | 6.x | Zacks comparison utility |
| `scripts/diagnostics/merge_subtier_replays.py` | EXPECTED_CODE_CHANGE | 6.3 | Subtier replay merge diagnostic |
| `scripts/diagnostics/partial_publish_current.py` | EXPECTED_CODE_CHANGE | 6.x | Partial publish utility |
| `scripts/migrate_base_universe_headers.py` | EXPECTED_CODE_CHANGE | 6.x | Header migration script |
| `scripts/patch_universe_zacks.py` | EXPECTED_CODE_CHANGE | 6.x | Zacks data patch utility |
| `scripts/recalculate_allocation_targets.py` | EXPECTED_CODE_CHANGE | 6.2 | Allocation target recalculation |
| `scripts/refresh_portfolio_signals.py` | EXPECTED_CODE_CHANGE | 6.x | Portfolio signal refresh |
| `scripts/refresh_signals.py` | EXPECTED_CODE_CHANGE | 6.x | Signal refresh utility |
| `scripts/rescore_all_universe.py` | EXPECTED_CODE_CHANGE | 6.x | Universe rescoring utility |
| `scripts/research/factor_effectiveness_report.py` | EXPECTED_CODE_CHANGE | 6.4 | Factor effectiveness research |
| `scripts/research/generate_v2_scores.py` | EXPECTED_CODE_CHANGE | 6.4 | V2 score generation research |
| `scripts/run_classification_audit.py` | EXPECTED_CODE_CHANGE | 6.3 | Classification audit runner |

---

## UNTRACKED FILES — DIAGNOSTIC / DEBUG SCRIPTS (temporary)

| File | Classification | Phase | Notes |
|---|---|---|---|
| `scripts/_archetype_validation.py` | GENERATED_ARTIFACT | 7.2 | Temporary validation diagnostic |
| `scripts/_check_alignment.py` | GENERATED_ARTIFACT | 7.0 | Temporary alignment check |
| `scripts/_debug_enrichment.py` | GENERATED_ARTIFACT | 6.x | Temporary enrichment debug |
| `scripts/_debug_fields.py` | GENERATED_ARTIFACT | 6.x | Temporary field debug |
| `scripts/_debug_mega.py` | GENERATED_ARTIFACT | 6.3 | Temporary mega subtier debug |
| `scripts/_fi_before_after.py` | GENERATED_ARTIFACT | 6.x | Temporary before/after comparison |
| `scripts/_generate_conviction_model_quality_report.py` | GENERATED_ARTIFACT | 7.x | Report generator script |
| `scripts/_generate_conviction_ranking_report.py` | GENERATED_ARTIFACT | 7.x | Report generator script |
| `scripts/_generate_coverage_denominator_report.py` | GENERATED_ARTIFACT | 7.x | Report generator script |
| `scripts/_generate_coverage_gap_report.py` | GENERATED_ARTIFACT | 7.x | Report generator script |
| `scripts/_generate_coverage_report.py` | GENERATED_ARTIFACT | 7.x | Report generator script |
| `scripts/_generate_phase72_audit_reports.py` | GENERATED_ARTIFACT | 7.2 | Phase 7.2 audit report generator |
| `scripts/_generate_phase73a_optimizer_reports.py` | GENERATED_ARTIFACT | 7.3A | Phase 7.3A optimizer report generator |
| `scripts/_generate_recommendation_explainability_report.py` | GENERATED_ARTIFACT | 7.x | Report generator script |
| `scripts/_generate_reconciliation_report.py` | GENERATED_ARTIFACT | 7.2 | Reconciliation report generator |
| `scripts/_generate_replay_alignment_audit.py` | GENERATED_ARTIFACT | 7.x | Replay alignment report generator |
| `scripts/_generate_strategic_narrative_audit.py` | GENERATED_ARTIFACT | 7.x | Narrative audit generator |
| `scripts/_generate_strategic_narrative_validation_report.py` | GENERATED_ARTIFACT | 7.x | Narrative validation generator |
| `scripts/_generate_taxonomy_clean_run_report.py` | GENERATED_ARTIFACT | 7.2 | Taxonomy clean run generator |
| `scripts/_generate_taxonomy_report.py` | GENERATED_ARTIFACT | 7.2 | Taxonomy report generator |
| `scripts/_phase7_build_data.py` | GENERATED_ARTIFACT | 7.0 | Temporary phase 7 data builder |
| `scripts/_phase7_drilldown_extract.py` | GENERATED_ARTIFACT | 7.x | Temporary drilldown extractor |
| `scripts/_phase7_explore.py` | GENERATED_ARTIFACT | 7.x | Temporary phase 7 explorer |
| `scripts/_phase7_extract.py` | GENERATED_ARTIFACT | 7.x | Temporary phase 7 extractor |
| `scripts/_pmi_audit.py` | GENERATED_ARTIFACT | 7.1 | Temporary PMI audit script |
| `scripts/_pmi_audit_analysis.py` | GENERATED_ARTIFACT | 7.1 | Temporary PMI audit analysis |
| `scripts/_pmi_audit_analysis2.py` | GENERATED_ARTIFACT | 7.1 | Temporary PMI audit analysis v2 |
| `scripts/_pmi_audit_direct.py` | GENERATED_ARTIFACT | 7.1 | Temporary PMI direct audit |
| `scripts/_portfolio_philosophy_validation.py` | GENERATED_ARTIFACT | 7.x | Temporary philosophy validation |
| `scripts/_test_pipeline.py` | GENERATED_ARTIFACT | 6.x | Temporary pipeline test script |
| `scripts/_ui_archetype_consistency_report.py` | GENERATED_ARTIFACT | 7.2 | Temporary UI consistency report gen |

---

## ACCIDENTAL / UNKNOWN FILES

| File | Classification | Notes |
|---|---|---|
| `xyz` | ACCIDENTAL_CHANGE | Empty file (0 bytes). No purpose. Likely accidental `touch xyz` or stray shell command. |

---

## SUMMARY COUNTS

| Classification | Count (entries) |
|---|---|
| EXPECTED_CODE_CHANGE | 62 |
| GENERATED_ARTIFACT | 66 |
| TEST_CHANGE | 14 |
| CONFIG_CHANGE | 12 |
| DOCUMENTATION_CHANGE | 11 |
| ACCIDENTAL_CHANGE | 1 |
| UNKNOWN | 0 |
| **Total** | **166** |

> Note: 8 directory entries in git status expand to ~75 individual files. Entry count = 142 (git status lines); estimated file count = ~185.
