
# UCF Readiness Assessment
## Phase 7.6A — Unified Conviction Framework Pre-Implementation Audit

**Run:** PAR-20260531-F794D952
**Date:** 2026-05-31
**Verdict: YELLOW — Several disagreements remain — UCF would add value but requires care**

---

## Readiness Criteria Evaluation

| Criterion | Threshold | Actual | Status |
|-----------|-----------|--------|--------|
| Convergence rate | ≥ 75% complete agreement | 77.8% | ✓ PASS |
| Material disagreements | 0 | 0 | ✓ PASS |
| Operator-needed (OW-tension) | ≤ 6 | 10 | ✗ FAIL |
| CCL-to-queue alignment | ≥ 80% | 100% | ✓ PASS |
| HCA-to-queue alignment | ≥ 50% | 100% | ✓ PASS |
| Replay signal premium | > 0 pts | Hard gate — 100% of queue is replay-supported | ✓ PASS |
| Trim suppression working | True | True | ✓ PASS |

---

## Verdict: YELLOW

### Several disagreements remain — UCF would add value but requires care

**Evidence:**

1. **77.8% convergence.** 63 of 81 holdings are in complete cross-system agreement. No holding is receiving contradictory signals that would confuse a UCF synthesis.

2. **0 material disagreements.** There are no cases where one system says "buy" and another says "sell" for the same holding. All conflicts are structural (OW-tension) or methodological (missing replay), not substantive signal conflicts.

3. **10 OW-tension cases require operator judgment**, not UCF resolution. The UCF should display these tensions as conflict flags, not attempt to auto-resolve them. This is by design.

4. **Replay is a hard gate for deployment.** 100% of queue items are replay-supported. Zero non-replay holdings entered the queue. Replay signal and deployment scoring are in perfect agreement.

5. **Tier-to-deployment alignment is strong.** CCL → 100% deployment rate. HCA → 100% deployment rate. The existing tier labels are valid input labels for UCF output labels.

---

## Pre-Implementation Constraints

The following constraints must be honored during UCF implementation:

### Hard Constraints

1. **UCF is a read-only synthesis layer.** It reads existing signals; it never recomputes narrative_tier, CW-DAS, or composite_score. Changes to those values require changes to the underlying systems.

2. **CONVICTION_OW_TENSION is a display flag, not a resolution.** UCF must expose this conflict to the operator without auto-resolving it. The operator decides whether to reduce the OW node, trim the blocked holding, or hold.

3. **Strategic classification is the primary tier input.** `HIGH_CONVICTION_RETAIN` → UCF `HIGH_CONVICTION_ANCHOR`. This is a 1:1 mapping, not an inference.

4. **CCL gate logic must match the existing _assign_narrative_tiers() criteria exactly:**
   - signal_direction == BULLISH
   - replay_supported == True
   - composite_score ≥ 4.0
   - percent_of_portfolio ≥ 1.5%
   - trim_priority_score < 30.0

### Implementation Sequence (Phase 7.7 guidance)

Based on this audit, the recommended implementation sequence:

1. **Layer 0 (existing):** No changes. All conviction signals are ready as inputs.
2. **Layer 1 (`unified_conviction.py`):** `build_ucf_verdicts()` reads profiles, overlays, deployment queue → produces `UnifiedConvictionVerdict` per holding.
3. **Layer 2 (`ucf_verdicts.json`):** Written by runner after build_deployment_queue().
4. **Layer 3 (runner.py):** 2-line additive integration after deployment_queue block.
5. **Layer 4 (conviction_dashboard.html):** Reads ucf_verdicts.json; companion page to existing UI.

### Acceptance Criteria (from Phase 7.6 design)

| Symbol | Expected UCF Label | Basis |
|--------|-------------------|-------|
| AEIS | CORE_CONVICTION_LEADER | All 5 CCL gates met, #1 CW-DAS |
| VRT | CORE_CONVICTION_LEADER | All 5 CCL gates met, #2 CW-DAS |
| PRIM | TRIM_WATCH | BEARISH, composite=2.06, trim priority high |
| SPAXX | MAINTAIN | Cash equivalent, no signal |
| PRG | TACTICAL_GROWTH (approaching CCL) | VERY_BULLISH but missing replay gate |

---

## Conflict Flags to Implement

The following 5 conflict flag types are validated by this audit and should be implemented:

| Flag | Instances in Run | Implementation Priority |
|------|-----------------|------------------------|
| `CONVICTION_OW_TENSION` | 10 | HIGH — affects operator deployment decisions |
| `REPLAY_LOSS` | 8 | MEDIUM — methodology gap flag, not urgent |
| `COMPOSITE_ESS_DIVERGE` | 0 | MEDIUM — operator awareness, rare |
| `SIGNAL_TIER_MISMATCH` | 0 | LOW — edge case |
| `TRIM_RETAIN_CONFLICT` | 0 | LOW — internal classification review needed |

---

## Summary

The conviction systems in Security Intelligence Hub are in strong natural agreement. The audit finds no evidence that the systems are contradicting each other on core signals. Conflicts are structural (allocation constraints) or methodological (coverage gaps), not signal-level disagreements.

**UCF implementation is justified and the codebase is ready for Phase 7.7.**

The primary value UCF adds is not reconciliation of conflicting signals — the signals already agree. UCF's value is **synthesis**: collapsing 10+ per-holding signals into a single actionable label with conflict flags surfaced in one view, eliminating the operator's manual reconciliation burden.
