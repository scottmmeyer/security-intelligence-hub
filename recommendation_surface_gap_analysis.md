# Recommendation Surface Gap Analysis

Project: Security Intelligence Hub (SIH)  
Scope: Backlog governance analysis for recommendation surfaces  
Date: 2026-06-07

## Gap Summary

Current recommendation surface mixes action and non-action artifacts in one stream. This creates inflation in reported recommendation counts and blurs operator actionability.

## Gap 1: Action vs Observation Conflation

Evidence from prior assessments:
- High Conviction Retain cards are presented in recommendation-like context.
- ISSUE-21 taxonomy classifies these as observation/narrative, not action.

Impact:
- Overstated action workload.
- Reduced salience of true execution tasks.

Remediation direction:
- Move to Conviction Anchors section.
- Keep cross-link to any related action card.

## Gap 2: Policy Effects Not Fully Surface-Normalized

Examples required by this backlog update:
- DO_NOT_SELL symbols appearing as funding candidates should be excluded from executable funding sources.
- SELL_LAST symbols in allocation reduction need explicit deprioritized styling and ordering.

Impact:
- Operator may receive policy-inconsistent action cues.
- Execution trust and auditability degrade.

Remediation direction:
- Apply ISSUE-20 canonical execution states across Funding Sources and Allocation Reduction surfaces.

## Gap 3: Single Aggregate Recommendation Count

Current pattern:
- Single number (for example 34 recommendations) used for mixed semantic classes.

Impact:
- Actionable workload appears much higher than real decision count.

Remediation direction:
- Typed count header:
  - Actions
  - Observations
  - Conviction Anchors
  - Watchlists/Explainability

## Gap 4: FVI Integration Risk (Future Inflation)

Risk:
- FVI outputs could become additional pseudo-recommendation cards if not typed.

Impact:
- Recommendation stream inflation worsens.

Remediation direction:
- FVI phase-1 as advisory overlay.
- Promote to action only when replacement criteria and economics thresholds are met.

## Gap 5: Missing Unified Card Contract

Need:
- Each card must declare semantic type and execution state.

Suggested minimum fields:
1. card_type
2. actionability
3. execution_state
4. effective_action
5. policy_effect
6. evidence_link

## Implementation-Track Readiness by Gap

| Gap | Ready for Implementation | Dependency |
|---|---|---|
| Conviction cards reclassification | Yes | ISSUE-22 contract + ISSUE-21 implementation issue |
| Policy-aware Funding Sources | Yes | ISSUE-20 implementation issue |
| Policy-aware Allocation Reduction | Yes | ISSUE-20 implementation issue |
| Typed recommendation counts | Yes | ISSUE-21 implementation issue |
| FVI-aware reduction treatment | Yes (phase 1 advisory) | ISSUE-19 implementation issue after ISSUE-20/21 baseline |

## Conclusion

Surface rationalization can proceed immediately as implementation-track backlog work if structured as contract-first architecture with policy normalization and typed card semantics.
