# Issue Disposition Recommendations
## GitHub Issue Triage and Action Plan
**Assessment Date**: 2026-06-22  
**Assessment Baseline**: Post-COMMIT-EXECUTION-01  
**Recommendation Type**: GitHub Actions to execute manually

> Freshness note (2026-07-07): This document is a point-in-time governance action plan captured after COMMIT-EXECUTION-01. Treat issue status, ownership, labels, and timelines below as historical guidance that may require re-validation before execution.

---

## Overview

This document provides explicit GitHub actions for each of the 7 open issues based on the post-commit assessment. All actions are **manual (not automated)** — no issues will be closed automatically without explicit user review.

---

## Action-by-Action Recommendations

---

## Issue #59: EPIC: Predictive Intelligence

**Current State:**
- Status: OPEN
- Created: 2026-06-17
- Completion Estimate: ~75%
- Child issue: #57 (PERF-VAL-01)

**Recommendation**: **KEEP OPEN — POST SCOPE-REFRESH COMMENT**

### Recommended GitHub Action

**Action Type**: Update issue body + post comment  
**Estimated Effort**: 15 minutes  
**Owner**: Data Science team lead

**Steps:**

1. Open issue #59 in GitHub

2. **Append to issue body** (at end, before "Future Milestones"):
   ```markdown
   ## Delivered Phases (Archived 2026-06-22)
   
   ✅ **DISLOCATION-02: Magnitude Accuracy** (merged 2026-06-15)
   ✅ **DISLOCATION-03: Correlation Analysis** (merged 2026-06-15)
   ✅ **DISLOCATION-04: Event Sensitivity** (merged 2026-06-16)
   ✅ **DISLOCATION-05: Conflict Alpha Analysis** (merged 2026-06-21)
   ✅ **DISLOCATION-06: Forward Return Estimates** (merged 2026-06-21)
   ✅ **DISLOCATION-07: Directional Accuracy** (merged 2026-06-22)
   
   Governance note: All predictive outputs remain **research-qualified** and display-only per governance boundary. 
   No predictive signals are promoted to decision-grade without explicit algorithm-change governance process.
   ```

3. **Post new comment**:
   ```markdown
   ## Scope Refresh — 2026-06-22
   
   COMMIT-EXECUTION-01 has delivered all DISLOCATION phases (02-07) and supporting infrastructure 
   for forward return estimates, event-triggered refresh, pattern persistence analysis, and conflict alpha.
   
   **Current active work**: #57 PERF-VAL-01 (Performance Validation Framework)
   
   **Remaining future work**:
   - Forward outcome validation against actual realized returns
   - Confidence calibration refinement (DISLOCATION-06 reliability tiers tuning)
   - Scenario intelligence evolution
   
   **Status**: Epic remains OPEN as strategic research program.
   **Production readiness**: Predictive outputs are informational/research-qualified; not decision-grade.
   **Next milestone**: Complete PERF-VAL-01 validation framework (#57).
   ```

4. **Labels**: Verify present: `epic`, `ai/predictive`, `research-qualified`  
   If missing, add them.

5. **Assign**: Assign to Data Science team lead for roadmap planning

**Expected outcome**: Epic body updated with clear delivery history and remaining scope; contributor clarity improved.

---

## Issue #57: PERF-VAL-01: Performance Calculation Validation — Fidelity vs SIH

**Current State:**
- Status: OPEN
- Child issue of: #59
- Completion Estimate: Not started
- Effort estimate: 2-4 weeks

**Recommendation**: **KEEP OPEN — ASSIGN FOR FY2027 PLANNING**

### Recommended GitHub Action

**Action Type**: Update labels + assign + post comment  
**Estimated Effort**: 10 minutes  
**Owner**: Engineering lead

**Steps:**

1. Open issue #57 in GitHub

2. **Add/Update Labels**: Verify present:
   - `ai/predictive` ✓
   - `validation` ✓
   - `post-release` ✓ (add if missing)
   - `fy2027-roadmap` (add if missing)

3. **Assign**: Assign to Data Science team lead

4. **Post comment**:
   ```markdown
   ## Scope Update — 2026-06-22
   
   COMMIT-EXECUTION-01 has delivered supporting infrastructure (MEI event history, outcome tracking, 
   performance data collection) for this validation framework.
   
   This issue is now ready for FY2027 workstream planning. Not a release blocker.
   
   **Next steps**:
   1. Decompose validation framework scope (reconciliation logic, reporting, edge cases)
   2. Assign to Data Science team with 2-4 week effort estimate
   3. Schedule for Q3 2026 execution
   
   **Owner**: Data Science team
   ```

5. **Milestone**: Set to "FY2027 Q3" or similar future milestone

**Expected outcome**: Issue remains tracked but explicitly marked as post-release work; team has clear ownership and timeline.

---

## Issue #56: ESS-INTAKE-PERSIST-01: Persistence Validator Mismatch

**Current State:**
- Status: OPEN
- Type: BUG (production defect)
- Priority: HIGH
- Completion Estimate: 2-3 days

**Recommendation**: **KEEP OPEN (HIGH PRIORITY) — URGENT POST-RELEASE FIX**

### Recommended GitHub Action

**Action Type**: Update labels + priority + assign + post urgent comment  
**Estimated Effort**: 10 minutes  
**Owner**: Data Engineering lead

**Steps:**

1. Open issue #56 in GitHub

2. **Add/Update Labels**: Ensure present:
   - `bug` ✓
   - `ess-intake` ✓
   - `high-priority` (add if missing)
   - `post-release-cleanup` (add if missing)
   - `production-defect` (add if missing)

3. **Assign**: Assign to Data Engineering team lead

4. **Priority/Severity**: Set to "Urgent" or "High" (if using priority field)

5. **Post urgent comment** (pin this):
   ```markdown
   ## POST-RELEASE PRIORITY — 2026-06-22
   
   ⚠️ **This is the only production defect blocking full automation trust.**
   
   **Defect summary:**
   - Intake writes valid run partitions but still reports FAILED
   - Merged snapshot row count includes prior same-day runs
   - Incoming files not auto-cleaned (cleanup gated behind COMPLETE status)
   - Operational consequence: incoming file automation cannot be fully trusted
   
   **Fix requirement:**
   - Implement validator logic comparing run-partition rows (not merged snapshot total)
   - Restore automatic incoming-file cleanup on successful persistence
   - Add comprehensive test coverage
   
   **Guidance**: See `backlog_current_state_audit.md` section "#56 ESS-INTAKE-PERSIST-01" for detailed fix direction.
   
   **Target**: Complete by 2026-06-27 (immediately post-release).
   
   **Owner**: Data Engineering
   ```

6. **Create milestone**: Create/assign to "2026-Q2-Hotfix" or "Post-Release-Cleanup" milestone

**Expected outcome**: Issue is explicitly flagged as highest-priority post-release work; team understands urgency and fix path.

---

## Issue #6: EPIC: Governance and Tooling

**Current State:**
- Status: OPEN
- Completion Estimate: ~91%
- Scope: Platform-wide governance and CI/CD

**Recommendation**: **KEEP OPEN — POST SCOPE-REFRESH COMMENT + CREATE 3 CHILD ISSUES**

### Recommended GitHub Action

**Action Type**: Create 3 child issues + post scope-refresh comment  
**Estimated Effort**: 30 minutes  
**Owner**: Engineering/Platform lead

**Steps:**

1. **Create Child Issue #60a: GOV-CI-01 (GitHub Actions CI on Push)**
   - Title: `GOV-CI-01: GitHub Actions automated test gate on push`
   - Body:
     ```markdown
     ## Objective
     Implement GitHub Actions workflow to run full test suite on every push to feature branches.
     
     ## Scope
     - Create `.github/workflows/ci.yml` with full test suite execution
     - Set as required status check for PR merges
     - Include performance benchmark tracking (optional)
     
     ## Acceptance Criteria
     - [ ] CI workflow runs on all pushes to non-main branches
     - [ ] PR cannot merge if tests fail
     - [ ] Test results visible in GitHub PR UI
     - [ ] Documentation updated with CI process
     
     ## Effort: 2-3 days
     ## Owner: Platform/DevOps team
     ```
   - Labels: `epic/6`, `governance`, `platform`, `ci-cd`
   - Assign to: Platform engineer

2. **Create Child Issue #60b: GOV-FRESH-01 (Signal Freshness Monitoring)**
   - Title: `GOV-FRESH-01: Automated signal freshness monitoring and alerting`
   - Body:
     ```markdown
     ## Objective
     Implement automated monitoring for stale signal detection and alerting.
     
     ## Scope
     - Monitor last-refresh timestamp for critical signal providers
     - Alert if signal older than defined threshold (e.g., 24 hours)
     - Dashboard visibility of signal freshness status
     
     ## Acceptance Criteria
     - [ ] Monitoring infrastructure established (cron or event-driven)
     - [ ] Alert mechanism configured (Slack, email, etc.)
     - [ ] Dashboard shows freshness status per provider
     - [ ] Documentation updated with SLA definitions
     
     ## Effort: 3-5 days
     ## Owner: Data Engineering team
     ```
   - Labels: `epic/6`, `governance`, `platform`, `monitoring`
   - Assign to: Data Engineering lead

3. **Create Child Issue #60c: GOV-DEBT-01 (Config Registry Cleanup)**
   - Title: `GOV-DEBT-01: YAML registry and config technical debt cleanup`
   - Body:
     ```markdown
     ## Objective
     Address technical debt in configuration and signal registry files.
     
     ## Scope
     - Consolidate config/* YAML files (currently scattered)
     - Validate signal registry for duplicates/conflicts
     - Establish config governance standards
     - Document config conventions in CONTRIBUTING.md
     
     ## Acceptance Criteria
     - [ ] All config files organized under config/
     - [ ] Signal registry validated and consolidated
     - [ ] No duplicate or conflicting definitions
     - [ ] Config loading documented
     - [ ] CONTRIBUTING.md updated with config guidelines
     
     ## Effort: 3-5 days
     ## Owner: Platform/Architecture team
     ```
   - Labels: `epic/6`, `governance`, `platform`, `technical-debt`
   - Assign to: Architecture lead

4. Open issue #6 and **append to issue body**:
   ```markdown
   ## Delivered Phases (Archived 2026-06-22)
   
   ✅ **Backlog Establishment & Governance Standards** (2026-06-17)
   ✅ **Issue Refresh Cycle & Triage Process** (2026-06-17)
   ✅ **Commit Governance Framework** (2026-06-22)
   ✅ **Clean Working Tree Processes** (2026-06-22)
   ✅ **Defect Tracking Activated** (Issue #56 active)
   
   ## Remaining Work (New Child Issues)
   
   - 🔧 #60a: GOV-CI-01 — GitHub Actions CI on push
   - 🔧 #60b: GOV-FRESH-01 — Signal freshness monitoring
   - 🔧 #60c: GOV-DEBT-01 — Config technical debt cleanup
   ```

5. **Post scope-refresh comment**:
   ```markdown
   ## Scope Refresh — 2026-06-22
   
   COMMIT-EXECUTION-01 has delivered core governance infrastructure (backlog process, issue triage, 
   commit governance, working tree hygiene).
   
   **Remaining work** is now decomposed into 3 explicit child issues (see "Remaining Work" section above).
   
   **Status**: Epic remains OPEN as evergreen platform governance epic.
   **Current focus**: Three targeted infrastructure improvements (CI, monitoring, technical debt).
   **Closure criteria**: N/A (platform governance is continuous evolution).
   
   Child issues #60a, #60b, #60c are now ready for assignment and execution.
   ```

**Expected outcome**: Epic body updated with clear decomposition; 3 child issues are actionable and ready for team assignment; governance framework is transparent and traceable.

---

## Issue #5: EPIC: Signal Intelligence Evolution

**Current State:**
- Status: OPEN
- Completion Estimate: ~95%
- Delivered: DISLOCATION-02 through DISLOCATION-07, ISSUE-12D, conflict analytics

**Recommendation**: **KEEP OPEN — REPHASE AS "SIGNAL INTELLIGENCE v2" + POST SCOPE REFRESH**

### Recommended GitHub Action

**Action Type**: Update issue body + post rephasing comment  
**Estimated Effort**: 20 minutes  
**Owner**: Research/Data Science lead

**Steps:**

1. Open issue #5 in GitHub

2. **Update issue title** (if allowed):
   - From: `EPIC: Signal Intelligence Evolution`
   - To: `EPIC: Signal Intelligence v2 — Quality, Freshness, and Governance`

3. **Append to issue body**:
   ```markdown
   ## Delivered Phases (Archived 2026-06-22)
   
   ✅ **ISSUE-12D: Signal Conflict Governance** (2026-06-21)
   ✅ **DISLOCATION-02: Magnitude Accuracy Baselines** (2026-06-15)
   ✅ **DISLOCATION-03: Correlation Analysis** (2026-06-15)
   ✅ **DISLOCATION-04: Event Sensitivity Calibration** (2026-06-16)
   ✅ **DISLOCATION-05: Conflict Alpha Analysis** (2026-06-21)
   ✅ **DISLOCATION-06: Forward Return Estimates** (2026-06-21)
   ✅ **DISLOCATION-07: Directional Accuracy Assessment** (2026-06-22)
   
   **Key findings**: All delivered diagnostics are research-qualified and display-only. 
   Predictive outputs support decision-making but are not autonomous scoring signals.
   ```

4. **Post rephasing comment**:
   ```markdown
   ## Scope Refresh & Rephasing — 2026-06-22
   
   COMMIT-EXECUTION-01 has delivered comprehensive signal diagnostics ecosystem (DISLOCATION phases 02-07, 
   conflict governance framework ISSUE-12D). All delivered work focuses on signal explainability, quality 
   assessment, and governance controls — not scoring or autonomous recommendations.
   
   **Rephasing**: From "Signal Intelligence Evolution" to "Signal Intelligence v2: Quality, Freshness, and Governance"
   
   **Delivered v1 capabilities**:
   - Signal conflict detection and governance badges
   - Performance diagnostics (magnitude, correlation, directional accuracy)
   - Event sensitivity calibration
   - Conflict alpha analysis and pattern persistence assessment
   
   **v2 Strategic Focus** (post-release):
   - Signal freshness governance and monitoring
   - Quality control and calibration refinement
   - Advanced validation and outcome tracking
   - Feature retirement strategy
   
   **Status**: Epic remains OPEN as strategic research program.
   **Production readiness**: Diagnostics mature; predictive outputs research-qualified.
   **Next milestone**: Define v2 roadmap with research team.
   
   The stale "FMP integration assessments" and "drift penalty progression" items from earlier 
   issue body have been superseded by the DISLOCATION work. Epic body should be refreshed in next planning cycle.
   ```

5. **Labels**: Verify present:
   - `epic` ✓
   - `signal-intelligence` ✓
   - `strategic` ✓
   - `research-qualified` (add if missing)

6. **Assign**: Assign to Research/Data Science lead for v2 roadmap definition

**Expected outcome**: Epic is rephased to accurately reflect current scope and capabilities; delivered work is clearly archived; v2 roadmap is transparent.

---

## Issue #3: EPIC: Portfolio Action Pipeline (PAP)

**Current State:**
- Status: OPEN
- Completion Estimate: ~94%
- Core PAP delivered; PAP v2 scope TBD

**Recommendation**: **KEEP OPEN — DECOMPOSE PAP v2 SCOPE INTO CHILD ISSUES (CRITICAL)**

### Recommended GitHub Action

**Action Type**: Create 2-3 child issues for PAP v2 + post scope-refresh comment  
**Estimated Effort**: 45 minutes  
**Owner**: Platform/PAP team lead

**Steps:**

1. **Create Child Issue: PAP-V2-DESIGN (PAP v2 Scope Definition)**
   - Title: `PAP-V2-DESIGN: Decompose and define Portfolio Action Pipeline v2 scope`
   - Body:
     ```markdown
     ## Objective
     Explicitly define scope, acceptance criteria, and prioritization for PAP v2 enhancements.
     
     ## Context
     Core PAP (v1) is ~94% complete and production-ready. PAP v2 (23.0B) is currently TBD and blocks contributor clarity.
     This is a **design/planning task**, not implementation.
     
     ## Scope
     - Review existing PAP v2 placeholder items in issue #3
     - Identify operator workflow pain points (from feedback or logs)
     - Define 2-4 concrete v2 features with acceptance criteria
     - Prioritize by business value and effort
     
     ## Deliverables
     - Prioritized list of v2 features (max 4 items)
     - Effort estimates for each
     - Business value justification
     - Acceptance criteria for each
     
     ## Acceptance Criteria
     - [ ] PAP v2 scope is no longer TBD
     - [ ] Each feature has explicit acceptance criteria
     - [ ] Effort estimates are documented
     - [ ] Team agrees on priority ordering
     
     ## Effort: 2-3 days (planning task)
     ## Owner: PAP/Platform team lead
     ```
   - Labels: `epic/3`, `portfolio-action`, `design`, `v2`
   - Assign to: PAP team lead

2. Open issue #3 and **append to issue body**:
   ```markdown
   ## Delivered Phases (Archived 2026-06-22)
   
   ✅ **Core PAP Implementation (23.0-23.5)** (2026-06-22)
   ✅ **Signal Attribution & Approval Workflows** (2026-06-22)
   ✅ **PIS Integration & Action Prioritization** (2026-06-22)
   ✅ **Deployment Workflow Foundations** (2026-06-22)
   
   ## Remaining Work (Planned v2)
   
   - 🔧 PAP-V2-DESIGN: Scope definition and decomposition (planning task)
   - Features TBD pending scope definition
   
   **Important**: PAP v2 scope (23.0B) is currently undefined. See PAP-V2-DESIGN issue for planning work.
   Do **not** start implementation until scope is explicitly defined.
   ```

3. **Post scope-refresh comment** on issue #3:
   ```markdown
   ## Scope Refresh — 2026-06-22
   
   COMMIT-EXECUTION-01 has delivered core PAP stack (v1), which is ~94% complete and production-ready 
   for current use cases. All core PAP objectives have been met.
   
   **PAP v2 scope (23.0B) is currently TBD and explicitly undefined.**
   
   **Next step**: Complete PAP-V2-DESIGN scope definition task (see new child issue) before any 
   implementation work begins.
   
   **Status**: Epic remains OPEN pending v2 scope definition.
   **Current phase**: Planning and design.
   **Blocker for contributors**: Do NOT start PAP v2 implementation until scope is defined.
   ```

4. **Labels**: Verify present:
   - `epic` ✓
   - `portfolio-action` ✓
   - `strategic` ✓

**Expected outcome**: PAP v2 scope is no longer TBD; a clear design task is created; contributors cannot start work until scope is defined (reducing rework risk).

---

## Issue #2: EPIC: Capital Rotation Advisor (CRA)

**Current State:**
- Status: OPEN
- Completion Estimate: ~96%
- Core CRA delivered; export/sign-off workflow refinements remaining

**Recommendation**: **KEEP OPEN — CONVERT TBD ITEMS TO NAMED WORK ITEMS**

### Recommended GitHub Action

**Action Type**: Create child issue + update issue body + post scope-refresh comment  
**Estimated Effort**: 30 minutes  
**Owner**: CRA team lead

**Steps:**

1. **Create Child Issue: CRA-EXPORT-01 (Persistence & Export Workflow)**
   - Title: `CRA-EXPORT-01: Draft persistence, export, and sign-off workflow (23.6C)`
   - Body:
     ```markdown
     ## Objective
     Complete CRA persistence, export, and operator sign-off workflow.
     
     ## Context
     Core CRA is production-ready. Remaining work is primarily workflow polish and export functionality.
     
     ## Scope (23.6C)
     - Implement draft save functionality for CRA recommendations
     - Design export format (CSV, JSON, PDF report)
     - Implement operator sign-off / approval workflow
     - Add audit trail for exports and sign-offs
     
     ## Acceptance Criteria
     - [ ] Draft save functionality tested and documented
     - [ ] Export formats implemented and validated
     - [ ] Sign-off workflow deployed
     - [ ] Audit trail captured and accessible
     - [ ] Operator documentation updated
     
     ## Effort: 1-2 weeks
     ## Owner: CRA team
     ```
   - Labels: `epic/2`, `capital-rotation`, `v1-polish`, `workflow`
   - Assign to: CRA team lead

2. Open issue #2 and **append to issue body**:
   ```markdown
   ## Delivered Phases (Archived 2026-06-22)
   
   ✅ **Core CRA Implementation (23.6A-23.6B.5)** (2026-06-22)
   ✅ **Policy Alignment & Ranking** (2026-06-22)
   ✅ **Source Intent Labeling & Explain** (2026-06-22)
   ✅ **Data Confidence Layers** (2026-06-22)
   ✅ **Governance Controls** (2026-06-22)
   
   ## Remaining Work
   
   - 🔧 CRA-EXPORT-01: Draft persistence & export workflow (23.6C)
   - 📋 CRA-TBD-01: [Name TBD] (23.6D scope to be defined)
   
   **23.6D Status**: Currently listed as "TBD" in issue body. To be converted to named work items 
   in next scope refresh cycle.
   ```

3. **Post scope-refresh comment** on issue #2:
   ```markdown
   ## Scope Refresh — 2026-06-22
   
   COMMIT-EXECUTION-01 has delivered core CRA implementation, which is ~96% complete and production-ready 
   for capital rotation workflows. All core ranking, scoring, and policy alignment objectives have been met.
   
   **Remaining work**:
   - 23.6C: Persistence, export, and operator sign-off workflow → See CRA-EXPORT-01 (child issue)
   - 23.6D: Currently TBD; to be scoped in next planning cycle
   
   **Status**: Epic remains OPEN for workflow refinement and polish.
   **Current phase**: Export workflow definition and implementation.
   **Timeline**: 1-2 weeks for 23.6C; 23.6D pending scope definition.
   ```

4. **Labels**: Verify present:
   - `epic` ✓
   - `capital-rotation` ✓
   - `strategic` ✓

**Expected outcome**: CRA TBD items are converted to concrete named work items; team has clear next steps; no ambiguous "TBD" remains.

---

## Summary of GitHub Actions

| Issue | Action Type | Action | Owner | Effort | Timeline |
|-------|------------|--------|-------|--------|----------|
| #59 | Comment + Update | Post scope-refresh comment, archive DISLOCATION phases | Data Science | 15 min | Immediate |
| #57 | Labels + Assign | Add post-release label, assign to Data Science | Engineering | 10 min | Immediate |
| **#56** | **Labels + Priority + Comment** | **Mark HIGH priority, assign to Data Eng, urgent comment** | **Data Eng** | **10 min** | **Immediate** |
| #6 | Create 3 issues + Comment | Create GOV-CI-01, GOV-FRESH-01, GOV-DEBT-01 child issues | Platform | 30 min | Today |
| #5 | Comment + Labels | Post rephasing comment, update labels | Research | 20 min | Today |
| #3 | Create issue + Comment | Create PAP-V2-DESIGN child issue, post scope-refresh | PAP lead | 45 min | This week |
| #2 | Create issue + Comment | Create CRA-EXPORT-01 child issue, post scope-refresh | CRA lead | 30 min | This week |

**Total GitHub effort**: ~2.5 hours to complete all actions.

---

## Execution Order

**Priority 1 (TODAY):**
1. Execute #59 scope refresh (15 min)
2. Execute #57 labels/assign (10 min)
3. Execute #56 priority/urgent (10 min)

**Priority 2 (THIS WEEK):**
4. Execute #6 create 3 child issues (30 min)
5. Execute #5 rephasing (20 min)
6. Execute #3 PAP v2 design issue (45 min)
7. Execute #2 CRA export issue (30 min)

---

## Post-Action Verification Checklist

- [ ] #59 body includes delivered phases; comment posted with DISLOCATION summary
- [ ] #57 has `post-release` label; assigned to Data Science
- [ ] #56 marked HIGH priority; has urgent comment; assigned to Data Engineering
- [ ] #6 has 3 child issues (GOV-CI-01, GOV-FRESH-01, GOV-DEBT-01); scope-refresh comment posted
- [ ] #5 has updated body and rephasing comment; `research-qualified` label added
- [ ] #3 has PAP-V2-DESIGN child issue; scope-refresh comment clarifies v2 is TBD
- [ ] #2 has CRA-EXPORT-01 child issue; scope-refresh comment clarifies 23.6D remains TBD
- [ ] All child issues are assigned to appropriate team leads
- [ ] All comments are posted and visible in GitHub

---

## Conclusion

**All 7 issues have clear disposition recommendations.** No issues require closure. All remain appropriately scoped as either strategic evergreen epics, tactical post-release work items, or production defects.

Execution of these GitHub actions will ensure **clear contributor guidance, transparent scope, and unambiguous next steps** for each work stream.

---

*Issue disposition recommendations completed by COMMIT-EXECUTION-01 governance post-review.*  
*Manual GitHub actions required; no automatic closures.*
