# Phase 22D.9B — Q7: Option C Revalidation

**Phase:** 22D.9B — ACCOUNTING_ADJUSTMENT Taxonomy Audit  
**Date:** 2026-06-02  
**Question:** Given the full ACCOUNTING_ADJUSTMENT taxonomy evidence, is Phase 22D.9A's
recommended Option C remediation still the right approach? Are there false positive
or false negative risks? What governance conditions must be satisfied before implementation?

---

## Option C Definition (from Phase 22D.9A)

Option C modifies the CW-DAS planner to use settlement-adjusted deployable cash:

```python
# Compute settlement adjustment from negative ACCOUNTING_ADJUSTMENT rows
adjustment = sum(
    abs(h.market_value)
    for h in non_investable
    if h.operational_state == "ACCOUNTING_ADJUSTMENT" and h.market_value < 0
)
adjusted_deployable_mv = deployable_mv - adjustment
# CW-DAS planner uses adjusted_deployable_mv instead of deployable_mv
```

**Effect on reference run PAR-20260602-8CF1CB84:**
- deployable_mv (reported): $7,658.25
- adjustment: $3,566.55 (one -$3,566.55 ACCOUNTING_ADJUSTMENT row)
- adjusted_deployable_mv: $4,091.70
- All 31 suggested_add values resized by factor 0.534× (not 1.0×)
- Post-deployment cash: exactly at 7.0% mandate floor

---

## False Positive Risk (Incorrectly Reduces Deployable Cash)

A false positive occurs when Option C subtracts cash that should NOT be subtracted
— i.e., cash that is NOT committed to an unsettled purchase.

**Q4 finding:** False positives would arise from Classes C', E, or F rows with mv < 0.

| False Positive Source | Observed? | Option C (mv < 0 filter) | Option C (safe_to_offset_cash filter) |
|----------------------|-----------|--------------------------|---------------------------------------|
| Class C' — missing counterpart in symmetric pair | NO (0 rows) | Not protected | Protected (default False) |
| Class E — corporate action | NO (0 rows) | Not protected | Protected (default False) |
| Class F — bookkeeping artifact | NO (0 rows) | Not protected | Protected (default False) |
| Any other new pattern with mv < 0 | NO (0 rows) | Not protected | Protected (default False) |

**Current false positive rate: 0 / 42 rows (0%)**

No false positives have occurred in 42 rows across 9 snapshots and 5 calendar days.

**Residual false positive risk:**
- LOW for current mandate and brokerage relationship (Fidelity)
- MEDIUM for unobserved corporate action scenarios
- Protection: implement `safe_to_offset_cash` attribute before Option C deploys

---

## False Negative Risk (Fails to Reduce Cash When It Should)

A false negative occurs when Option C FAILS to subtract cash that IS committed
to an unsettled purchase — i.e., a pending purchase that is not classified as
ACCOUNTING_ADJUSTMENT.

**Paths to a false negative:**

| Scenario | Could Happen? | Effect |
|----------|--------------|--------|
| Pending purchase with positive MV | Impossible under current classification logic | N/A |
| Pending purchase classified as PENDING_SETTLEMENT instead of ACCOUNTING_ADJUSTMENT | Possible if row has description keyword + negative mv | PENDING_SETTLEMENT row → not in ACCOUNTING_ADJUSTMENT → not offset by Option C |
| Pending purchase classified as ACTIVE_POSITION | Only if mv > 0 (impossible for a purchase debit) | N/A |

**Current false negative rate: 0 / 36 Class A rows (0%)**

All 36 pending purchase rows are correctly classified as ACCOUNTING_ADJUSTMENT
because: (a) description is blank, (b) symbol is not "PENDING", (c) mv < 0.

**Residual false negative risk:**
- LOW — the `mv < 0` condition is physically reliable for purchase settlements
- If Fidelity were to ever label a purchase debit with a description containing
  "PENDING", the PENDING_SETTLEMENT branch would win and the row would escape
  Option C's filter. Not observed.

---

## Impact on Mandate Compliance (Reference Run Validation)

**Without Option C:**
- CW-DAS budget: $7,658.25
- If all suggestions executed: cash depleted by $7,658.25
- Post-deployment SPAXX balance: $41,279.15 - $7,658.25 = $33,620.90
- But pending settlement will debit $3,566.55 at T+1
- Post-settlement cash: $33,620.90 - $3,566.55 = $30,054.35
- Post-settlement cash%: $30,054.35 / $480,298.55 = 6.26% → **BREACH** (floor = 7.0%)

**With Option C:**
- CW-DAS budget: $4,091.70 (adjusted for pending $3,566.55)
- If all suggestions executed: cash depleted by $4,091.70
- Post-deployment SPAXX balance: $41,279.15 - $4,091.70 = $37,187.45
- Pending settlement at T+1: $37,187.45 - $3,566.55 = $33,620.90
- Post-settlement cash%: $33,620.90 / $480,298.55 = 7.00% → **EXACTLY AT FLOOR**

Option C is exact. The mandate floor is preserved to the penny in the reference run.

---

## Operational Complexity Assessment

**Changes required in runner.py:**

1. Filter `non_investable` holdings for ACCOUNTING_ADJUSTMENT rows with mv < 0
2. Sum absolute values → `settlement_adjustment`
3. Compute `adjusted_deployable_mv = deployable_mv - settlement_adjustment`
4. Pass `adjusted_deployable_mv` (not `deployable_mv`) to CW-DAS planner
5. Persist `adjusted_deployable_mv` and `settlement_adjustment` to snapshot.json
   and deployment_queue.json for audit lineage

**Estimated code changes:** ~20 lines in runner.py

**Test impact:**
- Any test that asserts on `suggested_add` amounts for a run containing
  ACCOUNTING_ADJUSTMENT rows must be updated
- Tests using runs WITHOUT pending activity are unaffected
- Estimated affected test count: ~5 assertions across 2–3 test files
- Pre-settlement runs (no ACCOUNTING_ADJUSTMENT rows): settlement_adjustment = 0,
  adjusted_deployable_mv = deployable_mv (no behavioral change)

---

## Governance Conditions for Proceeding

Option C should NOT be implemented until all of the following conditions are met:

| Condition | Status | Notes |
|-----------|--------|-------|
| 22D.9B forensic audit complete | ✓ COMPLETE | This document is the final Q7 |
| False positive risk assessed | ✓ COMPLETE | 0 observed; theoretical risk documented |
| False negative risk assessed | ✓ COMPLETE | 0 observed; structural protection confirmed |
| Mandate compliance benefit confirmed | ✓ COMPLETE | Reference run: 6.26% → 7.00% |
| safe_to_offset_cash design documented | ✓ COMPLETE | Q5/Q6 deliverables |
| Phase 22D.9B final verdict accepted | ⬜ PENDING | Requires verdict document sign-off |
| Implementation plan drafted | ⬜ PENDING | Phase 22D.10 |
| Test impact enumerated | ⬜ PENDING | Phase 22D.10 pre-work |

---

## Revalidation Verdict

**Option C is CONFIRMED as the correct remediation for Phase 22D.9A's
material recommendation defect.**

The 22D.9B forensic investigation has validated every critical assumption
underlying the Option C proposal:

1. **All 36 negative ACCOUNTING_ADJUSTMENT rows are pending purchase settlements**
   → The offset is economically correct for 100% of observed cases.

2. **No false positives in 42 rows across 9 snapshots**
   → Option C would not have incorrectly reduced deployable cash in any prior run.

3. **Classification logic structurally prevents positive-MV rows from entering
   ACCOUNTING_ADJUSTMENT**
   → Option B (pending sale) false positive risk is structurally eliminated.

4. **The mandate breach is deterministic and exactly remediable**
   → Post-settlement cash goes from 6.26% to exactly 7.00% with Option C active.

**One governance condition strengthens Option C:**
Implement `safe_to_offset_cash` attribute alongside Option C (not as a prerequisite
but as a co-deliverable) to protect against theoretical Classes C', E, F which
have not materialized but represent non-zero future risk.

**Phase 22D.10 should proceed as planned.**
