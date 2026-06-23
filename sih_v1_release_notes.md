# Security Intelligence Hub — v1 Release Notes

**Tag:** `sih-v1-feature-complete`  
**Date:** 2026-06-16  
**Status:** Feature Complete v1 — transitioning to Research & Optimization

---

## Platform Summary

| Metric | Value |
|--------|-------|
| Test files | 91 |
| Individual tests | 2,025 |
| Last full run | 1,929 passed · 5 pre-existing failures · 0 new regressions |
| API endpoints | 93 |
| Source modules | 126 |
| Commits | 105 |
| Git tag | `sih-v1-feature-complete` |

---

## Major Capabilities Delivered

### Signal Intelligence
- **ESS intake pipeline** — multi-provider daily ingestion with immutable partition storage
- **ESS-INTAKE-ORDERING-01** — provider order no longer affects `signal_snapshot.csv`; coverage-rank merge across all same-day partitions
- **Signal conflict framework (ISSUE-12D)** — 3,897-entry inventory of ESS vs analyst disagreements across 15 archive dates
- **DISLOCATION-02** — excess return attribution per conflict pattern; key finding: `ESS_BULLISH_ANALYST_MAJORITY_BEARISH` → +2.26pp excess return (ALPHA_LEADER)
- **DISLOCATION-03** — security-level conflict alpha badges surfaced directly on DQ, RQ, and Dislocation panels
- **DISLOCATION-04** — per-symbol pattern persistence (streak, persistence_pct, trend)
- **DISLOCATION-05** — forward return estimation applying historical base rates to current conflict patterns

### CW-DAS / Scoring
- **CW-DAS 1.1** — multi-signal conviction scoring (ESS 55%, Danelfin, Zacks, Replay)
- **UCF** — CORE_CONVICTION_LEADER / HIGH_CONVICTION_ANCHOR / TACTICAL_GROWTH tiers
- **Deployment queue** — priority + headroom + deployment planner with cash allocation tiers
- **Signal governance (SIGNAL-GOV-02A)** — conflict classifier with advisory badges

### Capital Rotation Advisor (CRA)
- **Backend core** — 5-category capital source detection, funding policy, reduction scoring
- **UI** — 3-column rotation panel with source/rotation-map/impact columns
- **CRA-EXPLAIN-02** — source intent classification: THESIS_EXIT / THESIS_TRIM / TAX_FUNDING_SOURCE / PORTFOLIO_REALLOCATION / OVERWEIGHT_REPAIR
- **Intent badges + explanatory text** — on every source card, eliminating the "why is MSFT in the sell queue?" confusion
- **Tax-aware framework** — Bucket A–E integration; tax-driven reductions clearly labeled
- **Operator policies** — DO_NOT_SELL / SELL_LAST / CORE_ANCHOR / PREFERRED_ACCUMULATION
- **RESEARCH-01** — funding source effectiveness study validating ESS direction as primary CRA triage signal
- **SCENARIO-01** — lightweight portfolio scenario preview without full PAR re-run

### Portfolio Action Pipeline (PAP)
- **Recommendations engine** — full mandate alignment (CONCENTRATED_ALPHA + 5 others)
- **Mandate intelligence** — intentional asymmetry detection, conviction scoring
- **Allocation explainability (AI-003)** — deterministic recommendation explanations
- **Phase D/E synthesis** — STI profiles, thematic clustering, trim candidates
- **FVI** — fund vehicle intelligence for ETF suitability
- **Policy-aware execution** — BLOCKED / DEFERRED_BY_POLICY states
- **AI-004B** — policy change intelligence: severity classification, recommendation impact, before/after allocation views, policy timeline

### Portfolio Intelligence System (PIS)
- **Snapshot history** — account-level immutable partition storage
- **Canonical daily selection** — PASS-preferred with WARNING fallback
- **Governance Stage A** — PASS / WARNING / REJECT classification
- **Change detection, lineage, attribution** — full provenance tracking
- **Benchmark attribution** — BENCH-01B pipeline
- **Action attribution** — source effectiveness scoring
- **PA-006B** — drift intelligence: IMPROVING/DETERIORATING/STABLE/OSCILLATING trends, −100 to +100 momentum, TEMPORARY through STRUCTURAL persistence, top-10 attention ranking
- **Policy compliance (CPV)** — 8 CPV rules with COMPLIANT/ADVISORY/WARN/FAIL states

### Market Event Intelligence (MEI)
- **MEI Phase 1** — 54-event forward calendar, per-security sensitivity profiles, portfolio exposure analysis, recommendation context overlays
- **MEI-002** — event outcome attribution: 20 historical macro events attributed; FOMC Dec 2025 = most impactful (+4.5% 5d); Labor Market avg +2.56% 5d
- **MEI-003** — event sensitivity calibration (observed vs declared)
- **MEI-004** — event-triggered signal refresh suggestions

---

## Key Research Findings

1. **ESS overrides analyst consensus during conflict** — `ESS_BULLISH_ANALYST_MAJORITY_BEARISH` produces +2.26pp excess return. Analyst disagreement with ESS is historically associated with *better* outcomes, not worse.

2. **Conflict patterns with full analyst agreement underperform conflict patterns** — `ESS_BULLISH_ANALYST_FULL_AGREE` (+1.68pp) is outperformed by `ESS_BULLISH_ANALYST_MAJORITY_BEARISH` (+2.26pp). The "wisdom of crowds" does not apply in this universe.

3. **FOMC dominates CPI as portfolio driver** — FOMC Dec 2025: +4.5% 5d vs Inflation avg −0.33% 5d. Operators should prioritize FOMC above CPI as the primary event-driven risk.

4. **23 of 42 allocation nodes are structurally in violation** — EQUITIES.US.MID is the #1 priority (DETERIORATING + STRUCTURAL + SIGNIFICANT drift). This was invisible without PA-006B.

5. **ESS_BULLISH_ANALYST_SKEPTICAL is an ALPHA_NEUTRAL pattern** — +0.72pp excess return; 44% win rate. No material advantage for betting on ESS in this configuration; analysts' skepticism is partially valid.

---

## API Surface (Selected)

| Category | Endpoints |
|----------|-----------|
| Portfolio Analysis | `/api/portfolio/analyze`, `/api/portfolio/runs`, deployment plan |
| CRA | `/api/cra/proposal`, `/api/cra/draft`, export |
| Conflict Intelligence | `/api/conflict-review/summary|outcomes|scorecard|alpha` |
| Conflict Alpha | `/api/conflict-review/symbol/<SYM>`, `/api/conflict-review/security-alpha-*` |
| Predictive | `/api/predictive/pattern-persistence[/<sym>]`, `forward-estimate`, `event-triggers`, `funding-effectiveness`, `mei-calibration`, `scenario` |
| MEI | `/api/mei/events`, `exposures`, `recommendation-context`, `outcomes`, `event-impact`, `outcome-summary` |
| PIS | `/api/pis/summary`, `canonical`, `governance`, `allocation-drift`, `compliance`, policy suite |
| Drift Intelligence | `/api/drift/trends|priorities|chronic|momentum|intelligence-summary` |
| PAP | `/api/portfolio/analyze`, recommendations, deployment, explanations |

---

## Remaining Roadmap

### Active (v2)

| Initiative | Priority | Description |
|-----------|---------|-------------|
| **DISLOCATION-06: Confidence Calibration** | HIGH | Backtest DISLOCATION-05 forward estimates vs realized returns |
| **DISLOCATION-06: Forward Outcome Validation UI** | HIGH | Show estimated vs realized on Symbol Deep Dive |
| **Operator Sign-Off Workflow** | MEDIUM | CRA/PAP proposal acknowledgment with timestamp + audit trail |
| **MEI-005: Forward Attribution Auto-Run** | MEDIUM | Auto-append to `event_outcomes.json` as calendar events pass |
| **ESS Archive Expansion** | MEDIUM | Expand from 15 to 50+ dates for statistical depth |
| **SCENARIO-02: Alignment Score Estimation** | MEDIUM | Approximate alignment score delta from scenario changes |

### Research Track

| Initiative | Description |
|-----------|-------------|
| Cross-symbol pattern persistence | Chronic conflict registry per symbol |
| Predictive ranking confidence | Confidence intervals on CW-DAS scores |
| MEI-006: Event co-occurrence | Compound event effect analysis |
| PIS Stage B | Formal canonical selection beyond PASS-preferred |

---

## GitHub Issue Status

| Issue | Title | Status |
|-------|-------|--------|
| #52 | ESS-INTAKE-ORDERING-01 | CLOSED |
| #38 | PA-006 | CLOSED |
| #17 | ISSUE-12D | CLOSED |
| #32 | AI-004 | CLOSED |

### Retrospective Issues (Created + Closed)

CRA-EXPLAIN-02 · DISLOCATION-02 · DISLOCATION-03 · MEI-001 · MEI-002 · DISLOCATION-04 · DISLOCATION-05 · MEI-003 · MEI-004 · SCENARIO-01 · RESEARCH-01

### New Open Issues

- EPIC: Predictive Intelligence v2
- DISLOCATION-06: Confidence Calibration (HIGH priority, OPEN)
- Operator Sign-Off Workflow
- MEI-005: Forward Attribution Automation
- ESS Archive Expansion

---

*Security Intelligence Hub v1 — Feature Complete 2026-06-16 · Tag: `sih-v1-feature-complete`*
