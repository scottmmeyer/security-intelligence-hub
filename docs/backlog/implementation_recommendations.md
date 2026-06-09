# SIH Backlog Implementation Recommendations

Repository: security-intelligence-hub  
Created: 2026-06-09

---

## Executive Backlog Summary

The June 2026 operator review identified 10 actionable backlog items across two panels (Allocation Intelligence and Portfolio Alignment). Three items are trust-critical, five are high-usability, and two are medium-priority governance enhancements.

Three of the ten items have partial or full implementation infrastructure already in place:
- PRA-IMPL-01 (complete): enables card_type-based routing for PA-001, PA-003
- PRA-IMPL-02 (complete): normalizes policy execution state for PA-004 (Portfolio Alignment recs)
- PRA-IMPL-03/04 (open GitHub issues): directly implement PA-001, PA-002, PA-003, PA-005

The highest-urgency items that require new investigation work are AI-001 (policy contradiction) and PA-004 (cross-surface policy failure in PAP).

---

## Dependency Map

```
PRA-IMPL-01 (COMPLETE)
    └── PA-001 (lane separation — enabled)
    └── PA-003 (typed counts — enabled)

PRA-IMPL-02 (COMPLETE)
    └── PA-004 (portfolio alignment recs — fixed; PAP surface still open)

PRA-IMPL-03 (OPEN #26)
    └── PA-001 (implements)
    └── PA-002 (implements)
    └── PA-003 (implements)

PRA-IMPL-04 (OPEN #27)
    └── PA-005 (implements)
    └── requires PRA-IMPL-03 first

AI-001 (investigation required)
    └── no code prerequisites; requires governance decision

PA-004 (investigation + code)
    └── PRA-IMPL-02 (complete for Portfolio Alignment)
    └── PAP policy normalization (new work required)

AI-002 (display fix)
    └── no prerequisites

AI-003 (content + display)
    └── requires governance content creation first

AI-004 (versioning)
    └── requires archetype YAML versioning

PA-006 (new capability)
    └── requires drift history aggregator (new infrastructure)
```

---

## Recommended Implementation Sequence

### Phase A — Immediate (Trust Restoration)

**Goal:** Eliminate logically contradictory outputs before next investor or bank review.

1. **AI-001 Investigation** — Governance team determines whether micro-cap ceiling is hard constraint or advisory. Implement single-source-of-truth fix based on decision.
2. **PA-004 PAP Normalization** — Extend PRA-IMPL-02's `apply_policy_to_recommendations()` approach to the PAP queue so TSLA does not appear as TRIM while DO_NOT_SELL is active.

Estimated effort: 1 week combined.

---

### Phase B — PRA Program Completion (Usability Lift)

**Goal:** Implement the four remaining PRA implementation issues that directly address PA-001 through PA-005.

3. **PRA-IMPL-03** — Surface lane separation and typed counts (PA-001, PA-002, PA-003)
4. **PRA-IMPL-04** — Conviction anchors section extraction (PA-005)

Estimated effort: 2 weeks.

---

### Phase C — Display and Labeling Fixes (Quick Wins)

**Goal:** Address S-complexity display issues that require no new infrastructure.

5. **AI-002** — Add clear labels to all allocation tables (S complexity, 1–2 sessions)

Estimated effort: 2 days.

---

### Phase D — Governance Enrichment (Planned)

**Goal:** Improve explainability depth for operators, advisors, and investors.

6. **AI-003** — Create allocation philosophy content; surface in Allocation Intelligence panel
7. **AI-004** — Add policy version change log and diff visibility

Estimated effort: 1–2 weeks each (content creation is the bottleneck for AI-003).

---

### Phase E — Capability Expansion (Future)

8. **PA-006** — Allocation drift trend visibility (requires historical aggregation infrastructure)

Estimated effort: L (2–4 weeks including infrastructure).

---

## Critical-Path Analysis

```
TRUST CRITICAL PATH
AI-001 → governance decision (no code blocker)
PA-004 → extend PRA-IMPL-02 to PAP (code ready as template)

USABILITY CRITICAL PATH
PRA-IMPL-03 (PA-001 / PA-002 / PA-003)
    → PRA-IMPL-04 (PA-005)

ENHANCEMENT PATH
AI-002 (independent, no blocker)
AI-003 → content first, then UI
AI-004 → YAML versioning prerequisite
PA-006 → new infrastructure, no current dependency
```

The trust-critical path (AI-001, PA-004) can be worked in parallel with the PRA usability path (PRA-IMPL-03, PRA-IMPL-04), as they share no implementation dependencies.

---

## Suggested Phase Grouping

| Phase | Issues | Theme | Est. Duration |
|---|---|---|---|
| Phase A | AI-001, PA-004 | Trust restoration | 1 week |
| Phase B | PRA-IMPL-03/04 → PA-001, 002, 003, 005 | Recommendation surface rationalization | 2 weeks |
| Phase C | AI-002 | Quick display wins | 2 days |
| Phase D | AI-003, AI-004 | Governance enrichment | 2–4 weeks |
| Phase E | PA-006 | Capability expansion | 2–4 weeks |

---

## Investor / Bank Readiness Note

Before a bank partnership review or investor demo, Phase A (AI-001, PA-004) and Phase B (PRA-IMPL-03/04) should be complete. The current state — where TSLA receives TRIM guidance from PAP while DO_NOT_SELL is active, and where 34 undifferentiated cards represent "recommendations" — undermines the demonstration of SIH as a governance-quality advisory system.
