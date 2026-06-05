# SIH Backlog Inventory — Phase 8.0B.1D

## Scope
All deferred work, approved future phases, technical debt, and enhancement opportunities identified across Phases 23.0A–8.0B.X.2, compiled from deliverable documents, final verdict files, and technical debt markers.

---

## Category 1 — Authorized Next Phases

| ID | Title | Source Phase | Status |
|----|-------|-------------|--------|
| NEXT-01 | FMP Score Integration Assessment (Phase 8.0B.1C) | 8.0B.1B.5 final verdict | AUTHORIZED |
| NEXT-02 | CRA Draft Persistence + CSV Export (Phase 23.6C) | 23.6B.5 final verdict | AUTHORIZED |
| NEXT-03 | FMP Bulk Fetch — Full Universe Coverage | 8.0B.1B coverage report | AUTHORIZED |
| NEXT-04 | Dislocation Framework (Phase 8.0B.2) | 8.0B.1B.5 final verdict | AUTHORIZED post-8.0B.1C |

---

## Category 2 — Scoring Enhancements (Deferred)

| ID | Title | Source | Priority |
|----|-------|--------|----------|
| SCR-01 | Graduated Allocation Drift Penalty (LOW→MODERATE cliff resolution) | Phase 8.0B.X.4 drift audit | MEDIUM |
| SCR-02 | FMP Fundamental Integration into CW-DAS Momentum component | Phase 8.0B.1C design docs | HIGH |
| SCR-03 | FMP-based Analyst Consensus into UCF score | 8.0B.1C assessment | MEDIUM |
| SCR-04 | P/E Ratio availability (requires FMP Premium+ upgrade) | 8.0B.1B field mapping | LOW |
| SCR-05 | Replay curve full-universe historical expansion | Phase 7.8B design | LOW |
| SCR-06 | Replay tiebreaker / soft weight modifier | Phase 7.8B/7.8C design | LOW |

---

## Category 3 — CRA Enhancements

| ID | Title | Source | Priority |
|----|-------|--------|----------|
| CRA-01 | CRA Draft Persistence API (`POST /api/cra/proposal/draft`) | Phase 23.6C scope doc | HIGH |
| CRA-02 | CRA CSV Export (`GET /api/cra/proposal/export`) | Phase 23.6C scope doc | HIGH |
| CRA-03 | Clipboard copy button for CRA proposal | Phase 23.6C scope doc | MEDIUM |
| CRA-04 | Draft load on page reload | Phase 23.6C scope doc | MEDIUM |
| CRA-05 | Strategic Exit Automation Review (PAR `strategic_profiles.json` integration) | 23.6B.5 notes | MEDIUM |
| CRA-06 | CRA Phase 23.6D — TBD post-23.6C | Future planning | LOW |

---

## Category 4 — FMP Integration Track

| ID | Title | Source | Priority |
|----|-------|--------|----------|
| FMP-01 | FMP Bulk Fetch Implementation (replace per-symbol with bulk endpoints) | 8.0B.1B coverage report | HIGH |
| FMP-02 | FMP Score Integration Assessment (8.0B.1C) | Authorized | HIGH |
| FMP-03 | FMP Quarterly Income Growth (requires Premium+ upgrade) | 8.0B.1B field mapping | LOW |
| FMP-04 | FMP P/E Ratio field (requires Starter+ plan feature) | 8.0B.1B null handling | LOW |
| FMP-05 | FMP Subscription Upgrade Evaluation | 8.0B.1B final verdict | MEDIUM |
| FMP-06 | FMP Historical Fundamental Trends (multi-quarter display) | 8.0B.1B.5 design | MEDIUM |
| FMP-07 | FMP Consistency Monitor — automated stale signal detection | 8.0B.1B.5 | MEDIUM |

---

## Category 5 — UI/UX Enhancements

| ID | Title | Source | Priority |
|----|-------|--------|----------|
| UI-01 | Dislocation Watchlist panel (symbols flagged POTENTIAL/HIGH CONVICTION) | 8.0B.X.3/8.0B.1B.5 | MEDIUM |
| UI-02 | Fundamental Snapshot full-universe (after bulk FMP fetch) | 8.0B.1B.5 | HIGH |
| UI-03 | Company Snapshot — AI-assisted operator summaries | 8.0B.X.2 | LOW |
| UI-04 | Portfolio Theme Exposure dashboard | 8.0B.X.2 tag design | MEDIUM |
| UI-05 | CRA panel — clipboard and export buttons | Phase 23.6C | HIGH |
| UI-06 | Historical Fundamental Trends mini-chart in card expansion | 8.0B.1B.5 | LOW |
| UI-07 | Deployment Queue filter by Thesis Integrity status | 8.0B.1B.5 | MEDIUM |
| UI-08 | Deployment Queue filter by Dislocation status | 8.0B.1B.5 | MEDIUM |

---

## Category 6 — Technical Debt

| ID | Title | Source | Impact |
|----|-------|--------|--------|
| TD-01 | `etf_exposure_decomposition.yaml` — remove SPAXX/VMFXX/FZFXX entries | Phase 23.6B cert | Zero behavioral impact; registry cleanup |
| TD-02 | `phase_7_4a_analysis.py` — superseded analysis script in repo root | Observed | Low |
| TD-03 | Root-level analysis `.md` reports — relocation to `docs/analysis/` deferred | Phase 22D cert | Low |
| TD-04 | `scripts/fetch_fmp_validation_set.py` — one-time script, should be removed or promoted | Phase 8.0B.1B | Low |
| TD-05 | FMP `_write_csv()` signature inconsistency (headers as 2nd vs 3rd arg) | Phase 8.0B.1B impl | Low |
| TD-06 | PENDING ACTIVITY as ACTIVE_POSITION classification — behavioral guard not yet documented | Phase 22D.10 | Medium |

---

## Category 7 — Architecture / Governance

| ID | Title | Source | Priority |
|----|-------|--------|----------|
| ARCH-01 | GitHub Issues as authoritative backlog (this phase) | 8.0B.1D | HIGH |
| ARCH-02 | GitHub Actions — automated test run on push | Future | MEDIUM |
| ARCH-03 | Signal freshness monitoring — automated staleness alerts | refresh_signals.py | MEDIUM |
| ARCH-04 | FMP subscription governance — upgrade decision framework | 8.0B.1B | MEDIUM |
| ARCH-05 | Copilot execution standard — issue-driven workflow | 8.0B.1D | HIGH |

---

## Category 8 — Research / Validation

| ID | Title | Source | Priority |
|----|-------|--------|----------|
| RES-01 | FMS predictive value empirical validation (Phase 8.0D prerequisite) | Phase 8.0D design | HIGH |
| RES-02 | CW-DAS Graduated Drift Penalty — simulation against historical queue | 8.0B.X.4 audit | MEDIUM |
| RES-03 | Fundamental Consistency classifier — calibration against known outcomes | 8.0B.1B.5 | MEDIUM |
| RES-04 | Replay curve full-universe quality assessment | Phase 7.8 design | LOW |

---

## Total Inventory Summary

| Category | Count |
|----------|-------|
| Authorized Next Phases | 4 |
| Scoring Enhancements | 6 |
| CRA Enhancements | 6 |
| FMP Integration | 7 |
| UI/UX | 8 |
| Technical Debt | 6 |
| Architecture/Governance | 5 |
| Research/Validation | 4 |
| **Total** | **46** |
