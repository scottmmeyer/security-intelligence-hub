# PA-002 — Recommendation Ordering Defect

**Issue ID:** PA-002  
**Area:** Portfolio Alignment  
**Priority:** HIGH  
**Complexity:** S  
**Status:** Open  
**Related:** PA-001, PRA-IMPL-03

---

## Title

Recommendation Ordering Defect — Actionable Items Interleaved With Informational Content

---

## Problem Statement

The recommendation stream presents actionable items (REDUCE, INCREASE) interleaved with retain narratives and explainability cards. An operator scanning the list must read through narrative and explainability content to find the next executable action. The ordering does not prioritize actionability.

---

## Current Behavior

Observed ordering pattern:
1. Portfolio construction narrative (informational)
2. Build US Large (actionable — action)
3. Build Extended Mega (actionable — action)
4. Reduce International (actionable — action)
5. MSFT Retain (narrative — not actionable)
6. ARW Retain (narrative — not actionable)
7. MU Explainability (explainability)
8. VRT Explainability (explainability)
9. CVE Explainability (explainability)
10. ...more explainability cards

Actionable items at positions 2–4 are immediately followed by non-actionable content, then more actionable content appears further down.

---

## Expected Behavior

Ordering within the recommendation stream (or within each lane post-PA-001) must prioritize actionability:

**Suggested order:**
1. Actions (sorted by priority/severity)
2. Blocked/Deferred Actions (explicitly flagged as policy-constrained)
3. Allocation Observations
4. Retain Signals
5. Explainability (collapsed by default)

---

## Evidence

- Observed in Portfolio Alignment panel, PAR-20260529-B9E3E65F
- Recommendation priority fields are already populated and available for sorting

---

## Acceptance Criteria

- [ ] All ACTION card_type items appear before OBSERVATION and NARRATIVE items in the default view
- [ ] Within ACTION items, ordering follows recommendation priority (1 = highest urgency)
- [ ] EXPLAINABILITY items are either last in order or collapsed by default
- [ ] Ordering does not require a manual sort — default ordering reflects actionability

---

## Dependencies

- PA-001 (lane separation may supersede ordering fix by isolating content types)
- PRA-IMPL-01 (card_type field available — COMPLETE)

---

## Complexity Notes

If PA-001 is implemented first, this fix may be partially addressed by lane separation. An independent ordering fix for the current single-stream view is S complexity (CSS/JS sort order change).
