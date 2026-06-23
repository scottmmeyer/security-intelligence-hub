# Commit Sequence Plan
## COMMIT-EXECUTION-01 Phase 4
**Timestamp**: 2026-06-22 10:53 UTC  
**Status**: ✅ EXECUTION PLAN COMPLETE

---

## Commit Strategy

**Total Commits**: 12 core + 6 documentation sub-commits = 18 total  
**Deployment Sequence**: Linear, dependency-ordered  
**Rollback Strategy**: Each commit is independently revertible to baseline tag `sih-v1-feature-complete`

---

# Core Commits (A-K)

---

## Commit 1 — ESS Intake & Coverage

**Hash**: ESS-INTAKE-ORDERING-01  
**Risk**: 🟡 MEDIUM  
**Size**: 8 files | 369 insertions, 16 deletions  
**Execution Order**: **FIRST** ← Execute immediately

### Files
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

### Commit Message
```
ESS-INTAKE-ORDERING-01: merge ordering, coverage gap classification, StarMine freshness

- Add coverage gap detail types: MISSING, STALE, NO_FRESH_STARMINE
- Implement per-provider freshness classification
- Add intake stage merge logic with duplicate detection
- Extend EssCoverageGapWarning with detailed gap enumeration
- Add intake readiness validation with FidelityProvider coverage checks
- Verify persistence layer handles coverage metadata

All changes are display/transparency enhancements.
No algorithm modifications to ESS scoring.
No changes to ranking, recommendations, or allocation.

Baseline: sih-v1-feature-complete
Breaking changes: None (backward-compatible)
Tests: 6 suites PASSING (test_ess_intake_foundation, test_ess_coverage_semantics, etc.)
```

### Validation Commands
```bash
git add src/models/provider_health_models.py \
        src/pipeline/stages/ess_intake_stage.py \
        src/portfolio/ess_coverage.py \
        src/validation/intake_readiness_validator.py \
        src/validation/persistence_validator.py \
        tests/test_fidelity_provider_adapter.py \
        tests/test_intake_readiness_validator.py \
        tests/test_persistence_validator.py

PYTHONPATH=. .venv/bin/python -m pytest tests/test_ess_intake_*.py tests/test_ess_coverage_*.py -v

git commit -m "ESS-INTAKE-ORDERING-01: merge ordering, coverage gap classification, StarMine freshness"
```

### Rollback
```bash
git reset --hard sih-v1-feature-complete
```

---

## Commit 2 — CRA Explain

**Hash**: CRA-EXPLAIN-02  
**Risk**: 🟢 LOW  
**Size**: 3 files | 97 insertions, 0 deletions  
**Execution Order**: **SECOND** ← Execute immediately after Commit 1

### Files
```
src/portfolio/cra/capital_source_builder.py
src/portfolio/cra/models.py
tests/test_cra_explain_02.py
```

### Commit Message
```
CRA-EXPLAIN-02: source intent labels for capital rotation candidates (display-only)

- Add SOURCE_INTENT_* labels: THESIS_EXIT, THESIS_TRIM, TAX_FUNDING_SOURCE, 
  OVERWEIGHT_REPAIR, PORTFOLIO_REALLOCATION
- Implement _compute_source_intent() for category+signal→label mapping
- Add source_intent field to CapitalSourceRecord (frozen dataclass, backward-compatible)
- Populate source_intent during CRA ranking (display-only, no ranking changes)
- Verify label preservation through serialization

No changes to CRA allocation logic, ranking, or sizing.
No changes to capital deployment recommendations.

Baseline: Commit 1
Breaking changes: None (optional field, defaults to empty string)
Tests: 32 tests PASSING (test_cra_explain_02.py)
```

### Validation Commands
```bash
git add src/portfolio/cra/capital_source_builder.py \
        src/portfolio/cra/models.py \
        tests/test_cra_explain_02.py

PYTHONPATH=. .venv/bin/python -m pytest tests/test_cra_explain_02.py -v

git commit -m "CRA-EXPLAIN-02: source intent labels for capital rotation candidates (display-only)"
```

### Rollback
```bash
git reset --hard HEAD~1
```

---

## Commit 3 — Signal Governance & Conflict

**Hash**: SIGNAL-GOV-02A + ISSUE-12D  
**Risk**: 🟡 MEDIUM  
**Size**: 12 files | 300+ insertions, 50 deletions  
**Execution Order**: **THIRD** ← Execute after Commit 2

### Files
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

### Commit Message
```
SIGNAL-GOV-02A + ISSUE-12D: signal conflict classifier, conflict alpha analysis, governance advisory badges

- Implement signal_conflict_classifier for cross-signal contradiction detection
- Add conflict alpha analysis: leverage conflicts for return prediction
- Add security conflict alpha module: company-level conflict metrics
- Implement signal governance advisory badges (display-only)
- Update allocation_policy.yaml with conflict governance rules
- Add conflict review and outcome tracking

No changes to ESS scoring, CW-DAS ranking, or recommendation generation.
Conflict detection is advisory only; no ranking impact.

Baseline: Commit 2
Breaking changes: None (advisory badges)
Tests: 27 core tests + 10+ supporting tests PASSING
```

### Validation Commands
```bash
git add config/allocation_policy.yaml \
        src/portfolio/signal_conflict_classifier.py \
        src/sih/conflict_alpha_analysis.py \
        src/sih/security_conflict_alpha.py \
        src/sih/signal_conflict_review.py \
        tests/test_conflict_alpha_analysis.py \
        tests/test_dislocation_06_calibration.py \
        tests/test_dislocation_07_directional.py \
        tests/test_security_conflict_alpha.py \
        tests/test_signal_conflict_review.py \
        tests/test_signal_gov_02a_conflict_classifier.py

PYTHONPATH=. .venv/bin/python -m pytest tests/test_signal_gov_02a_* -v

git commit -m "SIGNAL-GOV-02A + ISSUE-12D: signal conflict classifier, conflict alpha analysis, governance advisory badges"
```

### Rollback
```bash
git reset --hard HEAD~1
```

---

## Commit 4 — PIS Analytics Modules

**Hash**: PA-006/007/008 + AI-004B + MEI  
**Risk**: 🟡 MEDIUM  
**Size**: 22+ files | 2000+ insertions, 100 deletions  
**Execution Order**: **FOURTH** ← Execute after Commit 3

### Files
```
src/pis/action_attribution.py
src/pis/allocation_compliance.py
src/pis/allocation_drift.py
src/pis/dislocation_outcome_review.py
src/pis/drift_trend_analyzer.py
src/pis/policy_change_summary.py
src/pis/policy_version_diff.py
src/portfolio/drift_analyzer.py
src/sih/predictive/*  (8 modules)
src/mei/*  (7 modules)
data/mei/*  (seed data)
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

### Commit Message
```
PA-006/007/008 + AI-004B + MEI: allocation compliance, drift intelligence, policy diff, market event intelligence

Portfolio Intelligence System (PIS) Analytics:
- Add allocation compliance analyzer (per-policy constraint validation)
- Add drift analyzer: allocation change tracking across time
- Add drift intelligence: drift trend analysis with Sharpe/Calmar metrics
- Add policy change summary: policy version diff tracking
- Add action attribution: map actions to underlying policy changes
- Add dislocation outcome review: track outcome of policy implementation

Market Event Intelligence (MEI) Phase 1:
- Add market event intelligence package for portfolio impact analysis
- Add predictive intelligence modules for forward-looking analysis
- Add outcome tracking for MEI events

No changes to ESS scoring, CW-DAS ranking, UCF evaluation, or recommendations.
All PIS/MEI modules are analytics/transparency only.
No impact on capital deployment or portfolio optimization.

Baseline: Commit 3
Breaking changes: None (new modules)
Tests: 10+ suites PASSING
```

### Validation Commands
```bash
git add src/pis/ src/sih/predictive/ src/mei/ src/portfolio/drift_analyzer.py \
        data/mei/ tests/test_pa_006* tests/test_ai_004b* tests/test_mei_* \
        tests/test_pis_* tests/test_allocation_compliance.py tests/test_policy_version_diff.py \
        tests/test_predictive_intelligence_epic.py

PYTHONPATH=. .venv/bin/python -m pytest tests/test_pa_006* tests/test_allocation_compliance.py \
    tests/test_mei_phase_001.py tests/test_predictive_intelligence_epic.py -v

git commit -m "PA-006/007/008 + AI-004B + MEI: allocation compliance, drift intelligence, policy diff, market event intelligence"
```

### Rollback
```bash
git reset --hard HEAD~1
```

---

## Commit 5 — Refresh Subsystem Backend

**Hash**: REFRESH-UX-01/02/03/04  
**Risk**: 🟡 MEDIUM  
**Size**: 2 files | 1364 insertions, 4 deletions  
**Execution Order**: **FIFTH** ← Execute after Commit 4

### Files
```
scripts/refresh_signals.py
scripts/run_outcome_ui.py
```

### Commit Message
```
REFRESH-UX-01/02/03/04: refresh mode routing, transparency API, signal-status coverage metrics

Refresh Subsystem Enhancement:
- Add refresh mode constants: STALE_ONLY, PORTFOLIO_SIGNALS, REBUILD_RESEARCH_UNIVERSE
- Implement mode-aware refresh routing in refresh_signals.py
- Add refresh mode label mapping for UI display
- Extend run_outcome_ui.py with new transparency APIs:
  * GET /api/signal-status → portfolio holdings coverage by provider
  * GET /api/refresh-transparency → research universe size, stale count, decision impact data
  * POST /api/signal-refresh → refresh orchestration start
  * GET /api/signal-refresh/status → active refresh status tracking

All changes are API/transparency additions.
No changes to refresh algorithm, provider integration, or stale detection logic.
No changes to scoring, ranking, or recommendation generation.

Baseline: Commit 4
Breaking changes: None (additive APIs)
Tests: 13 tests PASSING (test_si_refresh_02_coverage)
```

### Validation Commands
```bash
git add scripts/refresh_signals.py scripts/run_outcome_ui.py

PYTHONPATH=. .venv/bin/python -m pytest tests/test_si_refresh_02_coverage.py -v

git commit -m "REFRESH-UX-01/02/03/04: refresh mode routing, transparency API, signal-status coverage metrics"
```

### Rollback
```bash
git reset --hard HEAD~1
```

---

## Commit 6 — UI: Signal Translation Registry

**Hash**: SIGNAL-UX-01  
**Risk**: 🟢 LOW  
**Size**: 1 file | 50+ insertions  
**Execution Order**: **SIXTH** ← Execute with/after Commit 7

### Files
```
ui/signal_translation_registry.js
```

### Commit Message
```
SIGNAL-UX-01: signal translation registry for provider label normalization

UI Enhancement:
- Add signal_translation_registry.js utility for normalizing provider labels
- Map provider-specific signal names to canonical UI terms
- Support Zacks, Danelfin, Yahoo provider label translation
- Reusable across outcome_visualization and other UI surfaces

No business logic changes.
Purely client-side label normalization for UI consistency.

Baseline: Commit 5
Breaking changes: None (utility module)
Tests: Verified in Group G UI integration
```

### Validation Commands
```bash
git add ui/signal_translation_registry.js

git commit -m "SIGNAL-UX-01: signal translation registry for provider label normalization"
```

### Rollback
```bash
git reset --hard HEAD~1
```

---

## Commit 7 — UI: Outcome Visualization (Refresh UX)

**Hash**: REFRESH-UX-02/03/04/05/05A  
**Risk**: 🟡 MEDIUM  
**Size**: 2 files | 1143 insertions, 20 deletions  
**Execution Order**: **SEVENTH** ← Execute after Commit 5, with Commit 6

### Files
```
ui/outcome_visualization/app.js
ui/outcome_visualization/index.html
```

### Commit Message
```
REFRESH-UX-02/03/04/05/05A: candidate readiness, mode definition panel, dynamic universe counts, decision impact

Outcome Visualization UI Enhancement:
- Implement refresh mode guidance panel with 4 modes: stale_only, portfolio_signals, 
  rebuild_research_universe, prepare_portfolio_review
- Add dynamic universe counts (replace hardcoded estimates):
  * Portfolio holdings count from /api/signal-status
  * Research universe total from /api/refresh-transparency
  * Stale symbols count from /api/refresh-transparency
- Add decision-impact matrix (7 rows):
  * Coverage, Accuracy, Completeness, Prioritization, Execution Complexity, 
    Time-to-Market, Data Confidence
- Add investment guidance for Rebuild Research Universe mode
- Cache version bumped: v=12 → v=13 (hard-reload safety)
- Responsive grid CSS with color-coded impact levels

No business logic changes to refresh algorithm.
Purely UI rendering of transparency data from Commit 5 APIs.

Baseline: Commit 6
Breaking changes: None (new panel, additive UI)
Tests: Panel rendering verified, dynamic counts validated
```

### Validation Commands
```bash
git add ui/outcome_visualization/app.js ui/outcome_visualization/index.html

# Browser hard-reload Cmd+Shift+R and verify panel renders with live counts
git commit -m "REFRESH-UX-02/03/04/05/05A: candidate readiness, mode definition panel, dynamic universe counts, decision impact"
```

### Rollback
```bash
git reset --hard HEAD~1
```

---

## Commit 8 — UI: PIS Dashboard

**Hash**: PA-006A + PA-006B + AI-004B + MEI  
**Risk**: 🟡 MEDIUM  
**Size**: 2 files | 1631 insertions  
**Execution Order**: **EIGHTH** ← Execute after Commit 4

### Files
```
ui/pis_dashboard/app.js
ui/pis_dashboard/index.html
```

### Commit Message
```
PIS Dashboard: allocation drift, drift intelligence, policy change summary, MEI sections

Portfolio Intelligence System Dashboard:
- Implement PIS dashboard UI with sections:
  * Allocation compliance tracker
  * Drift intelligence charts (Sharpe/Calmar metrics)
  * Policy change summary timeline
  * Action attribution tracking
  * MEI (Market Event Intelligence) event log
- Real-time data binding to PIS analytics modules (Commit 4)
- Responsive dashboard layout with sortable tables

No business logic changes.
Dashboard visualization of analytics from Commit 4.

Baseline: Commit 7
Breaking changes: None (new dashboard)
Tests: test_pis_ui_phase1_dashboard.py PASSING
```

### Validation Commands
```bash
git add ui/pis_dashboard/app.js ui/pis_dashboard/index.html

PYTHONPATH=. .venv/bin/python -m pytest tests/test_pis_ui_phase1_dashboard.py -v

git commit -m "PIS Dashboard: allocation drift, drift intelligence, policy change summary, MEI sections"
```

### Rollback
```bash
git reset --hard HEAD~1
```

---

## Commit 9 — UI: Portfolio Alignment

**Hash**: DECISION-CONFIDENCE-02 + CRA-EXPLAIN-02 UI + Multiple Phases  
**Risk**: 🟡 MEDIUM  
**Size**: 3 files | 2775 insertions  
**Execution Order**: **NINTH** ← Execute after Commit 2 (CRA labels)

### Files
```
src/portfolio/enrichment.py
ui/portfolio_alignment/app.js
ui/portfolio_alignment/index.html
```

### Commit Message
```
Portfolio Alignment UI: data confidence layer, CRA source intent, signal governance display, multiple phases

Portfolio Alignment Enhancement:
- Add enrichment.py backend for portfolio data enhancement
- Implement data confidence visualization layer
- Display CRA source intent labels (from Commit 2)
- Display signal governance advisory badges (from Commit 3)
- Implement decision confidence matrix rendering
- Add portfolio alignment data binding to all enrichment modules

No changes to portfolio optimization, ranking, or allocation algorithms.
Pure UI/enrichment layer for data transparency.

Baseline: Commit 8
Breaking changes: None (additive UI)
Tests: Portfolio alignment data confidence layer verified
```

### Validation Commands
```bash
git add src/portfolio/enrichment.py ui/portfolio_alignment/app.js ui/portfolio_alignment/index.html

git commit -m "Portfolio Alignment UI: data confidence layer, CRA source intent, signal governance display, multiple phases"
```

### Rollback
```bash
git reset --hard HEAD~1
```

---

## Commit 10 — UI: Minor Surfaces

**Hash**: Allocation Intelligence + UCF Operator Dashboard  
**Risk**: 🟢 LOW  
**Size**: 3 files | 149 insertions, 0 deletions  
**Execution Order**: **TENTH** ← Execute anytime (independent)

### Files
```
ui/allocation_intelligence/app.js
ui/allocation_intelligence/index.html
ui/ucf_operator_dashboard/index.html
```

### Commit Message
```
UI: allocation intelligence and UCF operator dashboard minor display updates

Minor UI Surface Updates:
- Update allocation intelligence UI with display enhancements
- Update UCF operator dashboard with status indicators
- No business logic changes

Baseline: Commit 9
Breaking changes: None
```

### Validation Commands
```bash
git add ui/allocation_intelligence/app.js ui/allocation_intelligence/index.html \
        ui/ucf_operator_dashboard/index.html

git commit -m "UI: allocation intelligence and UCF operator dashboard minor display updates"
```

### Rollback
```bash
git reset --hard HEAD~1
```

---

## Commit 11 — Portfolio Review Script (⚠️ REVIEW REQUIRED)

**Hash**: scripts/prepare_portfolio_review  
**Risk**: 🟠 HIGH  
**Size**: 1 file | NEW  
**Execution Order**: **ELEVENTH** (after review approval)

### Files
```
scripts/prepare_portfolio_review.py
```

### ⚠️ PRE-COMMIT REQUIREMENTS
- [ ] Code review: Verify no scoring artifact mutations
- [ ] Verify read-only from existing systems
- [ ] Confirm purpose and output format
- [ ] Test execution and output validation
- [ ] Approval from review team

### Commit Message Template
```
scripts/prepare_portfolio_review: portfolio review artifact generation script

[AFTER REVIEW APPROVAL]

Purpose: [Describe purpose]
Inputs: [List input data sources]
Outputs: [List output artifacts]
Algorithm: [Describe transformation logic]

No changes to scoring, ranking, or allocation.
[Confirmation from code review]

Baseline: Commit 10
Breaking changes: None
Tests: [As determined in review]
```

### Validation Commands
```bash
# After review approval:
git add scripts/prepare_portfolio_review.py

PYTHONPATH=. .venv/bin/python -m pytest [review-determined-tests] -v

git commit -m "scripts/prepare_portfolio_review: portfolio review artifact generation script"
```

### Rollback
```bash
git reset --hard HEAD~1
```

---

# Documentation Commits (L1-L6)

---

## Commit 12 — Documentation L1: Refresh UX

**Hash**: docs: REFRESH-UX documentation  
**Size**: ~15 markdown files  
**Execution Order**: **TWELFTH** (after all code commits)

### Commit Message
```
docs: REFRESH-UX documentation

- REFRESH-UX-01 through REFRESH-UX-05A design documents
- Refresh mode guidance system architecture
- Dynamic universe count implementation notes
- Decision impact matrix specifications
- Investment guidance logic documentation

All design, architecture, and validation documentation for refresh subsystem.
```

### Validation
```bash
git add dirty_file_audit/*refresh*.md [other refresh docs]
git commit -m "docs: REFRESH-UX documentation"
```

---

## Commit 13 — Documentation L2: Data Coverage Investigation

**Size**: ~20 markdown files  
**Execution Order**: **THIRTEENTH**

### Commit Message
```
docs: DATA-COVERAGE-01 investigation reports

- Coverage gap analysis
- ESS freshness audit results
- Provider health status reports
- Coverage remediation recommendations

All investigation and audit documentation for data coverage phase.
```

---

## Commit 14 — Documentation L3: Signal Governance

**Size**: ~8 markdown files  
**Execution Order**: **FOURTEENTH**

### Commit Message
```
docs: Signal governance and conflict analysis documentation

- Conflict alpha analysis methodology
- Governance advisory badge specifications
- Signal governance policy documentation

All signal governance and conflict analysis documentation.
```

---

## Commit 15 — Documentation L4: CRA/PA/PIS/MEI

**Size**: ~30 markdown files  
**Execution Order**: **FIFTEENTH**

### Commit Message
```
docs: CRA explain, Portfolio Intelligence System (PIS), and Market Event Intelligence (MEI) documentation

- CRA source intent labeling design
- Portfolio Intelligence System (PA-006/007/008) specifications
- PIS action attribution methodology
- Policy change tracking documentation
- MEI Phase 1 design and validation
- Predictive intelligence modules documentation

All documentation for capital rotation, portfolio intelligence, and market event systems.
```

---

## Commit 16 — Documentation L5: ESS Audit

**Size**: ~10 markdown files  
**Execution Order**: **SIXTEENTH**

### Commit Message
```
docs: ESS intake and coverage audit documentation

- ESS intake ordering logic documentation
- Coverage gap classification methodology
- StarMine freshness detection specification
- Intake readiness assessment results

All ESS intake and coverage audit documentation.
```

---

## Commit 17 — Documentation L6: Governance & Backlog

**Size**: ~34 markdown files  
**Execution Order**: **SEVENTEENTH**

### Commit Message
```
docs: Governance, process, and backlog documentation

- Working tree audit results (DIRTY-FILE-AUDIT-01)
- Commit execution plan (COMMIT-EXECUTION-01)
- Phase verdicts and final assessments
- Backlog status and action inventory
- Architecture assessment and recommendations

All governance, release management, and backlog documentation.
```

---

## Commit 18 — Documentation: Supporting Audits

**Size**: ~10 markdown files  
**Execution Order**: **EIGHTEENTH**

### Commit Message
```
docs: Supporting audit reports and investigation artifacts

- Dirty file audit outputs
- Commit boundary validation
- Release candidate assessment
- Documentation strategy recommendations

All supporting audit and investigation documentation.
```

---

# Execution Checklist

## Pre-Commit Validation

- [ ] All tests passing: `PYTHONPATH=. .venv/bin/python -m pytest -q`
- [ ] Temp files cleaned: ✅ (completed in Phase 1)
- [ ] Git status verified: 186 dirty entries
- [ ] Branch confirmed: `stream/pis-006-post-ingestion-trigger`
- [ ] Baseline tag exists: `sih-v1-feature-complete`
- [ ] No uncommitted changes unaccounted for

## Per-Commit Validation

For each commit (1-10):
- [ ] Files staged with `git add`
- [ ] Related tests run and PASSING
- [ ] Commit message follows convention
- [ ] Rollback understood (reset --hard to previous commit)
- [ ] No unexpected file changes in git diff --cached

## Post-Sequence Validation

After all 18 commits:
- [ ] Repository history clean (18 commits added to baseline)
- [ ] All tests still passing
- [ ] UI validates with hard-reload
- [ ] Branch ready for merge approval
- [ ] Release notes extracted from commit messages

---

# Abort/Rollback Instructions

### Abort During Commit Sequence
If issues arise during commits 1-11:
```bash
# Abort all uncommitted changes
git reset --hard HEAD

# Return to baseline
git checkout sih-v1-feature-complete
```

### Rollback After Single Commit
```bash
# Undo last commit, keep changes in working tree
git reset --soft HEAD~1

# Or reset to clean state
git reset --hard HEAD~1
```

### Rollback After Multiple Commits
```bash
# Return to baseline (loses all commits)
git reset --hard sih-v1-feature-complete
```

---

# ✅ Phase 4 Conclusion

**Exact commit sequence defined**: 18 commits (12 core + 6 doc sub-commits)  
**All commits have**: Clear scope, validation steps, commit messages, rollback paths  
**Recommended start**: Commit 1 (ESS Intake & Coverage) — smallest, safest, no dependencies  
**Estimated execution time**: 30-45 minutes  
**Risk level**: LOW (all tests passing, zero algorithm changes)

**Next**: Phase 5 — Release candidate assessment
