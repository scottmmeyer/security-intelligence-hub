# PRA Implementation Dependency Graph

Project: Security Intelligence Hub (SIH)  
Type: Implementation sequencing model  
Date: 2026-06-08

## Full Dependency Graph

```mermaid
flowchart TD
    I12D["ISSUE-12D: Dislocation Outcome Review Panel\nOpen — milestone Dec 2026\n(runs in parallel)"]

    P00["PRA-IMPL-00\nPortfolio Recommendation Architecture\n(parent epic)"]
    P01["PRA-IMPL-01\nTyped Recommendation Contract\n+ Card Schema\nPRIORITY: HIGH"]
    P02["PRA-IMPL-02\nPolicy-Aware Funding Sources\n+ Allocation Reduction\nPRIORITY: HIGH"]
    P03["PRA-IMPL-03\nSurface Lane Separation\n+ Typed Counts\nPRIORITY: MEDIUM"]
    P04["PRA-IMPL-04\nConviction Anchors\nSection Extraction\nPRIORITY: MEDIUM"]
    P05["PRA-IMPL-05\nFVI Advisory Overlay\nPRIORITY: MEDIUM\n(needs-data)"]
    MCI["MCI Implementation\nPost architecture stabilization\n2027+"]

    P00 --> P01
    P00 --> P02
    P00 --> P03
    P00 --> P04
    P00 --> P05

    P01 --> P02
    P01 --> P03
    P01 --> P05

    P02 --> P03
    P02 --> P05

    P03 --> P04
    P03 --> P05

    P05 --> MCI

    I12D -. "parallel evidence track" .- P01
    I12D -. "milestone gate for dislocation signal" .- P05
```

## Build Sequence (Serial Dependencies)

```
Step 1: PRA-IMPL-01  → foundation, no dependencies
Step 2: PRA-IMPL-02  → requires 01
Step 3: PRA-IMPL-03  → requires 01; benefits from 02
Step 4: PRA-IMPL-04  → requires 03
Step 5: PRA-IMPL-05  → requires 01, 02, 03 + peer group data config
```

## Parallelization Opportunities

| What | When |
|---|---|
| ISSUE-12D evidence collection | Always parallel with PRA-IMPL stream |
| UX wireframes for PRA-IMPL-03 lane design | During PRA-IMPL-02 development |
| Peer group config for FVI | During PRA-IMPL-03/04 development |
| MCI design exploration | After PRA-IMPL-03 is stable |

## Critical Path

PRA-IMPL-01 → PRA-IMPL-02 → PRA-IMPL-03 → PRA-IMPL-04 → PRA-IMPL-05

## Blocking Conditions

| Child | Blocks If |
|---|---|
| PRA-IMPL-01 | Not delivered before any other child |
| PRA-IMPL-02 | FVI overlay misleads without policy state normalization |
| PRA-IMPL-03 | FVI and anchor labels inflate counts if surface isn't typed |
| PRA-IMPL-05 | Blocked if peer group config not created |

## External Dependencies

| Issue | Relationship |
|---|---|
| ISSUE-12D | Independent evidence program; informs future dislocation signal influence on FVI phase-2 |
| ISSUE-19 | Design record for PRA-IMPL-05 |
| ISSUE-20 | Design record for PRA-IMPL-02 |
| ISSUE-21 | Design record for PRA-IMPL-03, 04 |
| ISSUE-22 | Design record for PRA-IMPL-00, 01 |
