# Policy-Aware Recommendation Engine Problem Definition

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-20 Policy-Aware Recommendation Engine  
Date: 2026-06-06

## Mission Context

SIH already supports operator portfolio policies and displays them in the UI. Current policy primitives include:
- DO_NOT_SELL
- SELL_LAST

The unresolved gap is not policy storage. The unresolved gap is cross-engine governance behavior consistency across:
- Strategic Exit
- Allocation Reduction
- Funding Sources
- CRA
- PAP
- PMI

## Q1) Purpose of Operator Portfolio Policies

Operator policies should be treated as both:
1. Recommendation modifiers
2. Execution constraints

They should not be informational-only, and they should not rewrite intelligence/scoring.

Recommended policy role model:
- Intelligence layer: computes unbiased recommendations from signals and models.
- Policy layer: applies operator intent as post-intelligence execution governance.
- Execution layer: emits policy-aware actionability and priority.

This is consistent with existing SIH invariants:
- policy is post-queue transform,
- scores are not mutated,
- reconciliation inputs are not mutated.

## Core Problem Statement

Without a formal policy-aware engine specification, different recommendation surfaces can diverge:
- one surface may suppress a sell,
- another may still rank it highly,
- explanations may be inconsistent.

That creates governance risk, operator confusion, and non-auditable execution behavior.

## Required Separation of Concerns

1. Intelligence truth
- Keep original recommendation signal visible (for example TRIM).

2. Policy effect
- Explicitly encode execution state (for example BLOCKED_BY_POLICY, DEFERRED_BY_POLICY).

3. Final actionability
- Provide policy-aware effective action (for example MONITOR_ONLY, REDUCE_SELL_LAST).

## Non-Goals

ISSUE-20 does not require:
- score formula changes,
- CW-DAS methodology changes,
- replacing policy taxonomy,
- hiding intelligence evidence.

Assessment-only outcome: governance model, precedence, behavior matrix, and staged rollout recommendation.
