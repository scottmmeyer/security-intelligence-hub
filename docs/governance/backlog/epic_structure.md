# Epic Structure — Phase 8.0B.1D

## Overview

Epics group related issues into strategic initiative tracks. Each epic has a clear objective, a set of child phases, and a success definition.

---

## EPIC-01: FMP Integration

**Objective:** Make Financial Modeling Prep fundamental data fully available and progressively integrated across SIH signals, scoring, and display.

**Status:** Active — Phase 8.0B.1B.5 complete; 8.0B.1C next.

| Phase | Title | Status |
|-------|-------|--------|
| 8.0B.0 | FMP Capability Audit | ✅ Complete |
| 8.0B.0A | FMP Integration Philosophy | ✅ Complete |
| 8.0B.1A | FMP Signal Intake Pipeline | ✅ Complete |
| 8.0B.1A.1 | FMP API Corrections | ✅ Complete |
| 8.0B.1B | FMP Analytical Universe Enrichment | ✅ Complete |
| 8.0B.1B.5 | FMP Diagnostic Overlay | ✅ Complete |
| 8.0B.1C | FMP Score Integration Assessment | 🔲 Authorized |
| 8.0B.2 | Dislocation Framework | 🔲 Authorized post-1C |
| 8.0B.3+ | TBD — contingent on 8.0B.1C findings | 🔲 Deferred |

**Success Definition:** FMP fundamental data influences at least one scored component in CW-DAS or UCF, validated against historical queue quality.

---

## EPIC-02: Capital Rotation Advisor (CRA)

**Objective:** Provide an operator-facing capital rotation recommendation engine that identifies optimal sources and targets for portfolio rebalancing.

**Status:** Active — Phase 23.6B.5 complete; 23.6C pending.

| Phase | Title | Status |
|-------|-------|--------|
| 23.6A | CRA Design & Architecture | ✅ Complete |
| 23.6B.0 | CRA Backend Implementation | ✅ Complete |
| 23.6B.1 | CRA UI Implementation | ✅ Complete |
| 23.6B.2 | Tier-Aware Allocation | ✅ Complete |
| 23.6B.3 | CRA Forensics | ✅ Complete |
| 23.6B.4 | Trust Remediation | ✅ Complete |
| 23.6B.5 | FIS Strategic Exit Retirement | ✅ Complete |
| 23.6C | Draft Persistence + CSV Export | 🔲 Authorized |
| 23.6D | TBD post-23.6C | 🔲 Deferred |

**Success Definition:** Operator can save, export, and share a CRA proposal with a single action.

---

## EPIC-03: Portfolio Action Pipeline (PAP)

**Objective:** Provide a complete operator workflow from signal ingestion through portfolio analysis, deployment queue, and action tracking.

**Status:** Active — Core pipeline complete; incremental extensions ongoing.

| Phase | Title | Status |
|-------|-------|--------|
| 23.0A | Tax Position Panel | ✅ Complete |
| 23.1 | Operator Policy Registry | ✅ Complete |
| 23.2 | Policy Annotations | ✅ Complete |
| 23.3 | Deployment Planner | ✅ Complete |
| 23.4 | NBA/OW-node Filtering | ✅ Complete |
| 23.5 | Allocation Node Tracking | ✅ Complete |
| 23.0B | Portfolio Action Pipeline v2 | 🔲 Future planning |

**Success Definition:** Full operator workflow from CSV upload to deployment action is traceable, auditable, and policy-aware.

---

## EPIC-04: Company Context Track

**Objective:** Provide rich, operator-facing company context (identity, business description, market context, thesis support) directly in the deployment queue card.

**Status:** Complete for Phase 1.

| Phase | Title | Status |
|-------|-------|--------|
| 8.0B.X | Company Context Enrichment | ✅ Complete |
| 8.0B.X.1 | Company Business Snapshot | ✅ Complete |
| 8.0B.X.2 | Operator Optimization (What They Do / Why It Matters / Tags) | ✅ Complete |
| 8.0B.X.3 | Why SIH Likes It (Recommendation Rationale) | ✅ Complete |
| 8.0B.X.4 | CW-DAS Allocation Drift Audit | ✅ Complete |
| 8.0B.X.5 | Theme Concentration Analysis | 🔲 Needs design |
| 8.0B.X.6 | AI-Assisted Company Summary Refinement | 🔲 Low priority |

**Success Definition:** An operator reviewing any deployment queue candidate can fully understand the company, thesis, and SIH rationale without leaving the card.

---

## EPIC-05: Signal Intelligence Evolution

**Objective:** Evolve the composite signal model to incorporate additional evidence sources and improve conviction differentiation.

**Status:** Early stage — research-driven.

| Phase | Title | Status |
|-------|-------|--------|
| 7.5 | UCF / CW-DAS baseline | ✅ Complete |
| 8.0B.1C | FMP Score Integration Assessment | 🔲 Authorized |
| TBD | Graduated Drift Penalty | 🔲 Needs design |
| TBD | Analyst Consensus Integration | 🔲 Needs design |
| 8.0D | CW-DAS FMS Integration (requires empirical validation) | 🔲 Blocked on RES-01 |

**Success Definition:** Composite score more accurately reflects true investment opportunity quality, validated against deployment outcomes.

---

## EPIC-06: Governance & Tooling

**Objective:** Establish durable engineering practices for SIH development: backlog management, test standards, CI, deployment, and documentation.

**Status:** Active — this epic.

| Phase | Title | Status |
|-------|-------|--------|
| 8.0B.1D | GitHub Backlog Establishment | ✅ In progress |
| TBD | GitHub Actions CI (automated test run) | 🔲 Needs design |
| TBD | Signal freshness monitoring | 🔲 Needs design |
| TBD | Technical debt cleanup sprint | 🔲 Ready |

**Success Definition:** All SIH development work is tracked in GitHub Issues with acceptance criteria. No untracked deferred work.

---

## Epic Priority Matrix

| Epic | Operator Value | Strategic Importance | Effort | Priority |
|------|---------------|---------------------|--------|----------|
| EPIC-01: FMP Integration | High | Very High | High | 1 |
| EPIC-02: CRA | High | High | Medium | 2 |
| EPIC-06: Governance | Medium | Very High | Low | 3 |
| EPIC-04: Company Context | Medium | Medium | Low | 4 |
| EPIC-05: Signal Evolution | Very High | Very High | Very High | 5 |
| EPIC-03: PAP | Low (incremental) | High | Medium | 6 |
