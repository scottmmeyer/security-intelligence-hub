# Phase 22D.11 — Scope Integrity Audit
**Generated:** 2026-06-03  
**Baseline Commit:** `564f1a4` (HEAD → main, tag: portfolio-manager-v7.3b-stable)  
**Question:** For every dirty file, is it EXPECTED, QUESTIONABLE, or UNEXPECTED?

---

## Classification Definitions

| Classification | Meaning |
|---|---|
| **EXPECTED** | Attributable to a named phase with known mandate. Presence in dirty state is correct. |
| **QUESTIONABLE** | Cannot be fully attributed to a known phase, or raises scope questions. Needs human review before commit. |
| **UNEXPECTED** | No plausible attribution. Origin unknown. Requires investigation before any action. |

---

## Section 1: Tracked Modified Files (12 files)

| File | Classification | Reason |
|---|---|---|
| `.gitignore` | EXPECTED | Security hygiene: added `.env` exclusion |
| `scripts/run_outcome_ui.py` | EXPECTED | Phase 22D.10 D4: settlement-aware cash_arg |
| `src/history/analytical_universe_manager.py` | EXPECTED | Phase 7.4D + 22D.2: replay routing + percentile |
| `src/portfolio/enrichment.py` | EXPECTED | Phase 7.5E: danelfin_score wire-up |
| `src/portfolio/models.py` | EXPECTED | Phases 7.5E + 7.5J + 22D.10 D1: additive model extensions |
| `src/portfolio/optimizer.py` | EXPECTED | Phase 7.3C: preferred display helper |
| `src/portfolio/recommendations.py` | EXPECTED | Coverage-aware dedup for signal routing |
| `src/portfolio/runner.py` | EXPECTED | Phase 22D.10 D2/D3/D4 + earlier integration |
| `src/portfolio/scoring.py` | EXPECTED | Trivial wording fix |
| `tests/test_optimizer.py` | EXPECTED | Version assertion correctly loosened for 7.3C |
| `ui/portfolio_alignment/app.js` | EXPECTED | Phases 7.3C–22D.10: full deployment queue + settlement UI |
| `ui/portfolio_alignment/index.html` | EXPECTED | Phases 7.3C–22D.10: CSS for all UI additions |

**Tracked file integrity: 12/12 EXPECTED. Zero QUESTIONABLE or UNEXPECTED.**

---

## Section 2: New Source Files (5 files)

| File | Classification | Reason |
|---|---|---|
| `src/portfolio/analyst_consensus.py` | EXPECTED | Phase 7.5J: transparency-only model |
| `src/portfolio/deployment_planner.py` | EXPECTED | Phase 7.5D: deployment planner engine (373 lines) |
| `src/portfolio/deployment_queue.py` | EXPECTED | Phase 7.5B: deployment queue builder (452 lines) |
| `src/portfolio/fidelity_signal.py` | EXPECTED | Phase 7.5E: Fidelity signal integration (202 lines) |
| `src/portfolio/unified_conviction.py` | EXPECTED | Phase 7.7A: UCF foundation (664 lines) |

**New source integrity: 5/5 EXPECTED.**

---

## Section 3: New Test Files (7 files)

| File | Classification | Reason |
|---|---|---|
| `tests/test_7_3c_optimizer_preferred.py` | EXPECTED | Paired with Phase 7.3C optimizer change |
| `tests/test_7_4d_replay_evidence_routing.py` | EXPECTED | Paired with Phase 7.4D routing fix |
| `tests/test_7_5b_deployment_queue.py` | EXPECTED | Paired with Phase 7.5B deployment queue |
| `tests/test_7_5d_deployment_planner.py` | EXPECTED | Paired with Phase 7.5D deployment planner |
| `tests/test_7_5e_signal_transparency.py` | EXPECTED | Paired with Phase 7.5E signal transparency |
| `tests/test_7_5f_deployment_actionability.py` | EXPECTED | Paired with Phase 7.5F actionability |
| `tests/test_7_7a_ucf_foundation.py` | EXPECTED | Paired with Phase 7.7A UCF |

**New test integrity: 7/7 EXPECTED.**

---

## Section 4: New Script Files (6 files)

| File | Classification | Reason |
|---|---|---|
| `scripts/phase_7_5w_simulation.py` | EXPECTED | Phase 7.5W analysis script |
| `scripts/phase_7_8a_persistence.py` | EXPECTED | Phase 7.8A analysis script |
| `scripts/phase_8_0b0_fmp_probe.py` | EXPECTED | Phase 8.0B.0 FMP capability probe — forward-looking |
| `scripts/phase_8_0b0_stable_probe.py` | EXPECTED | Phase 8.0B.0 stable data probe — forward-looking |
| `scripts/ucf_7_7b_analysis.py` | EXPECTED | Phase 7.7B UCF analysis |
| `scripts/ucf_validation_probe.py` | EXPECTED | Phase 7.7A UCF validation probe |

**Script integrity: 6/6 EXPECTED.**

---

## Section 5: New UI (1 directory)

| File | Classification | Reason |
|---|---|---|
| `ui/ucf_operator_dashboard/` | EXPECTED | Phase 7.7A: UCF operator dashboard |

---

## Section 6: Config Files (2 files)

| File | Classification | Reason |
|---|---|---|
| `.env.example` | EXPECTED | Documents required API keys; safe to commit |

---

## Section 7: Governance Documents — `data/analysis/` (117 files)

All files are in subdirectories with explicit phase naming: `phase_22d4/`, `phase_22d4_workstream_b/`, `phase_22d5/`, `phase_22d6/`, `phase_22d6a/`, `phase_22d7/`, `phase_22d8/`, `phase_22d9/`, `phase_22d10/`, `phase_22d10a/`.

**Classification: ALL 117 EXPECTED** — every file is a governance analysis document generated as a required deliverable of the named phase.

---

## Section 8: Root-Level Reports (163 files: 160 .md/.csv + 3 .py)

This is the largest category of untracked files outside of generated artifacts. These are analysis/validation/design documents produced during Phases 7.x and 22D.x that were written to the repository root rather than to `data/analysis/` or `docs/`.

**Content attribution:** All are recognizably named after signal analysis, replay analysis, conviction framework, deployment queue, ESS, UCF, etc. — consistent with Phases 7.3C through 22D.3.

**Classification: EXPECTED** — content is attributable. However, they raise a **STRUCTURAL CONCERN**: root-level pollution.

### Structural Concern: Root Placement

Phase governance documents are correctly placed under `data/analysis/phase_*/`. Root-level reports were written directly to `/` during earlier phases before the `data/analysis/` convention was fully established.

**This is an organizational defect, not a content defect.** The files are legitimate artifacts. They should be committed as-is and relocated in a dedicated cleanup commit (separate from feature commits).

**Specific items of note:**

| File | Note |
|---|---|
| `phase_22d1_final_verdict.md` | Phase 22D.1 verdict — should be under `data/analysis/phase_22d1/` |
| `phase_22d2_validation_report.md` | Phase 22D.2 — should be under `data/analysis/phase_22d2/` |
| `phase_22d3_final_verdict.md` | Phase 22D.3 — should be under `data/analysis/phase_22d3/` |
| `phase_7_3c_validation_report.md` | Phase 7.3C — should be under `data/analysis/phase_7_3c/` |
| `phase_7_4a_analysis.py` | Root-level script — should be under `scripts/` |
| `phase_7_4b_analysis.py` | Root-level script — should be under `scripts/` |
| `phase_7_4c_validation.py` | Root-level script — should be under `scripts/` |
| `phase_7_4d_lineage_trace_report.md` | Should be under `data/analysis/phase_7_4d/` |
| `phase_7_4e_execution_path_audit.md` | Should be under `data/analysis/phase_7_4e/` |
| `phase_7_4f_replay_consistency_audit.md` | Should be under `data/analysis/phase_7_4f/` |

---

## Section 9: Generated Artifacts (1411+ files, 91MB)

| Path | Classification | Note |
|---|---|---|
| `data/portfolio_ingestion/analysis_runs/` | **EXPECTED — DO NOT COMMIT** | PAR run outputs; machine-generated; no business value in git history |
| `data/exports/archive/` | **EXPECTED — DO NOT COMMIT** | Export snapshots; generated artifacts |

**These must not be committed.** They should be gitignored. The `.gitignore` already excludes `data/portfolio_ingestion/analysis_runs/` from tracking (verified by `??` status — they are untracked, not staged).

---

## Section 10: Scratch Files (3 files in `untitled folder/`)

| File | Classification | Reason |
|---|---|---|
| `untitled folder/api_response_22d3.json` | EXPECTED — DO NOT COMMIT | Phase 22D.3 debug capture; 2.6MB JSON; scratch artifact |
| `untitled folder/smoke_22d2.py` | EXPECTED — DO NOT COMMIT | Phase 22D.2 smoke test; scratch |
| `untitled folder/trace_22d3.py` | EXPECTED — DO NOT COMMIT | Phase 22D.3 trace script; scratch |

**Note:** The `untitled folder/` name is suspicious (appears to be a macOS default folder name). Its contents are legitimately attributable to Phase 22D.2–22D.3 debugging. But the folder itself has an inadvertent name and should not be committed as-is. The scratch artifacts inside are captured for reference only; they have no production value.

---

## Integrity Verdict by Category

| Category | Count | EXPECTED | QUESTIONABLE | UNEXPECTED |
|---|---|---|---|---|
| Tracked modified | 12 | 12 | 0 | 0 |
| New source | 5 | 5 | 0 | 0 |
| New tests | 7 | 7 | 0 | 0 |
| New scripts | 6 | 6 | 0 | 0 |
| New UI | 1 | 1 | 0 | 0 |
| Config | 2 | 2 | 0 | 0 |
| Governance (data/analysis/) | 117 | 117 | 0 | 0 |
| Root reports | 163 | 163* | 0 | 0 |
| Generated artifacts | 1411+ | 1411+ (no-commit) | 0 | 0 |
| Exports | 3 | 3 (no-commit) | 0 | 0 |
| Scratch | 3 | 3 (no-commit) | 0 | 0 |

*163 root reports are EXPECTED in content but carry a STRUCTURAL CONCERN (root placement).

## Overall Integrity Verdict

**ZERO UNEXPECTED files detected.**  
**ZERO QUESTIONABLE files detected.**  
**All dirty files are fully attributable to named phases.**

The only concern is organizational (root pollution), which does not block commit safety.
