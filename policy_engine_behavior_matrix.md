# Policy Engine Behavior Matrix

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-20 Behavior and Precedence Matrix  
Date: 2026-06-06

## Q2) Behavior by Policy Type and Surface

### A. DO_NOT_SELL

| Surface | Visibility | Recommendation Generation | Ranking/Priority | Effective Behavior |
|---|---|---|---|---|
| Strategic Exit | Keep visible with policy badge and divergence note | Sell recommendation may be computed but is non-actionable | Remove from executable sell cohort | BLOCKED_BY_POLICY, MONITOR_ONLY |
| Allocation Reduction | Keep visible for evidence transparency | Reduction may be computed but cannot execute as sell/trim | Exclude from reduction-execution candidates | BLOCKED_BY_POLICY, MONITOR_ONLY |
| Funding Sources | Keep visible as informational-only item | Do not generate executable funding sell action | Rank as non-executable (tail or separate blocked section) | Not a valid source for sale proceeds while policy active |
| CRA | Keep signal visible | CRA reduce/sell output becomes advisory-only | No executable sell priority | Policy suppresses sell execution path |
| PAP | Keep visible in queue output and suppressed list | Candidate may exist in intelligence view, but execution disabled | Excluded from executable sell list | Explicitly suppressed entry |
| PMI | Keep full visibility | No generation change; interpretation remains | No ranking role | Show policy and original intelligence side-by-side |

### B. SELL_LAST

| Surface | Visibility | Recommendation Generation | Ranking/Priority | Effective Behavior |
|---|---|---|---|---|
| Strategic Exit | Keep visible with policy badge | Sell recommendation still generated | Push to tail of sell cohort | DEFERRED_BY_POLICY when sell action exists |
| Allocation Reduction | Keep visible | Reduction recommendation still generated | De-prioritize versus unprotected reduction candidates | Reduce only after non-SELL_LAST candidates |
| Funding Sources | Keep visible | Funding-source eligibility preserved | Lower priority as liquidation source | Eligible but last-resort among sell candidates |
| CRA | Keep visible | CRA reduce recommendation remains | Lower recommendation priority for sell path | Deferred liquidation preference |
| PAP | Keep visible in executable queue | Generated normally when sell signal exists | Tail-ranking within relevant sell cohort | Sell last ordering rule |
| PMI | Keep full visibility | No generation change; interpretation remains | No ranking role | Explanation includes deferral constraint |

## Q3) Impact Scope (Visibility / Ranking / Priority / Generation)

### DO_NOT_SELL
- Visibility: Yes, keep visible everywhere with explicit protected badge.
- Ranking: Yes, remove from executable sell ranking.
- Priority: Yes, set to non-executable for sell actions.
- Recommendation generation: Intelligence generation remains; execution recommendation is constrained.

### SELL_LAST
- Visibility: Yes, keep visible everywhere.
- Ranking: Yes, apply tail-of-sell-cohort ordering.
- Priority: Yes, downgrade liquidation priority.
- Recommendation generation: Keep generation intact; apply execution ordering transform.

## Q4) Governance Precedence

Policy precedence hierarchy (highest to lowest):
1. Hard policy constraints (DO_NOT_SELL)
2. Execution-order policies (SELL_LAST)
3. Engine recommendations (CRA, Allocation Reduction, Strategic Exit)
4. Raw model/scoring signals

Conflict outcomes:
- If CW-DAS or any engine says SELL, but policy says DO_NOT_SELL: DO_NOT_SELL wins for execution; signal remains visible.
- If CRA says reduce/sell, but policy says SELL_LAST: CRA signal remains, execution priority is deferred behind non-SELL_LAST candidates.

## Canonical State Mapping Recommendation

- DO_NOT_SELL + sell-context signal -> BLOCKED_BY_POLICY / MONITOR_ONLY
- SELL_LAST + sell-context signal -> DEFERRED_BY_POLICY / REDUCE_SELL_LAST (or sell-last equivalent)
- Any policy + non-sell action -> policy annotation only unless policy semantics apply

This preserves explainability while enforcing operator intent.
