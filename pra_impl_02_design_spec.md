# PRA-IMPL-02 Design Specification

Repository: security-intelligence-hub  
Date: 2026-06-08

## Objective

Propagate compute_execution_state() output into every PortfolioRecommendation dict before it is serialised to recommendations.json and served to the UI.

## Implementation Strategy

### New function: apply_policy_to_recommendations()

Location: src/portfolio/operator_policy.py

Purpose: Given a list of recommendation dicts (already serialised via dataclasses.asdict) and a loaded policy registry, mutate execution_state, effective_action, and card_lifecycle_state in-place using compute_execution_state().

Inputs:
- recs: list[dict] — the recs_with_drilldown list in runner.py
- registry: OperatorPolicyRegistry

Logic per recommendation dict:
1. Determine primary affected symbol from affected_symbols list.
2. Determine sell-context flag from recommendation_type mapping.
3. Call compute_execution_state(symbol, flag, registry).
4. If execution_state is not EXECUTABLE, update the dict fields.
5. Set card_lifecycle_state to POLICY_ADJUSTED when policy modifies execution.

### recommendation_type → opportunity_flag mapping

| recommendation_type | flag used in compute_execution_state |
|---|---|
| REDUCE_OVERWEIGHT | REDUCE |
| STRATEGIC_TRIM_CANDIDATE | TRIM |
| TOP_TRIM_CANDIDATES | TRIM |
| IMPROVE_RISK_PROFILE | TRIM |
| INCREASE_UNDERWEIGHT | BUY (not a sell context — never blocked) |
| IMPROVE_REPLAY_ALIGNMENT | BUY (not a sell context) |
| IMPROVE_SECTOR_EXPOSURE | (no sell context) |
| All NARRATIVE/EXPLAINABILITY types | (no sell context) |

### Primary Symbol Resolution

Use affected_symbols[0] when the recommendation_type is a sell-context type.

For REDUCE_OVERWEIGHT, affected_symbols may have multiple symbols (e.g., DODFX, TSLA, SBS for International reduction). The correct resolution is:
- Compute execution state per symbol
- If ANY affected symbol is DO_NOT_SELL, mark the recommendation as requiring policy annotation
- The most restrictive policy wins: BLOCKED > DEFERRED > EXECUTABLE

Simplified rule for PRA-IMPL-02 scope:
- Annotate at the recommendation level with the most restrictive state across primary affected symbols.
- individual-symbol policy visibility in drilldown is deferred to PRA-IMPL-03 scope.

### runner.py Integration Point

After this block in runner.py:
```
_policy_registry = OperatorPolicyRegistry.load(_OPERATOR_STATE)
deployment_queue, _policy_suppressed = _apply_policy_to_queue(...)
```

Add:
```python
from .operator_policy import apply_policy_to_recommendations as _apply_policy_to_recs
_apply_policy_to_recs(recs_with_drilldown, _policy_registry)
```

### canonical execution_state values (PRA-IMPL-01 contract)

EXECUTABLE — no policy modification
BLOCKED_BY_POLICY — DO_NOT_SELL prevents this sell/trim action
DEFERRED_BY_POLICY — SELL_LAST defers to last resort
INFORMATIONAL_ONLY — CORE_ANCHOR requires manual confirmation

### canonical effective_action values (PRA-IMPL-01 contract)

For ACTION card_type recommendations:
- EXECUTABLE sell recs: REDUCE, TRIM, SELL (matches rec type)
- EXECUTABLE buy recs: BUY, ADD
- BLOCKED: MONITOR_ONLY
- DEFERRED: REDUCE_SELL_LAST, TRIM_SELL_LAST

### card_lifecycle_state

OBSERVED → default (PRA-IMPL-01)
POLICY_ADJUSTED → set when execution_state is modified by policy

## Non-Changes

- No PortfolioRecommendation dataclass changes required (all fields already exist from PRA-IMPL-01)
- No scoring changes
- No ranking changes
- No generation logic changes
- No new output files
