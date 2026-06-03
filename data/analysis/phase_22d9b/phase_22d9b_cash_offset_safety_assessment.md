# Phase 22D.9B — Q4: Cash Offset Safety Assessment

**Phase:** 22D.9B — ACCOUNTING_ADJUSTMENT Taxonomy Audit  
**Date:** 2026-06-02  
**Question:** For each class of ACCOUNTING_ADJUSTMENT, would subtracting the amount
from deployable cash be Correct, Incorrect, or Ambiguous?

---

## Context

Option C (Phase 22D.9A recommendation) proposes:

```python
adjusted_deployable_mv = deployable_mv - sum(
    abs(h.market_value)
    for h in non_investable
    if h.operational_state == "ACCOUNTING_ADJUSTMENT" and h.market_value < 0
)
```

This document assesses whether this offset is safe for each observed and
theoretically possible class of ACCOUNTING_ADJUSTMENT row.

---

## Class A — PENDING_PURCHASE (36 observed rows)

**Verdict: CORRECT to offset**

| Assessment Dimension | Finding |
|----------------------|---------|
| Cash flow direction | Cash already debited (purchase placed). Cash is "gone" before settlement. |
| Real deployable reduction? | YES — the cash is committed, cannot be deployed again |
| Safe to subtract from cash_mv? | YES |
| Overstates cash risk? | NO — the debit is real and will clear at T+1 |
| Would cause false mandate breach? | NO — prevents a real mandate breach |
| Confidence | HIGH |

**Reasoning:** When an equity purchase is placed on day T, Fidelity immediately
reflects the cash outflow as a negative "Pending activity" entry. The SPAXX balance
has NOT yet decreased (it decreases at T+1 settlement), so `cash_mv` (derived from
SPAXX) still shows the pre-purchase balance. The "Pending activity" negative amount
is the correction that makes `cash_mv` economically accurate.

Subtracting -$3,566.55 from cash_mv to get adjusted_cash_mv = $37,712.60 is
exactly correct. The money was spent when the purchase was placed.

---

## Class C — CASH_TRANSFER net zero (6 observed rows, MV = 0.00)

**Verdict: CORRECT to offset (offset = $0.00, no effect)**

| Assessment Dimension | Finding |
|----------------------|---------|
| Cash flow direction | Symmetric: $X out of one account, $X into another. Net = $0. |
| Real deployable reduction? | NO — the net cash position is unchanged |
| Safe to subtract from cash_mv? | YES — subtracting $0 has no effect |
| Overstates cash risk? | NO |
| Would cause false mandate breach? | NO |
| Confidence | HIGH |

**Reasoning:** These rows result from `normalize_and_aggregate_holdings()` summing
a positive and negative PENDING ACTIVITY row to net zero. The offset amount is $0,
so the Option C formula subtracts nothing. No governance risk.

---

## Class B — PENDING_SALE (0 observed, theoretical)

**Verdict: INCORRECT to offset (but does not apply under current classification logic)**

| Assessment Dimension | Finding |
|----------------------|---------|
| Cash flow direction | Cash incoming: equity sold, proceeds pending T+1 |
| Real deployable reduction? | NO — cash will INCREASE at settlement |
| Safe to subtract from cash_mv? | NO — would reduce deployable cash when it should increase |
| Under current logic, would appear as ACCOUNTING_ADJUSTMENT? | NO |
| How it would appear? | ACTIVE_POSITION (mv > 0 → not ACCOUNTING_ADJUSTMENT) |
| Confidence | HIGH |

**Reasoning:** A pending sale creates positive pending activity (cash coming in,
not going out). Under the current classification logic, positive-MV rows cannot
receive the ACCOUNTING_ADJUSTMENT state. So Option C would never subtract pending
sale proceeds from deployable cash.

The risk direction is: pending sale proceeds are ACTIVE_POSITION and thus included
in `total_market_value`. This slightly overstates total MV until settlement. The
effect on deployable cash is negligible (pending sale is not SPAXX, so it doesn't
directly enter `cash_mv`).

**Conclusion for Option C:** Pending sale would NOT trigger an incorrect offset.
The classification logic provides natural protection.

---

## Class D — DIVIDEND_ACCRUAL (0 observed, theoretical)

**Verdict: AMBIGUOUS (depends on Fidelity representation)**

| Assessment Dimension | Finding |
|----------------------|---------|
| Cash flow direction | Cash incoming: dividend declared, not yet paid |
| Real deployable reduction? | NO — cash is accruing |
| Safe to subtract from cash_mv? | NO — dividend accruals should add to, not reduce, deployable cash |
| Would appear as ACCOUNTING_ADJUSTMENT with negative MV? | UNLIKELY |
| How Fidelity typically represents it? | As a separate dividend accrual line, not "Pending activity" |
| Confidence | MEDIUM |

**Reasoning:** Fidelity dividend accruals are typically represented as separate
line items in the CSV (not as "Pending activity"). If they were to appear with
negative MV under "Pending activity", offsetting would be incorrect. However,
this has not been observed and the pattern seems unlikely given Fidelity's CSV
format conventions.

**Conclusion for Option C:** Very low probability of producing an ACCOUNTING_ADJUSTMENT
row. Would require further investigation if ever observed.

---

## Class E — CORPORATE_ACTION (0 observed, theoretical)

**Verdict: AMBIGUOUS (requires case-by-case assessment)**

| Assessment Dimension | Finding |
|----------------------|---------|
| Cash flow direction | Variable: could be positive (spinoff cash) or negative (subscription, rights issue) |
| Real deployable reduction? | DEPENDS on action type |
| Safe to subtract from cash_mv? | NOT IN GENERAL — requires explicit review |
| Would appear as ACCOUNTING_ADJUSTMENT with negative MV? | POSSIBLE for cash subscriptions |
| Confidence | LOW |

**Reasoning:** Corporate actions like rights offerings, merger elections, or tender
offers can produce negative cash entries before settlement. If one appeared as
"Pending activity" with negative MV, it would be classified as ACCOUNTING_ADJUSTMENT
and subtracted under Option C. Whether this is correct depends on the specific action.

**Conclusion for Option C:** This is the highest-risk theoretical class. A governance
whitelist (safe_to_offset_cash) would protect against this edge case.

---

## Class F — FIDELITY_BOOKKEEPING (0 observed, theoretical)

**Verdict: INCORRECT to offset**

| Assessment Dimension | Finding |
|----------------------|---------|
| Cash flow direction | Bookkeeping artifact with no real cash impact |
| Real deployable reduction? | NO — the amount doesn't represent real capital |
| Safe to subtract from cash_mv? | NO |
| Would appear as ACCOUNTING_ADJUSTMENT with negative MV? | UNLIKELY in practice |
| Confidence | LOW (theoretical only) |

**Conclusion for Option C:** If such a row appeared, the governance attribute
`safe_to_offset_cash = False` would prevent incorrect subtraction.

---

## Class G — UNKNOWN (0 observed)

**Verdict: INCORRECT to offset (precautionary)**

| Assessment Dimension | Finding |
|----------------------|---------|
| Cash flow direction | Unknown |
| Real deployable reduction? | Unknown |
| Safe to subtract from cash_mv? | NO — unknown origin requires investigation |
| Governance default? | safe_to_offset_cash = False |
| Confidence | N/A (no data) |

---

## Summary Matrix

| Class | Observed? | Count | Net MV | Offset Correct? | Option C Risk |
|-------|-----------|-------|--------|-----------------|---------------|
| A — PENDING_PURCHASE | YES | 36 | -$60,199.65 | **CORRECT** | None |
| C — CASH_TRANSFER (net=0) | YES | 6 | $0.00 | CORRECT (noop) | None |
| B — PENDING_SALE | No | 0 | — | Incorrect (but N/A under current logic) | Structural protection |
| D — DIVIDEND_ACCRUAL | No | 0 | — | Ambiguous | Low probability |
| E — CORPORATE_ACTION | No | 0 | — | Ambiguous (case-by-case) | Medium risk if observed |
| F — FIDELITY_BOOKKEEPING | No | 0 | — | Incorrect | Low probability |
| G — UNKNOWN | No | 0 | — | Precautionary incorrect | Very low probability |

---

## Bottom Line

**For the observed universe (42 rows, 100% Class A or C):**

Option C is safe. Subtracting negative ACCOUNTING_ADJUSTMENT market values from
deployable cash is economically correct for all 36 Class A rows, and has zero effect
on the 6 Class C rows (MV=0).

**For the unobserved universe (Classes B–G):**

The current classification logic structurally protects against Class B (positive-MV
rows cannot be ACCOUNTING_ADJUSTMENT). Classes D–G have not been observed and would
require the `safe_to_offset_cash` governance attribute to ensure correct handling.

**The primary governance gap is Class E (corporate actions) and Class F
(bookkeeping artifacts) — both theoretical but both scenarios where an incorrect
offset would understate deployable cash and potentially prevent deployment when
capacity actually exists.**
