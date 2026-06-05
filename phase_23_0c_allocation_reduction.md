# Phase 23.0C — C3: Allocation Reduction

**Status**: COMPLETE  
**Date**: 2026-06-03  
**PAR Run**: PAR-20260603-B66B00E3

## Design

Category 3 (Allocation Reduction) identifies holdings that belong to asset allocation nodes that are **overweight vs. mandate targets**. These are sourced from the PAR recommendations layer (`recommendation_type === "REDUCE_OVERWEIGHT"`).

This is structurally different from signal-based reduction (Cat 1) — a holding can have a neutral or positive signal and still be in Cat 3 if its node is overweight.

## Data Source

`data.recommendations` — filtered to `recommendation_type === "REDUCE_OVERWEIGHT"`.  
Key fields extracted per recommendation:
- `affected_node_key` — allocation tree node ID
- `drilldown.affected_node_label` — human-readable label
- `drift_pct` — overweight magnitude in percentage points
- `affected_symbols` — holdings mapped to this node

## Active REDUCE_OVERWEIGHT Nodes (PAR-20260603-B66B00E3)

| Node | Drift | Holdings |
|------|-------|----------|
| EQUITIES.INTERNATIONAL | +6.76pp | SBS, DODFX, CVE, TSM, GTX |
| EQUITIES.INTERNATIONAL.LARGE | +4.15pp | SBS, DODFX, VXUS, VEA, FIGFX |
| EQUITIES.US.MEGA.ULTRA_MEGA | +4.81pp | MU, VOO, TSLA, FXAIX |

## Logic

For each symbol in reduce-node sets that is present in `security_overlays`:
- Include in Cat 3
- Determine primary node (highest absolute drift if in multiple nodes)
- Mark `is_protected = true` if symbol has HIGH_CONVICTION_ANCHOR or CORE_CONVICTION_LEADER in deployment queue
- Severity: HIGH if drift ≥ 5pp, MEDIUM otherwise

Protected holdings are NOT excluded from Cat 3 — they appear with a 🔒 badge and a note suggesting index vehicle reduction instead of direct reduction.

## Expected Results

Expected Cat 3 holdings: DODFX, VXUS, VEA, SBS, MU, VOO, TSLA, FXAIX, FIGFX (those with overlays).  
- TSLA appears in both Cat 1 and Cat 3 (signal deterioration + ULTRA_MEGA overweight)
- MU: check if it's a conviction anchor — if HIGH_CONVICTION_ANCHOR, shows 🔒 badge

## Cross-Reference

Cat 4 (Funding Sources) checks `isCat3` to mark such holdings as "Allocation Reduction" funding candidates (MEDIUM priority, amber row).
