# PRA-IMPL-02 Surface Matrix

Repository: security-intelligence-hub  
Date: 2026-06-08

## Policy Behavior Matrix: Before and After PRA-IMPL-02

### TSLA (DO_NOT_SELL)

| Surface | Before PRA-IMPL-02 | After PRA-IMPL-02 |
|---|---|---|
| Deployment queue | BLOCKED_BY_POLICY (correct) | BLOCKED_BY_POLICY (unchanged) |
| security_overlays.csv | BLOCKED_BY_POLICY (correct) | BLOCKED_BY_POLICY (unchanged) |
| REDUCE_OVERWEIGHT rec execution_state | EXECUTABLE (wrong) | BLOCKED_BY_POLICY |
| REDUCE_OVERWEIGHT rec effective_action | "" (missing) | MONITOR_ONLY |
| REDUCE_OVERWEIGHT rec card_lifecycle_state | OBSERVED (default) | POLICY_ADJUSTED |

### DODFX (SELL_LAST)

| Surface | Before PRA-IMPL-02 | After PRA-IMPL-02 |
|---|---|---|
| Deployment queue | DEFERRED (tail-ranked by sell cohort logic) | Unchanged |
| security_overlays.csv | DEFERRED_BY_POLICY (correct when flag is sell-context) | Unchanged |
| REDUCE_OVERWEIGHT rec execution_state | EXECUTABLE (wrong) | DEFERRED_BY_POLICY |
| REDUCE_OVERWEIGHT rec effective_action | "" (missing) | REDUCE_SELL_LAST |
| REDUCE_OVERWEIGHT rec card_lifecycle_state | OBSERVED (default) | POLICY_ADJUSTED |

### No-Policy Symbol (e.g., SBS, MU)

| Surface | Before PRA-IMPL-02 | After PRA-IMPL-02 |
|---|---|---|
| Deployment queue | EXECUTABLE | EXECUTABLE (unchanged) |
| security_overlays.csv | EXECUTABLE | EXECUTABLE (unchanged) |
| REDUCE_OVERWEIGHT rec execution_state | EXECUTABLE | EXECUTABLE (unchanged) |
| REDUCE_OVERWEIGHT rec effective_action | "" | REDUCE (resolved from type) |

## recommendation_type Sell-Context Mapping

| recommendation_type | Sell-Context | Flag | Expected State if DO_NOT_SELL |
|---|---|---|---|
| REDUCE_OVERWEIGHT | Yes | REDUCE | BLOCKED_BY_POLICY |
| STRATEGIC_TRIM_CANDIDATE | Yes | TRIM | BLOCKED_BY_POLICY |
| TOP_TRIM_CANDIDATES | Yes | TRIM | BLOCKED_BY_POLICY |
| IMPROVE_RISK_PROFILE | Yes | TRIM | BLOCKED_BY_POLICY |
| INCREASE_UNDERWEIGHT | No | BUY | EXECUTABLE (not a sell) |
| IMPROVE_REPLAY_ALIGNMENT | No | BUY | EXECUTABLE (not a sell) |
| IMPROVE_SECTOR_EXPOSURE | No | — | EXECUTABLE |
| STRATEGIC_RETAIN_SIGNAL | No | — | EXECUTABLE |
| All NARRATIVE types | No | — | INFORMATIONAL_ONLY (unchanged) |
| All EXPLAINABILITY types | No | — | INFORMATIONAL_ONLY (unchanged) |

## Policy Precedence Rule (Multi-Symbol Recommendations)

For recommendations with multiple affected_symbols, the most restrictive state wins:

1. If any primary affected symbol is DO_NOT_SELL: BLOCKED_BY_POLICY
2. Else if any primary affected symbol is SELL_LAST: DEFERRED_BY_POLICY
3. Else if any primary affected symbol is CORE_ANCHOR + TRIM: INFORMATIONAL_ONLY
4. Else: EXECUTABLE
