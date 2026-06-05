# Phase 23.0C — C1: Field Mapping Repair

**Status**: COMPLETE  
**Date**: 2026-06-03  
**PAR Run**: PAR-20260603-B66B00E3

## Problem

`_computeTaxActions()` (Phase 23.0A) read `ov.recommended_action` from security overlay objects.  
This field **does not exist** on the `SecurityIntelligenceOverlay` dataclass.

The correct field is `opportunity_flag`.

**Impact**: All opportunity flag–driven branching in Phase 23.0A was silently broken. Holdings such as TSLA (opportunity_flag=TRIM, VERY_BEARISH) would not appear in any action bucket because `ov.recommended_action` resolved to `undefined`, producing an empty string.

## Root Cause

Phase 23.0A's compute function was written against an earlier field schema draft. The overlay serialization was updated to use `opportunity_flag` but the consumer was never updated to match.

## Fix Applied

In `_computePortfolioActions()` (Phase 23.0C replacement):

```js
// Before (broken):
const flag = ov.recommended_action || ""

// After (correct):
const flag = ov.opportunity_flag || ""   // C1 FIX
```

This fix appears in Cat 1 (Signal Deterioration) item extraction and Cat 4 (Funding Sources) ACCUMULATE exclusion logic.

## Validation

- TSLA: `opportunity_flag=TRIM`, `ess_score_text=VERY_BEARISH` → appears in Cat 1 ✓
- PRIM: `opportunity_flag=WATCH`, `signal_direction=BEARISH` → appears in Cat 1 ✓
- DVN: `opportunity_flag=WATCH`, `signal_direction=BEARISH` → appears in Cat 1 ✓
