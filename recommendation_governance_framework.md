# Recommendation Governance Framework

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-22 Governance Framework  
Date: 2026-06-06

## Q5) Recommendation Precedence

Precedence should be deterministic and layered.

Recommended hierarchy (highest to lowest):
1. Policy constraints (DO_NOT_SELL, SELL_LAST)
2. Allocation and risk constraints (sleeve and concentration boundaries)
3. Vehicle quality context (FVI once available)
4. Security quality/context (STI, replay, dislocation, conviction)
5. Raw score/rank outputs

Interpretation:
- Policy governs executability.
- Allocation governs portfolio-level necessity.
- Vehicle quality governs implementation choice.
- Security quality governs confidence and rationale.

## Q6) Recommendation Counting Policy

Counting must be typed and truthful.

Count categories:
1. Recommendations (Action class only)
2. Observations
3. Explainability artifacts
4. Narrative items
5. Diagnostics

Display standard:
- Primary header: Actions: N
- Secondary header: Observations: N, Explainability: N, Narrative: N, Diagnostics: N
- Optional total: Total Cards: N (not labeled Recommendations)

Example conversion:
- Legacy: 34 Recommendations
- Rationalized: 6 Actions, 5 Observations, 5 Explainability, 18 Narrative/Conviction

## Governance Invariants

1. No policy mutation of base scores.
2. No recommendation count inflation via non-action cards.
3. Every action card must provide execution_state and evidence link.
4. Every policy-adjusted card must show original recommendation and adjusted action.
5. Every replacement recommendation (future FVI path) must include friction-adjusted economics and confidence band.

## Control Framework

Required controls:
1. Typed output schema enforcement
2. Cross-surface consistency checks
3. Policy precedence validation tests
4. Recommendation-count audit checks
5. Decision-to-outcome traceability snapshots

## Governance Outcome

This framework unifies CRA, PAP, STI, Dislocation, Policy, and future FVI into one coherent recommendation contract that is explainable, auditable, and extensible.
