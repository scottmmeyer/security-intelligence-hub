# PA-004 — Policy Consistency Failure Across Advisory Surfaces

**Issue ID:** PA-004  
**Area:** Portfolio Alignment  
**Priority:** CRITICAL  
**Complexity:** M  
**Status:** Open  
**Related:** PRA-IMPL-02, PA-001

---

## Title

Policy Consistency Failure Across Advisory Surfaces — TSLA Receives Conflicting Guidance from CRA and PAP

---

## Problem Statement

The Capital Rotation Advisor displays TSLA as DO_NOT_SELL / MONITOR_ONLY. The Portfolio Action Pipeline simultaneously displays TSLA as TRIM. The same security receives materially conflicting advisory guidance from two surfaces in the same session. An operator relying on either surface alone will receive an incomplete or incorrect picture of the policy constraint.

---

## Current Behavior

- **Capital Rotation Advisor (CRA):** TSLA — DO_NOT_SELL — MONITOR_ONLY
- **Portfolio Action Pipeline (PAP):** TSLA — TRIM (no policy annotation visible)
- **Result:** Operator sees "trim TSLA" in one surface and "do not sell TSLA" in another

---

## Expected Behavior

All advisory surfaces must present consistent policy execution state for the same security in the same session.

If TSLA is DO_NOT_SELL:
- CRA must show: BLOCKED_BY_POLICY / MONITOR_ONLY
- PAP must show: BLOCKED_BY_POLICY / MONITOR_ONLY (or exclude from sell candidates)
- Portfolio Alignment recommendation: BLOCKED_BY_POLICY (PRA-IMPL-02 — COMPLETE for this surface)

The intelligence signal (TRIM) may remain visible on all surfaces for transparency, but effective execution state must be BLOCKED everywhere.

---

## Evidence

- CRA proposal showing TSLA blocked
- PAP queue showing TSLA as trim candidate without policy annotation
- PRA-IMPL-02 certified: recommendation JSON now carries BLOCKED_BY_POLICY for TSLA in REDUCE_OVERWEIGHT recs
- Observed in Portfolio Alignment panel session, June 2026

---

## Required Investigation

1. Determine how the PAP queue is generated — does it consume the policy registry?
2. Determine whether PAP uses `compute_execution_state()` or ignores the policy registry
3. Determine whether the CRA proposal generation reads the same policy registry
4. Document the expected governance rule ordering for advisory surfaces

---

## Acceptance Criteria

- [ ] All advisory surfaces (CRA, PAP, Portfolio Alignment recs) produce the same execution_state for TSLA (DO_NOT_SELL)
- [ ] TSLA never appears as an executable TRIM/SELL candidate on any advisory surface while DO_NOT_SELL is active
- [ ] Intelligence signal (TRIM) may still be displayed for transparency, alongside the policy block annotation
- [ ] Cross-surface consistency test added to regression suite

---

## Dependencies

- PRA-IMPL-02 (policy normalization for Portfolio Alignment recs — COMPLETE)
- PAP implementation (source of current TRIM display without policy annotation)
- CRA proposal builder
- operator_policy.py (compute_execution_state is available and correct)

---

## Notes

This issue may require a separate investigation phase before implementation. The root cause is likely that PAP and/or CRA do not call `apply_policy_to_recommendations()` or equivalent. PRA-IMPL-02's approach should be extended to cover these surfaces.
