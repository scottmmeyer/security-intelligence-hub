# Phase 22D.9A — Q6: Policy Analysis

**Phase:** 22D.9A — CW-DAS Settlement-Aware Deployment Audit  
**Date:** 2026-06-02  
**Context:** CW-DAS uses `deployable_mv = $7,658.25` (reported, pre-settlement).  
Settlement-adjusted figure is `$4,091.70`. Gap: $3,566.55.

---

## Option A — Leave System Unchanged

### Description
No changes to code, display, or behavior. The system continues to use reported
deployable cash as the sole basis for CW-DAS sizing and UI display.

### Governance Impact
- **Negative.** The mandate compliance projection (`cash_after_pct = 7.00%`) is
  technically false whenever pending settlement exists. The system presents a
  governance-safe outcome that will not materialize.
- On-record audit artifacts (`deployment_plan.json`, `recommendations.json`)
  contain overstated allocation amounts.
- If a regulator or compliance reviewer checks the deployment plan against
  actual post-deployment portfolio state, they will find a systematic discrepancy
  equal to the settlement amount.

### Operator Clarity
- **None.** The operator has no way to know their dry powder is overstated.
- Risk of mandate breach is entirely invisible.
- The UI actively misleads (shows 7.0% "after").

### Accounting Purity
- **Preserved.** The reported figures match the Fidelity export exactly.
- Pending activity is correctly classified.
- No double-counting or incorrect attribution.

### Recommendation Quality
- **Degraded.** CW-DAS recommends 1.87× too much capital per position.
- Following the plan in full will breach the mandate.
- Recommendation quality is undermined by the cash overstatement, not by any
  defect in the scoring or ranking logic.

### Implementation Complexity
- **None.** No changes required.

### Risk Classification
- Accepts mandate breach risk at T+1 on every settlement-day run.
- Frequency of occurrence: every time an equity purchase is made (which is the
  purpose of the system — this is the normal operating condition).

### Verdict: **NOT RECOMMENDED** for current operations.

---

## Option B — Display Both Reported and Adjusted; CW-DAS Sizing Unchanged

### Description
Backend: After `compute_deployable_cash()`, runner.py computes advisory settlement
fields (`pending_settlement_mv`, `adjusted_cash_mv`, `adjusted_deployable_mv`) and
appends them to `cash_context` when negative ACCOUNTING_ADJUSTMENT rows exist.

UI: Show both reported and adjusted figures side-by-side in the cash context strip
and deployment plan panel. CW-DAS recommended amounts continue to be sized off
the reported figure.

### Governance Impact
- **Moderate improvement.** Audit artifacts now carry both figures.
- The "official" `deployable_cash` in `deployment_plan.json` remains the reported
  figure — governance record unchanged.
- Mandate compliance projection remains incorrect (`cash_after_pct = 7.00%`),
  but an adjusted projection could be shown.
- The deployment plan's `deployable_cash` (reported) and the advisory
  `adjusted_deployable_mv` are clearly distinguished.

### Operator Clarity
- **Significantly improved.** Operator sees both $7,658 and $4,092 labeled clearly.
- Settlement notice with T+1 date estimation informs decision.
- Operator must still choose which figure to act on — system does not enforce the
  correct figure.

### Accounting Purity
- **Fully preserved.** Core calculations unchanged.
- New fields are advisory addenda, not replacements.
- Reported deployable_cash remains the accounting record.

### Recommendation Quality
- **Partially improved.** CW-DAS `suggested_add` amounts remain based on $7,658.
  The operator sees both figures but must manually scale down if they choose to
  use the adjusted amount.
- The "Recalculate" button could be pre-populated with $4,092 instead of $7,658
  when pending settlement exists — this would allow the operator to regenerate
  the plan with correct sizing in one click.

### Implementation Complexity
- **Low.** ~15 lines in `runner.py` + conditional UI block.
- No change to `compute_deployable_cash()` or `build_deployment_plan()`.
- No test changes required for existing tests.
- New tests needed for the advisory field computation.

### Risk Classification
- Operator awareness substantially improved.
- Mandate breach risk reduced (operator is informed) but not eliminated (system
  does not enforce the correct figure for CW-DAS sizing).
- Breach remains possible if operator ignores the advisory.

### Verdict: **MINIMUM ACCEPTABLE REMEDIATION.**
Acceptable as a short-term fix. Does not fully solve the recommendation sizing issue.

---

## Option C — Display Both Values; CW-DAS Sizing Uses Adjusted Cash When Pending Exists

### Description
Backend: When negative ACCOUNTING_ADJUSTMENT rows exist:
1. Compute `adjusted_deployable_mv = $4,091.70`
2. Pass this to `build_deployment_plan()` as the `deployable_cash` override
3. All `suggested_add` amounts are computed from $4,091.70
4. Both reported and adjusted figures are displayed in UI

The `deployment_plan.deployable_cash` would be set to the adjusted figure.
The reported figure would be shown as an informational field.

### Governance Impact
- **Major improvement.** Deployment plan is mandate-safe.
- `deployment_plan.deployable_cash` changes from $7,658 to $4,092 on runs with
  pending settlement — this is a governance-level change.
- Prior runs without pending activity are unaffected.
- Requires explicit governance approval: the mandate floor calculation uses
  adjusted (settlement-aware) cash as the operative figure.

### Operator Clarity
- **Maximum.** A single `suggested_add` figure per position that is mandate-safe.
  Settlement notice explains the reduction.
- No mental math required.
- "Available to Deploy" = $4,092, "Allocated" = $4,092, "Remaining" = $0.
  Post-deployment cash projection = 7.0% (which is now actually true).

### Accounting Purity
- **Modified.** The deployment plan's `deployable_cash` no longer matches the
  accounting record's SPAXX balance directly.
- However, it remains derivable from the accounting record (SPAXX - pending).
- The relationship is transparent and documented.
- Risk: if a non-settlement ACCOUNTING_ADJUSTMENT row exists (not yet observed,
  but possible), it could incorrectly reduce deployable cash.

### Recommendation Quality
- **Fully restored.** CW-DAS recommendations are properly sized for the actual
  deployment capacity. Following the plan will not cause a mandate breach.

### Implementation Complexity
- **Moderate.** Changes to `runner.py` (pass adjusted figure to planner),
  `deployment_planner.py` (minor, already accepts override), `app.js` (dual display).
- All `deployment_plan.deployable_cash` assertions in tests must be updated for
  runs with pending settlement.
- Classification guard required: only `SAFE_TO_OFFSET_CASH` adjustment types
  should reduce deployable cash (currently all observed types qualify, but a
  check should be added to prevent future edge cases).
- Server restart + re-run required for validation.

### Risk Classification
- Mandate breach risk eliminated for runs processed with pending settlement.
- Classification guard prevents over-adjustment for non-settlement rows.
- Regression risk: existing test values reference $7,658-based allocations;
  must be updated.

### Verdict: **RECOMMENDED for implementation in next development sprint.**
Full remediation. Addresses the recommendation sizing defect directly.

---

## Comparative Scorecard

| Dimension | Option A | Option B | Option C |
|-----------|:--------:|:--------:|:--------:|
| Mandate breach risk | HIGH | MEDIUM | LOW |
| Operator clarity | LOW | HIGH | HIGH |
| Accounting purity | 100% | 100% | ~99% (transparent) |
| Recommendation quality | POOR | PARTIAL | FULL |
| CW-DAS sizing corrected | No | No | **YES** |
| Implementation complexity | None | Low | Moderate |
| Governance change required | No | No | **YES** |
| Test updates required | None | Minimal | Yes (expected values) |
| Deployment plan mandate-safe | No | No | **YES** |
| Self-certifying next run | N/A | N/A | Yes |

---

## Transition Recommendation

**Immediate (this sprint):** Implement Option B.
- Unblocks operator awareness within one code change.
- Zero regression risk.
- Operator can use the "Recalculate" button with the adjusted figure to get
  correct CW-DAS sizing today, without requiring a code change to the planner.

**Next sprint:** Implement Option C.
- Changes `deployable_cash` source to adjusted when pending settlement exists.
- Update tests to reflect new expected values on settlement-day runs.
- Requires governance sign-off on changing the operative cash metric.

Option A is unacceptable for a production mandate-management system.

---

## Governance Decision Required for Option C

Before implementing Option C, the following must be explicitly decided:

1. **Cash metric governance**: Is the operative "deployable cash" for CW-DAS
   the reported (accounting) figure or the settlement-adjusted figure?
   → Current implicit answer: reported. Proposed: adjusted when pending exists.

2. **Classification boundary**: Which `ACCOUNTING_ADJUSTMENT` row types qualify
   for the offset? Current inventory shows 100% are Fidelity purchase settlements.
   A formal whitelist should be codified.

3. **Mandate floor basis**: Should the mandate compliance projection use
   settlement-adjusted cash? (Currently uses reported SPAXX for both numerator
   and denominator denominator basis.) Option C changes the numerator only —
   the floor_mv denominator remains based on total_market_value as ingested.
