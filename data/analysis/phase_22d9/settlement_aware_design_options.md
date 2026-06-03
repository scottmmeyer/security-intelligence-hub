# Phase 22D.9 — Workstream A: Settlement-Aware Design Options

**Phase:** 22D.9 — Settlement-Aware Deployable Cash  
**Date:** 2026-06-02  
**Context:** Phase 22D.8A established that PENDING ACTIVITY rows (-$3,566.55) are excluded
from `cash_mv` but represent already-committed settlement debits that will reduce SPAXX
at T+1. The current system is accounting-correct but shows the operator a pre-settlement
cash balance as the basis for deployment decisions.

---

## Option A — No Behavioral Change; Display Warning Only

### Behavior
No changes to `compute_deployable_cash()`. Deployable cash continues to reflect pre-settlement
SPAXX balance. When one or more `ACCOUNTING_ADJUSTMENT` rows with negative market value are
detected in the portfolio, a warning banner is displayed in the UI.

### User Experience
```
Deployable Cash: $7,658
⚠ Settlement Notice: $3,567 in pending activity may reduce available cash.
```

### Pros
- Zero risk of changing calculation outputs that downstream systems depend on
- Easy to implement (UI-only change; no backend impact)
- The reported figure remains internally consistent with all existing artifact fields
  (`deployment_plan.deployable_cash`, `cash_context.deployable_mv`, reconciliation)
- Satisfies audit requirements: "reported figure" is always the unadjusted number
- No regression risk to any prior test
- Complies with current governance model: system shows what Fidelity says, flags ambiguity

### Cons
- Does not give the operator a clear actionable number
- The operator must mentally compute the adjustment
- Risk: operator deploys $7,658, breaches 7% mandate floor after T+1 settlement
- Warning text is advisory only — easy to ignore

### Governance Implications
- `deployment_plan.deployable_cash` remains $7,658 — operator must know to discount it
- If the operator deploys $7,658 and settlement reduces SPAXX, a subsequent run will show
  the portfolio below mandate — RC-05 or mandate drift alert will fire
- Governance is reactive (post-settlement check), not proactive

---

## Option B — Display Both; Reported and Adjusted Side-by-Side (Recommended)

### Behavior
No changes to `compute_deployable_cash()`. The function continues to return the same
9-field dict. A new read-only field `adjusted_deployable_mv` is added to the
`cash_context` payload computed in `runner.py` by subtracting negative
`ACCOUNTING_ADJUSTMENT` holdings from `cash_mv` — but this is used **only for display**.

The existing `deployable_mv` field is not changed. The adjustment is additive/non-destructive.

### User Experience
```
Current Cash:    8.59% ($41,279)
Pending:        -$3,567  (unsettled activity)
Adjusted Cash:   7.85% ($37,713)

Deployable Cash (reported):   $7,658   ← based on current account balance
Deployable Cash (adjusted):   $4,092   ← accounting for pending settlement
                                        ↑ Use this figure for deployment decisions
```

### Pros
- Operator sees both numbers with clear labeling
- Preserves the accounting record (reported figure unchanged)
- Eliminates the governance gap — operator has the adjusted figure before deploying
- Low regression risk: original fields untouched; `adjusted_deployable_mv` is a new field
- Distinguishes "what Fidelity reports" from "what is truly available"
- Self-corrects: when no pending activity exists, both figures are identical; dual display
  can be suppressed to avoid UI clutter

### Cons
- Two numbers for the same concept may confuse operators unfamiliar with T+1 settlement
- Requires clear, consistent labeling to avoid misinterpretation
- Backend change needed (new field in `cash_context` or separate payload)

### Governance Implications
- `deployment_plan.deployable_cash` continues to equal the reported figure → audit trail preserved
- New `adjusted_deployable_mv` field is advisory — operator uses it but it is not enforced
- When pending activity resolves, both figures converge → system self-corrects
- Mandate compliance is measured against reported figure (per governance model)

---

## Option C — Planner Uses Adjusted Cash When Negative Adjustments Exist

### Behavior
`compute_deployable_cash()` is modified to subtract negative `ACCOUNTING_ADJUSTMENT`
holdings from `cash_mv` before computing the floor comparison:

```python
# Proposed modification
adjustment_mv = sum(h.market_value for h in all_holdings
                    if h.operational_state == "ACCOUNTING_ADJUSTMENT" and h.market_value < 0)
effective_cash_mv = cash_mv + adjustment_mv  # adjustment_mv is negative
deployable_mv = max(0.0, effective_cash_mv - floor_mv)
```

`deployment_plan.deployable_cash` would reflect the adjusted figure: $4,092.

### User Experience
```
Cash: 8.59%   Deployable: $4,092
(Settlement-adjusted)
```

### Pros
- The operator's single deployable cash number is the correct, conservative figure
- No dual-display complexity
- Guards against mandate breach at T+1 settlement
- Strongest governance protection

### Cons
- **Regression risk**: All existing tests, reconciliation checks, and expected values
  reference the unadjusted calculation. Changes to `compute_deployable_cash()` must be
  reflected in all tests and audit trails.
- `deployment_plan.deployable_cash` changes — any downstream consumer that cached or
  compared prior figures will see a break
- The function signature changes (must accept all holdings, not just investable holdings)
- Edge cases: what if `ACCOUNTING_ADJUSTMENT` rows are NOT settlement-related? (Currently
  all observed adjustments are settlement-related, but that is not guaranteed by the data model)
- Requires classification narrowing: not all `ACCOUNTING_ADJUSTMENT` rows should be
  subtracted (e.g., a $0.00 zero-MV adjustment row should not be included)
- Audit complexity increases: the reported deployable cash is no longer directly derivable
  from the SPAXX balance alone

### Governance Implications
- This option changes the cash governance calculation itself — requires explicit approval
  as a governance framework change, not just a display change
- Prior runs (PAR-20260602-4A83D5BD, etc.) would be inconsistent with new calculation
- Mandate compliance threshold (7%) is applied against an adjusted figure — this is a
  philosophical change in what "cash" means in the mandate context
- Risk: if a non-settlement `ACCOUNTING_ADJUSTMENT` row is incorrectly included, the
  system will systematically understate deployable cash

---

## Side-by-Side Comparison

| Dimension | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| Backend change | No | Minimal (new field) | Yes (core function) |
| UI change | Warning banner | Dual display | Single updated display |
| Reported deployable_mv | $7,658 (unchanged) | $7,658 (unchanged) | $4,092 (changed) |
| Adjusted deployable_mv | Not computed | $4,092 (advisory) | $4,092 (operative) |
| Operator clarity | LOW | HIGH | MEDIUM |
| Regression risk | None | Very low | Moderate |
| Governance change? | No | No | Yes |
| Self-corrects post-settlement | N/A | Yes (dual display collapses) | Yes |
| Recommended | No | **YES** | Future consideration |

---

## Recommendation

**Option B** is recommended for Phase 22D.9.

It achieves the primary objective (operator sees the correct deployment figure) while
preserving the accounting record, avoiding governance model changes, and presenting minimal
regression risk. The dual display with clear "Settlement-Adjusted" labeling directly answers
the operator's question: "How much capital is truly available right now?"

Option C should be tracked as a future improvement once:
1. The `ACCOUNTING_ADJUSTMENT` classification is tightened to guarantee only settlement rows
2. Tests are updated to reflect the new calculation model
3. Governance explicitly approves adjusting the mandate cash floor against settlement-aware cash
