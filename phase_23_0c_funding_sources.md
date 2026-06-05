# Phase 23.0C — C4: Funding Sources

**Status**: COMPLETE  
**Date**: 2026-06-03  
**PAR Run**: PAR-20260603-B66B00E3

## Design

Category 4 (Funding Sources) identifies portfolio holdings that can be trimmed to fund higher-conviction opportunities (the deployment queue). This is the capital redeployment layer — it shows where liquidity can come from.

## Inclusion Criteria

A holding is included in Cat 4 if:
1. **Not a protected conviction tier** — HIGH_CONVICTION_ANCHOR and CORE_CONVICTION_LEADER are excluded entirely
2. **Has portfolio weight ≥ 0.05%** — filters out negligible positions
3. **Has a composite ESS score** — must have signal data
4. **Not ACCUMULATE-flagged** unless also in Cat 1 (signal deterioration cross-ref)

## Exclusion Logic

Protected tiers (from `deployment_queue.queue[].narrative_tier`):
- `HIGH_CONVICTION_ANCHOR` → excluded
- `CORE_CONVICTION_LEADER` → excluded

Expected exclusions from PAR-20260603-B66B00E3:
- VRT (CORE_CONVICTION_LEADER, rank 1) — excluded ✓
- ARW (HIGH_CONVICTION_ANCHOR, rank 2) — excluded ✓
- PSX (HIGH_CONVICTION_ANCHOR, rank 3) — excluded ✓
- SNX, ATLC, ASML, TSM, MU (conviction anchors) — excluded ✓

## Priority Levels

| Priority | Condition | Row Color |
|----------|-----------|-----------|
| HIGH     | Also in Cat 1 (signal deterioration) | Red-tinted |
| MEDIUM   | Also in Cat 3 (allocation reduction) | Amber-tinted |
| LOW      | Low conviction / HOLD / WATCH | Default |

## Sorting

1. Priority order: HIGH → MEDIUM → LOW
2. Within tier: composite_score ASC (weakest conviction first = best funding candidate)

## Cross-Reference Display

The "Cross-Reference" column in Cat 4 uses `pap-xref` badges:
- `pap-xref-SIGNAL_DETERIORATION` (red) — "Signal Deterioration"
- `pap-xref-ALLOCATION_REDUCTION` (amber) — "Allocation Reduction"
- No badge — "Low Conviction"

## Expected Results

Expected Cat 4 holdings (approximate): FIS, DODFX, VXUS, VEA, VOO, FXAIX, GTX.  
- FIS: strategic exit (Cat 2 primary) → may also appear here as LOW conviction
- DODFX/VXUS/VEA: Cat 3 cross-refs at MEDIUM priority
- VOO/FXAIX: ULTRA_MEGA reduce candidates at MEDIUM priority
