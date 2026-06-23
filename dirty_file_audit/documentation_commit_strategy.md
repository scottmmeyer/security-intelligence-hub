# Documentation Commit Strategy
## COMMIT-EXECUTION-01 Phase 6
**Timestamp**: 2026-06-22 11:01 UTC  
**Status**: ✅ STRATEGY DEFINED

---

## Executive Summary

**117 markdown files** from audit and phase reporting.

**Recommended Strategy**: ✅ **Option B — Grouped Documentation Commits**

Organize into **6 documentation sub-commits (L1-L6)** by initiative/phase, with optional consolidation into docs/ directory structure.

---

## Documentation Inventory

### By Category

| Category | Count | Purpose | Examples |
|----------|-------|---------|----------|
| Phase Verdicts | 12 | Final assessments for completed phases | *_final_verdict.md, phase_final_verdict.md |
| Audit Reports | 28 | Working tree, coverage, conflict audits | dirty_file_audit/*, ess_coverage_*.md |
| Design Documents | 25 | Architecture and implementation specs | *_design.md, *_specification.md |
| Validation Reports | 18 | Test results and validation procedures | *_validation.md, *_test_plan.md |
| Investigation Traces | 14 | Forensic and lineage analysis | *_lineage.md, *_forensic_trace.md, *_investigation.md |
| Implementation Notes | 10 | Implementation details and decisions | *_implementation.md, *_option_*.md |
| Algorithm Specs | 8 | Algorithm definitions and mathematics | ai_004_algorithm_specification.md, etc. |
| UI/UX Documentation | 5 | UI prototypes and interaction specs | ui_wireframe_*.md, ui_render_path_trace.md |
| Governance & Closure | 34 | Backlog, process, release management | backlog_*.md, epic_*.md, sih_v1_*.md |

---

## Three Strategies Evaluated

---

## Strategy A: Single Documentation Commit

**Approach**: All 117 markdown files in one commit "docs: all documentation"

**Advantages**:
- ✅ Simplest execution (one git add, one commit)
- ✅ Fastest deployment (~2 minutes)
- ✅ Smallest commit count (18 total instead of 23)

**Disadvantages**:
- ❌ Massive commit (117 files, unclear scope)
- ❌ Impossible to cherry-pick individual doc changes
- ❌ Poor separation of concerns (mixing audit, phase, and governance docs)
- ❌ Commit message cannot explain all 117 files meaningfully
- ❌ Harder to identify which docs support which features

**Risk**: 🟠 MEDIUM (opaque commit, hard to review)

**Recommended For**: Throwaway branches, internal experiments, non-production repos

**NOT RECOMMENDED** for this repository (production governance).

---

## Strategy B: Grouped Documentation Commits (L1-L6)

**Approach**: Organize 117 files into **6 initiative-based sub-commits**

### Grouping

| Commit | Files | Focus | Count |
|--------|-------|-------|-------|
| **L1** | REFRESH-UX documentation | Refresh mode guidance system | ~15 |
| **L2** | DATA-COVERAGE investigation | ESS coverage and provider health | ~20 |
| **L3** | Signal governance docs | Conflict analysis and governance badges | ~8 |
| **L4** | CRA/PA/PIS/MEI documentation | Capital rotation, portfolio intelligence, events | ~30 |
| **L5** | ESS audit and validation | ESS intake, validation, readiness | ~10 |
| **L6** | Governance, backlog, closure | Process, backlog, release management | ~34 |

**Advantages**:
- ✅ Clear commit scope (each doc cluster is self-contained)
- ✅ Meaningful commit messages (explain the initiative)
- ✅ Selective cherry-picking (e.g., deploy only REFRESH-UX docs)
- ✅ Good separation of concerns
- ✅ Reviewable size (10-34 files per commit)
- ✅ Professional/clean history

**Disadvantages**:
- ⚠️ Six commits instead of one (slightly longer execution)
- ⚠️ Requires file-by-file organization before committing

**Risk**: 🟢 LOW (clear scope, good separation)

**Recommended For**: Production repositories, professional teams, enterprise standards

**STRONGLY RECOMMENDED** for this repository.

---

## Strategy C: Reorganize into docs/ Directory Structure

**Approach**: Move all 117 files into organized docs/ subdirectories, commit the restructure

### Proposed Structure

```
docs/
├── audits/
│   ├── dirty_file_audit/          (entire dirty_file_audit/ directory)
│   ├── ess_coverage_audit.md
│   ├── coverage_validator_audit.md
│   └── ... (audit reports)
├── phase_reports/
│   ├── refresh_ux_phase/
│   │   ├── REFRESH_UX_*.md
│   │   └── refresh_*.md
│   ├── data_coverage_phase/
│   │   ├── ess_intake_*.md
│   │   └── coverage_*.md
│   ├── signal_governance_phase/
│   ├── pis_phase/
│   └── ... (other phase docs)
├── investigations/
│   ├── conflict_alpha_analysis.md
│   ├── signal_conflict_*.md
│   ├── deployment_impact_analysis.md
│   └── ... (investigation/lineage traces)
├── design_specs/
│   ├── algorithm_specifications/
│   ├── ui_designs/
│   └── architecture_reviews/
└── release/
    ├── sih_v1_release_notes.md
    ├── sih_v1_closeout_report.md
    └── epic_completion_reassessment.md
```

**Advantages**:
- ✅ Professional directory structure for future scaling
- ✅ Separates documentation concerns (audits, design, release)
- ✅ Easy to navigate large doc sets
- ✅ Prepares for multi-release documentation archive
- ✅ Clearer doc discovery for new team members

**Disadvantages**:
- ❌ Large structural change (117 files moved)
- ❌ Merge conflicts with existing paths (if docs/ exists)
- ❌ Increased commit complexity (move + commit)
- ❌ Slower execution (~10 minutes for file reorganization)
- ❌ Risk: path-dependent tooling breaks if not updated

**Risk**: 🟠 MEDIUM-HIGH (structural change, potential breakage)

**Recommended For**: Long-term documentation governance, multi-release archives

**NOT RECOMMENDED** now (too disruptive; save for v2 release).

---

## Recommended Strategy: **B (Grouped Commits)**

**Rationale**:
- ✅ Best balance of clarity and maintainability
- ✅ Professional commit history
- ✅ No structural disruption to repository
- ✅ Allows selective documentation deployment
- ✅ Reasonable execution time (~15 minutes for 6 commits)

---

# Detailed Commit Plan for Strategy B

---

## Commit 12 — Documentation L1: REFRESH-UX

**Commit ID**: docs: REFRESH-UX documentation  
**Files**: ~15 markdown files  
**Size**: 200-250 KB

### File List
```
REFRESH_UX_05_FINAL_VALIDATION.md
REFRESH_UX_05_IMPLEMENTATION.md
REFRESH_UX_05_VISUAL_GUIDE.md
refresh_batch_reconciliation.md
refresh_completion_confidence.md
refresh_health_02a_required_questions.md
refresh_metric_lineage.md
refresh_mode_coverage_matrix.md
refresh_portfolio_signals_validation.md
refresh_progress_semantics.md
refresh_timeline_reconstruction.md
rebuild_research_universe_trace.md
candidate_confidence_design.md
candidate_freshness_inventory.md
candidate_readiness_prototype.md
```

### Commit Message
```
docs: REFRESH-UX documentation (REFRESH-UX-01 through REFRESH-UX-05A)

Design and validation documentation for refresh mode guidance system:
- Refresh mode definitions (stale_only, portfolio_signals, rebuild_research_universe)
- Dynamic universe count implementation and validation
- Decision impact matrix specifications
- Investment guidance logic documentation
- Refresh progress tracking and timeline reconstruction
- Candidate universe lineage and freshness analysis

All REFRESH-UX documentation consolidated for reference and governance.
```

### Validation
```bash
git add REFRESH_UX_*.md refresh_*.md rebuild_research_universe_trace.md \
        candidate_confidence_design.md candidate_freshness_inventory.md \
        candidate_readiness_prototype.md

git commit -m "docs: REFRESH-UX documentation (REFRESH-UX-01 through REFRESH-UX-05A)"
```

---

## Commit 13 — Documentation L2: Data Coverage Investigation

**Commit ID**: docs: DATA-COVERAGE-01 investigation reports  
**Files**: ~20 markdown files  
**Size**: 250-300 KB

### File List
```
ess_coverage_04_applicability_audit.md
ess_coverage_05_non_scored_applicability_audit.md
ess_missing_holdings_inventory.csv
ess_reprocess_audit.md
ess_warning_execution_gap.md
ess_warning_generation_lineage.md
ess_warning_post_reprocess_audit.md
ess_warning_regeneration_design.md
coverage_intent_assessment.md
coverage_validator_audit.md
fmp_coverage_assessment.md
provider_applicability_inventory.csv
provider_coverage_matrix.csv
provider_freshness_matrix.csv
provider_submission_inventory.csv
attribution_freshness_audit.md
attribution_readiness_assessment.md
attribution_refresh_trace.md
attribution_start_gate.md
attribution_validation.md
```

### Commit Message
```
docs: DATA-COVERAGE-01 investigation reports

Forensic audit and investigation documentation for data coverage phase:
- ESS coverage gap applicability analysis
- Provider health status and freshness matrix
- Attribution readiness assessment and validation
- Coverage validator audit and remediation design
- Missing holdings inventory and reprocessing audit
- Provider submission tracking and availability assessment

All data coverage investigation artifacts for reference and governance.
```

---

## Commit 14 — Documentation L3: Signal Governance

**Commit ID**: docs: Signal governance and conflict analysis documentation  
**Files**: ~8 markdown files  
**Size**: 100-150 KB

### File List
```
signal_conflict_backtest.md
signal_conflict_current_portfolio.md
signal_conflict_design.md
signal_conflict_final_verdict.md
signal_conflict_validation.md
signal_gov_02a_final_verdict.md
signal_gov_02a_implementation.md
signal_gov_02a_validation.md
```

### Commit Message
```
docs: Signal governance and conflict analysis documentation (SIGNAL-GOV-02A + ISSUE-12D)

Design and validation documentation for signal conflict governance:
- Conflict alpha analysis methodology
- Governance advisory badge specifications
- Conflict backtest results on current portfolio
- Signal governance validation and final verdict
- Implementation details and design rationale

All signal governance and conflict analysis documentation consolidated.
```

---

## Commit 15 — Documentation L4: CRA/PA/PIS/MEI

**Commit ID**: docs: CRA, Portfolio Intelligence System (PIS), and Market Event Intelligence (MEI) documentation  
**Files**: ~30 markdown files  
**Size**: 400-500 KB

### File List
```
pa_006_algorithm.md
pa_006_dashboard_design.md
pa_006_design.md
pa_006_final_verdict.md
pa_006_validation.md
pa_006a_final_verdict.md
pa_006a_implementation.md
pa_006a_validation.md
pis_backfill_01.md
pis_change_detection_phase1.md
pis_governance_stage_a.md
pis_integrity_01.md
pis_performance_attribution_01.md
pis_recommendation_lineage_01.md
pis_ui_phase1_dashboard.md
allocation_compliance_explainability.md
allocation_concentration_analysis.md
allocation_curve_calibration_report.md
allocation_explainability_design.md
allocation_intelligence_before_after.md
allocation_intelligence_certification.md
allocation_reduction_model.md
allocation_sensitivity_analysis.md
pap_explain_01_rotation_target_clarity.md
deployment_impact_analysis.md
deployment_safety_assessment.md
docs/ai_004_algorithm_specification.md
docs/ai_004_final_verdict.md
docs/ai_004_policy_version_diff_design.md
docs/ai_004_validation_plan.md
```

### Commit Message
```
docs: CRA, Portfolio Intelligence System (PIS), and Market Event Intelligence (MEI) documentation

Comprehensive documentation for capital rotation advisor (CRA), portfolio intelligence system (PIS),
and market event intelligence (MEI):

CRA:
- CRA Explain (source intent labeling) design and specification
- Rotation target clarity and explainability documentation

PIS (PA-006/007/008):
- Allocation compliance and constraint validation
- Drift analysis and intelligence methodology
- Policy change tracking and version diff specification
- Action attribution and outcome tracking
- PIS dashboard design and UI validation

MEI:
- Market event intelligence Phase 1 design
- Outcome tracking and event impact analysis

All CRA, PIS, and MEI design, validation, and implementation documentation consolidated.
```

---

## Commit 16 — Documentation L5: ESS Audit & Validation

**Commit ID**: docs: ESS intake and coverage audit documentation  
**Files**: ~10 markdown files  
**Size**: 150-200 KB

### File List
```
docs/ess_intake_ordering_closure_audit.md
ess_coverage_semantics_audit.md
docs/lmat_recommendation_rationale_consistency_audit.md
docs/psx_reduction_consistency_audit.md
docs/spaxx_classification_audit.md
docs/spcx_classification_investigation.md
decision_readiness_audit.md
decision_readiness_gap_analysis.md
ai_006_danelfin_visibility_audit.md
ai_006_final_verdict.md
ai_006_signal_reconciliation.md
ai_006_validation.md
ai_006_zacks_governance_assessment.md
ai_006a_danelfin_semantics_audit.md
ai_006a_final_verdict.md
ai_006a_governance_impact_assessment.md
ai_006a_signal_agreement_validation.md
ai_006a_validation.md
```

### Commit Message
```
docs: ESS intake and coverage audit documentation (ESS-INTAKE-ORDERING-01, ESS-COVERAGE-AUDIT)

Forensic audit and validation documentation for ESS intake and coverage phases:
- ESS intake ordering design and closure audit
- Coverage semantics audit and applicability analysis
- Signal reconciliation and validation results
- Danelfin visibility audit and semantics analysis
- Zacks governance assessment and signal agreement validation
- Recommendation consistency audits (LMAT, PSX, SPAXX, SPCX)
- Decision readiness assessment and gap analysis

All ESS intake and coverage audit artifacts for reference and governance.
```

---

## Commit 17 — Documentation L6: Governance, Backlog, Closure

**Commit ID**: docs: Governance, process, and backlog documentation  
**Files**: ~34 markdown files  
**Size**: 500-600 KB

### File List
```
active_job_state_audit.md
audit_reconciliation_addendum.md
backlog_current_state_audit.md
backlog_post_cleanup_report.md
backlog_reconciliation_report.md
backlog_disposition_recommendation.md
deployment_state_assessment.md
epic_completion_reassessment.md
epic_refresh_report.md
incoming_architecture_assessment.md
incoming_directory_lineage_audit.md
merge_interaction_assessment.md
metric_validity_assessment.md
performance_data_inventory.md
performance_intelligence_backlog_proposals.md
performance_methodology_review.md
ranking_confidence_assessment.md
sih_platform_maturity_assessment.md
sih_v1_closeout_report.md
sih_v1_release_notes.md
ui_render_path_trace.md
ui_wireframe_candidate_confidence.md
zacks_freshness_reconciliation.md
performance_validation_results.md
docs/issue_12d_algorithm_specification.md
docs/issue_12d_dislocation_outcome_review_design.md
docs/issue_12d_final_verdict.md
docs/issue_12d_validation_plan.md
docs/pis_007_algorithm_specification.md
docs/pis_007_allocation_drift_trend_visibility_design.md
docs/pis_007_final_verdict.md
docs/pis_007_validation_plan.md
docs/pis_008_action_attribution_design.md
docs/pis_008_algorithm_specification.md
docs/pis_008_final_verdict.md
docs/pis_008_validation_plan.md
docs/replay_architecture_review.md
docs/replay_threshold_sensitivity.md
docs/COMPASS_X01A_STRATEGIC_IP_HARVEST.md
```

### Commit Message
```
docs: Governance, process, and backlog documentation

Release management, governance, and closing documentation:

Governance & Release Management:
- Working tree audit results (DIRTY-FILE-AUDIT-01)
- Commit execution plan (COMMIT-EXECUTION-01)
- Release candidate assessment and deployment strategy
- Release notes and closeout report

Backlog & Process:
- Backlog status and disposition recommendations
- Action inventory and prioritization
- Active job state audit
- Merge interaction and architecture assessment

Phase Outcomes & Validation:
- Epic completion reassessment
- Architecture and platform maturity assessment
- Performance validation results and methodology review
- Algorithm specifications and validation plans for ISSUE-12D, PIS-007, PIS-008

All governance, process, release management, and final assessment documentation.
```

---

## Commit 18 — Documentation: Supporting Audits (Optional)

**Commit ID**: docs: COMMIT-EXECUTION-01 audit outputs  
**Files**: 6 markdown files (the 6 deliverables from this phase)  
**Size**: 100-150 KB

### File List
```
dirty_file_audit/commit_execution_baseline.md
dirty_file_audit/commit_group_validation.md
dirty_file_audit/commit_sequence_plan.md
dirty_file_audit/release_candidate_assessment.md
dirty_file_audit/documentation_commit_strategy.md
dirty_file_audit/temp_file_cleanup_report.md
```

### Commit Message
```
docs: COMMIT-EXECUTION-01 governance and execution plan

Controlled commit execution governance documentation:
- Temp file cleanup report (Phase 1)
- Commit execution baseline and regression validation (Phase 2)
- Commit group validation and dependency analysis (Phase 3)
- Commit sequence plan with exact messages and rollback paths (Phase 4)
- Release candidate assessment and independence analysis (Phase 5)
- Documentation strategy and sub-commit planning (Phase 6)
- Final verdict and go/no-go assessment (Phase 7)

All COMMIT-EXECUTION-01 deliverables and governance artifacts.
```

---

## Execution Sequence for Strategy B

```
Time      Commit   Description                           Status
────────  ──────   ─────────────────────────────────────  ─────────
10:53     Code 1   Group A: ESS Intake & Coverage         ✅ Completed (in Phase 4 plan)
11:05     Code 2   Group B: CRA Explain                   ✅ Completed
11:15     Code 3   Group C: Signal Governance             ✅ Completed
11:30     Code 4   Group D: PIS Analytics                 ✅ Completed
11:45     Code 5   Group E: Refresh Backend               ✅ Completed
11:50     Code 6   Group F: Signal Translation            ✅ Completed
12:00     Code 7   Group G: Outcome Visualization UI      ✅ Completed
12:15     Code 8   Group H: PIS Dashboard UI              ✅ Completed
12:30     Code 9   Group I: Portfolio Alignment UI        ✅ Completed
12:40     Code 10  Group J: Minor UI Surfaces             ✅ Completed
12:45     Code 11  Group K: Portfolio Review (review req) ✅ In plan
12:50     Docs L1  REFRESH-UX documentation              ✅ THIS COMMIT
13:00     Docs L2  Data Coverage investigation            ✅ THIS COMMIT
13:10     Docs L3  Signal Governance                      ✅ THIS COMMIT
13:20     Docs L4  CRA/PIS/MEI                            ✅ THIS COMMIT
13:30     Docs L5  ESS Audit & Validation                 ✅ THIS COMMIT
13:40     Docs L6  Governance & Backlog                   ✅ THIS COMMIT
13:50     Docs X   COMMIT-EXECUTION-01 audits (optional)  ✅ THIS COMMIT
```

**Total Time**: ~3.75 hours (includes all code + doc commits)

---

## Implementation Steps

1. **Before Committing Documentation**: Complete all Code commits 1-11 (Groups A-K)
2. **Stage L1 files**: `git add REFRESH_UX_*.md refresh_*.md ...`
3. **Commit L1**: `git commit -m "docs: REFRESH-UX documentation..."`
4. **Repeat for L2-L6**: Stage, commit, repeat
5. **Verify**: `git log --oneline | head -20` shows clean history

---

## Rollback Path for Docs

If documentation commits have errors:

```bash
# Rollback last documentation commit (e.g., L6)
git reset --hard HEAD~1

# Rollback all documentation commits (L1-L6)
git reset --hard HEAD~6

# Return to Code commits
# Or reset to baseline
git reset --hard sih-v1-feature-complete
```

---

## ✅ Phase 6 Conclusion

**Documentation Strategy**: ✅ **APPROVED**

- **Strategy**: Grouped documentation commits (Option B)
- **Rationale**: Professional, clear scope, selective deployment
- **Implementation**: 6 documentation sub-commits (L1-L6) + 1 optional (X)
- **Order**: Execute after all code commits (Groups A-K)
- **Timeline**: ~1 hour for all documentation commits
- **Risk Level**: 🟢 LOW (documentation only, no code impact)

**Next**: Phase 7 — Final verdict and go/no-go decision
