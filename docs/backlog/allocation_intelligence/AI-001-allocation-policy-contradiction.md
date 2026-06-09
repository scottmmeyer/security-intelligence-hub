# AI-001 — Allocation Policy vs Actual Allocation Contradiction

**Issue ID:** AI-001  
**Area:** Allocation Intelligence  
**Priority:** CRITICAL  
**Complexity:** M  
**Status:** Open

---

## Title

Allocation Policy vs Actual Allocation Contradiction — Policy Compliance Status Logically Inconsistent

---

## Problem Statement

The Allocation Intelligence panel simultaneously displays contradictory policy compliance signals:

The UI shows **Micro Cap combined: 6.50% / 5% ceiling — OVER**, indicating a policy ceiling is violated. At the same time, it reports **policy_bounds: PASS** and **concentration_ceilings: PASS**, indicating full compliance.

These two statements cannot both be true. This creates a governance trust failure: the operator cannot determine whether the portfolio is compliant or not.

---

## Current Behavior

- Max Micro Cap ceiling displayed as 5%
- Actual allocation: US.MICRO = 6.0%, INTERNATIONAL.MICRO = 0.5%, combined = 6.5%
- UI reports "Micro Cap combined 6.50% / 5% ceiling OVER"
- Reconciliation reports `policy_bounds: PASS` and `concentration_ceilings: PASS`

---

## Expected Behavior

All policy compliance indicators must be internally consistent. If 6.5% > 5% ceiling:

- Either the ceiling check must FAIL in the reconciliation report
- Or the ceiling must not apply in this context and the UI must not display a violation

One of the following must be true and must be clearly communicated:

A) The ceiling is informational/advisory only — the UI must not use FAIL-style language  
B) The ceiling is a hard constraint — reconciliation must report FAIL  
C) The validator uses a different calculation than the display — must be documented and reconciled

---

## Evidence

- Allocation Intelligence panel: "Micro Cap combined 6.50% / 5% ceiling OVER"
- Reconciliation report: `policy_bounds: PASS`, `concentration_ceilings: PASS`
- Portfolio: PAR-20260529-B9E3E65F (representative run)

---

## Required Investigation

1. Determine the definition of the 5% ceiling — is it hard constraint or advisory?
2. Determine which allocation calculation the ceiling uses (direct exposure, effective exposure, or combined including ETF decomposition)
3. Determine why `concentration_ceilings` validation passes when display shows OVER
4. Produce a single-source-of-truth definition of policy ceiling checks

---

## Acceptance Criteria

- [ ] A single source of truth exists defining what constitutes a policy ceiling violation
- [ ] Policy compliance status (PASS/FAIL/ADVISORY) is unambiguous
- [ ] PASS/FAIL behavior in reconciliation is consistent with violation indicators in the UI
- [ ] If ceiling is advisory-only, the UI must use different visual treatment than a hard violation
- [ ] The governance decision (hard constraint vs advisory) is documented

---

## Dependencies

- Reconciliation engine (`reconciliation.py`)
- Allocation policy configuration (archetype YAML targets)
- Concentration ceiling validator

---

## Notes

This issue may reveal a design gap: the concentration ceiling check may only evaluate individual node ceilings, not combined cross-node aggregates (e.g., US.MICRO + INTERNATIONAL.MICRO). If so, the UI's combined ceiling calculation is using logic that the reconciliation validator does not replicate.
