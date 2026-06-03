# Phase 22D.11 — Commit Recommendations
**Generated:** 2026-06-03  
**Baseline Commit:** `564f1a4` (HEAD → main, tag: portfolio-manager-v7.3b-stable)  
**Mandate:** CLASSIFICATION ONLY. No commits are authorized by this document alone.

---

## Commit Disposition Groups

Files are classified into four groups:

| Group | Meaning |
|---|---|
| **SAFE_TO_COMMIT** | Infrastructure, config, gitignore — no business logic |
| **EXPECTED_IMPLEMENTATION_CHANGE** | Source code, tests, scripts, UI with clear phase attribution |
| **EXPECTED_GOVERNANCE_CHANGE** | Analysis documents, phase verdicts, certifications |
| **DO_NOT_COMMIT** | Generated artifacts, scratch, data with no version control value |

---

## GROUP 1: SAFE_TO_COMMIT

*Commit independently or as part of any commit.*

| File | Reason |
|---|---|
| `.gitignore` | Security hygiene: `.env` exclusion |
| `.env.example` | API key template; documents requirements without exposing secrets |

---

## GROUP 2: EXPECTED_IMPLEMENTATION_CHANGE

*Commit together as the implementation commit. Recommended tag: `portfolio-manager-v7.7a-22d10-stable` or equivalent.*

### Tracked Modified — Core Source

| File | Phase | Notes |
|---|---|---|
| `scripts/run_outcome_ui.py` | 22D.10 | Settlement-aware API endpoint |
| `src/history/analytical_universe_manager.py` | 7.4D + 22D.2 | Replay routing + percentile |
| `src/portfolio/enrichment.py` | 7.5E | Danelfin score wire-up |
| `src/portfolio/models.py` | 7.5E + 7.5J + 22D.10 | Model extensions (additive) |
| `src/portfolio/optimizer.py` | 7.3C | Preferred display helper |
| `src/portfolio/recommendations.py` | MULTI | Coverage-aware signal dedup |
| `src/portfolio/runner.py` | MULTI + 22D.10 | Settlement engine + queue integration |
| `src/portfolio/scoring.py` | MINOR | Wording fix |

### Tracked Modified — Tests & UI

| File | Phase | Notes |
|---|---|---|
| `tests/test_optimizer.py` | 7.3C | Version assertion fix |
| `ui/portfolio_alignment/app.js` | MULTI → 22D.10 | Full queue + settlement UI |
| `ui/portfolio_alignment/index.html` | MULTI → 22D.10 | CSS additions |

### New Source Files (untracked)

| File | Phase | Notes |
|---|---|---|
| `src/portfolio/analyst_consensus.py` | 7.5J | New module |
| `src/portfolio/deployment_planner.py` | 7.5D | New module |
| `src/portfolio/deployment_queue.py` | 7.5B | New module |
| `src/portfolio/fidelity_signal.py` | 7.5E | New module |
| `src/portfolio/unified_conviction.py` | 7.7A | New module |

### New Test Files (untracked)

| File | Phase |
|---|---|
| `tests/test_7_3c_optimizer_preferred.py` | 7.3C |
| `tests/test_7_4d_replay_evidence_routing.py` | 7.4D |
| `tests/test_7_5b_deployment_queue.py` | 7.5B |
| `tests/test_7_5d_deployment_planner.py` | 7.5D |
| `tests/test_7_5e_signal_transparency.py` | 7.5E |
| `tests/test_7_5f_deployment_actionability.py` | 7.5F |
| `tests/test_7_7a_ucf_foundation.py` | 7.7A |

### New Script Files (untracked)

| File | Phase |
|---|---|
| `scripts/phase_7_5w_simulation.py` | 7.5W |
| `scripts/phase_7_8a_persistence.py` | 7.8A |
| `scripts/phase_8_0b0_fmp_probe.py` | 8.0B.0 |
| `scripts/phase_8_0b0_stable_probe.py` | 8.0B.0 |
| `scripts/ucf_7_7b_analysis.py` | 7.7B |
| `scripts/ucf_validation_probe.py` | 7.7A |

### New UI (untracked)

| File | Phase |
|---|---|
| `ui/ucf_operator_dashboard/` | 7.7A |

**Pre-commit action required:** Bump `app.js?v=4` → `app.js?v=5` in `ui/portfolio_alignment/index.html` before committing.

---

## GROUP 3: EXPECTED_GOVERNANCE_CHANGE

*Commit separately as a governance/documentation commit. Can be committed before or after Group 2.*

### Phase Governance Documents — `data/analysis/`

| Subdirectory | Files | Phase |
|---|---|---|
| `data/analysis/phase_22d4/` | 5 files | 22D.4 |
| `data/analysis/phase_22d4_workstream_b/` | 9 files | 22D.4-WB |
| `data/analysis/phase_22d5/` | 8 files | 22D.5 |
| `data/analysis/phase_22d6/` | 5 files | 22D.6 |
| `data/analysis/phase_22d6a/` | 1 file | 22D.6A |
| `data/analysis/phase_22d7/` | 1 file | 22D.7 |
| `data/analysis/phase_22d8/` | 3 files | 22D.8 |
| `data/analysis/phase_22d9/` | 1 file | 22D.9 |
| `data/analysis/phase_22d10/` | 2 files | 22D.10 |
| `data/analysis/phase_22d10a/` | 5 files | 22D.10A |
| `data/analysis/phase_22d11/` | (this set) | 22D.11 |

**Total governance documents:** 117 files across 11 phase directories.

### Root-Level Reports (163 files)

These files are attributable governance/analysis outputs that were placed at the repository root instead of under `data/analysis/` or `docs/`. They should be committed in their current location as-is, then relocated in a subsequent cleanup commit.

**Do NOT attempt to relocate and commit simultaneously** — relocation requires careful path tracking to avoid losing git history lineage.

**Recommended commit message for root reports:** `docs: add Phase 7.x-22D.3 analysis reports and governance documents (root placement; relocation deferred)`

---

## GROUP 4: DO_NOT_COMMIT

*These files must never be staged or committed. Some require gitignore entries.*

| File / Path | Reason |
|---|---|
| `data/portfolio_ingestion/analysis_runs/` (175 dirs, 1411 files, 91MB) | Machine-generated run outputs; massive; zero git history value. Must remain gitignored. |
| `data/exports/archive/` (3 files) | Export snapshots; generated data artifacts |
| `untitled folder/api_response_22d3.json` | 2.6MB raw API response; debug scratch |
| `untitled folder/smoke_22d2.py` | Phase 22D.2 scratch script |
| `untitled folder/trace_22d3.py` | Phase 22D.3 trace script |

### Gitignore Status Check

The `data/portfolio_ingestion/analysis_runs/` directory is **currently untracked** (shown as `??` in git status), which confirms it is already excluded by gitignore. No action needed to maintain exclusion — but verify this is explicitly in `.gitignore` before the commit that modifies `.gitignore`.

The `untitled folder/` contents are also untracked. Consider adding `untitled folder/` to `.gitignore` or simply leaving it untracked permanently.

---

## Recommended Commit Sequence

**If committing all work in a single session:**

```
Commit A: "config: add .env to gitignore, add .env.example template"
  - .gitignore
  - .env.example

Commit B: "feat: Phases 7.3C–7.7A + 22D.10 implementation (Settlement-Aware CW-DAS, UCF, Deployment Queue, Signal Transparency)"
  - All GROUP 2 files

Commit C: "docs: Phase 22D.4–22D.11 governance documents and analysis reports"
  - data/analysis/ (all phase subdirectories)
  - Root-level reports (163 files)
```

**If splitting for cleanliness:**

```
Commit B1: "feat: Phases 7.3C–7.7A (UCF, Deployment Queue, Signal Transparency)"
  - src/portfolio/ changes through 7.7A
  - New modules (deployment_planner, deployment_queue, unified_conviction, etc.)
  - New tests through test_7_7a
  - app.js + index.html through Phase 7.7A

Commit B2: "feat: Phase 22D.10 Settlement-Aware CW-DAS"
  - runner.py (22D.10 changes)
  - run_outcome_ui.py
  - models.py (safe_to_offset_cash only)
  - app.js (settlement disclosure)
  - index.html (settlement CSS)
```

**Note:** Splitting requires careful staging of partial file diffs via `git add -p`. The multi-phase changes in single files make clean splitting non-trivial. A single "accumulation commit" (Commit B above) is simpler and is semantically correct given the tag-based release model used in this repo.

---

## Pre-Commit Checklist

Before executing any commit:

- [ ] Bump `app.js?v=4` → `app.js?v=5` in `ui/portfolio_alignment/index.html`
- [ ] Verify `data/portfolio_ingestion/analysis_runs/` is NOT staged (`git status` check)
- [ ] Verify `untitled folder/` is NOT staged
- [ ] Verify `data/exports/archive/` is NOT staged
- [ ] Confirm `phase_22d11_final_verdict.md` is complete and included in Commit C
- [ ] No `.env` file exists at root (should be excluded by `.gitignore`)
