# Phase 23.0C — Validation Checklist

**Status**: READY FOR VALIDATION  
**Date**: 2026-06-03  
**Server**: http://localhost:8765/ui/portfolio_alignment/

## Pre-conditions

- [ ] Server running on port 8765
- [ ] `data/operator/portfolio_alignment_state.json` contains `"strategic_exit_symbols": ["FIS"]`
- [ ] PAR run `PAR-20260603-B66B00E3` is the active run

## Load Validation

- [ ] Upload `data/portfolio_ingestion/analysis_runs/PAR-20260603-B66B00E3/` or re-run analysis
- [ ] Pipeline section appears after analysis loads
- [ ] Header shows "N actions · M categories active"

## Category 1 — Signal Deterioration

- [ ] TSLA in Cat 1 (opportunity_flag=TRIM, ess=VERY_BEARISH, priority=HIGH)
- [ ] PRIM in Cat 1 (signal_direction=BEARISH, priority=MEDIUM)
- [ ] DVN in Cat 1 (signal_direction=BEARISH, priority=MEDIUM)
- [ ] Cat 1 auto-expands (has HIGH priority items)
- [ ] Rationale column present

## Category 2 — Strategic Exit

- [ ] FIS appears in Cat 2 table with priority HIGH
- [ ] "Operator Designated Exit" shown as reason
- [ ] FIS chip visible in Strategic Exit Manager
- [ ] Add/Remove UI functional:
  - [ ] Type symbol + Enter → adds to list
  - [ ] ✕ button removes chip
  - [ ] Pipeline re-renders after add/remove
- [ ] Cat 2 always visible (even when no exits designated)

## Category 3 — Allocation Reduction

- [ ] DODFX in Cat 3 (INTERNATIONAL.LARGE node, drift ~4pp)
- [ ] VXUS in Cat 3 (INTERNATIONAL.LARGE node)
- [ ] VEA in Cat 3 (INTERNATIONAL.LARGE node)
- [ ] TSLA in Cat 3 (ULTRA_MEGA node, drift ~5pp)
- [ ] High-drift nodes show HIGH severity with red row
- [ ] Protected (🔒) holdings show appropriate note

## Category 4 — Funding Sources

- [ ] VOO appears in Cat 4 (HOLD, not conviction anchor)
- [ ] FXAIX appears in Cat 4 (ULTRA_MEGA reduce candidate → MEDIUM)
- [ ] DODFX/VEA/VXUS appear in Cat 4 with Allocation Reduction cross-reference
- [ ] VRT NOT in Cat 4 (CORE_CONVICTION_LEADER — excluded)
- [ ] ARW NOT in Cat 4 (HIGH_CONVICTION_ANCHOR — excluded)
- [ ] PSX NOT in Cat 4 (HIGH_CONVICTION_ANCHOR — excluded)
- [ ] Sorted: HIGH priority → MEDIUM → LOW, then by composite_score ASC

## Cross-Reference

- [ ] TSLA: Cat 1 (primary) + Cat 3 + Cat 4 cross-ref
- [ ] FIS: Cat 2 (primary) + possibly Cat 4 (LOW)

## Clear Behavior

- [ ] Clear button hides pipeline section

## Tax Position Panel

- [ ] Tax Position Panel still visible (Phase 23.0A panel preserved)
- [ ] Save Tax Position re-renders pipeline if analysis loaded
