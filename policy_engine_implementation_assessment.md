# Policy Engine Implementation Assessment

Project: Security Intelligence Hub (SIH)  
Scope: ISSUE-20 implementation planning detail  
Date: 2026-06-08

## Q2-A / Q5) Policy-Aware Recommendation Engine: Implementation Scope

The policy engine assessment (ISSUE-20) is implementation-ready. This document defines the specific surface behaviors, acceptance criteria, and implementation boundaries.

## Required Surface Behaviors

### Funding Sources

DO_NOT_SELL:
- Symbol must not appear in the executable funding source candidate list.
- Symbol may remain visible in a policy-suppressed section for transparency.
- Explanation must read: "[Symbol] excluded from funding candidates — DO_NOT_SELL policy active."
- No executable liquidation action should be generated.

SELL_LAST:
- Symbol remains in funding source candidate list.
- Symbol is ranked at the tail of the funding cohort, behind all non-SELL_LAST candidates.
- Badge: "⏸ Sell Last — liquidation last resort"
- Explanation must reference ordering constraint explicitly.

### Allocation Reduction

DO_NOT_SELL:
- Reduction recommendation may still be computed and displayed for intelligence transparency.
- Execution state must be BLOCKED_BY_POLICY.
- Effective action must be MONITOR_ONLY.
- UI badge: "🔒 Operator Protected — not executable"

SELL_LAST:
- Reduction recommendation is generated and visible.
- Execution state is DEFERRED_BY_POLICY when reduction action exists.
- Effective action is REDUCE_SELL_LAST.
- Symbol is ranked below all non-SELL_LAST reduction candidates.
- UI badge: "⏸ Sell Last"

### Strategic Exit

DO_NOT_SELL:
- Exit recommendation computed and displayed (intelligence truth preserved).
- Execution state BLOCKED_BY_POLICY.
- Effective action MONITOR_ONLY.

SELL_LAST:
- Exit recommendation is generated.
- Ordering places symbol at tail of exit cohort.

### CRA Recommendations

DO_NOT_SELL:
- CRA reduce/sell output displayed as advisory context only.
- Not placed in executable reduce sequence.

SELL_LAST:
- CRA reduce output generated; priority deferred behind non-constrained candidates.

### PAP Queue

DO_NOT_SELL:
- Entry appears in policy_suppressed section with BLOCKED_BY_POLICY state.
- Not in executable action queue.

SELL_LAST:
- Entry in executable queue, tail-ranked within sell cohort.

## Acceptance Criteria (12 Baseline Assertions Required)

Cross-surface × policy type matrix:
1. Funding Sources + DO_NOT_SELL → not executable, visible with badge
2. Funding Sources + SELL_LAST → tail-ranked, visible with badge
3. Allocation Reduction + DO_NOT_SELL → BLOCKED_BY_POLICY / MONITOR_ONLY
4. Allocation Reduction + SELL_LAST → DEFERRED_BY_POLICY / REDUCE_SELL_LAST
5. Strategic Exit + DO_NOT_SELL → BLOCKED_BY_POLICY / MONITOR_ONLY
6. Strategic Exit + SELL_LAST → tail-ranked / DEFERRED_BY_POLICY
7. CRA + DO_NOT_SELL → advisory only, not executable
8. CRA + SELL_LAST → deferred priority
9. PAP + DO_NOT_SELL → suppressed section
10. PAP + SELL_LAST → tail of sell cohort
11. Any surface + non-sell action + DO_NOT_SELL → EXECUTABLE (policy does not block non-sell)
12. Any surface + any policy → intelligence signal always visible alongside policy effect

## Q5) Should Policies Influence These Surfaces?

Answers:
- Funding Sources: Yes (Q5B)
- Allocation Reduction: Yes (Q5C)
- Strategic Exit: Yes (already validated in Phase 23.2/23.3)
- CRA recommendations: Yes, as advisory governance layer
- PAP recommendations: Yes, as suppression and ordering

## Implementation Boundaries

Must not change:
- CW-DAS composite scores
- ESS signal values
- Reconciliation inputs
- Dislocation intelligence scores

Must change only:
- Execution state outputs per surface
- Recommendation display ordering
- Card visibility classification
- Explanation text for policy-affected cards

## Implementation Complexity Estimate

- Funding Sources policy pass: Low-Medium
- Allocation Reduction policy pass: Low-Medium
- Cross-surface explanation normalization: Medium
- Test suite additions (12+ assertions): Low
- Total estimate: 2-3 focused development sessions without scoring risk

## Recommended Issue Title

PRA-IMPL-02: Policy-Aware Funding Sources and Allocation Reduction Normalization

Labels: enhancement, governance, ui-ux, policy-engine, priority-high, ready
