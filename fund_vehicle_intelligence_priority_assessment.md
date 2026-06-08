# Fund Vehicle Intelligence Priority Assessment

Project: Security Intelligence Hub (SIH)  
Scope: ISSUE-19 implementation priority and phasing  
Date: 2026-06-08

## Q2-C / Q6) FVI Implementation Scope and Priority

## Phase-1 Scope: What Can Be Implemented Now

Advisory fund quality scoring using three percentile inputs:
1. Category-relative risk-adjusted return percentile
2. Expense ratio percentile within category/share class
3. Downside capture percentile

Output label set: LOW | MEDIUM | HIGH | ELITE

This output is:
- advisory-only
- displayed as context on fund-related allocation/reduction cards
- not used to modify CW-DAS scores
- not used to modify conviction tiers
- explicitly labelled as informational

Specific use case that is immediately addressable:
- DODFX evaluated against Foreign Large Value peer set
- Quality label (for example ELITE) displayed alongside allocation reduction recommendation
- Operator sees: "International sleeve reduction recommended, DODFX quality: ELITE — consider alternative reduction vehicles first"

## What Requires Policy and Surface Infrastructure First

FVI phase-1 advisory display requires:
- A surface with card_type metadata (from PRA-IMPL-01/03)
- Policy-aware execution state fields to avoid conflating FVI quality with policy constraints (from PRA-IMPL-02)

Why:
- If a fund is both SELL_LAST and ELITE, the surface must clearly show both states without merging them.
- Without typed lanes, FVI labels risk appearing as pseudo-recommendations.

## What Is Explicitly Blocked (Phase-2+)

Direct scoring influence on CW-DAS:
- Blocked until multi-quarter peer performance evidence is available.
- Blocked until formal scoring-governance review.

Replacement recommendation generation:
- Blocked until friction-adjusted switching economics model is implemented and tested.

FVI influence on CRA ranking:
- Blocked at phase-1; eligible for phase-2 policy-gate after advisory validation.

## Q6) Should FVI Be Implemented Before Policy Engine and Surface Rationalization?

No.

Rationale:
1. FVI advisory labels require a typed card surface to render cleanly without inflating recommendation counts.
2. FVI + fund policy (SELL_LAST) interactions require policy-aware execution state fields to be consistent.
3. Implementing FVI before these foundations risks:
   - ELITE quality label appearing as a recommendation
   - Policy and quality signals competing for the same display space without precedence logic
   - Inflating inflation further rather than reducing it

Correct sequence:
1. Policy-aware execution state normalization (PRA-IMPL-02)
2. Typed card surface and lane separation (PRA-IMPL-03)
3. FVI advisory overlay (PRA-IMPL-05) on top of normalized, typed surfaces

## Peer Group Configuration Requirement

Before implementation, a peer group mapping configuration must exist or be created:
- Mutual funds present in portfolio mapped to canonical peer category
- Minimum: DODFX → Foreign Large Value (or equivalent)
- Stored as configuration, not hardcoded

This is a pre-implementation design task, not a blocking architecture problem.

## Data Source Requirement

Phase-1 FVI requires:
1. Category-relative percentile ranks for held funds
2. Expense ratio by fund ticker
3. Downside capture or Sortino percentile

Acceptable phase-1 data path:
- Manual or semi-automated ingestion of quality metadata for held mutual funds only
- Full universe coverage not required for phase-1 advisory

This lowers the barrier to phase-1 implementation substantially.

## Implementation Complexity Estimate

Phase-1 advisory overlay:
- Data ingestion for held mutual funds: Low (manual config acceptable)
- Quality label computation: Low
- Surface integration: Low-Medium (dependent on PRA-IMPL-03 card_type support)
- Total estimate: 1-2 development sessions after surface contract exists

## Recommended Issue Title

PRA-IMPL-05: FVI Advisory Overlay for Allocation Reduction and Replacement Review

Labels: enhancement, governance, fvi, recommendation-engine, priority-medium, needs-data
