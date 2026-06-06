# Commit Inventory
## June 5, 2026 — Pre-Commit Staging Plan

---

## Category: SOURCE (9 modified tracked + 2 new source files = 11 files)

### Modified Tracked Source Files (9)

| File | Issue(s) | Change Summary |
|------|---------|----------------|
| `src/portfolio/deployment_queue.py` | ISSUE-07, ISSUE-05 | Fundamental Modifier, thesis/consistency fields in CwDasBreakdown |
| `src/portfolio/runner.py` | ISSUE-04B, ISSUE-12B | Dislocation wiring, detection persistence call |
| `src/portfolio/analyst_consensus.py` | ISSUE-08 | `_int()` helper, analyst_count wiring |
| `src/scoring/fetch_yahoo_supplemental.py` | ISSUE-08 | `numberOfAnalystOpinions` fetch, `analyst_count` in headers |
| `scripts/run_outcome_ui.py` | Multiple | CRA endpoints, security-metadata, FMP overlay |
| `ui/portfolio_alignment/app.js` | ISSUE-05, 04C, 10, 12B | Filters, watchlist panel, ATI block, detection persistence |
| `ui/portfolio_alignment/index.html` | ISSUE-05, 04C, 10 | CSS additions, dq-fs-badge, version v25 |
| `tests/test_7_5b_deployment_queue.py` | ISSUE-07 | Updated for CW-DAS v1.1 / ARW acceptance criteria |
| `.gitignore` | ISSUE-09 | Added `data/operator/cra_draft.json` |

### New Source Files (2)

| File | Issue | Description |
|------|-------|-------------|
| `src/portfolio/dislocation.py` | ISSUE-04B/D | Dislocation classifier — A1, D1, B2, MULTI_CLASS |
| `src/portfolio/outcome_tracker.py` | ISSUE-12B/C | Detection persistence + outcome computation engine |

**Source subtotal: 11 files**

---

## Category: TESTS (4 new test files)

| File | Issue | Tests |
|------|-------|-------|
| `tests/test_issue_04b_dislocation.py` | ISSUE-04B | 26 Class A1 tests |
| `tests/test_issue_04d_dislocation.py` | ISSUE-04D | 34 Class D1/B2 tests |
| `tests/test_issue_07_fundamental_modifier.py` | ISSUE-07 | 33 Fundamental Modifier tests |
| `tests/test_issue_12bc_outcome_tracker.py` | ISSUE-12C | 30 outcome tracker tests |

**Tests subtotal: 4 files, 123 new tests**

---

## Category: DOCUMENTATION (93 untracked files across 22 directories)

| Directory | Issues Covered | Files |
|-----------|---------------|-------|
| `docs/governance/` | Governance cleanup, EPIC review, roadmap, milestone | 5 |
| `docs/issue_04a/` | Dislocation methodology | 5 |
| `docs/issue_04b/` | Backend classifier | 5 |
| `docs/issue_04c/` | Watchlist panel | 5 |
| `docs/issue_05/` | DQ filters | 5 |
| `docs/issue_08/` | analyst_count pipeline | 5 |
| `docs/issue_09/` | CRA bug fix | 5 |
| `docs/issue_10/` | ATI block | 5 |
| `docs/issue_12/` | Outcome tracking assessment | 5 |
| `docs/issue_12c/` | Outcome engine | 5 |
| `docs/phase_23_6c/` | CRA Phase 23.6C | ~3 |
| `docs/phase_8_0b1c/` | FMP Phase 8.0B.1C | ~8 |
| `docs/phase_8_0b1c_impl/` | FMP implementation | ~4 |
| `docs/phase_cii003/` | CII-003 governance | ~4 |
| `docs/phase_cii004/` | CII-004 modal | ~3 |
| `docs/phase_cii004a/` | CII-004A | ~2 |
| `docs/phase_cii005/` | Analyst Target assessment | ~5 |
| `docs/phase_cii_002/` | CII-002 | ~2 |

**Documentation subtotal: 93 files**

---

## Category: PLANNING ARTIFACTS (produced during this triage session)

| File | Purpose |
|------|---------|
| `repo_dirty_file_triage.md` | Triage report (Session 1) |
| `analysis_artifact_review.md` | Analysis artifact decision |
| `gitignore_recommendation.md` | .gitignore gap analysis |
| `commit_inventory.md` | This file |
| `issue_closure_validation.md` | Issue audit |
| `repo_commit_recommendation.md` | Final recommendation |

These triage files can either be committed (as governance artifacts) or excluded. See `repo_commit_recommendation.md`.

---

## Category: EXCLUDED (do not stage)

| Path | Reason |
|------|--------|
| `data/analysis/git_governance/checkpoint_execution_report.md` | Working artifact — see analysis_artifact_review.md |
| `data/analysis/phase_8_0b1c_a/` (7 files) | Intermediate research — superseded by docs/phase_cii005/ |

**Excluded subtotal: 8 files**

---

## Grand Total

| Category | Files |
|----------|-------|
| Source (modified + new) | 11 |
| Tests (new) | 4 |
| Documentation | 93 |
| Planning/triage docs | 6 |
| **Commit total** | **~114** |
| Excluded | 8 |
| **Grand total staged** | **~114 of 122 dirty entries** |

---

## Suggested Commit Commands (NOT executed — plan only)

```bash
# Commit 1: Source + Tests (atomic, regression-verified)
git add src/portfolio/dislocation.py
git add src/portfolio/outcome_tracker.py
git add src/portfolio/runner.py
git add src/portfolio/analyst_consensus.py
git add src/portfolio/deployment_queue.py
git add src/scoring/fetch_yahoo_supplemental.py
git add scripts/run_outcome_ui.py
git add ui/portfolio_alignment/app.js
git add ui/portfolio_alignment/index.html
git add tests/
git add .gitignore
git commit -m "feat: Dislocation Intelligence (04B/C/D), DQ Filters (05), Analyst Intelligence (08/10), Outcome Tracking (12B/C) — 1,127 tests passing"

# Commit 2: Documentation
git add docs/
git commit -m "docs: Certification artifacts ISSUE-04A-D, 05, 07-10, 12, governance cleanup June 5 2026"

# Optional Commit 3: Triage planning docs (if desired)
git add repo_dirty_file_triage.md analysis_artifact_review.md gitignore_recommendation.md \
        commit_inventory.md issue_closure_validation.md repo_commit_recommendation.md
git commit -m "chore: Repo cleanup triage and commit planning documents"

# After approval: Update .gitignore for analysis/ artifacts
# (Add data/analysis/phase_*/ and data/analysis/git_governance/ entries)
```
