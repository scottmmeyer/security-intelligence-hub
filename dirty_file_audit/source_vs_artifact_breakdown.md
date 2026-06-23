# Source vs Artifact Breakdown
# DIRTY-FILE-AUDIT-01 — 2026-06-22

## Primary Classification Table

| Type | Count | Details |
|---|---|---|
| **Source Code** | **49** | Tracked + untracked Python, JS, HTML, CSS, YAML |
| **Test Files** | **22** | 3 tracked modified + 19 untracked new |
| **Documentation** | **117** | All .md files (root + docs/) |
| **Generated Artifacts** | **~25** | CSVs, JSONs, artifacts/ dir, data/analysis/, data/mei/ |
| **Temp Scripts** | **2** | coverage_summary_tmp.py, performance_validation.py |
| **Total** | **~215** | |

---

## Source Code Detail (49 files)

### Tracked Modified Source (23 files)
| File | Lines Changed |
|---|---|
| config/allocation_policy.yaml | +6 |
| scripts/refresh_signals.py | +125 / -4 |
| scripts/run_outcome_ui.py | +1239 / -12 |
| src/models/provider_health_models.py | +22 / -1 |
| src/pipeline/stages/ess_intake_stage.py | +86 / -32 |
| src/portfolio/cra/capital_source_builder.py | +66 |
| src/portfolio/cra/models.py | +31 |
| src/portfolio/enrichment.py | +1 |
| src/portfolio/ess_coverage.py | +121 / -59 |
| src/validation/intake_readiness_validator.py | +6 / -3 |
| src/validation/persistence_validator.py | +15 / -7 |
| ui/allocation_intelligence/app.js | +109 |
| ui/allocation_intelligence/index.html | +13 |
| ui/outcome_visualization/app.js | +694 / -67 |
| ui/outcome_visualization/index.html | +449 / -20 |
| ui/pis_dashboard/app.js | +1459 |
| ui/pis_dashboard/index.html | +172 |
| ui/portfolio_alignment/app.js | +2229 / -18 |
| ui/portfolio_alignment/index.html | +546 / -4 |
| ui/ucf_operator_dashboard/index.html | +27 / -11 |
| tests/test_fidelity_provider_adapter.py | +253 |
| tests/test_intake_readiness_validator.py | +32 |
| tests/test_persistence_validator.py | +60 |

### New Untracked Source Modules (15 entries)
- src/mei/ (full package — ~4-6 files)
- src/pis/action_attribution.py
- src/pis/allocation_compliance.py
- src/pis/allocation_drift.py
- src/pis/dislocation_outcome_review.py
- src/pis/drift_trend_analyzer.py
- src/pis/policy_change_summary.py
- src/pis/policy_version_diff.py
- src/portfolio/drift_analyzer.py
- src/portfolio/signal_conflict_classifier.py
- src/sih/conflict_alpha_analysis.py
- src/sih/predictive/ (full package — ~5-6 files)
- src/sih/security_conflict_alpha.py
- src/sih/signal_conflict_review.py
- scripts/prepare_portfolio_review.py

### New Untracked UI (1 file)
- ui/signal_translation_registry.js

---

## Generated Artifact Detail (~25 entries)

### Root Level CSVs (Generated Outputs — Not Source)
- ess_missing_holdings_inventory.csv
- freshness_failure_attribution.csv
- provider_applicability_inventory.csv
- provider_coverage_matrix.csv
- provider_freshness_matrix.csv
- provider_submission_inventory.csv
- research_universe_composition.csv

### Root Level JSON (Generated)
- coverage_summary_tmp.json
- performance_validation_results.json

### Directories (Generated/Data)
- artifacts/ (~10 files) — generated run artifacts
- data/analysis/dislocation/ (~4 files) — analysis cache
- data/mei/ (~3 files) — MEI seed data

---

## Temp/Ad-Hoc Scripts (Should Not Be Committed As-Is)
- coverage_summary_tmp.py — naming indicates temporary
- performance_validation.py — naming indicates temporary ad-hoc use

---

## Key Finding
**63% of working tree is documentation** (117/189 entries). The actual source-code footprint is much smaller and well-defined. The apparent "217 files" figure is heavily inflated by narrative markdown outputs produced during audit and investigation phases.
