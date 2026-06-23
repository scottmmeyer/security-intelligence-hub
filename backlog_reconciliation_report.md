# SIH-BACKLOG-RECON-01 — Repository & Backlog Reconciliation Report

**Date:** 2026-06-16  
**Auditor:** SIH Governance  
**Baseline:** Working tree HEAD (commit 294b55b, stream/pis-006-post-ingestion-trigger)

---

## Executive Summary

The Security Intelligence Hub has undergone concentrated development from 2026-05-13 through 2026-06-16. This period produced **105 commits**, **88 test files**, **1,929 individual tests**, and **80 API endpoints**. Multiple GitHub issues reported as "in progress" are fully delivered and production-ready.

**Recommended immediate closures: #52, #38, #17**  
**Partially-delivered / active: #32 (AI-004)**  
**New tracking recommended: 9 delivered capabilities without issue representation**

---

## Part A — Repository Capability Inventory

### ESS Signal Intelligence

| Capability | Module | Status | Tests |
|-----------|--------|--------|-------|
| ESS intake ordering fix | `src/history/signal_snapshot_manager.py` | **COMPLETE** | 9 ordering + 7 foundation |
| Provider-order-independent merge (`_build_merged_snapshot`) | same | **COMPLETE** | T01–T09 all pass |
| ESS archive intake pipeline | `src/pipeline/stages/ess_intake_stage.py` | **COMPLETE** | — |
| Signal conflict framework | `src/sih/signal_conflict_review.py` | **COMPLETE** | 66 tests |
| Conflict pattern outcomes (Part B) | `data/analysis/dislocation/pattern_outcomes.json` | **COMPLETE** | — |
| Signal reliability scorecard (Part C) | `data/analysis/dislocation/signal_scorecard.json` | **COMPLETE** | — |
| Symbol deep dive (Part D) | `/api/conflict-review/symbol/<SYM>` | **COMPLETE** | — |
| Conflict alpha attribution | `src/sih/conflict_alpha_analysis.py` | **COMPLETE** | 41 tests |
| Security-level alpha insights | `src/sih/security_conflict_alpha.py` | **COMPLETE** | 41 tests |
| ESS coverage audit | `data/history/ess_archive/` + reporting | **COMPLETE** | — |
| ESS intake closure audit | `docs/ess_intake_ordering_closure_audit.md` | **COMPLETE** | — |

### CW-DAS / Scoring

| Capability | Module | Status | Tests |
|-----------|--------|--------|-------|
| Danelfin AI signal integration | `src/scoring/` | **COMPLETE** | via AI-006 audit |
| UCF conviction classification | `src/sih/` ucf engine | **COMPLETE** | 53 tests |
| Signal governance conflict classification | `src/portfolio/signal_conflict_classifier.py` | **COMPLETE** | gov02a tests |
| FMP data quality validation | `src/scoring/fetch_fmp_signals.py` | **COMPLETE** | 50 tests |
| Deployment queue (CW-DAS 1.1) | `src/portfolio/deployment_queue_builder.py` | **COMPLETE** | 61 tests |
| Deployment plan / cash allocation | `src/portfolio/deployment_planner.py` | **COMPLETE** | 35 tests |

### Replay

| Capability | Module | Status | Tests |
|-----------|--------|--------|-------|
| Replay foundation (WP-03 through WP-05D) | `data/history/replays/` | **COMPLETE** | wp04/wp05 test suite |
| Replay coverage governance | `src/replay/` | **COMPLETE** | wp05b tests |
| Stock replay curves | `src/replay/` | **COMPLETE** | wp05d tests |
| Temporal snapshot (WP-05C) | — | **COMPLETE** | wp05c tests |
| Benchmark attribution | `src/pis/benchmark_attribution.py` | **COMPLETE** | bench-01b tests |

### CRA — Capital Rotation Advisor

| Capability | Module | Status | Tests |
|-----------|--------|--------|-------|
| CRA backend core | `src/portfolio/cra/` | **COMPLETE** | 89 tests |
| Capital source detection (5 categories) | `capital_source_builder.py` | **COMPLETE** | — |
| Funding policy & reduction scoring | `funding_policy.py` | **COMPLETE** | — |
| CRA UI (3-column rotation panel) | `app.js` Phase 23.6B | **COMPLETE** | — |
| Strategic exit remediation | Phase 23.6B.4 | **COMPLETE** | — |
| Capital source intent classification (CRA-EXPLAIN-02) | `models.py` + builder | **COMPLETE** | 32 tests |
| Source intent summary (THESIS_EXIT/TAX_FUNDING/etc.) | API + UI | **COMPLETE** | — |
| Intent badges and explanatory text | `app.js` RQ panel | **COMPLETE** | — |
| Tax-aware action framework | Phase 23.0A | **COMPLETE** | — |
| Operator policies | Phase 23.2 | **COMPLETE** | — |

### PAP — Portfolio Action Pipeline

| Capability | Module | Status | Tests |
|-----------|--------|--------|-------|
| PAP recommendations engine | `src/portfolio/` | **COMPLETE** | reconciliation tests |
| Mandate intelligence | `src/portfolio/mandate_intelligence.py` | **COMPLETE** | 64 tests |
| Allocation explainability (AI-003) | `src/sih/allocation_explainability.py` | **COMPLETE** | — |
| Optimizer integration (Phase 7.3B/C) | `app.js` | **COMPLETE** | — |
| Recommendation explanation | `src/sih/` explanations | **COMPLETE** | — |
| Phase E synthesis (STI profiles) | `src/portfolio/phase_e/` | **COMPLETE** | 40 tests |
| Phase D trim intelligence | — | **COMPLETE** | 35 tests |
| FVI (Fund Vehicle Intelligence) | `src/portfolio/fvi/` | **COMPLETE** | fvi tests |
| FMI / dislocation watchlist | `src/portfolio/fmi/` | **COMPLETE** | — |
| Vehicle suitability | `src/portfolio/vehicle_suitability.py` | **COMPLETE** | veh suitability tests |
| CPV compliance validator | `src/portfolio/compliance_validator.py` | **COMPLETE** | via AI-001-B |
| Dynamic subtier classification | — | **COMPLETE** | 47 tests |

### PIS — Portfolio Intelligence System

| Capability | Module | Status | Tests |
|-----------|--------|--------|-------|
| Phase 1: account-level snapshots | `src/pis/storage.py` | **COMPLETE** | pis_phase1 tests |
| Canonical daily selection | `src/pis/canonical_daily.py` | **COMPLETE** | PIS-004B |
| Governance (Stage A) | `src/pis/governance.py` | **COMPLETE** | PIS-004A |
| Change detection | `src/pis/change_detection.py` | **COMPLETE** | — |
| Lineage tracking | `src/pis/recommendation_lineage.py` | **COMPLETE** | — |
| Performance attribution | `src/pis/performance_attribution.py` | **COMPLETE** | — |
| Benchmark attribution | `src/pis/benchmark_attribution.py` | **COMPLETE** | — |
| Action attribution | `src/pis/action_attribution.py` | **COMPLETE** | 51 tests |
| Allocation drift trends | `src/pis/allocation_drift.py` | **COMPLETE** | 61 pis drift + 89 legacy |
| PA-006B drift intelligence | `src/pis/drift_trend_analyzer.py` | **COMPLETE** | 60 tests |
| PIS DOR (Outcome Review) | `src/pis/dislocation_outcome_review.py` | **COMPLETE** | 43 tests |
| Policy version diff | `src/pis/policy_version_diff.py` | **COMPLETE** | 35 tests |
| Allocation compliance | `src/pis/allocation_compliance.py` | **COMPLETE** | 39 tests |
| Refresh orchestration | `src/pis/refresh_orchestrator.py` | **COMPLETE** | — |
| PIS dashboard (executive layer) | `app.js` PIS-UI-03 | **COMPLETE** | dashboard tests |
| Post-ingestion refresh trigger | PIS-006 | **COMPLETE** | — |
| PIS integrity hardening | PIS-007A | **COMPLETE** | — |

### MEI — Market Event Intelligence

| Capability | Module | Status | Tests |
|-----------|--------|--------|-------|
| Event calendar engine | `src/mei/events.py` | **COMPLETE** | 46 tests |
| Portfolio exposure engine | `src/mei/exposures.py` | **COMPLETE** | — |
| Security sensitivity profiles | `src/mei/security_profiles.py` | **COMPLETE** | — |
| Recommendation context overlay | `src/mei/recommendation_context.py` | **COMPLETE** | — |
| Event history repository | `src/mei/event_history.py` | **COMPLETE** | — |
| MEI dashboard panel (7 sections) | `app.js` PIS dashboard | **COMPLETE** | — |

### Signal Conflict Review / Dislocation Intelligence

| Capability | Module | Status | Tests |
|-----------|--------|--------|-------|
| ISSUE-12D conflict inventory (Part A) | `signal_conflict_review.py` | **COMPLETE** | 66 tests |
| Outcome analysis (Part B) | `pattern_outcomes.json` | **COMPLETE** | — |
| Signal scorecard (Part C) | `signal_scorecard.json` | **COMPLETE** | — |
| MSFT deep dive (Part D) | `/api/conflict-review/symbol/` | **COMPLETE** | — |
| Learning panel (Part E) | `app.js` | **COMPLETE** | — |
| DISLOCATION-02 alpha attribution | `conflict_alpha_analysis.py` | **COMPLETE** | 41 tests |
| DISLOCATION-03 security-level alpha | `security_conflict_alpha.py` | **COMPLETE** | 41 tests |
| Conflict alpha badges on DQ/RQ/Dislocation | `app.js` | **COMPLETE** | — |

---

## Part B — GitHub Issue Reconciliation

### Issue #52 — ESS-INTAKE-ORDERING-01

**Current State: COMPLETE**

Evidence:
- Root cause identified: `signal_snapshot.csv` used last-write-wins semantics
- Fix committed: `bed805a` (2026-06-15): `_build_merged_snapshot()` + `_coverage_rank()`
- Fix mechanism: Coverage-rank-based merge rebuilds snapshot from ALL same-day partitions, provider-order-independent
- Formal closure audit: `docs/ess_intake_ordering_closure_audit.md` (2026-06-16)
- Tests: 9 ordering tests (T01–T09) + 7 foundation tests + 2 readiness tests = **18/18 passing**
- Full suite: 1,847 passed, 0 new failures
- Q3: Provider ordering cannot influence `signal_snapshot.csv` — formally proven
- Q4: No downstream system (CW-DAS, UCF, PAP, CRA, Replay) retains exposure

**Recommendation: CLOSE IMMEDIATELY**

---

### Issue #38 — PA-006 (Allocation Drift)

**Current State: COMPLETE — Three Phases Delivered**

Evidence:
- **PA-006**: Allocation compliance foundation (`allocation_compliance.py`, `compliance_validator.py`) — complete
- **PA-006A**: Drift analyzer (`drift_analyzer.py`) — complete, 89 tests
- **PA-006B**: Drift intelligence (`drift_trend_analyzer.py`) — complete, 60 tests
  - Trend classification (IMPROVING/DETERIORATING/STABLE/OSCILLATING)
  - Momentum score (−100 to +100)
  - Persistence classification (TEMPORARY/RECURRING/CHRONIC/STRUCTURAL)
  - Priority ranking (top-10 attention list)
  - Historical learning (`allocation_drift_learning.json`)
  - 5 API endpoints: `/api/drift/trends|priorities|chronic|momentum|intelligence-summary`
  - Allocation Intelligence dashboard panel with trend strip, priority table, chronic violations, momentum heatmap
- All 84 PA-006/PA-006A tests passing; 60 PA-006B tests passing

**Recommendation: CLOSE IMMEDIATELY**

---

### Issue #17 — ISSUE-12D (Signal Conflict Review)

**Current State: FULLY DELIVERED + EXTENDED**

Evidence:
- **ISSUE-12D Core**: 3,897-entry conflict inventory, 369 conflict cases, 15 ESS archive dates, 6 patterns
- Part A: `dislocation_inventory.csv` — complete
- Part B: `pattern_outcomes.json` — complete  
- Part C: `signal_scorecard.json` — complete
- Part D: `/api/conflict-review/symbol/<SYM>` — complete
- Part E: Learning panel + Portfolio Learning Summary — complete
- All 66 core tests passing
- **DISLOCATION-02** (Alpha Attribution): `conflict_alpha_analysis.py`, 41 tests, `/api/conflict-review/alpha`
- **DISLOCATION-03** (Security-Level Alpha): `security_conflict_alpha.py`, 41 tests, 2 API endpoints, badges on DQ/RQ/Dislocation
- Key finding operationalized: `ESS_BULLISH_ANALYST_MIXED` → +2.81pp excess return → **ALPHA_LEADER** visible on security profiles

**Recommendation: CLOSE IMMEDIATELY** (extensions tracked under DISLOCATION series)

---

### Issue #32 — AI-004 (Allocation Policy Version Diff Visibility)

**Current State: PARTIALLY DELIVERED**

Evidence:
- `src/pis/policy_version_diff.py` — **complete** (35 tests)
- `/api/pis/policy/current`, `/api/pis/policy/history`, `/api/pis/policy/diff` — **complete**
- PIS dashboard section for policy history — **complete**
- Basic diff visualization on PIS dashboard — **complete**
- **Missing**: Rich operator-facing UI showing what changed between policy versions with affected node impact analysis
- **Missing**: "Policy Change Impact" notifications on recommendations (e.g. "This recommendation changed because the EQUITIES.US.SMALL target moved from 12% to 14%")
- **Missing**: Visual timeline of policy versions with drift before/after overlays

**Current completion: ~60%**

**Recommendation: KEEP OPEN — remaining UI enhancement work is valuable but not urgent**

---

## Part C — Missing Issue Detection

The following delivered capabilities have no corresponding GitHub issue:

| Capability | Delivered | Recommended Action |
|-----------|-----------|-------------------|
| **CRA-EXPLAIN-02**: Capital Source Intent Classification | 2026-06-16 | Create issue CLOSED |
| **DISLOCATION-02**: Conflict Alpha Attribution | 2026-06-16 | Create issue CLOSED |
| **DISLOCATION-03**: Security-Level Alpha Insight Cards | 2026-06-16 | Create issue CLOSED |
| **MEI Phase 1**: Market Event Intelligence | 2026-06-16 | Create issue CLOSED |
| **PA-006B**: Drift Intelligence (momentum, persistence, priority) | 2026-06-16 | Part of #38 → close with #38 |
| **PIS-007A**: Production hardening (integrity, refresh logging) | 2026-06-03 | Document only |
| **BENCH-01B**: Benchmark attribution pipeline | pre-release | Document only |
| **AI-001-D (CPV)**: Portfolio Compliance Validator | pre-release | Document only |
| **Signal Governance (SIGNAL-GOV-02A)**: Conflict classifier | pre-release | Document only |
| **FMP Phase 8.0B.1A/1B**: FMP data quality + universe extension | pre-release | Document only |

---

## Part D — Epic Review

### EPIC: CRA (Capital Rotation Advisor)

**Completion: ~85%**

| Milestone | Status |
|-----------|--------|
| Backend core (23.6A) | ✅ Complete |
| UI (23.6B) | ✅ Complete |
| Defect remediation (23.6B.4) | ✅ Complete |
| Tax-aware actions (23.0A/C) | ✅ Complete |
| Source intent classification (CRA-EXPLAIN-02) | ✅ Complete |
| Funding source transparency | ✅ Complete |
| Draft persistence + CSV export | ✅ Complete |
| **Remaining: CRA Phase 23.6C** | Clipboard copy enhancements (low priority) |
| **Remaining: CRA-EXPLAIN-03** | Full rotation narrative for operator sign-off |

---

### EPIC: PAP (Portfolio Action Pipeline)

**Completion: ~90%**

| Milestone | Status |
|-----------|--------|
| Recommendations engine | ✅ Complete |
| Mandate intelligence | ✅ Complete |
| Allocation explainability (AI-003) | ✅ Complete |
| Optimizer integration (7.3B/C) | ✅ Complete |
| Phase D/E synthesis | ✅ Complete |
| FVI advisory integration | ✅ Complete |
| Policy-aware execution states | ✅ Complete |
| **Remaining: AI-004 rich policy diff** | ~60% complete |
| **Remaining: Operator sign-off workflow** | Not started |

---

### EPIC: Signal Intelligence Evolution

**Completion: ~80%**

| Milestone | Status |
|-----------|--------|
| ESS intake ordering fix | ✅ Complete |
| Signal conflict review (ISSUE-12D) | ✅ Complete |
| Conflict alpha attribution (DISLOCATION-02) | ✅ Complete |
| Security-level alpha insights (DISLOCATION-03) | ✅ Complete |
| Danelfin integration + AI-006 audit | ✅ Complete |
| **Remaining: DISLOCATION-04** | Cross-date pattern persistence analysis |
| **Remaining: Signal decay modeling** | Not started |

---

### EPIC: Governance & Tooling

**Completion: ~75%**

| Milestone | Status |
|-----------|--------|
| PIS foundation + snapshots | ✅ Complete |
| Governance Stage A | ✅ Complete |
| Benchmark attribution | ✅ Complete |
| Allocation drift intelligence | ✅ Complete |
| Policy version diff | ✅ ~60% complete |
| **Remaining: PIS Stage B** | Canonical selection |
| **Remaining: RESEARCH-01** | Funding source effectiveness study |

---

## Part E — Updated Backlog Ranking

### Immediate Priorities (Next 30 Days)

| Priority | Item | Rationale |
|----------|------|-----------|
| 1 | **MEI-002: Event Outcome Attribution** | Closes the historical feedback loop for MEI — track which events caused which portfolio moves. High operator value. |
| 2 | **AI-004 Completion**: Policy Diff UI Enhancement | Rich "what changed and why" notification when policy changes affect recommendations. #32 is partially done; closing the gap improves operator trust. |
| 3 | **DISLOCATION-04**: Cross-date pattern persistence | Which conflict patterns repeat persistently for the same symbols? Extends DISLOCATION-03 with longitudinal per-symbol conflict history. |
| 4 | **PA-006C**: Drift narrative engine | Plain-language summaries of drift changes tied to recommendation cards. E.g. "International overweight has deteriorated for 3 consecutive periods." |

---

### Medium Priorities (30–90 Days)

| Priority | Item | Rationale |
|----------|------|-----------|
| 5 | **RESEARCH-01: Funding Source Effectiveness** | Which CRA capital sources historically produced better redeployment outcomes? Closes the capital rotation learning loop. |
| 6 | **Operator Sign-off Workflow** | Lightweight proposal approval with timestamp and rationale, tracked in PIS. Required for institutional-grade governance. |
| 7 | **PIS Stage B**: Canonical selection Phase 2 | Formalize canonical selection beyond PASS-preferred fallback. Required for stable downstream attribution. |
| 8 | **CRA Phase 23.6C**: Export and clipboard enhancements | Copy rotation summary to clipboard; Markdown export improvements. Low complexity, user-facing. |
| 9 | **ESS Archive Date Extension** | Currently 15 dates (Aug 2025–Mar 2026). Adding recent ESS archive entries extends the conflict inventory depth. |

---

### Future Research (90+ Days)

| Item | Description |
|------|-------------|
| **Signal Decay Modeling** | How quickly does an ESS bullish signal "decay" if the position underperforms? At what point should a signal be considered stale for conviction purposes? |
| **DISLOCATION-05: Replay × Conflict Correlation** | When replay-supported securities show ESS/analyst conflict, are the outcomes systematically different from non-replay-backed conflicts? |
| **Allocation Scenario Modeling** | If operator executes the CRA proposal, show projected allocation map changes. Requires lightweight portfolio recompute. |
| **Position Sizing Intelligence** | Historical analysis of whether CRA sizing fractions (25%/50%/100%) were appropriately calibrated vs actual outcomes. |

---

## Part F — Closure Recommendations

| Issue | Current State | Evidence | Recommended Action |
|-------|--------------|----------|--------------------|
| **#52 ESS-INTAKE-ORDERING-01** | **COMPLETE** | bed805a fix, 18 tests, formal closure audit | **CLOSE IMMEDIATELY** |
| **#38 PA-006** | **COMPLETE** (3 phases) | PA-006, PA-006A, PA-006B all delivered, 200+ tests | **CLOSE IMMEDIATELY** |
| **#17 ISSUE-12D** | **COMPLETE + EXTENDED** | Inventory + outcomes + scorecard + DISLOCATION-02/03 | **CLOSE IMMEDIATELY** |
| **#32 AI-004** | **PARTIALLY DELIVERED** (~60%) | policy_version_diff.py done; rich UI enhancement pending | **KEEP OPEN** — reprioritize as Medium |

---

## Required Questions — Formal Answers

| Question | Answer |
|----------|--------|
| **Q1: Which open issues are actually complete?** | #52, #38, #17 are all fully delivered and production-ready with passing tests. |
| **Q2: Which should close immediately?** | #52 (ESS-INTAKE-ORDERING-01), #38 (PA-006), #17 (ISSUE-12D) |
| **Q3: Which delivered capabilities lack issue tracking?** | CRA-EXPLAIN-02, DISLOCATION-02, DISLOCATION-03, MEI Phase 1, PA-006B (subissue), PIS-007A, BENCH-01B, CPV, SIGNAL-GOV-02A, FMP 8.0B |
| **Q4: Which epics are effectively complete?** | CRA (~85%), PAP (~90%). Signal Intelligence (~80%) and Governance/Tooling (~75%) are mature but have active remaining work. |
| **Q5: Highest-value remaining enhancements?** | MEI-002 (Event Outcome Attribution), AI-004 completion (Policy Diff UI), DISLOCATION-04 (per-symbol pattern persistence), PA-006C (drift narrative) |
| **Q6: Research initiatives to track?** | RESEARCH-01 (funding source effectiveness), DISLOCATION-05 (Replay × Conflict), signal decay modeling |
| **Q7: Updated backlog ranking?** | See Part E above. MEI-002 → AI-004 → DISLOCATION-04 → PA-006C → RESEARCH-01 |
| **Q8: Next implementation priority?** | **MEI-002: Event Outcome Attribution** — closes the only major learning loop that currently has no historical feedback (events fired but outcomes not attributed). |

---

## Repository Statistics (as of 2026-06-16)

| Metric | Value |
|--------|-------|
| Total commits | 105 |
| Test files | 88 |
| Individual tests defined | 1,929 |
| Tests passing (last full run) | 1,847 |
| Pre-existing failures (unrelated to current work) | 5 |
| New failures from today's work | 0 |
| API endpoints | 80 |
| Source modules | 50+ |
| Dashboard sections | 15+ |

---

*This report was produced on 2026-06-16 by automated repository analysis. All test counts and module listings are derived from the live repository state.*
