# AI-003 — Allocation Philosophy Explainability Gap

**Issue ID:** AI-003  
**Area:** Allocation Intelligence  
**Priority:** HIGH  
**Complexity:** M  
**Status:** Open

---

## Title

Allocation Philosophy Explainability Gap — Target Percentages Displayed Without Rationale

---

## Problem Statement

The Allocation Intelligence panel displays allocation targets (e.g., US MID = 20%, US SMALL = 14%, US MEGA = 18%) with no narrative explaining why those targets were chosen. An operator, analyst, or investor reviewing the portfolio has no way to understand the investment philosophy driving these allocations.

---

## Current Behavior

Allocation targets are displayed as numbers only:
- US MEGA = 18%
- US MID = 20%
- US SMALL = 14%
- INTERNATIONAL = (target)
- CASH = 7%

No rationale, narrative, or philosophy statement accompanies these figures.

---

## Expected Behavior

The Allocation Intelligence panel should include an allocation philosophy narrative that explains the investment logic behind major target choices. The narrative should address:

1. **Small/mid overweight rationale** — why 20%/14% vs a typical broad-market weight
2. **Mega cap reduction** — why 18% vs the market-weight ~30–35%
3. **International weighting** — philosophy behind international allocation target
4. **Cash philosophy** — why 7% target, what it represents (operational buffer, dry powder, mandate)
5. **Replay influence** — whether historical replay evidence informs allocation targets
6. **Mandate influence** — which mandate archetype drives the target set and why

---

## Evidence

- Allocation Intelligence panel showing numeric targets without narrative context
- Concentrated Alpha archetype YAML defines targets without embedded philosophy text
- PAR-20260529 analysis runs

---

## Acceptance Criteria

- [ ] Allocation Intelligence panel includes a collapsible or inline allocation philosophy section
- [ ] Philosophy narrative addresses at minimum: small/mid emphasis, mega positioning, international weighting, cash target, mandate driver
- [ ] Each major allocation node target links to or references supporting rationale
- [ ] The philosophy section is sourced from a configurable governance artifact (not hardcoded in UI)

---

## Dependencies

- Archetype YAML (configuration source)
- Allocation Intelligence panel
- Mandate governance documentation

---

## Notes

The philosophy content itself may need to be created as a governance artifact (e.g., `allocation_philosophy.yaml` per archetype) before the UI can surface it. This is both a content and a display requirement.
