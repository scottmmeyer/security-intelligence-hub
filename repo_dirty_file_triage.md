# Repo Dirty File Triage
## June 5, 2026 — Security Intelligence Hub

---

## Summary

```
git status --short: 39 entries (9 Modified tracked, 30 Untracked)
git diff --stat:    9 files, +1,293 / -57 lines
```

The "138 dirty files" figure was a terminal line-count artifact from a prior
session. Actual git status shows **39 entries** total.

---

## Category 1 — Intended Source Code Changes (9 modified tracked files)

These are all intentional changes from this session's implemented issues.
All regression-tested: **1,127 passed**.

| File | Issue | Lines +/- | Status |
|------|-------|-----------|--------|
| `src/portfolio/deployment_queue.py` | ISSUE-07 Fundamental Modifier, ISSUE-05 thesis/consistency fields | +251 / -3 | ✅ Commit |
| `src/portfolio/runner.py` | ISSUE-04B dislocation wiring, ISSUE-12B detection persistence | +53 / 0 | ✅ Commit |
| `src/portfolio/analyst_consensus.py` | ISSUE-08 analyst_count `_int()` helper | +9 / 0 | ✅ Commit |
| `src/scoring/fetch_yahoo_supplemental.py` | ISSUE-08 `numberOfAnalystOpinions` fetch + headers | +7 / -1 | ✅ Commit |
| `ui/portfolio_alignment/app.js` | ISSUE-05 filters, ISSUE-10 ATI block, ISSUE-04C watchlist panel, ISSUE-12B persistence wiring | +540 / -26 | ✅ Commit |
| `ui/portfolio_alignment/index.html` | CSS for filters/watchlist/ATI, dq-fs-badge CSS, v25 version bump | +253 / -4 | ✅ Commit |
| `scripts/run_outcome_ui.py` | Various API endpoint additions (CRA, security-metadata, etc.) | +159 / 0 | ✅ Commit |
| `tests/test_7_5b_deployment_queue.py` | Test updates for ISSUE-07 / CW-DAS v1.1 | -43 / 0 | ✅ Commit |
| `.gitignore` | Added `data/operator/cra_draft.json` | +1 | ✅ Commit |

**Count: 9 source files — all safe to commit.**

---

## Category 2 — Intended Documentation / Certification Artifacts (22 untracked doc entries)

All produced during this session as required deliverables for each issue.

| Path | Issues Covered | Status |
|------|---------------|--------|
| `docs/governance/` (5 files) | Governance cleanup, EPIC review, roadmap, ISSUE-12D proposal, calibration milestone | ✅ Commit |
| `docs/issue_04a/` (5 files) | Dislocation methodology design | ✅ Commit |
| `docs/issue_04b/` (5 files) | Dislocation backend classifier | ✅ Commit |
| `docs/issue_04c/` (5 files) | Dislocation watchlist panel | ✅ Commit |
| `docs/issue_05/` (5 files) | Deployment queue filters | ✅ Commit |
| `docs/issue_08/` (5 files) | analyst_count pipeline | ✅ Commit |
| `docs/issue_09/` (5 files) | CRA _craProposal bug fix | ✅ Commit |
| `docs/issue_10/` (5 files) | Analyst Target Intelligence block | ✅ Commit |
| `docs/issue_12/` (5 files) | Outcome tracking assessment | ✅ Commit |
| `docs/issue_12c/` (5 files) | Outcome computation engine | ✅ Commit |
| `docs/phase_23_6c/` | CRA Phase 23.6C | ✅ Commit |
| `docs/phase_8_0b1c/` | FMP Phase 8.0B.1C | ✅ Commit |
| `docs/phase_8_0b1c_impl/` | FMP implementation docs | ✅ Commit |
| `docs/phase_cii003/` | CII-003 governance | ✅ Commit |
| `docs/phase_cii004/` | CII-004 modal update | ✅ Commit |
| `docs/phase_cii004a/` | CII-004A | ✅ Commit |
| `docs/phase_cii005/` | Analyst Target assessment | ✅ Commit |
| `docs/phase_cii_002/` | CII-002 | ✅ Commit |

**Count: ~93 markdown/CSV files across 22 untracked directories — all safe to commit.**

---

## Category 3 — New Source Modules (6 untracked src/test files)

| File | Issue | Status |
|------|-------|--------|
| `src/portfolio/dislocation.py` | ISSUE-04B/D — Dislocation classifier (A1, D1, B2) | ✅ Commit |
| `src/portfolio/outcome_tracker.py` | ISSUE-12B/C — Detection persistence + outcome engine | ✅ Commit |
| `tests/test_issue_04b_dislocation.py` | 26 Class A1 tests | ✅ Commit |
| `tests/test_issue_04d_dislocation.py` | 34 Class D1/B2 tests | ✅ Commit |
| `tests/test_issue_07_fundamental_modifier.py` | 33 Fundamental Modifier tests | ✅ Commit |
| `tests/test_issue_12bc_outcome_tracker.py` | 30 outcome tracker tests | ✅ Commit |

**Count: 6 files — all safe to commit.**

---

## Category 4 — Generated Runtime / Analysis Artifacts (8 untracked data files)

| File | Description | Status |
|------|-------------|--------|
| `data/analysis/git_governance/checkpoint_execution_report.md` | Runtime analysis doc | ⚠️ Review — could commit or exclude |
| `data/analysis/phase_8_0b1c_a/*.md` (6 files) | FMP analyst target analysis reports | ⚠️ Review — analysis outputs |
| `data/analysis/phase_8_0b1c_a/*.csv` (1 file) | Analysis data CSV | ⚠️ Review |

These are analysis output files under `data/analysis/` which is not in `.gitignore`.

**Current `.gitignore` coverage for `data/`:**
```
data/current/          ← ignored
data/history/**        ← ignored
data/signals/**        ← ignored
data/portfolio_ingestion/...  ← ignored
data/allocation/       ← ignored
data/derived/          ← ignored
data/operator/...      ← ignored
data/analysis/fmp_dq_validation.json ← ignored
```

**NOT ignored:** `data/analysis/` subdirectories (except `fmp_dq_validation.json`)

**Recommendation:** Add `data/analysis/` to `.gitignore` OR commit selectively.

---

## Category 5 — Cache / Runtime / Pycache

**Status: None visible in `git status`.**

`.gitignore` already covers `*.pyc`, `*.pyo`, `__pycache__/`. No cache files are showing as dirty. ✅

---

## Category 6 — Unexpected or Unsafe Changes

**None found.** Every modified and untracked file traces cleanly to an implemented issue. No files appear accidentally modified.

---

## .gitignore Gap Analysis

| Gap | Impact | Recommendation |
|-----|--------|---------------|
| `data/analysis/` subdirectories not ignored | 8 files currently untracked | Add `data/analysis/*/` or evaluate committing selectively |
| No gap for `__pycache__` | Already covered | No action needed |
| No gap for `.venv/` | Already covered | No action needed |

---

## Answers to Required Questions

| Question | Answer |
|----------|--------|
| How many dirty files are source code? | **15** (9 modified + 6 new src/test files) |
| How many are docs? | **~95** (22 untracked doc directories, ~93 markdown files) |
| How many are generated data artifacts? | **8** (under `data/analysis/`) |
| How many are cache/runtime files? | **0** (all covered by .gitignore) |
| Are any files unexpectedly modified? | **No** — all trace to implemented issues |
| Is .gitignore missing patterns? | **Yes** — `data/analysis/` subdirs are not ignored |
| What is the safest commit strategy? | See below |

---

## Recommended Commit Strategy

### Commit 1 — Source + Tests (atomic, regression-verified)
```
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
git commit -m "feat: ISSUE-04B/C/D/05/07/08/10/12B/C — dislocation intelligence, filters, analyst target, outcome tracking (1,127 tests passing)"
```

### Commit 2 — Documentation (separate for clarity)
```
git add docs/
git commit -m "docs: certification artifacts for ISSUE-04A-D, 05, 07-10, 12, governance cleanup"
```

### Decision required — `data/analysis/` files
Either:
- **Option A:** Add `data/analysis/` to `.gitignore` and leave these untracked
- **Option B:** Commit them: `git add data/analysis/` → separate commit
- **Option C:** Review each file individually (8 files)

Recommend **Option A** (add to `.gitignore`) unless these analysis reports should be versioned as permanent reference artifacts.

---

## No changes made. Plan only.
