# Remaining Dirty File Inventory — Phase SC-H2B

**Generated:** 2026-05-30  
**State:** Post SC-H2A cleanup  
**Total entries:** 92 (25 modified + 67 untracked)

---

## Classification Key

| Class | Meaning |
|---|---|
| COMMIT | Include in a stabilization commit |
| ARCHIVE | Move to archive location; do not commit in current location |
| IGNORE | Add to `.gitignore` and/or untrack via `git rm --cached`; do not commit |
| INVESTIGATE | Requires manual review before final disposition |

---

## MODIFIED TRACKED FILES (25 entries)

### Infrastructure & Scoring Layer (pre-Phase-6 modifications)

| File | +/- Lines | Classification | Rationale |
|---|---|---|---|
| `src/history/analytical_universe_manager.py` | +364 | COMMIT | Core universe management; extended for Phase 6.x composite scoring, subtier classification, and allocation pipeline integration |
| `src/history/base_universe_manager.py` | +1 | COMMIT | Single-line field addition for Phase 6.x compatibility; low risk |
| `src/models/analytical_models.py` | — | COMMIT | Analytical model extensions for Phase 6.x |
| `src/models/canonical_models.py` | +3 | COMMIT | 3-line field additions for Phase 6.x schema compatibility |
| `src/normalize/ess_normalizer.py` | +13 | COMMIT | ESS normalization extended to handle new provider fields |
| `src/normalize/provider_normalizer.py` | +1 | COMMIT | Single-line normalization fix for Phase 6.x provider integration |
| `src/providers/fidelity/fidelity_ess_adapter.py` | +60 | COMMIT | Fidelity ESS adapter extended with Phase 6.x field mappings |
| `src/providers/fidelity/fidelity_schema_contract.py` | +15 | COMMIT | Schema contract updates for new ESS fields |
| `src/replay/foundation_service.py` | +92 | COMMIT | Foundation service extended for portfolio analysis API endpoints |
| `src/replay/replay_engine.py` | +39 | COMMIT | WP-05D stock replay curve additions |
| `src/replay/stock_replay_service.py` | +2 | COMMIT | WP-05D minor additions |
| `src/scoring/fetch_danelfin_scores.py` | +52 | COMMIT | Danelfin fetcher extended with resume logic and portfolio filtering |
| `src/scoring/fetch_yahoo_supplemental.py` | +50 | COMMIT | Yahoo fetcher extended with resume logic |
| `src/scoring/fetch_zacks_scores.py` | +59 | COMMIT | Zacks fetcher extended with resume logic and portfolio filtering |
| `src/validation/replay_validator.py` | +17 | COMMIT | WP-05D replay validator additions |

### Server & Server-Adjacent

| File | +/- Lines | Classification | Rationale |
|---|---|---|---|
| `scripts/run_outcome_ui.py` | +414 | COMMIT | Major additions: POST /api/portfolio/analyze, GET /api/portfolio/runs, POST /api/signal-refresh, full portfolio alignment server routes |
| `scripts/diagnostics/build_wp04_foundation.py` | +6 | COMMIT | Extended to call `ensure_signals_fresh()`; needed for Phase 6.x diagnostic builds |
| `scripts/diagnostics/build_wp05b_replay_matrix.py` | +26 | COMMIT | Extended to call `ensure_signals_fresh()`; matrix builder updated for Phase 6.x |
| `scripts/score_lookup.py` | +13 | COMMIT | Score lookup utility extended for Phase 6.x composite scoring |

### Outcome Visualization UI (WP-05D)

| File | +/- Lines | Classification | Rationale |
|---|---|---|---|
| `ui/outcome_visualization/app.js` | +784 | COMMIT | WP-05D stock replay curve UI — interactive chart, symbol lookup, subtier filter dropdown |
| `ui/outcome_visualization/index.html` | +396 | COMMIT | WP-05D HTML structure and styling for stock replay curve |

### Tests (WP-04 adaptations)

| File | +/- Lines | Classification | Rationale |
|---|---|---|---|
| `tests/test_wp04_1_ui_prototype.py` | +10 | COMMIT | Minor adaptation for Phase 6.x API contract changes; all assertions valid |
| `tests/test_wp04_replay_foundation.py` | +6/-1 | COMMIT | Minor adaptation for Phase 6.x API contract changes; all assertions valid |

### Config & State

| File | +/- Lines | Classification | Rationale |
|---|---|---|---|
| `.gitignore` | varies | COMMIT | SC-H2A gitignore hardening — 26 new patterns added for artifacts, diagnostics, and derived outputs |
| `navigation_state.yaml` | +17/-17 | IGNORE | Auto-updated UI waypoint state (no content value); file is currently tracked — requires `git rm --cached navigation_state.yaml` to untrack before ignoring |

---

## UNTRACKED FILES (67 entries, expanded from directory entries)

### Core Source — New Modules (Phases 6.1–7.3A)

| File | Phase | Classification | Rationale |
|---|---|---|---|
| `src/portfolio/__init__.py` | 6.1 | COMMIT | Package init |
| `src/portfolio/models.py` | 6.1 | COMMIT | Portfolio models (Holding, PortfolioSummary, etc.) |
| `src/portfolio/ingestion.py` | 6.1 | COMMIT | CSV portfolio ingestion pipeline |
| `src/portfolio/enrichment.py` | 6.1 | COMMIT | Holding enrichment with scoring data |
| `src/portfolio/alignment.py` | 7.0 | COMMIT | Alignment engine — asset class weight analysis |
| `src/portfolio/recommendations.py` | 7.0 | COMMIT | Recommendation engine |
| `src/portfolio/runner.py` | 7.0 | COMMIT | Orchestration runner (parallel analysis) |
| `src/portfolio/mandate.py` | 7.1 | COMMIT | Mandate intelligence |
| `src/portfolio/scoring.py` | 7.1 | COMMIT | Vehicle scoring |
| `src/portfolio/exposure_decomposition.py` | 7.1 | COMMIT | ETF exposure decomposition |
| `src/portfolio/reconciliation.py` | 7.2 | COMMIT | Position reconciliation |
| `src/portfolio/archetype.py` | 7.2 | COMMIT | Portfolio archetype classification |
| `src/portfolio/taxonomy.py` | 7.2 | COMMIT | Portfolio taxonomy |
| `src/portfolio/trim_intelligence.py` | 7.2 | COMMIT | Trim intelligence module |
| `src/portfolio/phase_e_synthesis.py` | 7.2 | COMMIT | Phase E synthesis |
| `src/portfolio/optimizer.py` | 7.3A | COMMIT | Parallel optimizer |
| `src/allocation/__init__.py` | 6.2 | COMMIT | Allocation package init |
| `src/allocation/dimensions_loader.py` | 6.2 | COMMIT | Allocation dimensions loader |
| `src/allocation/methodology_loader.py` | 6.2 | COMMIT | Allocation methodology loader |
| `src/allocation/models.py` | 6.2 | COMMIT | Allocation models |
| `src/allocation/recalculation_engine.py` | 6.2 | COMMIT | Allocation recalculation engine |
| `src/allocation/replay_integration.py` | 6.2 | COMMIT | Allocation-replay integration |
| `src/allocation/structural_policy.py` | 6.2 | COMMIT | Structural policy |
| `src/allocation/tactical_overlay.py` | 6.2 | COMMIT | Tactical overlay |
| `src/allocation/validators.py` | 6.2 | COMMIT | Allocation validators |
| `src/classification/__init__.py` | 6.3 | COMMIT | Classification package init |
| `src/classification/benchmark_assignment_engine.py` | 6.3 | COMMIT | Benchmark assignment engine |
| `src/classification/classification_validators.py` | 6.3 | COMMIT | Classification validators |
| `src/classification/geography_resolver.py` | 6.3 | COMMIT | Geography resolver |
| `src/classification/security_type_policy.py` | 6.3 | COMMIT | Security type policy |
| `src/effectiveness/__init__.py` | 6.4 | COMMIT | Effectiveness package init |
| `src/effectiveness/composite_versioning.py` | 6.4 | COMMIT | Composite versioning |
| `src/effectiveness/factor_contribution.py` | 6.4 | COMMIT | Factor contribution |
| `src/history/allocation_manager.py` | 6.2 | COMMIT | Allocation history manager |
| `src/scoring/fetch_security_metadata.py` | 6.x | COMMIT | Security metadata fetcher |
| `src/scoring/market_cap_subtier_classifier.py` | 6.3 | COMMIT | Market cap subtier classifier |
| `src/validation/market_cap_subtier_validator.py` | 6.3 | COMMIT | Market cap subtier validator |

### UI (New Modules)

| File | Phase | Classification | Rationale |
|---|---|---|---|
| `ui/portfolio_alignment/app.js` | 6.1→7.3B | COMMIT | Portfolio alignment UI (complete; includes Phase 7.3B optimizer badges, view block, summary panel) |
| `ui/portfolio_alignment/index.html` | 6.1→7.3B | COMMIT | Portfolio alignment HTML (complete; includes Phase 7.3B CSS and optimizer placeholder) |
| `ui/allocation_intelligence/app.js` | 6.2 | COMMIT | Allocation intelligence UI |
| `ui/allocation_intelligence/index.html` | 6.2 | COMMIT | Allocation intelligence HTML |

### Tests (New)

| File | Phase | Classification | Rationale |
|---|---|---|---|
| `tests/test_dynamic_subtier_classification.py` | 6.3 | COMMIT | Dynamic subtier classification tests |
| `tests/test_signal_fetch_resume.py` | 6.x | COMMIT | Signal fetch resume tests |
| `tests/test_mandate_intelligence.py` | 7.0 | COMMIT | Mandate intelligence tests |
| `tests/test_vehicle_suitability.py` | 7.1 | COMMIT | Vehicle suitability tests |
| `tests/test_etf_exposure_decomposition.py` | 7.1 | COMMIT | ETF exposure decomposition tests |
| `tests/test_cash_semantics.py` | 7.x | COMMIT | Cash semantics tests |
| `tests/test_reconciliation.py` | 7.2 | COMMIT | Reconciliation tests |
| `tests/test_archetype.py` | 7.2 | COMMIT | Archetype tests |
| `tests/test_phase_d_trim_intelligence.py` | 7.2 | COMMIT | Trim intelligence tests |
| `tests/test_phase_e_synthesis.py` | 7.2 | COMMIT | Phase E synthesis tests |
| `tests/test_optimizer.py` | 7.3A | COMMIT | Optimizer tests |
| `tests/test_7_3b_optimizer_ui.py` | 7.3B | COMMIT | Optimizer UI tests (Phase 7.3B deliverable) |

### Config (New)

| File | Phase | Classification | Rationale |
|---|---|---|---|
| `config/adr_domicile_policy.yaml` | 6.x | COMMIT | ADR domicile policy |
| `config/allocation_dimensions.yaml` | 6.2 | COMMIT | Allocation dimensions |
| `config/allocation_methodology.yaml` | 6.2 | COMMIT | Allocation methodology |
| `config/allocation_models/balanced_allocation_profile.yaml` | 6.2 | COMMIT | Balanced allocation profile |
| `config/allocation_models/concentrated_alpha_profile.yaml` | 6.2 | COMMIT | Concentrated alpha profile |
| `config/allocation_models/growth_allocation_profile.yaml` | 6.2 | COMMIT | Growth allocation profile |
| `config/allocation_policy.yaml` | 6.2 | COMMIT | Allocation policy |
| `config/etf_exposure_decomposition.yaml` | 7.1 | COMMIT | ETF exposure decomposition config |
| `config/geography_overrides.yaml` | 6.3 | COMMIT | Geography overrides |
| `config/market_cap_subtier_policy.yaml` | 6.3 | COMMIT | Market cap subtier policy |
| `config/security_type_policy.yaml` | 6.3 | COMMIT | Security type policy |

### Docs (New)

| File | Phase | Classification | Rationale |
|---|---|---|---|
| `docs/ALLOCATION_INTELLIGENCE_PHILOSOPHY.md` | 6.2 | COMMIT | Architecture philosophy doc |
| `docs/ALLOCATION_PRIMER_WHY_THESE_NUMBERS.md` | 6.2 | COMMIT | Allocation primer — authored design doc |
| `docs/ASSET_CLASS_FIRST_ARCHITECTURE.md` | 6.x | COMMIT | Architecture decision doc |
| `docs/HIERARCHICAL_ALLOCATION_MODEL.md` | 6.2 | COMMIT | Allocation model design doc |
| `docs/VEHICLE_SELECTION_RATIONALE.md` | 7.1 | COMMIT | Vehicle selection design doc |
| `docs/conflict_graph_report.md` | 7.3 | COMMIT | Architecture design doc (224 lines) — specifies conflict taxonomy and conflict graph for Phase 7.3; NOT a generated runtime report despite the filename |
| `docs/equity-summary-score-methodology.pdf` | 6.x | COMMIT | Provider scoring methodology reference PDF |
| `docs/migration_plan.md` | 6.x | COMMIT | Migration planning doc |
| `docs/recommendation_flow_analysis.md` | 7.x | COMMIT | Recommendation flow design analysis |
| `docs/security_vs_etf_decision_framework.md` | 7.1 | COMMIT | Security-vs-ETF decision framework doc |
| `docs/unified_optimizer_design.md` | 7.3A | COMMIT | Optimizer architecture design doc |

### Operational Scripts (New)

| File | Phase | Classification | Rationale |
|---|---|---|---|
| `scripts/apply_eligibility_flags.py` | 6.x | COMMIT | Operational utility — eligibility flag application |
| `scripts/assign_geography.py` | 6.3 | COMMIT | Operational utility — geography assignment |
| `scripts/compare_zacks_ess_vs_internet.py` | 6.x | INVESTIGATE | 21-line script; no module structure; hardcoded to `ESS_2026May14.csv`; lacks `_` prefix but is clearly a one-time validation tool. **Resolved: ARCHIVE** — functionally expired (hardcoded ESS file date), no production value, but preserve in `scripts/archive/` as Phase 6.x audit evidence. |
| `scripts/diagnostics/merge_subtier_replays.py` | 6.3 | COMMIT | Diagnostic utility for subtier replay merging |
| `scripts/diagnostics/partial_publish_current.py` | 6.x | COMMIT | Diagnostic utility — partial publish |
| `scripts/migrate_base_universe_headers.py` | 6.x | COMMIT | Operational migration utility |
| `scripts/patch_universe_zacks.py` | 6.x | COMMIT | Operational utility — Zacks universe patching |
| `scripts/recalculate_allocation_targets.py` | 6.2 | COMMIT | Allocation target recalculation utility |
| `scripts/refresh_portfolio_signals.py` | 6.x | COMMIT | Portfolio signal refresh utility (distinct from `refresh_signals.py`: targets a fixed portfolio symbol list, patches `analytical_universe.csv`) |
| `scripts/refresh_signals.py` | 6.x | COMMIT | **Core dependency**: imported by `run_outcome_ui.py`, `build_wp04_foundation.py`, `build_wp05b_replay_matrix.py`; exposes `ensure_signals_fresh()` |
| `scripts/rescore_all_universe.py` | 6.x | COMMIT | Operational utility — full universe rescore |
| `scripts/research/factor_effectiveness_report.py` | 6.4 | COMMIT | Phase 6.4 factor effectiveness research script |
| `scripts/research/generate_v2_scores.py` | 6.4 | COMMIT | Phase 6.4 v2 score generation script |
| `scripts/run_classification_audit.py` | 6.3 | COMMIT | Classification audit runner |

### Archive Directory (New)

| Entry | Classification | Rationale |
|---|---|---|
| `scripts/archive/` (14 files) | COMMIT | Organized archive of report generators; `scripts/archive/` is a legitimate project structure directory; the 14 `_generate_*.py` files inside are appropriately archived |

### Data Exports (Generated)

| File | Classification | Rationale |
|---|---|---|
| `data/exports/optimizer_candidate_report.md` | ARCHIVE | Generated by `_generate_phase73a_optimizer_reports.py` (now archived); point-in-time Phase 7.3A run output; move to `data/exports/archive/` |
| `data/exports/optimizer_vs_legacy_report.md` | ARCHIVE | Same origin; same disposition |

### Hygiene & Process Docs (SC-H1/H2)

| File | Classification | Rationale |
|---|---|---|
| `commit_candidate_report.md` | COMMIT | SC-H1 hygiene deliverable; documents pre-cleanup commit candidate analysis |
| `generated_artifact_audit.md` | COMMIT | SC-H1 hygiene deliverable; documents artifact classification |
| `optimizer_ui_validation_report.md` | COMMIT | Phase 7.3B deliverable; documents live optimizer validation results |
| `repo_code_footprint.md` | COMMIT | SC-H1 hygiene deliverable; documents phase-to-file footprint |
| `repo_dirty_inventory.md` | COMMIT | SC-H1 hygiene deliverable; original dirty file inventory |
| `stabilization_step1_report.md` | COMMIT | SC-H2A deliverable; documents step 1 cleanup actions |
| `unexpected_dirty_files.md` | COMMIT | SC-H1 hygiene deliverable; documents investigation results |

---

## Summary

| Classification | Count (entries) |
|---|---|
| COMMIT | 88 |
| ARCHIVE | 3 (`data/exports/` ×2 + `compare_zacks_ess_vs_internet.py` resolved to ARCHIVE) |
| IGNORE | 1 (`navigation_state.yaml` — tracked; needs `git rm --cached`) |
| INVESTIGATE | 0 (all resolved) |
| **Total** | **92** |
