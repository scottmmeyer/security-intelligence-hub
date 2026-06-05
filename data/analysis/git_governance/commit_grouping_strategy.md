# Commit Grouping Strategy — Phase GIT-001

## Principle
Each commit group should be independently deployable, pass all tests, and represent a coherent unit of change. Groups are ordered by logical dependency.

---

## Group A — Core Portfolio Action Pipeline (PAP) Changes
**Tag candidate:** `feat/pap-23x-pipeline`

**Files:**
- `src/portfolio/ingestion.py` (M)
- `src/portfolio/enrichment.py` (M)
- `src/portfolio/reconciliation.py` (M)
- `src/portfolio/optimizer.py` (M)
- `src/portfolio/runner.py` (M)
- `src/portfolio/operator_policy.py` (??)
- `tests/test_reconciliation.py` (M)
- `tests/test_operator_policy.py` (??)
- `tests/test_policy_api.py` (??)
- `tests/test_23_5_block_diagnostics.py` (??)
- `tests/test_apply_policy_to_queue.py` (??)
- `tests/test_compute_execution_state.py` (??)
- `config/etf_exposure_decomposition.yaml` (M)
- Root-level `phase_23_*.md` docs (68 files)

**Commit message:** `feat: Phase 23.x Portfolio Action Pipeline — operator policy, reconciliation, execution state`

---

## Group B — CW-DAS and Deployment Queue
**Tag candidate:** `feat/cwdas-23x`

**Files:**
- `src/portfolio/deployment_queue.py` (M)
- `config/allocation_dimensions.yaml` (M)
- `tests/test_compute_execution_state.py` (??) *(if not in Group A)*

**Commit message:** `feat: CW-DAS deployment queue enhancements — policy rank boost, allocation node, Phase 23.5`

---

## Group C — Capital Rotation Advisor (CRA)
**Tag candidate:** `feat/cra-23-6`

**Files:**
- `src/portfolio/cra/` (entire module — 5 source files)
- `tests/test_cra_phase_23_6a.py` (??)
- `docs/phase_23_6/` through `docs/phase_23_6b5/` (8 directories)

**Commit message:** `feat: Capital Rotation Advisor (CRA) — Phases 23.6A through 23.6B.5`

---

## Group D — FMP Integration
**Tag candidate:** `feat/fmp-8-0b`

**Files:**
- `src/scoring/fetch_fmp_signals.py` (??)
- `src/scoring/fmp_universe_enrichment.py` (??)
- `tests/test_fmp_phase_8_0b1a.py` (??)
- `scripts/refresh_signals.py` (M) — FMP provider addition
- `scripts/fmp_bulk_fetch_universe.py` (??)
- `data/analysis/phase_8_0b1b/` (??)
- `data/analysis/issue_01_fmp_bulk/` (??)
- `docs/phase_8_0b0/` through `docs/phase_8_0b1a1/` and `docs/phase_8_0bx/`

**Commit message:** `feat: FMP Integration — signal intake, universe enrichment, bulk fetch (Phases 8.0B.0 through ISSUE-01)`

---

## Group E — Company Snapshot and Methodology UI
**Tag candidate:** `feat/company-context-8-0bx`

**Files:**
- `src/scoring/fetch_company_profile.py` (??)
- `docs/methodology/` (9 files)
- `data/analysis/phase_8_0b_x1/` (11 files)
- `data/analysis/phase_8_0b1e/` (3 files)

**Commit message:** `feat: Company Context and Consensus Intelligence Methodology (Phases 8.0B.X through 8.0B.1E)`

---

## Group F — UI and Server Changes
**Tag candidate:** `feat/ui-phases-23x-8x`

**Files:**
- `scripts/run_outcome_ui.py` (M)
- `ui/portfolio_alignment/app.js` (M)
- `ui/portfolio_alignment/index.html` (M)

**Commit message:** `feat: UI enhancements — CRA panel, Company Snapshot, Fundamental Snapshot, CII modal (v17)`

---

## Group G — GitHub Governance
**Tag candidate:** `docs/github-governance`

**Files:**
- `docs/governance/` (all backlog/taxonomy/roadmap/standards files)
- `data/analysis/git_governance/` (this audit)
- `data/analysis/phase_22d11/` (2 files)
- `/tmp/create_labels.sh`, `/tmp/create_epics.sh`, `/tmp/create_issues.sh` → archived to `docs/governance/backlog/github_issue_creation_commands.sh` (already exists)

**Commit message:** `docs: GitHub backlog governance — labels, epics, issues, roadmap, execution standard`

---

## Group H — Generated Artifacts to EXCLUDE from commits

These should NOT be committed — add to `.gitignore` if not already:

| File | Reason |
|------|--------|
| `data/analysis/fmp_dq_validation.json` | Runtime-generated JSON — add to gitignore |
| `data/operator/portfolio_alignment_state.json` | Runtime operator state — see options in artifact audit |
| `scripts/fetch_fmp_validation_set.py` | One-time dev helper — decision: commit for traceability OR delete |
| `scripts/fmp_dq_analyze.py`, `scripts/fmp_dq_validate.py` | Development-phase scripts — decision: commit or delete |

---

## Commit Order (Dependency Sequence)

```
1. Group A (PAP core) — foundation for everything
2. Group B (CW-DAS) — depends on PAP models
3. Group C (CRA) — depends on PAP + CW-DAS
4. Group D (FMP) — independent of CRA, depends on PAP runner
5. Group E (Company Context / Methodology) — depends on FMP infrastructure
6. Group F (UI) — depends on all backend changes
7. Group G (Governance) — independent, commit last
```

---

## Alternative: Single Consolidation Commit

If per-group commits are too granular for this stage of development, a single consolidation commit is acceptable:

```bash
git add -A -- ':!data/analysis/fmp_dq_validation.json' ':!data/operator/'
git commit -m "feat: Multi-phase development — PAP, CRA, FMP integration, Company Context, UI, Governance (Phases 23.0–8.0B.1E)"
```

This is the lowest-effort path and still creates a meaningful, recoverable checkpoint.
