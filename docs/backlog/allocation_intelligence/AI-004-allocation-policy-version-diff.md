# AI-004 — Allocation Policy Version Diff Visibility

**Issue ID:** AI-004  
**Area:** Allocation Intelligence  
**Priority:** MEDIUM  
**Complexity:** M  
**Status:** Open

---

## Title

Allocation Policy Version Diff Visibility — Policy Changes Have No Impact Explanation

---

## Problem Statement

The system tracks a policy version number but provides no visibility into what changed between versions, why it changed, or what impact the change has on current portfolio alignment. An operator updating from Policy v1 to v2 cannot determine whether recommendations changed because of portfolio drift or because the policy targets shifted.

---

## Current Behavior

- A policy version identifier is stored and displayed
- No change log, diff view, or impact summary is provided
- Operators cannot distinguish recommendation changes caused by policy updates vs portfolio value changes

---

## Expected Behavior

When a policy version changes, the system should surface:

1. **What changed** — specific node targets that were modified (e.g., "US Mega: 25% → 18%")
2. **Why it changed** — governance rationale or operator note attached to version change
3. **Impact on current alignment** — how the drift percentages and recommendation set would differ under old vs new policy

---

## Evidence

- Policy version field present in archetype YAML and run metadata
- No version history or diff capability implemented
- Example change that would benefit from visibility: US Mega target shift from 25% to 18% (historical), US Mid shift from 15% to 20%

---

## Acceptance Criteria

- [ ] Policy versions are stored with a change log entry (what changed, when, rationale)
- [ ] Allocation Intelligence panel shows a "Policy Change Summary" when the current run's policy version differs from the prior run
- [ ] Change summary shows: node key, old target, new target
- [ ] Operator can optionally view alignment calculated under prior policy version for comparison
- [ ] Policy version change does not silently alter recommendation outputs without surfacing context

---

## Dependencies

- Archetype YAML versioning
- Run metadata (stores policy version per PAR)
- Allocation Intelligence panel

---

## Complexity Notes

Phase 1 (M): Store change log and display diff in UI.  
Phase 2 (L, future): Side-by-side alignment comparison under old vs new policy.
