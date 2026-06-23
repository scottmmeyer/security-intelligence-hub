# Commit Boundary Recommendations
# DIRTY-FILE-AUDIT-01 — 2026-06-22

## Recommended Commit Order

Commit in this order to maintain clean logical boundaries and minimize risk:
1. Smallest / most atomic (tests + minor config)
2. New standalone modules (no prior dependency)
3. Modified core backend
4. UI layers
5. Documentation
6. Generated artifacts (gitignore or commit last)

---

## Commit Group A — ESS Intake & Coverage (MEDIUM risk)
**Purpose**: ESS-INTAKE-ORDERING-01 and ESS-COVERAGE-AUDIT
**Commit message**: `ESS-INTAKE-ORDERING-01: merge logic, coverage gap classification, StarMine freshness detection`

**Files**:
```
src/models/provider_health_models.py
src/pipeline/stages/ess_intake_stage.py
src/portfolio/ess_coverage.py
src/validation/intake_readiness_validator.py
src/validation/persistence_validator.py
tests/test_fidelity_provider_adapter.py
tests/test_intake_readiness_validator.py
tests/test_persistence_validator.py
```

---

## Commit Group B — CRA Explain (HIGH topology / display-only)
**Purpose**: CRA-EXPLAIN-02 source intent labeling
**Commit message**: `CRA-EXPLAIN-02: source intent labels for capital rotation candidates (display-only)`

**Files**:
```
src/portfolio/cra/capital_source_builder.py
src/portfolio/cra/models.py
tests/test_cra_explain_02.py
```

---

## Commit Group C — Signal Governance & Conflict
**Purpose**: SIGNAL-GOV-02A and ISSUE-12D conflict review and alpha
**Commit message**: `SIGNAL-GOV-02A + ISSUE-12D: signal conflict classifier, conflict alpha analysis, governance advisory badges`

**Files**:
```
config/allocation_policy.yaml
src/portfolio/signal_conflict_classifier.py
src/sih/conflict_alpha_analysis.py
src/sih/security_conflict_alpha.py
src/sih/signal_conflict_review.py
tests/test_conflict_alpha_analysis.py
tests/test_dislocation_06_calibration.py
tests/test_dislocation_07_directional.py
tests/test_security_conflict_alpha.py
tests/test_signal_conflict_review.py
tests/test_signal_gov_02a_conflict_classifier.py
```

---

## Commit Group D — PIS Analytics Modules
**Purpose**: PA-006, PA-006A, PA-006B, PIS-007, PIS-008, AI-004B, MEI Phase 1
**Commit message**: `PA-006/007/008 + AI-004B + MEI: allocation compliance, drift intelligence, policy diff, market event intelligence`

**Files**:
```
src/pis/action_attribution.py
src/pis/allocation_compliance.py
src/pis/allocation_drift.py
src/pis/dislocation_outcome_review.py
src/pis/drift_trend_analyzer.py
src/pis/policy_change_summary.py
src/pis/policy_version_diff.py
src/portfolio/drift_analyzer.py
src/sih/predictive/ (full directory)
src/mei/ (full directory)
data/mei/ (seed data required by MEI)
tests/test_ai_004b_policy_change_summary.py
tests/test_allocation_compliance.py
tests/test_dislocation_outcome_review.py
tests/test_mei_002_outcome_tracker.py
tests/test_mei_phase_001.py
tests/test_pa_006a_drift_analyzer.py
tests/test_pa_006b_drift_intelligence.py
tests/test_pis_action_attribution.py
tests/test_pis_allocation_drift_trends.py
tests/test_policy_version_diff.py
tests/test_predictive_intelligence_epic.py
```

---

## Commit Group E — Refresh Subsystem Backend
**Purpose**: REFRESH-UX-01 through REFRESH-UX-04 backend changes
**Commit message**: `REFRESH-UX-01/02/03/04: refresh mode routing, transparency API, signal-status coverage metrics`

**Files**:
```
scripts/refresh_signals.py
scripts/run_outcome_ui.py
```

---

## Commit Group F — UI: Signal Translation Registry
**Purpose**: SIGNAL-UX-01 — provider translation layer
**Commit message**: `SIGNAL-UX-01: signal translation registry for provider label normalization`

**Files**:
```
ui/signal_translation_registry.js
```

---

## Commit Group G — UI: Outcome Visualization (Refresh UX)
**Purpose**: REFRESH-UX-02 through REFRESH-UX-05A
**Commit message**: `REFRESH-UX-02/03/04/05/05A: candidate readiness, mode definition panel, dynamic universe counts, decision impact`

**Files**:
```
ui/outcome_visualization/app.js
ui/outcome_visualization/index.html
```

---

## Commit Group H — UI: PIS Dashboard
**Purpose**: PA-006A, PA-006B, AI-004B, MEI dashboard sections
**Commit message**: `PIS Dashboard: allocation drift, drift intelligence, policy change summary, MEI sections`

**Files**:
```
ui/pis_dashboard/app.js
ui/pis_dashboard/index.html
```

---

## Commit Group I — UI: Portfolio Alignment (Multiple Phases)
**Purpose**: All portfolio alignment UI phases (DECISION-CONFIDENCE-02, CRA-EXPLAIN-02 UI, data confidence layer, etc.)
**Commit message**: `Portfolio Alignment UI: data confidence layer, CRA source intent, signal governance display, multiple phases`

**Files**:
```
ui/portfolio_alignment/app.js
ui/portfolio_alignment/index.html
ui/portfolio_alignment/ (enrichment.py is backend — should be in Group C or standalone)
src/portfolio/enrichment.py
```

---

## Commit Group J — UI: Minor Surfaces
**Purpose**: UCF dashboard and allocation intelligence minor updates
**Commit message**: `UI: allocation intelligence and UCF operator dashboard minor display updates`

**Files**:
```
ui/allocation_intelligence/app.js
ui/allocation_intelligence/index.html
ui/ucf_operator_dashboard/index.html
```

---

## Commit Group K — New Script: Portfolio Review
**Purpose**: New portfolio review generation script — needs review first
**Commit message**: `scripts/prepare_portfolio_review: portfolio review artifact generation script`

**Files**:
```
scripts/prepare_portfolio_review.py
```

**⚠ CAUTION**: Review this script before committing to confirm it does not mutate scoring artifacts.

---

## Commit Group L — Documentation
**Purpose**: All markdown documentation for completed features
**Commit message**: `docs: audit outputs, design docs, validation reports, phase verdicts`

**Files**:
All *.md files from root and docs/ directory (117 files)

**Strategy**: Can be committed in logical sub-groups:
- L1: REFRESH-UX docs (15 files)
- L2: DATA-COVERAGE-01 investigation (20 files)
- L3: Signal governance docs (8 files)
- L4: CRA/PA/PIS docs (30 files)
- L5: ESS audit docs (10 files)
- L6: Governance/backlog docs (34 files)

---

## Do Not Commit / Needs Gitignore

| File | Reason |
|---|---|
| coverage_summary_tmp.json | Temporary artifact — naming indicates temp |
| coverage_summary_tmp.py | Temporary script — naming indicates temp |
| performance_validation.py | Ad-hoc validation — naming indicates temp |
| performance_validation_results.json | Generated output from temp script |
| artifacts/ | Generated run artifacts — add to .gitignore |
| data/analysis/dislocation/ | Analysis cache — consider .gitignore |

---

## Recommended Commit Sequence

```
A → B → C → D → E → F → G → H → I → J → K (after review) → L (documentation)
```

**Total commits**: 11 (12 if K passes review) + optional docs sub-commits
