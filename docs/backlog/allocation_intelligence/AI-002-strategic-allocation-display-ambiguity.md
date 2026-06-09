# AI-002 — Strategic Allocation Display Ambiguity

**Issue ID:** AI-002  
**Area:** Allocation Intelligence  
**Priority:** HIGH  
**Complexity:** S  
**Status:** Open

---

## Title

Strategic Allocation Display Ambiguity — Multiple Unexplained Allocation Sets

---

## Problem Statement

The Allocation Intelligence page displays two materially different allocation breakdowns with no labels explaining what each represents. An operator viewing these tables cannot determine which is the baseline, strategic target, tactical allocation, or current actual allocation.

---

## Current Behavior

The page shows two allocation tables sequentially:

**Table 1:**
- Equities 88%, Cash 7%, FI 2%, Digital 1%, Commodities 2%

**Table 2 (later on same page):**
- Equities 70%, FI 20%, Digital 4%, Commodities 4%, Cash 2%

No header, label, or explanation distinguishes these tables.

---

## Expected Behavior

Every allocation table on the Allocation Intelligence page must carry a clear label identifying:

1. **What it represents** — e.g., Strategic Target, Current Actual, Mandate Target, Tactical Overlay
2. **Source** — e.g., archetype YAML, current portfolio, operator-defined mandate
3. **As-of date** — when applicable

The operator must be able to answer: "What is my actual allocation today vs my strategic target?"

---

## Evidence

- Allocation Intelligence panel displaying two allocation tables without labeling
- Portfolio analysis run: PAR-20260529-B9E3E65F

---

## Acceptance Criteria

- [ ] Every allocation table on the Allocation Intelligence page has a clear, unambiguous label
- [ ] Labels identify the source and purpose of each allocation model
- [ ] No two allocation tables can appear on the same view without clear differentiation
- [ ] Operator can identify within 5 seconds which table is current vs target

---

## Dependencies

- Allocation Intelligence UI component
- Archetype YAML definitions
- Alliance result data model

---

## Complexity Notes

This is a display/labeling fix. The underlying data is correct; the presentation layer needs header labels and possibly a legend.
