# Refresh Program Attribution
# DIRTY-FILE-AUDIT-01 — 2026-06-22

## Refresh-Transparency Initiative File Count

**Total files attributed to the Refresh-Transparency initiative**: 31

Initiatives covered:
- REFRESH-UX-01: Refresh Portfolio Signals (signal-status coverage)
- REFRESH-UX-02: Refresh Health and Candidate Readiness
- REFRESH-UX-03: Research Universe Freshness Investigation
- REFRESH-UX-04: Active Refresh Display Fix
- REFRESH-UX-05: Refresh Mode Definition Panel
- REFRESH-UX-05A: Dynamic Counts, Data Confidence, Investment Guidance
- DECISION-CONFIDENCE-01: Candidate confidence design
- DECISION-CONFIDENCE-02: Action vs Data Confidence distinction
- DATA-COVERAGE-01: Research universe coverage investigation

---

## Source Code Files (Refresh Initiative)

| File | Status | Initiative |
|---|---|---|
| scripts/refresh_signals.py | Modified | REFRESH-UX-01/02 |
| scripts/run_outcome_ui.py | Modified | REFRESH-UX-01/02/03/04 |
| ui/outcome_visualization/app.js | Modified | REFRESH-UX-02/03/04/05/05A |
| ui/outcome_visualization/index.html | Modified | REFRESH-UX-02/03/04/05/05A |
| ui/portfolio_alignment/app.js | Modified (partial) | DECISION-CONFIDENCE-02 |
| ui/portfolio_alignment/index.html | Modified (partial) | DECISION-CONFIDENCE-02 |

**Subtotal source code**: 6 files

---

## Documentation Files (Refresh Initiative)

| File | Initiative |
|---|---|
| active_job_state_audit.md | REFRESH-UX |
| candidate_confidence_design.md | DECISION-CONFIDENCE-01 |
| candidate_freshness_inventory.md | DATA-COVERAGE-01 |
| candidate_readiness_prototype.md | DATA-COVERAGE-01 |
| candidate_universe_lineage.md | DATA-COVERAGE-01 |
| coverage_intent_assessment.md | DATA-COVERAGE-01 |
| coverage_validator_audit.md | DATA-COVERAGE-01 |
| decision_readiness_audit.md | DECISION-CONFIDENCE-01 |
| decision_readiness_gap_analysis.md | DECISION-CONFIDENCE-01 |
| deployment_impact_analysis.md | DATA-COVERAGE-01 |
| deployment_safety_assessment.md | DATA-COVERAGE-01 |
| deployment_state_assessment.md | DATA-COVERAGE-01 |
| epic_refresh_report.md | REFRESH-UX |
| fmp_coverage_assessment.md | DATA-COVERAGE-01 |
| metric_validity_assessment.md | DATA-COVERAGE-01 |
| mu_lineage_trace.md | DATA-COVERAGE-01 |
| phase_final_verdict.md | DATA-COVERAGE-01 |
| ranking_confidence_assessment.md | DECISION-CONFIDENCE-01 |
| rebuild_research_universe_trace.md | DATA-COVERAGE-01/REFRESH-UX-03 |
| recommendation_confidence_inventory.md | DECISION-CONFIDENCE-01 |
| recommendation_freshness_audit.md | DATA-COVERAGE-01 |
| recommendation_freshness_panel_design.md | REFRESH-UX-02 |
| refresh_batch_reconciliation.md | REFRESH-UX-02 |
| refresh_completion_confidence.md | REFRESH-UX-02 |
| refresh_health_02a_required_questions.md | REFRESH-UX-02 |
| refresh_metric_lineage.md | REFRESH-UX-03 |
| refresh_mode_coverage_matrix.md | REFRESH-UX-05 |
| refresh_portfolio_signals_validation.md | REFRESH-UX-01 |
| refresh_progress_semantics.md | REFRESH-UX-02 |
| refresh_timeline_reconstruction.md | REFRESH-UX-02 |
| research_universe_composition.csv | DATA-COVERAGE-01 |
| research_universe_freshness_lineage.md | DATA-COVERAGE-01 |
| ui_render_path_trace.md | REFRESH-UX |
| ui_wireframe_candidate_confidence.md | DECISION-CONFIDENCE-01 |
| zacks_freshness_reconciliation.md | DATA-COVERAGE-01 |

**Subtotal documentation**: 35 files (including 1 CSV)

---

## Generated Artifact Files (Refresh Initiative)

| File | Initiative |
|---|---|
| coverage_summary_tmp.json | DATA-COVERAGE-01 |
| coverage_summary_tmp.py | DATA-COVERAGE-01 |
| freshness_failure_attribution.csv | DATA-COVERAGE-01 |
| provider_applicability_inventory.csv | DATA-COVERAGE-01 |
| provider_coverage_matrix.csv | DATA-COVERAGE-01 |
| provider_freshness_matrix.csv | DATA-COVERAGE-01 |
| provider_submission_inventory.csv | DATA-COVERAGE-01 |

**Subtotal generated artifacts**: 7 files

---

## Total Refresh Initiative Attribution

| Category | Count |
|---|---|
| Source code (modified) | 6 |
| Documentation | 35 |
| Generated artifacts | 7 |
| **Total** | **48** |

---

## Key Observations

1. **REFRESH-UX-05 and REFRESH-UX-05A** landed entirely in `ui/outcome_visualization/app.js` and `index.html` — no backend changes required.
2. **DATA-COVERAGE-01** was a pure investigation — its output is 20+ markdown files and 7 CSVs with zero algorithmic impact.
3. **DECISION-CONFIDENCE-02** landed in `ui/portfolio_alignment/app.js` / `index.html` as part of the larger multi-phase portfolio alignment work.
4. The refresh initiative accounts for approximately **25%** of total dirty entries (48/189), with documentation dominant within that group (73%).
