# Repository Code Footprint Report — Phase SC-H1

**Generated:** 2026-05-30  
**Scope:** All files modified or created across Phases 6.1–7.3B (post-WP-05D)  
**Note:** All Phase 6.x–7.3B work is in a single uncommitted working tree since commit `c8859f0`. Phase assignments are derived from file purpose and known phase scope, not individual git commits.

---

## Phase Reference

| Phase | Scope |
|---|---|
| WP-05D | Stock replay curve foundation (committed; some tracked-file modifications postdate this) |
| 6.1 | Portfolio alignment pipeline foundation — ingestion, models, server routes, initial UI |
| 6.2 | Allocation intelligence — allocation engine, allocation UI, mandate profiles |
| 6.3 | Classification — geography resolver, security type policy, market cap subtier |
| 6.4 | Effectiveness — composite versioning, factor contribution, research scripts |
| 7.0 | Portfolio analysis — alignment engine, recommendation engine, runner orchestrator |
| 7.1 | Vehicle suitability — ETF scoring, exposure decomposition, mandate intelligence, PMI |
| 7.2 | Reconciliation, archetype, taxonomy, trim intelligence, Phase E synthesis |
| 7.3A | Parallel optimizer — read-only conflict detection, scoring, ETF gate |
| 7.3B | Optimizer UI — conflict badges, Optimizer View block, Summary Panel |

---

## Code File Footprint by Phase

| File | First Modified Phase | Last Modified Phase |
|---|---|---|
| **src/portfolio/** | | |
| `src/portfolio/__init__.py` | 6.1 | 6.1 |
| `src/portfolio/models.py` | 6.1 | 7.1 |
| `src/portfolio/ingestion.py` | 6.1 | 6.1 |
| `src/portfolio/enrichment.py` | 6.1 | 7.0 |
| `src/portfolio/alignment.py` | 7.0 | 7.1 |
| `src/portfolio/recommendations.py` | 7.0 | 7.2 |
| `src/portfolio/runner.py` | 7.0 | 7.3A |
| `src/portfolio/mandate.py` | 7.1 | 7.2 |
| `src/portfolio/scoring.py` | 7.1 | 7.2 |
| `src/portfolio/exposure_decomposition.py` | 7.1 | 7.1 |
| `src/portfolio/reconciliation.py` | 7.2 | 7.2 |
| `src/portfolio/archetype.py` | 7.2 | 7.2 |
| `src/portfolio/taxonomy.py` | 7.2 | 7.2 |
| `src/portfolio/trim_intelligence.py` | 7.2 | 7.2 |
| `src/portfolio/phase_e_synthesis.py` | 7.2 | 7.2 |
| `src/portfolio/optimizer.py` | 7.3A | 7.3A |
| **src/allocation/** | | |
| `src/allocation/__init__.py` | 6.2 | 6.2 |
| `src/allocation/dimensions_loader.py` | 6.2 | 6.2 |
| `src/allocation/methodology_loader.py` | 6.2 | 6.2 |
| `src/allocation/models.py` | 6.2 | 6.2 |
| `src/allocation/recalculation_engine.py` | 6.2 | 6.2 |
| `src/allocation/replay_integration.py` | 6.2 | 6.2 |
| `src/allocation/structural_policy.py` | 6.2 | 6.2 |
| `src/allocation/tactical_overlay.py` | 6.2 | 6.2 |
| `src/allocation/validators.py` | 6.2 | 6.2 |
| **src/classification/** | | |
| `src/classification/__init__.py` | 6.3 | 6.3 |
| `src/classification/benchmark_assignment_engine.py` | 6.3 | 6.3 |
| `src/classification/classification_validators.py` | 6.3 | 6.3 |
| `src/classification/geography_resolver.py` | 6.3 | 6.3 |
| `src/classification/security_type_policy.py` | 6.3 | 6.3 |
| **src/effectiveness/** | | |
| `src/effectiveness/__init__.py` | 6.4 | 6.4 |
| `src/effectiveness/composite_versioning.py` | 6.4 | 6.4 |
| `src/effectiveness/factor_contribution.py` | 6.4 | 6.4 |
| **src/history/** (modified) | | |
| `src/history/analytical_universe_manager.py` | WP-04 | 6.x |
| `src/history/base_universe_manager.py` | WP-01 | 6.x |
| `src/history/allocation_manager.py` | 6.2 | 6.2 |
| **src/models/** (modified) | | |
| `src/models/analytical_models.py` | WP-02 | 6.x |
| `src/models/canonical_models.py` | WP-01 | 6.x |
| **src/normalize/** (modified) | | |
| `src/normalize/ess_normalizer.py` | WP-03 | 6.x |
| `src/normalize/provider_normalizer.py` | WP-03 | 6.x |
| **src/providers/fidelity/** (modified) | | |
| `src/providers/fidelity/fidelity_ess_adapter.py` | WP-03 | 6.x |
| `src/providers/fidelity/fidelity_schema_contract.py` | WP-03 | 6.x |
| **src/replay/** (modified) | | |
| `src/replay/foundation_service.py` | WP-04 | 6.x |
| `src/replay/replay_engine.py` | WP-05A | WP-05D |
| `src/replay/stock_replay_service.py` | WP-05D | WP-05D |
| **src/scoring/** | | |
| `src/scoring/fetch_danelfin_scores.py` | WP-05x | 6.x |
| `src/scoring/fetch_yahoo_supplemental.py` | WP-05x | 6.x |
| `src/scoring/fetch_zacks_scores.py` | WP-05x | 6.x |
| `src/scoring/fetch_security_metadata.py` | 6.x | 6.x |
| `src/scoring/market_cap_subtier_classifier.py` | 6.3 | 6.3 |
| **src/validation/** | | |
| `src/validation/replay_validator.py` | WP-05B | WP-05D |
| `src/validation/market_cap_subtier_validator.py` | 6.3 | 6.3 |
| **ui/** | | |
| `ui/outcome_visualization/app.js` | WP-04.1 | WP-05D |
| `ui/outcome_visualization/index.html` | WP-04.1 | WP-05D |
| `ui/portfolio_alignment/app.js` | 6.1 | 7.3B |
| `ui/portfolio_alignment/index.html` | 6.1 | 7.3B |
| `ui/allocation_intelligence/app.js` | 6.2 | 6.2 |
| `ui/allocation_intelligence/index.html` | 6.2 | 6.2 |
| **tests/** | | |
| `tests/test_wp04_1_ui_prototype.py` | WP-04.1 | 7.x |
| `tests/test_wp04_replay_foundation.py` | WP-04 | 7.x |
| `tests/test_dynamic_subtier_classification.py` | 6.3 | 6.3 |
| `tests/test_signal_fetch_resume.py` | 6.x | 6.x |
| `tests/test_mandate_intelligence.py` | 7.0 | 7.1 |
| `tests/test_vehicle_suitability.py` | 7.1 | 7.1 |
| `tests/test_etf_exposure_decomposition.py` | 7.1 | 7.1 |
| `tests/test_cash_semantics.py` | 7.x | 7.x |
| `tests/test_reconciliation.py` | 7.2 | 7.2 |
| `tests/test_archetype.py` | 7.2 | 7.2 |
| `tests/test_phase_d_trim_intelligence.py` | 7.2 | 7.2 |
| `tests/test_phase_e_synthesis.py` | 7.2 | 7.2 |
| `tests/test_optimizer.py` | 7.3A | 7.3A |
| `tests/test_7_3b_optimizer_ui.py` | 7.3B | 7.3B |
| **scripts/** | | |
| `scripts/run_outcome_ui.py` | WP-04.1 | 7.3B |
| `scripts/score_lookup.py` | WP-05x | 6.x |
| `scripts/diagnostics/build_wp04_foundation.py` | WP-04 | 6.x |
| `scripts/diagnostics/build_wp05b_replay_matrix.py` | WP-05B | 6.x |
| `scripts/recalculate_allocation_targets.py` | 6.2 | 6.2 |
| `scripts/apply_eligibility_flags.py` | 6.x | 6.x |
| `scripts/assign_geography.py` | 6.3 | 6.3 |
| `scripts/run_classification_audit.py` | 6.3 | 6.3 |
| `scripts/migrate_base_universe_headers.py` | 6.x | 6.x |
| `scripts/patch_universe_zacks.py` | 6.x | 6.x |
| `scripts/refresh_signals.py` | 6.x | 6.x |
| `scripts/refresh_portfolio_signals.py` | 6.x | 6.x |
| `scripts/rescore_all_universe.py` | 6.x | 6.x |
| `scripts/compare_zacks_ess_vs_internet.py` | 6.x | 6.x |
| `scripts/diagnostics/merge_subtier_replays.py` | 6.3 | 6.3 |
| `scripts/diagnostics/partial_publish_current.py` | 6.x | 6.x |
| `scripts/research/factor_effectiveness_report.py` | 6.4 | 6.4 |
| `scripts/research/generate_v2_scores.py` | 6.4 | 6.4 |
| **config/** | | |
| `config/allocation_dimensions.yaml` | 6.2 | 6.2 |
| `config/allocation_methodology.yaml` | 6.2 | 6.2 |
| `config/allocation_policy.yaml` | 6.2 | 6.2 |
| `config/allocation_models/balanced_allocation_profile.yaml` | 6.2 | 6.2 |
| `config/allocation_models/concentrated_alpha_profile.yaml` | 6.2 | 6.2 |
| `config/allocation_models/growth_allocation_profile.yaml` | 6.2 | 6.2 |
| `config/etf_exposure_decomposition.yaml` | 7.1 | 7.1 |
| `config/geography_overrides.yaml` | 6.3 | 6.3 |
| `config/market_cap_subtier_policy.yaml` | 6.3 | 6.3 |
| `config/security_type_policy.yaml` | 6.3 | 6.3 |
| `config/adr_domicile_policy.yaml` | 6.x | 6.x |
| `.gitignore` | WP-01 | 6.x |

---

## Files per Phase (Code Only — excludes tests, docs, artifacts)

| Phase | New Files | Modified Files | Key Additions |
|---|---|---|---|
| WP-05D | 1 | 4 | `stock_replay_service.py`; `replay_engine.py`, `ui/outcome_visualization/` major additions |
| 6.1 | 4 | 1 | `src/portfolio/{__init__,models,ingestion,enrichment}`; `ui/portfolio_alignment/`; `run_outcome_ui.py` API routes |
| 6.2 | 10 | 0 | `src/allocation/` (9 files); `src/history/allocation_manager.py`; `ui/allocation_intelligence/`; `config/allocation_*` |
| 6.3 | 7 | 0 | `src/classification/` (5 files); `src/scoring/market_cap_subtier_classifier.py`; `src/validation/market_cap_subtier_validator.py` |
| 6.4 | 3 | 0 | `src/effectiveness/` (3 files); `scripts/research/` (2 scripts) |
| 6.x | ~12 | ~12 | Various scoring fetchers, scoring utilities, universe managers, provider adapters |
| 7.0 | 3 | 1 | `alignment.py`, `recommendations.py`, `runner.py`; `enrichment.py` extended |
| 7.1 | 3 | 2 | `mandate.py`, `scoring.py`, `exposure_decomposition.py`; `models.py`, `alignment.py` extended |
| 7.2 | 5 | 2 | `reconciliation.py`, `archetype.py`, `taxonomy.py`, `trim_intelligence.py`, `phase_e_synthesis.py`; `recommendations.py`, `scoring.py` extended |
| 7.3A | 1 | 1 | `optimizer.py`; `runner.py` extended (optimizer injection) |
| 7.3B | 0 | 2 | `ui/portfolio_alignment/app.js` (optimizer badges/view/summary); `ui/portfolio_alignment/index.html` (CSS + placeholder) |

---

## Largest Single-Phase Code Contributions

| Rank | Phase | Estimated LoC Added | Primary Files |
|---|---|---|---|
| 1 | WP-05D | ~1,100 | `ui/outcome_visualization/app.js` (+784), `ui/outcome_visualization/index.html` (+396) |
| 2 | 6.x (aggregate) | ~700 | Scoring fetchers, universe managers, provider adapters |
| 3 | 7.2 | ~600 | 5 new portfolio modules (reconciliation, archetype, taxonomy, trim, synthesis) |
| 4 | 6.2 | ~500 | `src/allocation/` (9 files), allocation UI, config profiles |
| 5 | 7.0/7.1 | ~450 | Alignment engine, recommendation engine, runner, mandate, scoring |
| 6 | 7.3A | ~400 | `optimizer.py` full parallel optimizer implementation |
| 7 | 7.3B | ~300 | `app.js` optimizer UI additions (badges, view block, summary panel) |
