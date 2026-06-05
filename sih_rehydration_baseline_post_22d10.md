# SIH Rehydration Baseline — Post Phase 22D.10 / 22D.11A
**Created:** 2026-06-03 | **Commit HEAD:** `d6c11fa` | **Status:** CERTIFIED

---

## Purpose

This baseline document enables clean session rehydration after the Phase 22D.11A
commit sequence. It records the authoritative post-commit system state, certified
phases, closed defects, and next authorized work.

---

## Repository State

| Attribute | Value |
|---|---|
| HEAD commit | `d6c11fa` |
| Branch | `main` |
| Working tree | CLEAN (nothing to commit) |
| Baseline tag | `portfolio-manager-v7.3b-stable` at `564f1a4` |
| Commits since baseline | 3 (Commits 1–3 of Phase 22D.11A) |

## Commit Sequence (Phase 22D.11A)

| Hash | Type | Summary |
|---|---|---|
| `2d68fe5` | CONFIG | .gitignore hardening + .env.example |
| `9f2c35b` | IMPLEMENTATION | Phases 7.3C–7.7A + 22D.10 (Settlement-Aware CW-DAS) |
| `d6c11fa` | GOVERNANCE | Phase 22D.4–22D.11 governance docs (308 files) |

---

## Certified Phases

| Phase | Description | Certification |
|---|---|---|
| Phase 22D.8A | Signal trust certification | ✅ CERTIFIED |
| Phase 22D.9A | Coverage framework reconciliation | ✅ CERTIFIED |
| Phase 22D.9B | Deployment workflow audit | ✅ CERTIFIED |
| Phase 22D.10 | Settlement-Aware CW-DAS | ✅ PRODUCTION CERTIFIED (PAR-20260603-AC8FD5F0) |
| Phase 22D.10A | Frontend cache + runtime reload audit | ✅ CERTIFIED |
| Phase 22D.11 | Dirty scope classification + commit readiness audit | ✅ CERTIFIED |
| Phase 22D.11A | Commit execution + baseline certification | ✅ CERTIFIED |

---

## Closed Defects

### [CLOSED] Material Recommendation Defect — CW-DAS Settlement Sizing Error

| Attribute | Value |
|---|---|
| Defect ID | CW-DAS-SETTLEMENT-001 |
| Severity | MATERIAL — affected production deployment sizing |
| Root cause | CW-DAS sized deployment from `deployable_mv` (reported cash) while ignoring ACCOUNTING_ADJUSTMENT settlement obligations (`market_value < 0`) |
| Impact | Deployment oversized by settlement amount; risk of cash floor breach |
| Resolution | `safe_to_offset_cash: bool = False` on `PortfolioHolding`; settlement adjustment engine in `runner.py`; `adjusted_deployable_mv` propagated through API and UI |
| Certified run | PAR-20260603-AC8FD5F0 — `adjusted_deployable_mv: $4,091.70`, `cash_after_pct: 7.7426%` ≥ 7.0% floor |
| Status | **CLOSED — PRODUCTION CERTIFIED** |

---

## Current System Architecture

### Core Modules (src/portfolio/)

| Module | Phase | Purpose |
|---|---|---|
| `models.py` | 7.5E + 7.5J + 22D.10 | `PortfolioHolding`, `safe_to_offset_cash`, `danelfin_score`, `AnalystConsensus` |
| `runner.py` | MULTI + 22D.10 | Settlement engine, `adjusted_deployable_mv`, CW-DAS |
| `optimizer.py` | 7.3C | `_build_preferred_display()`, parallel optimizer |
| `recommendations.py` | MULTI | Coverage-aware dedup, signal routing |
| `scoring.py` | MINOR | Scoring calibration |
| `enrichment.py` | 7.5E | `danelfin_score` wire-up |
| `analyst_consensus.py` | 7.5J | Analyst consensus module |
| `deployment_planner.py` | 7.5D | Deployment planning logic |
| `deployment_queue.py` | 7.5B | Deployment queue management |
| `fidelity_signal.py` | 7.5E | Fidelity signal integration |
| `unified_conviction.py` | 7.7A | Unified conviction framework (UCF) |

### UI

| File | Phase | Description |
|---|---|---|
| `ui/portfolio_alignment/index.html` | 22D.10 | Cache bust: `app.js?v=5` |
| `ui/portfolio_alignment/app.js` | MULTI → 22D.10 | Deployment queue + settlement disclosure UI |
| `ui/ucf_operator_dashboard/index.html` | 7.7A | UCF operator dashboard |

### Server

| Script | Description |
|---|---|
| `scripts/run_outcome_ui.py` | `http.server` + `socketserver.TCPServer`, port 8765; reads `adjusted_deployable_mv` from `cash_context` |

### Active Mandate

| Attribute | Value |
|---|---|
| Mandate | CONCENTRATED_ALPHA |
| `mandate_cash_target_pct` | 7.0% |
| Cash floor enforcement | Via `adjusted_deployable_mv` in settlement engine |

### Python Environment

| Attribute | Value |
|---|---|
| Python | 3.14 |
| Venv | `.venv/` |
| Invocation | `PYTHONPATH=. .venv/bin/python3` |

---

## Advisory Items (Non-Blocking, Pre-8.0B.0)

| ID | Item | Priority |
|---|---|---|
| A4 | No Phase 22D.10 unit test for settlement engine in runner.py | Low — post-Phase 8.0B.0 improvement |
| A5 | 163 root-level report files not relocated to data/analysis/ | Low — relocate in future cleanup commit |
| A6 | Repository is 17 commits ahead of origin/main (no push executed) | Deferred to operator decision |

---

## Next Authorized Phase

### Phase 8.0B.0 — FMP Capability Audit

**Authorization:** Granted upon completion of Phase 22D.11A ✅

**Prerequisite:** `FMP_API_KEY` must be present in `.env` at repo root (template: `.env.example`)

**Probe scripts (already committed):**
- `scripts/phase_8_0b0_fmp_probe.py` — FMP API capability probe
- `scripts/phase_8_0b0_stable_probe.py` — Stable/fallback data probe

**Objective:** Assess FMP API coverage for securities in the analytical universe.
Determine which data fields are reliably available to inform Phase 8.0B design decisions.

---

## Session Rehydration Prompt (Copy-Paste Ready)

```
REHYDRATION BASELINE: POST-22D.11A

Repository HEAD: d6c11fa (main) — working tree CLEAN
Certified phases: 22D.8A, 22D.9A, 22D.9B, 22D.10, 22D.10A, 22D.11, 22D.11A
Closed defect: CW-DAS-SETTLEMENT-001 — CLOSED PRODUCTION CERTIFIED
Active mandate: CONCENTRATED_ALPHA, cash_target=7.0%
Certified run: PAR-20260603-AC8FD5F0 (adjusted_deployable_mv: $4,091.70, cash_after_pct: 7.7426%)
UI cache bust: app.js?v=5 in ui/portfolio_alignment/index.html
Server: scripts/run_outcome_ui.py, port 8765
Python: 3.14, PYTHONPATH=. .venv/bin/python3
Next phase: Phase 8.0B.0 — FMP Capability Audit (requires FMP_API_KEY in .env)
```
