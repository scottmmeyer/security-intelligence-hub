# Repo Commit Recommendation
## June 5, 2026

---

## Recommendation: OPTION B

**Ignore analysis artifacts. Commit source, tests, and docs only.**

---

## Detailed Recommendation

### What to Commit

**Commit 1 — Source + Tests** (atomic unit; regression-verified at 1,127 tests)

```bash
git add src/portfolio/dislocation.py
git add src/portfolio/outcome_tracker.py
git add src/portfolio/runner.py
git add src/portfolio/analyst_consensus.py
git add src/portfolio/deployment_queue.py
git add src/scoring/fetch_yahoo_supplemental.py
git add scripts/run_outcome_ui.py
git add ui/portfolio_alignment/app.js
git add ui/portfolio_alignment/index.html
git add tests/test_issue_04b_dislocation.py
git add tests/test_issue_04d_dislocation.py
git add tests/test_issue_07_fundamental_modifier.py
git add tests/test_issue_12bc_outcome_tracker.py
git add tests/test_7_5b_deployment_queue.py
git add .gitignore
git commit -m "feat: Dislocation Intelligence (04B/C/D), DQ Filters (05), Analyst Intelligence (08/10), Outcome Tracking (12B/C) — 1,127 tests passing"
```

**Commit 2 — Documentation** (separates deliverables from code for clean history)

```bash
git add docs/
git commit -m "docs: Certification artifacts ISSUE-04A-D, 05, 07-10, 12, governance cleanup — June 5, 2026"
```

**Commit 3 — Triage Planning Docs** (optional; include if you want repo governance artifacts versioned)

```bash
git add repo_dirty_file_triage.md analysis_artifact_review.md gitignore_recommendation.md \
        commit_inventory.md issue_closure_validation.md repo_commit_recommendation.md
git commit -m "chore: Repo triage and commit planning documents — June 5, 2026"
```

---

### What to Exclude (do not stage)

```
data/analysis/git_governance/checkpoint_execution_report.md
data/analysis/phase_8_0b1c_a/ (7 files)
```

---

### What to Update Before Committing

Add to `.gitignore` (narrow pattern — see `gitignore_recommendation.md`):

```gitignore
# Analysis working artifacts — intermediate research, superseded by docs/
data/analysis/phase_*/
data/analysis/git_governance/
```

Then run:
```bash
git add .gitignore
# include with Commit 1
```

---

## Rationale

### Repository Cleanliness

Committing `data/analysis/` working artifacts would introduce noise into the
permanent commit history. The `data/analysis/` directory is a working scratchpad —
analogous to a `/tmp` directory for research. Its outputs graduate to `docs/` when
finalized. The 8 untracked `data/analysis/` files have all been superseded by
finalized deliverables in `docs/phase_cii005/`.

### Future Maintainability

A clean separation between:
- `src/` — source code (versioned)
- `tests/` — test suite (versioned)
- `docs/` — finalized deliverables and certifications (versioned)
- `data/analysis/` — working scratchpad (NOT versioned)

makes future contributors immediately understand what is permanent and what is
transitional. Committing working artifacts into `data/analysis/` would blur
this distinction.

### Auditability

The `docs/` directory already contains complete, organized certification records
for every issue implemented in this session. All governance decisions are
documented. All tests are committed. The issue closure record is in GitHub.

Auditing the codebase requires only:
1. `git log` for source history
2. `docs/` for decision rationale and certifications
3. GitHub issues for governance trail

The `data/analysis/` working artifacts add no audit value that isn't already
in `docs/`.

### Governance Impact

The 8 excluded files are all Phase 8.0B.1C-A analyst target working drafts and
a governance checkpoint report. Their conclusions are captured in:
- `docs/phase_cii005/` — all 5 CII-005 assessment deliverables
- `docs/governance/` — all 5 governance cleanup documents

**No governance information is lost by excluding them.**

---

## Option A Assessment (for reference)

**Option A: Commit analysis artifacts** — would work but:
- Pollutes commit history with intermediate working files
- Creates confusion about what `data/analysis/` means going forward
- These files are not referenced by any test, source module, or documented deliverable
- Not recommended

---

## Pre-Commit Checklist

- [ ] `.gitignore` updated with `data/analysis/phase_*/` and `data/analysis/git_governance/`
- [ ] `git status --short` shows only files listed in Commit 1–3 above
- [ ] `PYTHONPATH=. .venv/bin/python3 -m pytest -q --tb=no` → 1,127 passed
- [ ] `node --check ui/portfolio_alignment/app.js` → SYNTAX OK
- [ ] All GitHub issues verified closed (see `issue_closure_validation.md`)
- [ ] No files in `data/` staged
