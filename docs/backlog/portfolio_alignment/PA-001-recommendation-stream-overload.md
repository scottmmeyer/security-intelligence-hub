# PA-001 — Recommendation Stream Overload

**Issue ID:** PA-001  
**Area:** Portfolio Alignment  
**Priority:** CRITICAL  
**Complexity:** M  
**Status:** Open  
**Related:** PRA-IMPL-03, PRA-IMPL-04

---

## Title

Recommendation Stream Overload — 34 Heterogeneous Items Presented in a Single Undifferentiated Stream

---

## Problem Statement

The Portfolio Alignment panel reports "34 Recommendations" in a single mixed stream containing deployment actions, allocation observations, mandate blocks, retain narratives, and explainability cards. Actionable decisions are buried alongside informational content, creating operator cognitive overload and misrepresenting the true decision workload.

---

## Current Behavior

All 34 items appear in one stream with equal visual weight. The stream includes:
- Actionable allocation decisions (REDUCE, INCREASE)
- Policy-blocked items (DO_NOT_SELL)
- Narrative synthesis cards (PORTFOLIO_CONSTRUCTION_NARRATIVE)
- Retain signals (STRATEGIC_RETAIN_SIGNAL)
- Explainability cards (CONVICTION_EXPLAINABILITY_CARD)
- Replay alignment context
- Mandate blocks (INTENTIONAL_UNDERWEIGHT demotions)

---

## Expected Behavior

Recommendations should be separated into distinct lanes or sections:

1. **Actions** — executable portfolio decisions (REDUCE_OVERWEIGHT, INCREASE_UNDERWEIGHT, STRATEGIC_TRIM_CANDIDATE)
2. **Blocked Actions** — policy-suppressed items (BLOCKED_BY_POLICY, DEFERRED_BY_POLICY)
3. **Observations** — allocation drift context, mandate interpretations
4. **Retain Signals** — STRATEGIC_RETAIN_SIGNAL, STRATEGIC_RETAIN_NARRATIVE
5. **Explainability** — conviction cards, replay context (collapsed by default)

The headline count "34 Recommendations" should be replaced with typed counts per lane.

---

## Evidence

- Current PAR output: 33–34 cards, 6 true ACTION cards, ~18 EXPLAINABILITY cards, ~5 NARRATIVE cards, ~3 OBSERVATION cards
- PRA-IMPL-01 card_type field is now available on all recommendations to drive lane routing
- Operator feedback: "I cannot find the action items"

---

## Acceptance Criteria

- [ ] Recommendation cards are routed to lanes by `card_type` field (ACTION, OBSERVATION, NARRATIVE, EXPLAINABILITY)
- [ ] Headline count shows typed breakdown: "6 Actions | 3 Observations | 18 Explainability"
- [ ] "Total Recommendations" label is replaced or supplemented with category counts
- [ ] ACTION lane is visually primary; other lanes are secondary or collapsible
- [ ] Existing functionality (drill-down, click-through, execution) is preserved

---

## Dependencies

- PRA-IMPL-01 (card_type field — COMPLETE)
- PRA-IMPL-02 (execution_state normalization — COMPLETE)
- PRA-IMPL-03 (implementation issue for this feature — OPEN)

---

## Notes

The `card_type` field required to drive lane routing was delivered in PRA-IMPL-01. This issue is the UI implementation of the lane separation defined in PRA-IMPL-03 scope.
