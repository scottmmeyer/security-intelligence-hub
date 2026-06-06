# Recommendation Surface Governance Assessment

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-21 Governance Model  
Date: 2026-06-06

## Governance Objectives

1. Make action workload truthful.
2. Preserve supporting intelligence without inflating action counts.
3. Keep policy and explainability effects explicit and auditable.

## Governance Rules

1. Every card must declare a semantic type:
- ACTION
- OBSERVATION
- EXPLAINABILITY
- NARRATIVE
- DIAGNOSTIC

2. Only ACTION cards contribute to recommendation count.

3. Any card affected by operator policy must include policy-adjusted execution context.

4. Non-action cards cannot carry action urgency labels unless explicitly converted to ACTION by rule.

## Q9) Interaction with ISSUE-20 (Policy-Aware Engine)

Policy treatment in rationalized surface:

### DO_NOT_SELL
- If base recommendation is sell-context, card remains visible but marked non-executable.
- Main action queue behavior:
  - either excluded from executable actions,
  - or shown in blocked subsection with explicit BLOCKED_BY_POLICY state.
- Do not count as executable action workload.

### SELL_LAST
- Card remains actionable but lower liquidation priority.
- Keep in action queue with deferred marker.
- Count as action, but with downgraded priority tier.

Policy-protected positions should still generate visible cards for transparency, but counting and priority must reflect execution reality.

## Q10) Interaction with ISSUE-19 (FVI)

FVI placement recommendation:
- Default: advisory overlay attached to action/observation cards.
- Not a standalone recommendation by default.

Usage pattern:
1. Sleeve action remains an ACTION recommendation.
2. FVI quality label appears as decision context (for example ELITE, HIGH).
3. Replacement action becomes ACTION only when explicit replacement criteria are met.

Inflation prevention rule:
- "FVI quality" alone is an observation/advisory signal, not a recommendation.

## Auditability Requirements

Every action card should include:
- base rationale,
- semantic class,
- execution_state,
- policy effects (if any),
- supporting evidence links.

Every non-action card should include:
- reason for non-action classification,
- relation to any parent action card (if applicable).

## Risk and Mitigation

Risks without rationalization:
- over-alerting,
- operator fatigue,
- action ambiguity,
- trust erosion.

Mitigation:
- typed taxonomy,
- typed counts,
- action-first lane,
- policy-aware execution context.
