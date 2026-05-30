# Stabilization Step 1 Report — Phase SC-H2A

**Generated:** 2026-05-30  
**Branch:** `main`  
**Last commit:** `c8859f0`  
**Test suite:** 504 / 504 passing

---

## A — Files Removed

| File | Reason |
|---|---|
| `xyz` | Accidental 0-byte file; stray shell artifact; unreferenced by any module or phase |

**Removed count: 1**

---

## B — Files Archived

All 14 `_generate_*.py` scripts moved from `scripts/` to `scripts/archive/`.  
`scripts/archive/` directory created new.

| Original Path | Archived To |
|---|---|
| `scripts/_generate_conviction_model_quality_report.py` | `scripts/archive/` |
| `scripts/_generate_conviction_ranking_report.py` | `scripts/archive/` |
| `scripts/_generate_coverage_denominator_report.py` | `scripts/archive/` |
| `scripts/_generate_coverage_gap_report.py` | `scripts/archive/` |
| `scripts/_generate_coverage_report.py` | `scripts/archive/` |
| `scripts/_generate_phase72_audit_reports.py` | `scripts/archive/` |
| `scripts/_generate_phase73a_optimizer_reports.py` | `scripts/archive/` |
| `scripts/_generate_recommendation_explainability_report.py` | `scripts/archive/` |
| `scripts/_generate_reconciliation_report.py` | `scripts/archive/` |
| `scripts/_generate_replay_alignment_audit.py` | `scripts/archive/` |
| `scripts/_generate_strategic_narrative_audit.py` | `scripts/archive/` |
| `scripts/_generate_strategic_narrative_validation_report.py` | `scripts/archive/` |
| `scripts/_generate_taxonomy_clean_run_report.py` | `scripts/archive/` |
| `scripts/_generate_taxonomy_report.py` | `scripts/archive/` |

**Archived count: 14**  
**Git status delta: 14 individual `??` entries collapsed to 1 `?? scripts/archive/` entry**

---

## C — New `.gitignore` Entries

The following patterns were appended to `.gitignore`:

| Pattern | Effect |
|---|---|
| `navigation_state.yaml` | Prevent future untracked state (file is currently tracked/modified; pattern applies to new instances) |
| `data/allocation/` | Gitignore runtime allocation outputs (was partially covered; now fully covered) |
| `data/derived/` | Gitignore derived CSV/JSON outputs |
| `scripts/_*.py` | Gitignore all diagnostic/debug scripts with underscore prefix |
| `archetype_validation_report.md` | Auto-generated report |
| `cash_deployment_report.md` | Auto-generated report |
| `cash_reconciliation_report.md` | Auto-generated report |
| `conviction_deployment_report.md` | Auto-generated report |
| `conviction_model_quality_report.md` | Auto-generated report |
| `conviction_ranking_report.md` | Auto-generated report |
| `coverage_denominator_report.md` | Auto-generated report |
| `coverage_gap_report.md` | Auto-generated report |
| `coverage_reconciliation_report.md` | Auto-generated report |
| `l1_allocation_gap_report.md` | Auto-generated report |
| `overlap_analysis_report.md` | Auto-generated report |
| `portfolio_philosophy_validation_report.md` | Auto-generated report |
| `portfolio_reconciliation_report.md` | Auto-generated report |
| `recommendation_conflict_report.md` | Auto-generated report |
| `recommendation_explainability_report.md` | Auto-generated report |
| `replay_alignment_audit.md` | Auto-generated report |
| `security_vs_etf_report.md` | Auto-generated report |
| `strategic_narrative_audit.md` | Auto-generated report |
| `strategic_narrative_validation_report.md` | Auto-generated report |
| `taxonomy_clean_run_report.md` | Auto-generated report |
| `taxonomy_reconciliation_report.md` | Auto-generated report |
| `ui_archetype_consistency_report.md` | Auto-generated report |

**Note:** `optimizer_ui_validation_report.md` is NOT gitignored — it remains a tracked Phase 7.3B deliverable.

**New gitignore pattern count: 26**  
**Entries removed from `git status` by gitignore: 37** (22 root reports + 14 archive entries - 1 new archive dir + data/derived entries)

---

## D — Dirty-File Count Before

| Category | Count |
|---|---|
| Modified tracked files (`M`) | 25 |
| Untracked files/dirs (`??`) | 117 |
| **Total** | **142** |

---

## E — Dirty-File Count After

| Category | Count |
|---|---|
| Modified tracked files (`M`) | 25 |
| Untracked files/dirs (`??`) | 66 |
| **Total** | **91** |

**Net reduction: 51 entries**  
**Reduction breakdown:**
- 22 root-level report `.md` files → gitignored
- 14 `_generate_*.py` individual entries → collapsed to 1 `scripts/archive/` directory entry (net -13)
- `data/allocation/` and `data/derived/` subentries → gitignored (net -15, approximate)
- `xyz` → deleted (-1)

---

## F — Remaining Dirty Files by Category

### Modified tracked files — 25 entries

| Category | Count | Files |
|---|---|---|
| **Code** | 19 | `src/history/analytical_universe_manager.py`, `src/history/base_universe_manager.py`, `src/models/analytical_models.py`, `src/models/canonical_models.py`, `src/normalize/ess_normalizer.py`, `src/normalize/provider_normalizer.py`, `src/providers/fidelity/fidelity_ess_adapter.py`, `src/providers/fidelity/fidelity_schema_contract.py`, `src/replay/foundation_service.py`, `src/replay/replay_engine.py`, `src/replay/stock_replay_service.py`, `src/scoring/fetch_danelfin_scores.py`, `src/scoring/fetch_yahoo_supplemental.py`, `src/scoring/fetch_zacks_scores.py`, `src/validation/replay_validator.py`, `scripts/diagnostics/build_wp04_foundation.py`, `scripts/diagnostics/build_wp05b_replay_matrix.py`, `scripts/run_outcome_ui.py`, `scripts/score_lookup.py` |
| **Tests** | 2 | `tests/test_wp04_1_ui_prototype.py`, `tests/test_wp04_replay_foundation.py` |
| **UI** | 2 | `ui/outcome_visualization/app.js`, `ui/outcome_visualization/index.html` |
| **Config (.gitignore)** | 1 | `.gitignore` |
| **Investigate** | 1 | `navigation_state.yaml` *(tracked auto-generated file; gitignored pattern added but requires `git rm --cached` to fully untrack)* |

### Untracked files — 66 entries

| Category | Count | Examples |
|---|---|---|
| **Code** | 10 | `src/allocation/`, `src/classification/`, `src/effectiveness/` (3 files), `src/history/allocation_manager.py`, `src/portfolio/`, `src/scoring/` (2 files), `src/validation/market_cap_subtier_validator.py` |
| **Tests** | 12 | `tests/test_7_3b_optimizer_ui.py`, `tests/test_archetype.py`, `tests/test_cash_semantics.py`, `tests/test_dynamic_subtier_classification.py`, `tests/test_etf_exposure_decomposition.py`, `tests/test_mandate_intelligence.py`, `tests/test_optimizer.py`, `tests/test_phase_d_trim_intelligence.py`, `tests/test_phase_e_synthesis.py`, `tests/test_reconciliation.py`, `tests/test_signal_fetch_resume.py`, `tests/test_vehicle_suitability.py` |
| **Config** | 9 | `config/adr_domicile_policy.yaml`, `config/allocation_dimensions.yaml`, `config/allocation_methodology.yaml`, `config/allocation_models/`, `config/allocation_policy.yaml`, `config/etf_exposure_decomposition.yaml`, `config/geography_overrides.yaml`, `config/market_cap_subtier_policy.yaml`, `config/security_type_policy.yaml` |
| **Docs** | 11 | `docs/ALLOCATION_INTELLIGENCE_PHILOSOPHY.md`, `docs/ALLOCATION_PRIMER_WHY_THESE_NUMBERS.md`, `docs/ASSET_CLASS_FIRST_ARCHITECTURE.md`, `docs/HIERARCHICAL_ALLOCATION_MODEL.md`, `docs/VEHICLE_SELECTION_RATIONALE.md`, `docs/conflict_graph_report.md`, `docs/equity-summary-score-methodology.pdf`, `docs/migration_plan.md`, `docs/recommendation_flow_analysis.md`, `docs/security_vs_etf_decision_framework.md`, `docs/unified_optimizer_design.md` |
| **Scripts (operational)** | 13 | `scripts/apply_eligibility_flags.py`, `scripts/assign_geography.py`, `scripts/compare_zacks_ess_vs_internet.py`, `scripts/diagnostics/merge_subtier_replays.py`, `scripts/diagnostics/partial_publish_current.py`, `scripts/migrate_base_universe_headers.py`, `scripts/patch_universe_zacks.py`, `scripts/recalculate_allocation_targets.py`, `scripts/refresh_portfolio_signals.py`, `scripts/refresh_signals.py`, `scripts/rescore_all_universe.py`, `scripts/research/`, `scripts/run_classification_audit.py` |
| **UI** | 2 | `ui/allocation_intelligence/`, `ui/portfolio_alignment/` |
| **Archive (new)** | 1 | `scripts/archive/` |
| **Data exports** | 2 | `data/exports/optimizer_candidate_report.md`, `data/exports/optimizer_vs_legacy_report.md` *(SHOULD_ARCHIVE per SC-H1)* |
| **SC-H1 / hygiene docs** | 6 | `commit_candidate_report.md`, `generated_artifact_audit.md`, `optimizer_ui_validation_report.md`, `repo_code_footprint.md`, `repo_dirty_inventory.md`, `unexpected_dirty_files.md` |

---

## Validation Checklist

| Check | Status |
|---|---|
| No source files changed except `.gitignore` | PASS |
| No tests modified | PASS |
| No portfolio logic modified | PASS |
| No optimizer logic modified | PASS |
| No UI logic modified | PASS |
| No commits created | PASS |
| `xyz` deleted | PASS |
| 14 `_generate_*.py` scripts moved to `scripts/archive/` | PASS |
| 26 new `.gitignore` patterns added | PASS |
| `optimizer_ui_validation_report.md` NOT gitignored | PASS |

---

**Step 1 complete. Stopped per instructions. Awaiting next step directive.**
