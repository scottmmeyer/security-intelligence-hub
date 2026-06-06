# Recommendation Classification Framework

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-21 Taxonomy and Counting Policy  
Date: 2026-06-06

## Q2) Taxonomy for Current Observation Types

| Surface Item Type | Primary Class | Actionable? | Suggested Home |
|---|---|---|---|
| Allocation Reduction | Action | Yes | Actions lane (main stream) |
| Strategic Exit | Action | Yes | Actions lane (main stream) |
| Funding Sources | Action | Yes | Actions lane (main stream) |
| Deployment Opportunities | Action | Yes | Actions lane (main stream) |
| Replay Alignment | Diagnostic / Explainability | Usually no (unless used as explicit gate) | Explainability lane or drill-down |
| High Conviction Retain | Observation | No direct action | Conviction summary section |
| Strategic Retain Signal | Observation | Usually no direct action | Observation lane |
| Conviction Anchor | Narrative / Observation | No direct action | Conviction summary section |
| STI Classification | Explainability / Diagnostic | No direct action | Explainability drill-down |
| Dislocation Observation | Diagnostic | Usually no immediate action | Observation lane with optional alerting |

## Q3) Explicit Recommendation Criteria

A card is a recommendation only if all are true:
1. It has a concrete action verb (ADD, REDUCE, EXIT, REALLOCATE, FUND_FROM).
2. It maps to an actionable symbol/node list.
3. It has an execution_state (or equivalent) that can resolve to executable/deferred/blocked.
4. It contributes to a near-term operator decision queue.

If criteria are partially met:
- classify as observation if it changes awareness,
- classify as explainability if it justifies another action,
- classify as narrative if it summarizes posture.

## Q4) Recommendation Inflation Assessment

Reference operator snapshot indicates a headline count of 34 "recommendations" with mixed semantic types.

Rationalized decomposition model:
- True actionable count: 6
- Informational observation count: 5
- Explainability artifact count: 5
- Conviction/narrative count: 18

Interpretation:
- Headline count of 34 overstates actionable workload.
- Actionable burden is closer to 6 priority decisions in the same snapshot.

Governance note:
- Exact counts should be computed dynamically from typed card metadata at runtime.
- If typed metadata is absent, use provisional classification with explicit "estimated" badge.

## Q8) Recommendation Counting Policy

Replace single-count headline with typed counts:
- Actions: N
- Observations: N
- Explainability: N
- Conviction/Narrative: N

Display policy:
1. Primary KPI: Actions count.
2. Secondary KPI: total non-action intelligence count.
3. Optional total count can remain visible, but must be labeled "Total Cards" not "Recommendations."

Truthfulness standard:
- "Recommendations" label should be reserved for action-qualified cards only.
