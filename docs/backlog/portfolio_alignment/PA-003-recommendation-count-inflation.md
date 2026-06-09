# PA-003 — Recommendation Count Inflation

**Issue ID:** PA-003  
**Area:** Portfolio Alignment  
**Priority:** HIGH  
**Complexity:** S  
**Status:** Open  
**Related:** PA-001, PRA-IMPL-03

---

## Title

Recommendation Count Inflation — Headline Count Misrepresents Actual Operator Workload

---

## Problem Statement

The system reports "34 Recommendations" as its primary KPI. The majority of these are informational explainability cards and retain narratives, not actionable decisions. An operator relying on this number to assess their decision workload is systematically misled.

---

## Current Behavior

- Headline count: 34 (or similar)
- Actual true-action cards: approximately 6
- Explainability/narrative/observation cards: approximately 28
- No distinction in the count or display

---

## Expected Behavior

The headline count must reflect actionable workload. The display should provide:

- **Actions: 6** (primary KPI — reflects true decision workload)
- **Observations: 3** (secondary)
- **Retain Signals: 2** (secondary)
- **Explainability: 22** (collapsed by default, not in primary count)

"Total Cards: 34" may remain as a secondary disclosure, but must not be the primary headline.

---

## Evidence

- Portfolio Alignment panel: headline "34 Recommendations"
- PRA-IMPL-01 card_type field now available on all cards to enable typed counting
- Rationalized decomposition: 6 ACTION, 3 OBSERVATION, 5 NARRATIVE, 18+ EXPLAINABILITY

---

## Acceptance Criteria

- [ ] Primary headline displays action count only (e.g., "6 Actions")
- [ ] Secondary summary shows per-type counts
- [ ] "Recommendations" label used only for ACTION-class cards
- [ ] Total card count is accessible but not the primary metric
- [ ] Counts update dynamically based on current PAR

---

## Dependencies

- PRA-IMPL-01 (card_type field — COMPLETE)
- PA-001 (lane separation)
- PRA-IMPL-03 (implementation track)

---

## Complexity Notes

S complexity: Requires reading `card_type` from recommendation objects and calculating per-type totals. The data is already present via PRA-IMPL-01.
