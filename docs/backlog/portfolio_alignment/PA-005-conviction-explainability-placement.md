# PA-005 — Conviction Explainability Placement Problem

**Issue ID:** PA-005  
**Area:** Portfolio Alignment  
**Priority:** HIGH  
**Complexity:** M  
**Status:** Open  
**Related:** PA-001, PRA-IMPL-04

---

## Title

Conviction Explainability Placement Problem — Explainability Cards Dominate the Recommendation Stream

---

## Problem Statement

A large number of CONVICTION_EXPLAINABILITY_CARD items appear within the main recommendation stream alongside actionable portfolio decisions. These cards (e.g., MU Explainability, VRT Explainability, CVE Explainability) are valuable conviction intelligence but are not recommendations. Their presence in the action stream dilutes actionable signal and inflates the recommendation count.

---

## Current Behavior

Approximately 18–20 CONVICTION_EXPLAINABILITY_CARD items appear in the recommendation stream alongside:
- REDUCE_OVERWEIGHT actions
- INCREASE_UNDERWEIGHT actions
- STRATEGIC_RETAIN_SIGNAL observations

Examples visible in current run:
- MU: High Conviction Retain | tier=CORE_CONVICTION_LEADER
- VRT: High Conviction Retain | tier=CORE_CONVICTION_LEADER
- CVE: High Conviction Retain | tier=CORE_CONVICTION_LEADER
- ARW: High Conviction Retain | tier=HIGH_CONVICTION_ANCHOR
- CIEN: Tactical Growth | tier=TACTICAL_GROWTH_CANDIDATE
- (+ 12–15 more)

---

## Expected Behavior

Explainability cards belong in a dedicated Conviction Library or Explainability Panel, not in the primary recommendation stream.

**Proposed destinations:**
1. **Conviction Library** — a separate panel or page listing all conviction cards, sorted by tier and composite score
2. **Top Conviction Holdings section** — collapsed by default, accessible on demand
3. **Explainability drawer** — opened from an individual holding card, not from the recommendation list

The primary recommendation stream should contain only ACTION, OBSERVATION, and NARRATIVE cards.

---

## Evidence

- Portfolio Alignment panel: current PAR includes 18+ CONVICTION_EXPLAINABILITY_CARD items in recommendation stream
- card_type = EXPLAINABILITY is already set on these cards (PRA-IMPL-01 — COMPLETE)
- These cards are the primary driver of the "34 Recommendations" count inflation

---

## Acceptance Criteria

- [ ] CONVICTION_EXPLAINABILITY_CARD items do not appear in the primary recommendation action stream
- [ ] Explainability cards are accessible via a dedicated panel, drawer, or page
- [ ] Conviction Anchors section (or equivalent) renders these cards with UCF tier context
- [ ] The action stream's recommendation count no longer includes explainability cards
- [ ] No conviction intelligence is lost — all cards remain accessible

---

## Dependencies

- PRA-IMPL-01 (card_type = EXPLAINABILITY already set — COMPLETE)
- PA-001 (lane separation framework)
- PRA-IMPL-04 (Conviction Anchors Section Extraction — open implementation issue)

---

## Notes

PRA-IMPL-04 is the corresponding implementation issue. This backlog item documents the operator-facing problem statement and acceptance criteria.
