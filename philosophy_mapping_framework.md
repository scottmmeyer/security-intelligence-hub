# Philosophy Mapping Framework

## Purpose

Map each recommendation to one or more capital-allocation philosophies using deterministic rules.

## Philosophy Set

- Concentrated Alpha
- Capital Rotation
- Risk Reduction
- Cash Deployment
- Dislocation Recovery

## Mapping Rules

### Concentrated Alpha

Assigned to:
- `PORTFOLIO_CONSTRUCTION_NARRATIVE`
- `STRATEGIC_RETAIN_NARRATIVE`
- `THEMATIC_SATURATION_NARRATIVE`
- `CONCENTRATION_ECOSYSTEM`
- `INCREASE_UNDERWEIGHT`
- `IMPROVE_REPLAY_ALIGNMENT`

### Capital Rotation

Assigned to:
- `REDUCE_OVERWEIGHT`
- `TOP_TRIM_CANDIDATES`
- `STRATEGIC_TRIM_CANDIDATE`
- policy-constrained sell-context recommendations

### Risk Reduction

Assigned to:
- `REDUCE_OVERWEIGHT`
- `DIVERSIFY_CONCENTRATION`
- `IMPROVE_RISK_PROFILE`
- trim-focused strategic recommendations

### Cash Deployment

Assigned to:
- `INCREASE_UNDERWEIGHT`

### Dislocation Recovery

Assigned to:
- `IMPROVE_REPLAY_ALIGNMENT`
- replay-backed increase recommendations

## Ranking

Each recommendation receives integer philosophy scores.

The output is sorted by:
1. descending score
2. philosophy name for deterministic tie-break

## Governance

This framework is explanatory only. It does not affect ranking, scoring, or action selection.
