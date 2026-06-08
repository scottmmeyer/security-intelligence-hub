# Implementation Issue Recommendations

Project: Security Intelligence Hub (SIH)  
Scope: Proposed GitHub backlog actions (no changes executed)  
Date: 2026-06-07

## Recommended New GitHub Issues to Create

## 1) PRA-IMPL-01: Typed Recommendation Contract and Lifecycle Engine

Purpose:
- Implement ISSUE-22 architecture contract for recommendation typing, lifecycle states, and precedence integration points.

Priority:
- P0 High

Recommended labels:
- enhancement
- governance
- architecture
- recommendation-engine
- priority-high
- ready

Dependencies:
- None (foundation)

## 2) PRA-IMPL-02: Policy-Aware Funding Sources and Allocation Reduction Normalization

Purpose:
- Implement ISSUE-20 behavior for DO_NOT_SELL and SELL_LAST specifically in Funding Sources and Allocation Reduction surfaces.

Priority:
- P0 High

Recommended labels:
- enhancement
- governance
- ui-ux
- policy-engine
- priority-high
- ready

Dependencies:
- PRA-IMPL-01 (contract fields)

## 3) PRA-IMPL-03: Recommendation Surface Lane Separation and Typed Counts

Purpose:
- Implement ISSUE-21 lane model and split counts (Actions, Observations, Conviction Anchors, Watchlists/Explainability).

Priority:
- P1 High-Medium

Recommended labels:
- enhancement
- ui-ux
- governance
- recommendation-surface
- priority-medium
- ready

Dependencies:
- PRA-IMPL-01
- PRA-IMPL-02 preferred before final UX polish

## 4) PRA-IMPL-04: Conviction Anchors Section Extraction

Purpose:
- Move High Conviction Retain class out of main action recommendation stream into dedicated Conviction Anchors section.

Priority:
- P1 Medium

Recommended labels:
- enhancement
- ui-ux
- sti
- recommendation-surface
- priority-medium
- ready

Dependencies:
- PRA-IMPL-03

## 5) PRA-IMPL-05: FVI Advisory Overlay for Allocation Reduction and Replacement Review

Purpose:
- Phase-1 ISSUE-19 integration: advisory fund quality overlay and policy-gated replacement signaling.

Priority:
- P1 Medium

Recommended labels:
- enhancement
- governance
- fvi
- recommendation-engine
- priority-medium
- needs-data

Dependencies:
- PRA-IMPL-01
- PRA-IMPL-02
- PRA-IMPL-03

## Recommended Issue Grouping Strategy

Use parent-child structure:
1. Parent: PRA implementation umbrella (can be PRA-IMPL-01 or separate tracking epic issue)
2. Children: PRA-IMPL-02 through PRA-IMPL-05

This avoids one oversized implementation issue while preserving integrated sequencing.

## Recommended Issues to Close

After creating and linking implementation issues, recommend closing:
- ISSUE-19 (assessment complete)
- ISSUE-20 (assessment complete)
- ISSUE-21 (assessment complete)
- ISSUE-22 (assessment complete)

Closure note recommendation:
- "Assessment complete. Implementation tracked in linked PRA-IMPL issues."

## Recommended Issues to Leave Open

Leave open:
- ISSUE-12D (#17) due to explicit milestone and evidence window dependency.
- Existing EPICs (#2, #3, #5, #6) as portfolio-level containers.

## Recommended Issues to Leave as Assessment-Only (Status Class)

Status class should remain assessment-only even if closed:
- ISSUE-19
- ISSUE-20
- ISSUE-21
- ISSUE-22

These remain permanent design artifacts and decision rationale references.
