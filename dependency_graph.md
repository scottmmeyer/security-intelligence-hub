# Dependency Graph

Project: Security Intelligence Hub (SIH)  
Scope: Backlog implementation dependency model  
Date: 2026-06-07

## Dependency Model

```mermaid
flowchart TD
    I12D[ISSUE-12D Outcome Review Panel\nOpen, milestone-gated]

    PRA1[PRA-IMPL-01 Typed Recommendation Contract\nfrom ISSUE-22]
    PRA2[PRA-IMPL-02 Policy-Aware Funding/Allocation\nfrom ISSUE-20]
    PRA3[PRA-IMPL-03 Surface Lane Separation + Typed Counts\nfrom ISSUE-21]
    PRA4[PRA-IMPL-04 Conviction Anchors Section\nfrom ISSUE-21]
    PRA5[PRA-IMPL-05 FVI Advisory Overlay\nfrom ISSUE-19]

    MCI[MCI Follow-on Implementation\npost current architecture stabilization]

    PRA1 --> PRA2
    PRA1 --> PRA3
    PRA3 --> PRA4
    PRA2 --> PRA3
    PRA1 --> PRA5
    PRA2 --> PRA5
    PRA3 --> PRA5

    PRA5 --> MCI

    I12D -. evidence program proceeds in parallel .-> PRA1
    I12D -. remains open and milestone-bound .-> PRA5
```

## Build-First Sequence

1. PRA-IMPL-01 (typed contract)
2. PRA-IMPL-02 (policy-aware normalization)
3. PRA-IMPL-03 (surface lanes + typed counts)
4. PRA-IMPL-04 (conviction anchors section)
5. PRA-IMPL-05 (FVI advisory overlay)

## Parallelization Opportunities

Can run in parallel:
- ISSUE-12D evidence program with PRA implementation stream
- Early UX wireframing for PRA-IMPL-03 while PRA-IMPL-02 is in development

Cannot safely parallelize fully:
- PRA-IMPL-05 should not be finalized before PRA-IMPL-02 and PRA-IMPL-03 because it depends on policy-aware and typed-surface contracts.

## Governance Notes

- This graph is a recommendation artifact only.
- No GitHub issue modifications are performed in this package.
