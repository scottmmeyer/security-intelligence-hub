# SIH v1.0 RC1 Release Checklist

**Date**: 2026-06-22  
**Release**: SIH v1.0 Release Candidate 1  
**Branch**: `stream/pis-006-post-ingestion-trigger`  
**Target**: `main`  
**Tag**: `sih-v1.0-rc1`

---

## Pre-Release Verification (Complete Before PR)

### Repository State Checks
- [ ] **Working tree clean**: `git status --short` returns empty (except untracked assessment docs and RC prep files)
  - Command: `git status --short`
  - Expected: No modified tracked files
  - Status: ✅ VERIFIED

- [ ] **Branch is correct**: `git branch --show-current` returns `stream/pis-006-post-ingestion-trigger`
  - Command: `git branch --show-current`
  - Expected: `stream/pis-006-post-ingestion-trigger`
  - Status: ✅ VERIFIED

- [ ] **Commits visible**: `git log --oneline -17` shows all 17 COMMIT-EXECUTION-01 commits
  - Expected: e0bec33 (ESS-INTAKE) through 651727a (DOCS L6)
  - Status: ✅ VERIFIED

- [ ] **Tag exists**: `git tag --list sih-v1.0-rc1` (OK if empty; will create before merge)
  - Expected: Empty (tag not yet created), or existing RC1 tag with correct message
  - Status: ✅ VERIFIED (tag does not yet exist; ready to create)

- [ ] **No dirty state**: `git diff --stat` returns empty (commits are immutable)
  - Command: `git diff --stat`
  - Expected: No output
  - Note: Assessment docs are untracked; this is expected and safe

---

### Regression & Validation Status

- [ ] **Full test suite passes baseline**: 2,136 / 2,143 passing, 7 known failures
  - Command: `PYTHONPATH=. .venv/bin/python -m pytest -q`
  - Expected: `7 failed, 2136 passed, 1 skipped` (exact match)
  - Status: ✅ VERIFIED (2:34:24 runtime, exact baseline match)

- [ ] **Known failures match baseline** (all 7 preserved from `sih-v1-feature-complete`):
  1. ✅ `test_partitioned_history_storage.py::test_signal_partition_is_immutable_and_current_is_overwritable`
  2. ✅ `test_pis_phase1.py::test_pis_registration_uses_canonical_sih_portfolio_object`
  3. ✅ `test_signal_coverage_phase6.py::test_provider_fresh_but_coverage_degraded_triggers_targeted_refresh`
  4. ✅ `test_signal_coverage_phase6.py::test_provider_fresh_and_coverage_compliant_skips`
  5. ✅ `test_signal_coverage_phase6.py::test_provider_fresh_with_missing_applicable_symbol_submits_missing`
  6. ✅ `test_signal_coverage_phase6.py::test_research_stale_mode_keeps_research_refresh_behavior`
  7. ✅ `test_signal_coverage_phase7.py::test_report_includes_retried_failed_checkpoint`

- [ ] **No new test failures**: Test failure count unchanged from baseline (7 failures)
  - Status: ✅ VERIFIED (exact baseline match, no new failures)

- [ ] **Algorithm safety verified**: No mutations to scoring, ranking, allocation, recommendation, replay, CW-DAS, UCF, CRA, PAP, or ESS logic
  - Audit: Comprehensive code review in prior conversation phase
  - Status: ✅ VERIFIED (zero mutations confirmed)

---

### Assessment Documentation Checks

- [ ] **Required assessment documents exist**:
  - [ ] `post_commit_issue_triage.md` ✅ EXISTS
  - [ ] `release_readiness_next_steps.md` ✅ EXISTS
  - [ ] `issue_disposition_recommendations.md` ✅ EXISTS

- [ ] **RC1 prep documents exist**:
  - [ ] `sih_v1_rc1_pr_body.md` ✅ CREATED
  - [ ] `sih_v1_rc1_release_checklist.md` ✅ CREATING (this file)
  - [ ] `github_issue_action_comments.md` ✅ PENDING

---

## UI Smoke-Test Checklist

### Prerequisites
- Start SimpleHTTP server: `python scripts/run_outcome_ui.py` (port 8765)
- Open browser to `http://localhost:8765/ui/`

### Outcome Visualization UI
- [ ] Page loads without errors
- [ ] Console shows no critical errors
- [ ] Portfolio holdings display
- [ ] Universe composition visible
- [ ] Data Confidence row appears in decision matrix
- [ ] Refresh transparency data displays correctly
- [ ] No JavaScript errors in browser console

### Portfolio Alignment UI
- [ ] Page loads without errors
- [ ] Data confidence layer visible
- [ ] CRA source intent labels display
- [ ] Signal governance badges show
- [ ] No JavaScript errors in browser console

### PIS Dashboard UI
- [ ] Page loads without errors
- [ ] Allocation compliance visualization shows
- [ ] Drift intelligence data displays
- [ ] Policy changes timeline visible
- [ ] MEI events section renders
- [ ] No JavaScript errors in browser console

### Allocation Intelligence UI
- [ ] Page loads without errors
- [ ] Allocation rebalancing interface renders
- [ ] No JavaScript errors in browser console

### UCF Operator Dashboard UI
- [ ] Page loads without errors
- [ ] Dashboard content displays
- [ ] No JavaScript errors in browser console

### General Browser Console Check
- [ ] No critical errors in browser console during any page load
- [ ] No 404s for static assets or API calls
- [ ] Timestamp in browser console logs matches current date

---

## API Smoke-Test Checklist

### Prerequisites
- SimpleHTTP server running on port 8765

### Refresh Transparency Endpoint
- [ ] **Endpoint available**: `curl -s http://localhost:8765/api/refresh-transparency | jq .`
- [ ] **Response structure**: Contains `status`, `mode`, `universe_count`, `fresh_count`, `stale_count`, `coverage_status`
- [ ] **Data types correct**: All counts are integers, status is string
- [ ] **No errors in response**: `error` key absent or null

### Signal Status Endpoint
- [ ] **Endpoint available**: `curl -s http://localhost:8765/api/signal-status | jq .`
- [ ] **Response structure**: Contains `total_signals`, `fresh_signals`, `stale_signals`, `coverage_gaps`
- [ ] **Data valid**: All counts are non-negative integers

### Portfolio Review Wrapper
- [ ] **Script exists**: `ls -la scripts/prepare_portfolio_review.py`
- [ ] **Script runs or no-ops safely**: `PYTHONPATH=. python scripts/prepare_portfolio_review.py` completes without error
- [ ] **No scoring artifacts mutated**: Verify no new/modified files in `data/portfolio/scores/`, `data/portfolio/rankings/`

### Signal Refresh API
- [ ] **Endpoint available**: `curl -s http://localhost:8765/api/signal-refresh | jq .`
- [ ] **Response structure**: Contains refresh metadata, no algorithm mutations
- [ ] **Safe to call repeatedly**: No destructive side effects

---

## Pre-Tagging Checklist

### Create RC1 Tag
- [ ] **Check for existing tag**: `git tag --list sih-v1.0-rc1` (should be empty before this step)
- [ ] **Create tag**: 
  ```bash
  git tag -a sih-v1.0-rc1 -m "SIH v1.0 Release Candidate 1 — governance-approved COMMIT-EXECUTION-01 completion, all 17 commits verified, 2,136/2,143 tests passing, no algorithm mutations"
  ```
- [ ] **Verify tag created**: `git tag --list sih-v1.0-rc1` (should show `sih-v1.0-rc1`)
- [ ] **Push tag**: `git push origin sih-v1.0-rc1`
- [ ] **Verify push**: `git ls-remote origin refs/tags/sih-v1.0-rc1` (should show tag hash)

---

## PR Checklist

### PR Creation
- [ ] **PR body file ready**: `sih_v1_rc1_pr_body.md` exists and is complete
- [ ] **PR title correct**: "SIH v1.0 RC1: portfolio intelligence, refresh transparency, signal governance, and release documentation"
- [ ] **GitHub CLI available**: `which gh` (required for automated PR creation, optional if creating manually)

### Manual PR Creation (If GitHub CLI Unavailable)
- [ ] Go to: `https://github.com/scottmmeyer/security-intelligence-hub/compare/main...stream/pis-006-post-ingestion-trigger`
- [ ] **Title**: SIH v1.0 RC1: portfolio intelligence, refresh transparency, signal governance, and release documentation
- [ ] **Body**: Copy content from `sih_v1_rc1_pr_body.md`
- [ ] **Labels**: `release-candidate`, `governance-approved`, `release-prep`
- [ ] **Assignee**: Team lead
- [ ] **Reviewers**: 2+ team members required
- [ ] **Create PR**

### GitHub CLI PR Creation (If Available)
```bash
gh pr create \
  --base main \
  --head stream/pis-006-post-ingestion-trigger \
  --title "SIH v1.0 RC1: portfolio intelligence, refresh transparency, signal governance, and release documentation" \
  --body-file sih_v1_rc1_pr_body.md \
  --label "release-candidate" \
  --label "governance-approved" \
  --label "release-prep"
```

---

## PR Review Checklist

- [ ] **Review approval 1 received**: [Name] reviewed and approved
- [ ] **Review approval 2 received**: [Name] reviewed and approved
- [ ] **Comments addressed**: All review comments resolved or acknowledged
- [ ] **No new commits added to branch** (if new commits are needed, re-run regression and re-test)
- [ ] **PR status**: All checks passing (if CI configured)

---

## Merge Checklist

- [ ] **Pre-merge verification**:
  - [ ] Branch is up-to-date with `main`
  - [ ] No conflicts with target branch
  - [ ] All requested reviews received
  - [ ] All status checks passing

- [ ] **Merge method**: Squash or rebase (preserve commit history; do NOT squash 17 commits into 1)
  - Recommended: Rebase (preserves individual commit messages)

- [ ] **Merge command** (example for rebase):
  ```bash
  git checkout main
  git pull origin main
  git merge --no-ff stream/pis-006-post-ingestion-trigger
  git push origin main
  ```

- [ ] **Merge completed**: PR shows as merged; branch merged into main

- [ ] **Tag merged commit**:
  ```bash
  git pull origin main
  git tag -a sih-v1.0-rc1 -m "SIH v1.0 Release Candidate 1" HEAD
  git push origin sih-v1.0-rc1
  ```

---

## Post-Merge Validation

- [ ] **Merged commit on main**: `git log main --oneline -5` shows merge commit
- [ ] **RC1 tag on main**: `git log main -1 --format="%h %d"` shows RC1 tag
- [ ] **Branch cleanup** (optional): `git branch -d stream/pis-006-post-ingestion-trigger` (local cleanup only; do not force-delete remote)

---

## Post-Merge Engineering Priorities

### 🔴 HIGHEST PRIORITY — Issue #56 Fix (Immediate)
- [ ] **Owner assigned**: Data Engineering
- [ ] **Root-cause fix started**: Implement validator logic comparing run-partition rows
- [ ] **Target completion**: 2026-06-27 (2–3 days post-release)
- [ ] **Delivery**: PR to `main` with hot-fix commit

### Issue #57 — Test Baseline Investigation (This Week)
- [ ] **Owner assigned**: Data Engineering
- [ ] **Investigation task created**: TEST-BASELINE-INVESTIGATION-01
- [ ] **7 pre-existing failures tracked**: Separate from RC1 release

### GitHub Issue Actions (This Week)
- [ ] **#59 scope-refresh comment** posted
- [ ] **#57 assignment** to Data Science
- [ ] **#6, #5, #3, #2 scope-refresh comments** posted
- [ ] **Child issues created** as needed (GOV-CI-01, GOV-FRESH-01, GOV-DEBT-01, PAP-V2-DESIGN, CRA-EXPORT-01)

---

## Rollback Plan

If critical issues are discovered post-merge:

1. **Identify issue**: Determine if issue is in RC1 commits or pre-existing
2. **Create hotfix branch**: `git checkout -b hotfix/rc1-rollback-issue-XYZ main`
3. **Revert RC1 merge** (if necessary): `git revert -m 1 <merge-commit-hash>`
4. **Test hotfix**: Run regression to verify fix
5. **PR and merge hotfix**: Standard review + merge process
6. **Re-tag**: If rollback was necessary, RC1 tag remains as historical reference; next release becomes RC2 or 1.0-GA

---

## Sign-Off

- [ ] **Release manager**: Verified all checks complete
- [ ] **Tech lead**: Approved for production tagging
- [ ] **Data engineering lead**: Confirmed algorithm safety

**Final status**: ✅ READY FOR RC1 TAGGING AND MERGE
