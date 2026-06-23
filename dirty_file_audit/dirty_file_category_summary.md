# Dirty File Category Summary
# DIRTY-FILE-AUDIT-01 — 2026-06-22

## Working Tree Overview

- **Total git entries reported**: 189
- **Tracked modified (M) files**: 23
- **Untracked entries (??)**: 166 (including 5 directory-level entries representing expanded file counts)
- **Estimated total actual files**: ~206 (untracked directories contain ~17 additional files)

---

## Category Breakdown

| Category | Entry Count | Notes |
|---|---|---|
| UI (JavaScript, HTML, CSS) | 9 tracked + 1 untracked = **10** | portfolio_alignment, outcome_visualization, pis_dashboard, allocation_intelligence, ucf_operator_dashboard, signal_translation_registry |
| Refresh Subsystem (Python/Server) | 2 tracked | scripts/refresh_signals.py, scripts/run_outcome_ui.py |
| ESS Coverage | 3 tracked | provider_health_models.py, ess_intake_stage.py, ess_coverage.py |
| CRA | 2 tracked | capital_source_builder.py, models.py |
| Configuration | 1 tracked | allocation_policy.yaml |
| Portfolio/Validation | 3 tracked | enrichment.py, intake_readiness_validator.py, persistence_validator.py |
| Test Files (tracked) | 3 tracked | test_fidelity_provider_adapter.py, test_intake_readiness_validator.py, test_persistence_validator.py |
| New Source Modules | 14 untracked entries | src/pis/*, src/sih/*, src/portfolio/drift_analyzer.py, src/mei/ |
| New Test Files | 19 untracked | tests/test_*.py |
| Documentation | **117 untracked** | .md files at root and docs/ |
| Generated Artifacts (CSV/JSON) | 7 + 2 dirs + temp scripts | *.csv, *.json, artifacts/, data/analysis/ |
| Scripts | 1 untracked | scripts/prepare_portfolio_review.py |

---

## Source Code Changes Summary (Tracked)

All 23 tracked modified files represent intentional development across multiple completed epics since last commit (tag: sih-v1-feature-complete).

### Largest Changes (by line additions)
1. `ui/portfolio_alignment/app.js` — +2229 lines (largest single change)
2. `ui/pis_dashboard/app.js` — +1459 lines
3. `scripts/run_outcome_ui.py` — +1239 lines
4. `ui/portfolio_alignment/index.html` — +546 lines
5. `ui/outcome_visualization/index.html` — +449 lines

**Total tracked change**: 7,529 insertions, 232 deletions across 23 files.

---

## Untracked Content Distribution

| Content Type | Count |
|---|---|
| Markdown documentation files | 117 |
| New Python source modules | 15 |
| New Python test files | 19 |
| CSV data artifacts | 7 |
| JSON artifacts | 2 |
| Temp/ad-hoc scripts | 2 (coverage_summary_tmp.py, performance_validation.py) |
| Untracked directories (summary entries) | 5 |
