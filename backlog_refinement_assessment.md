# Backlog Refinement Assessment

Project: Security Intelligence Hub (SIH)  
Scope: Governance and backlog refinement only  
Date: 2026-06-07

## Executive Summary

Assessment wave (ISSUE-19 through ISSUE-22) is complete and has produced sufficient architecture guidance to begin implementation issue decomposition. The primary gap is not additional assessment depth; it is backlog structure and sequencing.

## Q1) Should New Implementation Issues Be Created Immediately?

Yes, with constraints.

Immediate creation is recommended for implementation-track issues that are already fully specified by existing assessment outputs and UI review findings.

Creation should be staged as:
1. Architecture contract implementation issue (from ISSUE-22)
2. Policy-aware execution normalization issue (from ISSUE-20)
3. Recommendation surface rationalization issue (from ISSUE-21)
4. FVI advisory integration issue (from ISSUE-19)

## Q2) Assessment Status and Implementation Readiness

| Assessment Issue | Assessment Complete | Ready for Implementation Issue Creation | Blocked | Needs Additional Design | Should Remain Assessment-Only |
|---|---|---|---|---|---|
| ISSUE-19 FVI Assessment | Yes | Yes (advisory phase and policy-gated phase) | Partially (full scoring influence path blocked by evidence burden) | No for phase-1 advisory | Yes (the assessment issue itself should remain an archival assessment record) |
| ISSUE-20 Policy-Aware Recommendation Engine Assessment | Yes | Yes | No (for DO_NOT_SELL and SELL_LAST scope) | Minor implementation details only | Yes (assessment issue should remain archival) |
| ISSUE-21 Recommendation Surface Rationalization Assessment | Yes | Yes | No | Minor UI decomposition details only | Yes (assessment issue should remain archival) |
| ISSUE-22 Portfolio Recommendation Architecture Assessment | Yes | Yes (as umbrella implementation contract) | No | No | Yes (assessment issue should remain archival) |

Interpretation:
- All four assessment issues are complete as design/governance artifacts.
- None should be repurposed as direct implementation tickets.
- Implementation should proceed via newly created implementation-track issues linked to these assessments.

## Q3) UI Concept Promotion to Implementation Track

### A) Move High Conviction Retain cards to dedicated Conviction Anchors section

Recommendation: Yes, promote to implementation.

Reason:
- Already validated by ISSUE-21 taxonomy (observation/narrative class, not action).
- Directly reduces recommendation inflation and operator confusion.

### B) Funding Sources policy-aware behavior (DO_NOT_SELL suppression)

Recommendation: Yes, promote to implementation.

Reason:
- Fully aligned to ISSUE-20 behavior matrix.
- Governance rule is already explicit: DO_NOT_SELL should not produce executable funding-source sell actions.

### C) Allocation Reduction policy-aware behavior (SELL_LAST distinction/deprioritization)

Recommendation: Yes, promote to implementation.

Reason:
- Fully aligned to ISSUE-20 behavior matrix.
- Requires queue ordering and visibility treatment, not new governance discovery.

### D) Allocation Reduction FVI-aware behavior (quality-aware treatment)

Recommendation: Yes, promote to implementation, but phase-gated.

Reason:
- ISSUE-19 defines advisory-first pattern and replacement gating.
- Should start as advisory overlay and policy gate, not direct score mutation.

### E) Typed recommendation counts (Actions, Observations, Conviction Anchors, Watchlists)

Recommendation: Yes, promote to implementation.

Reason:
- ISSUE-21 and ISSUE-22 both define this as core truthfulness requirement.

## Q4) One Issue vs Multiple vs Subtasks

Recommendation:
- Use one umbrella implementation issue under ISSUE-22 contract, with multiple child implementation issues.

Why:
1. Prevents fragmented precedence logic.
2. Preserves coherent architecture governance.
3. Enables parallel implementation where safe.

Suggested structure:
- Parent implementation issue: PRA implementation contract
- Child issues:
  1. Policy-aware funding/allocation behavior
  2. Recommendation surface lane separation
  3. Typed count and card classification
  4. Conviction anchors section extraction
  5. FVI advisory overlay integration

## Q5) Priority Ordering Recommendation

Recommended order:
1. ISSUE-12D (time-gated evidence program)
2. Portfolio Recommendation Architecture implementation contract (derived from ISSUE-22)
3. Policy Engine implementation (ISSUE-20 implementation track)
4. Recommendation Surface Rationalization implementation (ISSUE-21 implementation track)
5. FVI implementation phase-1 advisory integration (ISSUE-19 implementation track)
6. MCI implementation (post current architecture stabilization)

Rationale:
- ISSUE-12D is already in-flight and milestone-bound.
- ISSUE-22/20/21 provide actionability infrastructure for all later recommendation work.
- FVI quality integration should land after policy and surface contracts exist.
- MCI remains valuable but less immediate for execution integrity.

## Governance Decision

Do not modify current assessment issues into implementation containers.
Create separate implementation issues and close assessments once linked and archived.
