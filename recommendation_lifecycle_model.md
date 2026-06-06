# Recommendation Lifecycle Model

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-22 Lifecycle Design  
Date: 2026-06-06

## Q3) Lifecycle Definition

Canonical lifecycle:

Signal -> Observation -> Recommendation -> Decision -> Action -> Outcome

## Stage Definitions

1. Signal
- Raw model/system outputs (scores, drifts, policy states, quality metrics)

2. Observation
- Interpreted state representation from one or more signals
- No required action yet

3. Recommendation
- Observation promoted to action-qualified guidance after criteria checks

4. Decision
- Operator acceptance, rejection, deferral, or override

5. Action
- Executed portfolio change (or explicit non-action when blocked)

6. Outcome
- Measured post-action impact and governance evidence

## Promotion Rules

Observation -> Recommendation requires:
1. Actionability criteria satisfied
2. Policy pass completed (blocked/deferred/executable resolved)
3. Explainability payload attached
4. Target and horizon defined

Recommendation -> Decision requires:
1. Operator-visible rationale
2. Evidence trace link
3. Priority and urgency context

Decision -> Action requires:
1. Execution eligibility confirmed
2. Policy constraints enforced
3. Action logging enabled

Action -> Outcome requires:
1. Outcome window defined
2. Measurement metrics registered
3. Post-mortem traceability retained

## Lifecycle States (Card-Level)

Suggested state machine:
- OBSERVED
- ACTION_QUALIFIED
- POLICY_ADJUSTED
- DECISION_PENDING
- DECISION_CAPTURED
- EXECUTED
- OUTCOME_MEASURED
- CLOSED

## Governance Benefit

Lifecycle discipline prevents two key failures:
1. Treating observations as recommendations
2. Presenting recommendations without decision and outcome accountability
