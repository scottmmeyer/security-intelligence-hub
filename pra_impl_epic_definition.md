# PRA-IMPL-00 Epic Definition

Project: Security Intelligence Hub (SIH)  
Type: Implementation Epic  
Date: 2026-06-08  
Design basis: ISSUE-22 Portfolio Recommendation Architecture Assessment

## Purpose

PRA-IMPL-00 is the umbrella implementation epic for the Portfolio Recommendation Architecture (PRA) program. It tracks the full delivery of recommendation typing, policy normalization, surface rationalization, and FVI advisory integration across SIH.

## Problem Statement

SIH currently produces recommendations from multiple systems (CRA, PAP, STI, Dislocation, Policy Engine) but lacks a unifying contract for:
- recommendation semantic classification (action vs observation vs narrative)
- deterministic policy precedence across all surfaces
- truthful recommendation count presentation
- extensible integration for future intelligence sources (FVI, MCI)

This creates: recommendation inflation, policy inconsistency across surfaces, and operator action ambiguity.

## Epic Scope

| Child Issue | Title | Priority |
|---|---|---|
| PRA-IMPL-01 | Typed Recommendation Contract and Card Schema | High |
| PRA-IMPL-02 | Policy-Aware Funding Sources and Allocation Reduction | High |
| PRA-IMPL-03 | Recommendation Surface Lane Separation and Typed Counts | Medium |
| PRA-IMPL-04 | Conviction Anchors Section Extraction | Medium |
| PRA-IMPL-05 | FVI Advisory Overlay for Allocation Reduction | Medium |

## Success Criteria for Epic Completion

1. All recommendation-producing surfaces emit typed card_type metadata.
2. DO_NOT_SELL and SELL_LAST policies produce consistent execution states across Funding Sources, Allocation Reduction, Strategic Exit, CRA, and PAP.
3. Recommendation header shows typed counts (Actions / Observations / Conviction Anchors / Explainability) instead of a single aggregate.
4. High Conviction Retain cards appear in Conviction Anchors section, not in Action Queue.
5. FVI advisory quality label appears alongside fund-related allocation reduction cards.

## Implementation Invariants (Must Not Change)

- CW-DAS composite scores
- ESS, Zacks, Danelfin signal values
- UCF verdict computation
- STI profile generation
- Reconciliation inputs

## Design Records (Archival)

- ISSUE-19: Fund Vehicle Intelligence Assessment
- ISSUE-20: Policy-Aware Recommendation Engine Assessment
- ISSUE-21: Recommendation Surface Rationalization Assessment
- ISSUE-22: Portfolio Recommendation Architecture Assessment

## Timeline Guidance

- PRA-IMPL-01/02: June–July 2026
- PRA-IMPL-03/04: August 2026
- PRA-IMPL-05: Q4 2026 (data config dependency)
