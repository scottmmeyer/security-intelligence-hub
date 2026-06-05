# Working Tree Cleanup Plan — Phase GIT-001

## Status: PLAN ONLY — DO NOT EXECUTE

This is a read-only audit. The steps below are the recommended sequence to execute when authorized. No commands have been run.

---

## Pre-Conditions Required Before Execution

1. All 1,004 tests pass: `PYTHONPATH=. .venv/bin/python3 -m pytest -q` ✅ (confirmed)
2. Server is running and UI accessible ✅ (confirmed)
3. No in-progress implementation work pending

---

## Step 1 — Decide on Operator State File
**Decision required (human):** Should `data/operator/portfolio_alignment_state.json` be:
- (A) Committed as a seeded default
- (B) Added to `.gitignore`

**Recommended:** Option B — add to `.gitignore` because it contains live operator decisions that will diverge from any committed version. Provide `data/operator/portfolio_alignment_state.default.json` as the committed template.

```bash
# If Option B chosen (DO NOT EXECUTE NOW):
echo "data/operator/portfolio_alignment_state.json" >> .gitignore
cp data/operator/portfolio_alignment_state.json data/operator/portfolio_alignment_state.default.json
```

---

## Step 2 — Add New .gitignore Rules
**Purpose:** Prevent certain runtime artifacts from appearing as untracked.

```bash
# Lines to append to .gitignore (DO NOT EXECUTE NOW):
# Runtime FMP data quality artifacts
data/analysis/fmp_dq_validation.json
data/analysis/**/*.json

# Operator runtime state (if Option B chosen in Step 1)
data/operator/portfolio_alignment_state.json
```

---

## Step 3 — Decide on One-Time Dev Scripts
**Decision required (human):** For `scripts/fetch_fmp_validation_set.py`, `scripts/fmp_dq_analyze.py`, `scripts/fmp_dq_validate.py`:
- (A) Commit for historical traceability
- (B) Delete — they are no longer needed

**Recommended:** Option A — commit for historical record. Low risk.

---

## Step 4 — Stage Commits in Order

Execute commits in the sequence from `commit_grouping_strategy.md`.

**Option A — Per-group commits (recommended for clean history):**
```bash
# Group A: PAP
git add src/portfolio/ingestion.py src/portfolio/enrichment.py src/portfolio/reconciliation.py
git add src/portfolio/optimizer.py src/portfolio/runner.py src/portfolio/operator_policy.py
git add tests/test_reconciliation.py tests/test_operator_policy.py tests/test_policy_api.py
git add tests/test_23_5_block_diagnostics.py tests/test_apply_policy_to_queue.py tests/test_compute_execution_state.py
git add config/etf_exposure_decomposition.yaml
git add phase_23_*.md portfolio_alignment_tax_columns.md tax_*.md sih_rehydration_*.md
git commit -m "feat: Phase 23.x Portfolio Action Pipeline — operator policy, reconciliation, execution state"

# Group B: CW-DAS
git add src/portfolio/deployment_queue.py config/allocation_dimensions.yaml
git commit -m "feat: CW-DAS deployment queue — policy rank boost, allocation node (Phase 23.5)"

# Group C: CRA
git add src/portfolio/cra/ tests/test_cra_phase_23_6a.py docs/phase_23_6*/
git commit -m "feat: Capital Rotation Advisor (Phases 23.6A through 23.6B.5)"

# Group D: FMP
git add src/scoring/fetch_fmp_signals.py src/scoring/fmp_universe_enrichment.py
git add tests/test_fmp_phase_8_0b1a.py scripts/refresh_signals.py scripts/fmp_bulk_fetch_universe.py
git add scripts/fetch_fmp_validation_set.py scripts/fmp_dq_analyze.py scripts/fmp_dq_validate.py
git add data/analysis/phase_8_0b1b/ data/analysis/issue_01_fmp_bulk/ docs/phase_8_0b*/
git commit -m "feat: FMP Integration — signal intake, universe enrichment, bulk fetch (Phases 8.0B.0 through ISSUE-01)"

# Group E: Company Context + Methodology
git add src/scoring/fetch_company_profile.py docs/methodology/
git add data/analysis/phase_8_0b_x1/ data/analysis/phase_8_0b1e/ data/analysis/phase_22d11/
git commit -m "feat: Company Snapshot and Consensus Intelligence Methodology (Phases 8.0B.X through 8.0B.1E)"

# Group F: UI
git add scripts/run_outcome_ui.py ui/portfolio_alignment/app.js ui/portfolio_alignment/index.html
git commit -m "feat: UI — CRA panel, Company/Fundamental Snapshot, CII modal (v17)"

# Group G: Governance
git add docs/governance/ data/analysis/git_governance/
git commit -m "docs: GitHub backlog governance — GIT-001 audit, labels, epics, roadmap"
```

**Option B — Single consolidation commit:**
```bash
git add -A
git reset HEAD data/analysis/fmp_dq_validation.json
# (optionally) git reset HEAD data/operator/portfolio_alignment_state.json
git commit -m "feat: Multi-phase development (23.0–8.0B.1E) — PAP, CRA, FMP, Company Context, UI, Governance"
```

---

## Step 5 — Verify Clean State
```bash
git status  # should show only ignored files + operator state (if excluded)
git log --oneline -10  # review commits
PYTHONPATH=. .venv/bin/python3 -m pytest -q  # confirm 1,004 tests pass
```

---

## Step 6 — Push to Remote
**Requires explicit human authorization — do not push without confirmation.**

```bash
# DO NOT EXECUTE without authorization:
git push origin main
```

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|---------|------------|
| Accidentally committing operator secrets | LOW | `.env` is already gitignored; operator state is the only sensitive-adjacent file |
| Committing large generated CSVs | LOW | `data/signals/**` is already gitignored |
| Merge conflicts on push | LOW | Likely no competing remote changes |
| Breaking tests after commit | NONE | 1,004 tests pass pre-commit |

**Overall risk: LOW** — this is a straightforward add-and-commit of well-tested code.
