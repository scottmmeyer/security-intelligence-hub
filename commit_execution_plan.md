# Commit Execution Plan — Phase SC-H2C

**Generated:** 2026-05-30  
**Branch:** `main`  
**Last commit:** `c8859f0`  
**State:** Post SC-H2A + SC-H2B + SC-H2C final hygiene  
**Test suite:** 504 / 504 passing

---

## Pre-Flight State

| Check | Status |
|---|---|
| `xyz` deleted | ✓ |
| `navigation_state.yaml` untracked (`git rm --cached`) | ✓ |
| `data/exports/optimizer_*.md` archived to `data/exports/archive/` | ✓ |
| `scripts/compare_zacks_ess_vs_internet.py` archived to `scripts/archive/` | ✓ |
| 22 root-level reports gitignored | ✓ |
| `scripts/_*.py` pattern gitignored | ✓ |
| `data/allocation/` and `data/derived/` gitignored | ✓ |
| All tests passing | ✓ (504/504) |
| Remaining dirty entries | 92 (25 modified/deleted + 67 untracked) |
| All entries classified | ✓ (0 INVESTIGATE remaining) |

---

## Execution Order

**Recommended order:** A → B → C → D → E

Rationale: Each commit builds on the previous. Tests in each group depend on the source modules in the same or earlier commit. Commit E (hygiene) is last so all process docs exist before they are staged.

---

## Commit A — Portfolio Intelligence Foundation

**Scope:** Pre-Phase-6 infrastructure extensions + all Phase 6.1–6.4 modules

**Commit message:**
```
Add portfolio intelligence foundation: scoring pipeline, universe management,
allocation engine, classification, effectiveness, subtier architecture (Phases 6.1–6.4)

- Extended analytical_universe_manager, ESS normalizer, provider adapters,
  and scoring fetchers (Zacks/Yahoo/Danelfin) for Phase 6.x composite scoring
- Added src/allocation/ (9 modules): recalculation engine, allocation methodology,
  replay integration, structural policy, tactical overlay
- Added src/classification/ (5 modules): geography resolver, benchmark assignment,
  security type policy, subtier classifier
- Added src/effectiveness/ (3 modules): composite versioning, factor contribution
- Added allocation config: dimensions, methodology, policy, 3 allocation profiles
- Added classification config: geography overrides, market cap subtier policy,
  security type policy, ADR domicile policy
- Added allocation intelligence UI, operational scripts, research utilities
- 504 tests passing
```

**File count:** 69 files staged  
**Risk:** LOW — additive; all new modules; backward-compatible extensions to tracked files

### git add commands

```bash
# --- Modified tracked files (infrastructure extensions) ---
git add src/history/analytical_universe_manager.py
git add src/history/base_universe_manager.py
git add src/models/analytical_models.py
git add src/models/canonical_models.py
git add src/normalize/ess_normalizer.py
git add src/normalize/provider_normalizer.py
git add src/providers/fidelity/fidelity_ess_adapter.py
git add src/providers/fidelity/fidelity_schema_contract.py
git add src/scoring/fetch_danelfin_scores.py
git add src/scoring/fetch_yahoo_supplemental.py
git add src/scoring/fetch_zacks_scores.py
git add scripts/score_lookup.py

# --- New portfolio module (Phase 6.1 files only — stage individually) ---
git add src/portfolio/__init__.py
git add src/portfolio/models.py
git add src/portfolio/ingestion.py
git add src/portfolio/enrichment.py

# --- New allocation, classification, effectiveness modules ---
git add src/allocation/
git add src/classification/
git add src/effectiveness/
git add src/history/allocation_manager.py
git add src/scoring/fetch_security_metadata.py
git add src/scoring/market_cap_subtier_classifier.py
git add src/validation/market_cap_subtier_validator.py

# --- Config ---
git add config/adr_domicile_policy.yaml
git add config/allocation_dimensions.yaml
git add config/allocation_methodology.yaml
git add config/allocation_models/
git add config/allocation_policy.yaml
git add config/geography_overrides.yaml
git add config/market_cap_subtier_policy.yaml
git add config/security_type_policy.yaml

# --- UI ---
git add ui/allocation_intelligence/

# --- Operational scripts ---
git add scripts/apply_eligibility_flags.py
git add scripts/assign_geography.py
git add scripts/diagnostics/merge_subtier_replays.py
git add scripts/diagnostics/partial_publish_current.py
git add scripts/migrate_base_universe_headers.py
git add scripts/patch_universe_zacks.py
git add scripts/recalculate_allocation_targets.py
git add scripts/refresh_portfolio_signals.py
git add scripts/refresh_signals.py
git add scripts/rescore_all_universe.py
git add scripts/research/
git add scripts/run_classification_audit.py

# --- Tests ---
git add tests/test_dynamic_subtier_classification.py
git add tests/test_signal_fetch_resume.py

# --- Docs ---
git add docs/ALLOCATION_INTELLIGENCE_PHILOSOPHY.md
git add docs/ALLOCATION_PRIMER_WHY_THESE_NUMBERS.md
git add docs/ASSET_CLASS_FIRST_ARCHITECTURE.md
git add docs/HIERARCHICAL_ALLOCATION_MODEL.md
git add docs/equity-summary-score-methodology.pdf
git add docs/migration_plan.md
```

### Verify before committing

```bash
git status --short | grep "^A\|^M " | wc -l   # should be ~69
git diff --cached --stat | tail -3
```

### Commit command

```bash
git commit -m "Add portfolio intelligence foundation: scoring pipeline, universe management, allocation engine, classification, effectiveness, subtier architecture (Phases 6.1–6.4)"
```

---

## Commit B — WP-05D Stock Replay Curve

**Scope:** Stock replay engine additions, outcome visualization UI, server API foundation, diagnostic builders

**Commit message:**
```
Add WP-05D stock replay curve: outcome visualization UI, server API routes, replay engine extensions

- Extended replay_engine.py and stock_replay_service.py for WP-05D stock replay curve
- Extended replay_validator.py for WP-05D validation support
- Extended foundation_service.py (+92 lines) for portfolio analysis API endpoints
- Extended run_outcome_ui.py (+414 lines) with POST /api/portfolio/analyze,
  GET /api/portfolio/runs, POST /api/signal-refresh server routes
- Added outcome_visualization UI: interactive chart, symbol lookup, subtier filter
- Extended WP-04 diagnostic builders to call ensure_signals_fresh()
- Adapted test_wp04_1_ui_prototype.py and test_wp04_replay_foundation.py
  for Phase 6.x API contract changes
```

**File count:** 11 files staged  
**Risk:** LOW — self-contained replay additions; adapted tests confirm no regressions

### git add commands

```bash
# --- Modified tracked files ---
git add src/replay/replay_engine.py
git add src/replay/stock_replay_service.py
git add src/validation/replay_validator.py
git add src/replay/foundation_service.py
git add scripts/run_outcome_ui.py
git add scripts/diagnostics/build_wp04_foundation.py
git add scripts/diagnostics/build_wp05b_replay_matrix.py
git add ui/outcome_visualization/app.js
git add ui/outcome_visualization/index.html

# --- Tests (adapted) ---
git add tests/test_wp04_1_ui_prototype.py
git add tests/test_wp04_replay_foundation.py
```

### Commit command

```bash
git commit -m "Add WP-05D stock replay curve: outcome visualization UI, server API routes, replay engine extensions"
```

---

## Commit C — Recommendation Intelligence

**Scope:** Portfolio alignment engine, recommendation engine, mandate intelligence, vehicle scoring, ETF exposure, reconciliation, archetype, taxonomy, trim, synthesis (Phases 7.0–7.2)

**Commit message:**
```
Add recommendation intelligence: alignment engine, mandate, vehicle scoring,
ETF decomposition, reconciliation, archetype, taxonomy, trim, synthesis (Phases 7.0–7.2)

- Added src/portfolio/alignment.py: asset-class weight alignment engine
- Added src/portfolio/recommendations.py: recommendation engine (BUILD/REDUCE/HOLD)
- Added src/portfolio/runner.py: parallel analysis orchestration runner
- Added src/portfolio/mandate.py + scoring.py + exposure_decomposition.py (Phase 7.1):
  mandate intelligence, vehicle suitability scoring, ETF exposure decomposition
- Added src/portfolio/reconciliation.py + archetype.py + taxonomy.py +
  trim_intelligence.py + phase_e_synthesis.py (Phase 7.2)
- Added config/etf_exposure_decomposition.yaml
- 8 new test files covering all Phase 7.0–7.2 modules
- Architecture docs: VEHICLE_SELECTION_RATIONALE, conflict_graph_report,
  recommendation_flow_analysis, security_vs_etf_decision_framework
```

**File count:** 24 files staged  
**Risk:** LOW — all new files; no existing source modified

### git add commands

```bash
# --- New portfolio modules (Phase 7.0–7.2, stage individually) ---
git add src/portfolio/alignment.py
git add src/portfolio/recommendations.py
git add src/portfolio/runner.py
git add src/portfolio/mandate.py
git add src/portfolio/scoring.py
git add src/portfolio/exposure_decomposition.py
git add src/portfolio/reconciliation.py
git add src/portfolio/archetype.py
git add src/portfolio/taxonomy.py
git add src/portfolio/trim_intelligence.py
git add src/portfolio/phase_e_synthesis.py

# --- Config ---
git add config/etf_exposure_decomposition.yaml

# --- Tests ---
git add tests/test_mandate_intelligence.py
git add tests/test_vehicle_suitability.py
git add tests/test_etf_exposure_decomposition.py
git add tests/test_cash_semantics.py
git add tests/test_reconciliation.py
git add tests/test_archetype.py
git add tests/test_phase_d_trim_intelligence.py
git add tests/test_phase_e_synthesis.py

# --- Docs ---
git add docs/VEHICLE_SELECTION_RATIONALE.md
git add docs/conflict_graph_report.md
git add docs/recommendation_flow_analysis.md
git add docs/security_vs_etf_decision_framework.md
```

### Commit command

```bash
git commit -m "Add recommendation intelligence: alignment engine, mandate, vehicle scoring, ETF decomposition, reconciliation, archetype, taxonomy, trim, synthesis (Phases 7.0–7.2)"
```

---

## Commit D — Unified Optimizer

**Scope:** Parallel optimizer (Phase 7.3A), optimizer UI — conflict badges, ETF gate, view block, summary panel (Phase 7.3B), portfolio alignment UI (complete)

**Commit message:**
```
Add unified parallel optimizer and portfolio alignment UI (Phases 7.3A–7.3B)

Phase 7.3A — Parallel Optimizer:
- Added src/portfolio/optimizer.py: read-only parallel conflict detector,
  ETF gate (NCS threshold, suitability, overweight check), PIS scorer,
  MANDATE_BLOCKED / NO_CANDIDATES / SECURITY_SUPERIOR / ETF_CANDIDATE outcomes
- Optimizer metadata injected additively by runner.py post-optimization

Phase 7.3B — Optimizer UI:
- ui/portfolio_alignment/app.js: renderOptimizerSummary(), _buildOptimizerBadges(),
  _buildOptimizerViewBlock(), toggleOptimizerView() — conflict badges,
  ETF gate FAIL/PASS display, optimizer summary panel
- ui/portfolio_alignment/index.html: optimizer CSS, summary container placeholder
- optimizer_ui_validation_report.md: live validation of 6 canonical optimizer cases
- 15 optimizer UI tests + 27 optimizer unit tests
```

**File count:** 7 entries staged (ui/portfolio_alignment/ expands to 2 files)  
**Risk:** LOW — all new files; optimizer is read-only (no portfolio state mutation)

### git add commands

```bash
# --- New optimizer module ---
git add src/portfolio/optimizer.py

# --- Portfolio alignment UI (complete: Phase 6.1 init through 7.3B final state) ---
git add ui/portfolio_alignment/

# --- Tests ---
git add tests/test_optimizer.py
git add tests/test_7_3b_optimizer_ui.py

# --- Docs and deliverables ---
git add docs/unified_optimizer_design.md
git add optimizer_ui_validation_report.md
```

### Commit command

```bash
git commit -m "Add unified parallel optimizer and portfolio alignment UI (Phases 7.3A–7.3B)"
```

---

## Commit E — Repository Hygiene

**Scope:** .gitignore hardening, archive structure, navigation_state.yaml deletion, SC-H1/H2 process documentation

**Commit message:**
```
Repository hygiene: .gitignore hardening, archive structure, SC-H1/H2 process docs

- .gitignore: added 26 patterns covering generated reports, navigation state,
  derived data outputs, and diagnostic scripts (scripts/_*.py convention)
- scripts/archive/: organized archive of 15 report generators and one-time
  diagnostic scripts (compare_zacks_ess_vs_internet.py, _generate_*.py ×14)
- navigation_state.yaml: removed from tracking (auto-updated UI session state)
- SC-H1/H2 stabilization documents: dirty inventory, code footprint, artifact
  audit, commit candidate analysis, unexpected file investigation, step reports
```

**File count:** ~13 entries staged (scripts/archive/ expands to 15 files)  
**Risk:** NONE — no code changes; config and documentation only

### git add commands

```bash
# --- Config (already staged from git rm --cached) ---
# navigation_state.yaml deletion is already in the index — no add needed

# --- Modified tracked ---
git add .gitignore

# --- Archive directory ---
git add scripts/archive/

# --- SC-H1 / SC-H2 process documents ---
git add commit_candidate_report.md
git add commit_execution_plan.md
git add commit_readiness_report.md
git add generated_artifact_audit.md
git add remaining_dirty_inventory.md
git add repo_code_footprint.md
git add repo_dirty_inventory.md
git add stabilization_certification.md
git add stabilization_step1_report.md
git add unexpected_dirty_files.md
```

### Commit command

```bash
git commit -m "Repository hygiene: .gitignore hardening, archive structure, SC-H1/H2 process docs"
```

---

## Tagging Plan

Apply tags **after** each commit completes. Use annotated tags (`-a`) for milestone releases.

### Per-commit tags

| After Commit | Tag | Command |
|---|---|---|
| A | `portfolio-foundation-v6.4` | `git tag -a portfolio-foundation-v6.4 -m "Portfolio intelligence foundation: scoring pipeline, allocation, classification, effectiveness — Phase 6.4 complete"` |
| B | *(no tag — foundation continuation)* | — |
| C | `recommendation-intelligence-v7.2` | `git tag -a recommendation-intelligence-v7.2 -m "Recommendation intelligence: alignment engine, mandate, vehicle scoring, reconciliation, archetype, taxonomy — Phase 7.2 complete"` |
| D | `optimizer-parallel-v7.3b` | `git tag -a optimizer-parallel-v7.3b -m "Unified parallel optimizer with conflict detection, ETF gate, and optimizer UI badges/summary panel — Phase 7.3B complete"` |
| E | `portfolio-manager-v7.3b-stable` | `git tag -a portfolio-manager-v7.3b-stable -m "Stabilization checkpoint: all Phases 6.1–7.3B committed, 504 tests passing, repository hygiene complete"` |

### Tag summary

```
portfolio-foundation-v6.4         ← Phase 6.4 milestone
recommendation-intelligence-v7.2  ← Phase 7.2 milestone  
optimizer-parallel-v7.3b          ← Phase 7.3B milestone
portfolio-manager-v7.3b-stable    ← Stabilization checkpoint (primary release tag)
```

> **Note on pushing tags:** Tags are local until pushed. When ready: `git push origin --tags`

---

## Complete Execution Sequence (copy-paste ready)

```bash
# ============================================================
# COMMIT A — Portfolio Intelligence Foundation
# ============================================================
git add src/history/analytical_universe_manager.py src/history/base_universe_manager.py
git add src/models/analytical_models.py src/models/canonical_models.py
git add src/normalize/ess_normalizer.py src/normalize/provider_normalizer.py
git add src/providers/fidelity/fidelity_ess_adapter.py src/providers/fidelity/fidelity_schema_contract.py
git add src/scoring/fetch_danelfin_scores.py src/scoring/fetch_yahoo_supplemental.py src/scoring/fetch_zacks_scores.py
git add scripts/score_lookup.py
git add src/portfolio/__init__.py src/portfolio/models.py src/portfolio/ingestion.py src/portfolio/enrichment.py
git add src/allocation/ src/classification/ src/effectiveness/
git add src/history/allocation_manager.py
git add src/scoring/fetch_security_metadata.py src/scoring/market_cap_subtier_classifier.py
git add src/validation/market_cap_subtier_validator.py
git add config/adr_domicile_policy.yaml config/allocation_dimensions.yaml config/allocation_methodology.yaml
git add config/allocation_models/ config/allocation_policy.yaml
git add config/geography_overrides.yaml config/market_cap_subtier_policy.yaml config/security_type_policy.yaml
git add ui/allocation_intelligence/
git add scripts/apply_eligibility_flags.py scripts/assign_geography.py
git add scripts/diagnostics/merge_subtier_replays.py scripts/diagnostics/partial_publish_current.py
git add scripts/migrate_base_universe_headers.py scripts/patch_universe_zacks.py
git add scripts/recalculate_allocation_targets.py scripts/refresh_portfolio_signals.py
git add scripts/refresh_signals.py scripts/rescore_all_universe.py
git add scripts/research/ scripts/run_classification_audit.py
git add tests/test_dynamic_subtier_classification.py tests/test_signal_fetch_resume.py
git add docs/ALLOCATION_INTELLIGENCE_PHILOSOPHY.md docs/ALLOCATION_PRIMER_WHY_THESE_NUMBERS.md
git add docs/ASSET_CLASS_FIRST_ARCHITECTURE.md docs/HIERARCHICAL_ALLOCATION_MODEL.md
git add docs/equity-summary-score-methodology.pdf docs/migration_plan.md
git commit -m "Add portfolio intelligence foundation: scoring pipeline, universe management, allocation engine, classification, effectiveness, subtier architecture (Phases 6.1–6.4)"
git tag -a portfolio-foundation-v6.4 -m "Portfolio intelligence foundation: scoring pipeline, allocation, classification, effectiveness — Phase 6.4 complete"

# ============================================================
# COMMIT B — WP-05D Stock Replay Curve
# ============================================================
git add src/replay/replay_engine.py src/replay/stock_replay_service.py
git add src/validation/replay_validator.py
git add src/replay/foundation_service.py
git add scripts/run_outcome_ui.py
git add scripts/diagnostics/build_wp04_foundation.py scripts/diagnostics/build_wp05b_replay_matrix.py
git add ui/outcome_visualization/app.js ui/outcome_visualization/index.html
git add tests/test_wp04_1_ui_prototype.py tests/test_wp04_replay_foundation.py
git commit -m "Add WP-05D stock replay curve: outcome visualization UI, server API routes, replay engine extensions"

# ============================================================
# COMMIT C — Recommendation Intelligence
# ============================================================
git add src/portfolio/alignment.py src/portfolio/recommendations.py src/portfolio/runner.py
git add src/portfolio/mandate.py src/portfolio/scoring.py src/portfolio/exposure_decomposition.py
git add src/portfolio/reconciliation.py src/portfolio/archetype.py src/portfolio/taxonomy.py
git add src/portfolio/trim_intelligence.py src/portfolio/phase_e_synthesis.py
git add config/etf_exposure_decomposition.yaml
git add tests/test_mandate_intelligence.py tests/test_vehicle_suitability.py
git add tests/test_etf_exposure_decomposition.py tests/test_cash_semantics.py
git add tests/test_reconciliation.py tests/test_archetype.py
git add tests/test_phase_d_trim_intelligence.py tests/test_phase_e_synthesis.py
git add docs/VEHICLE_SELECTION_RATIONALE.md docs/conflict_graph_report.md
git add docs/recommendation_flow_analysis.md docs/security_vs_etf_decision_framework.md
git commit -m "Add recommendation intelligence: alignment engine, mandate, vehicle scoring, ETF decomposition, reconciliation, archetype, taxonomy, trim, synthesis (Phases 7.0–7.2)"
git tag -a recommendation-intelligence-v7.2 -m "Recommendation intelligence: alignment engine, mandate, vehicle scoring, reconciliation, archetype, taxonomy — Phase 7.2 complete"

# ============================================================
# COMMIT D — Unified Optimizer
# ============================================================
git add src/portfolio/optimizer.py
git add ui/portfolio_alignment/
git add tests/test_optimizer.py tests/test_7_3b_optimizer_ui.py
git add docs/unified_optimizer_design.md
git add optimizer_ui_validation_report.md
git commit -m "Add unified parallel optimizer and portfolio alignment UI (Phases 7.3A–7.3B)"
git tag -a optimizer-parallel-v7.3b -m "Unified parallel optimizer with conflict detection, ETF gate, and optimizer UI badges/summary panel — Phase 7.3B complete"

# ============================================================
# COMMIT E — Repository Hygiene
# ============================================================
git add .gitignore
git add scripts/archive/
git add commit_candidate_report.md commit_execution_plan.md commit_readiness_report.md
git add generated_artifact_audit.md remaining_dirty_inventory.md
git add repo_code_footprint.md repo_dirty_inventory.md
git add stabilization_certification.md stabilization_step1_report.md unexpected_dirty_files.md
git commit -m "Repository hygiene: .gitignore hardening, archive structure, SC-H1/H2 process docs"
git tag -a portfolio-manager-v7.3b-stable -m "Stabilization checkpoint: all Phases 6.1–7.3B committed, 504 tests passing, repository hygiene complete"
```

---

## Post-Commit Verification Commands

```bash
# Verify clean working tree
git status --short

# Verify commit log
git log --oneline -8

# Verify tags
git tag -l | sort

# Verify test suite still green
PYTHONPATH=. pytest -q

# Expected: 504 passed, 0 failed
```
