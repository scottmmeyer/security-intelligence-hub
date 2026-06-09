# PA-004 Implementation Report

Repository: security-intelligence-hub  
Date: 2026-06-09  
Issue: PA-004 Policy Consistency Failure Across Advisory Surfaces (#36)  
Status: RESOLVED

## Implementation Summary

PA-004 was fixed by adding policy gates to Cat 3 (Allocation Reduction) and Cat 4 (Funding Sources) inside `_computePortfolioActions()` in `ui/portfolio_alignment/app.js`. No backend changes were required.

## Files Changed

| File | Change |
|---|---|
| ui/portfolio_alignment/app.js | Policy gates added to Cat 3 and Cat 4 in _computePortfolioActions() |

## Cat 3 (Allocation Reduction) Fix

Before: All symbols from REDUCE_OVERWEIGHT `affected_symbols` were included without policy check.

After:
- `DO_NOT_SELL` symbols → moved to `cat5` (Policy-Suppressed Actions) with `effective_action: MONITOR_ONLY`
- `SELL_LAST` symbols → included with `execution_state: DEFERRED_BY_POLICY`, `effective_action: REDUCE_SELL_LAST`, tail-ranked (priority `LOW`)
- All others → `EXECUTABLE`, `effective_action: REDUCE`, sorted by absolute drift descending

Policy check uses `ov.policy_type` directly (not `ov.execution_state`) because `ov.execution_state` reflects the overlay's `opportunity_flag` context, which may not be a sell flag even when the holding is a reduction candidate.

## Cat 4 (Funding Sources) Fix

Before: All overlays passing size/score/tier filters could appear as funding sources regardless of policy.

After:
- `DO_NOT_SELL` symbols → excluded entirely (`continue`)
- `SELL_LAST` symbols → included but assigned `priority: LAST_RESORT` and always sorted last

## Invariants Confirmed

- No scoring changes
- No CW-DAS changes
- No ESS changes
- No recommendation generation changes
- No new data fields required
- `policy_type` field is already present on overlay objects

## Test Results

Full regression suite: **1161 passed, 1 skipped, 0 failed** (unchanged)
