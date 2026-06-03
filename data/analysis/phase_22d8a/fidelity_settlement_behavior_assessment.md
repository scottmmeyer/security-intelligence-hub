# Phase 22D.8A — Fidelity Settlement Behavior Assessment

**Run:** PAR-20260602-8CF1CB84  
**Date:** 2026-06-02

---

## Fidelity Export Settlement Mechanics

### How Fidelity Handles Executed but Unsettled Purchases

Fidelity's portfolio position export (CSV) uses a **T+1 settlement pattern**:

When a purchase order is executed:

1. **Immediately:** The purchased security appears in the CSV at current market value.
2. **Immediately:** SPAXX balance remains at the pre-purchase amount (not yet debited).
3. **Immediately:** A "Pending activity" row appears with a **negative market value** equal to the
   purchase cost (not market value). This negative value signals the forthcoming SPAXX debit.
4. **After T+1 settlement:** The "Pending activity" row disappears. SPAXX balance is reduced by
   the settlement amount.

### Observed in This Export

From `Portfolio_Positions_Jun-02-2026 (2).csv`:

| Row | Symbol | Description | Market Value |
|-----|--------|-------------|-------------|
| Position | PRG | PROG HOLDINGS INC COM NPV | $3,622.00 |
| Settlement | (blank) | Pending activity | **-$3,566.55** |
| Cash | SPAXX | HELD IN MONEY MARKET (Individual - TOD) | $41,209.64 |

The $55.45 difference between PRG's MV ($3,622.00) and the pending debit ($3,566.55)
represents unrealized P&L since purchase execution.

---

## Is This a Known Fidelity Artifact?

**Yes.** This is standard Fidelity CSV behavior for accounts with unsettled T+1 equity purchases.

Characteristics:
- The "Pending activity" row appears in the account's holdings section
- It always has a **negative** value (cash debit, not a position)
- It has no symbol, no security type, no quantity
- It disappears automatically after settlement
- It is transient: present only for 1–2 business days post-execution

---

## Does the SIH System Understand This Behavior?

### Ingestion awareness: PARTIAL

`ingestion.py` contains `_PENDING_DESCRIPTION_KEYWORDS = {"PENDING ACTIVITY", "PENDING", "SETTLEMENT"}`
and has a `PENDING_SETTLEMENT` operational state, suggesting the system was designed to
recognize pending rows.

However, in this export the "Pending activity" row has **blank symbol and blank description**
in the parsed CSV fields. The `_PENDING_DESCRIPTION_KEYWORDS` check fails (desc is empty).
The row is caught by the fallback `mv < 0 → ACCOUNTING_ADJUSTMENT` check instead.

### Cash calculation awareness: NO

`compute_deployable_cash()` uses `sum(h.market_value for h in holdings if h.is_cash_equivalent)`.
Neither `PENDING_SETTLEMENT` nor `ACCOUNTING_ADJUSTMENT` holdings carry `is_cash_equivalent=True`.
PENDING ACTIVITY does not reduce `cash_mv` regardless of which operational state it receives.

---

## Settlement Window Timing

The settlement window for this specific trade (PRG purchase, Jun 2):
- **T+0 (Jun 2, 2026):** Execution day — export shows PENDING ACTIVITY
- **T+1 (Jun 3, 2026):** Settlement day — SPAXX reduced, PENDING ACTIVITY row disappears

During the T+0 window (current state), any system reading SPAXX as "available cash"
without subtracting PENDING ACTIVITY will overstate deployable cash.

---

## Scope of Impact

**When does this matter?**
1. The operator ingests a Fidelity export on the same day as an equity purchase
2. The purchase has not yet settled (T+1 or T+2)
3. The system computes deployable cash using the pre-settlement SPAXX balance

**Magnitude:** Exactly equal to the sum of all PENDING ACTIVITY rows
- In this run: $3,566.55 overstatement
- Reported deployable: $7,658.25 → True deployable: $4,091.70

**Duration:** Transient. Self-corrects after settlement without any system changes.

---

## Is This a Defect, an Artifact, or Expected Behavior?

This is a **known broker export artifact**, not a data error in the Fidelity CSV.
Fidelity is correctly reporting the settlement state. The overstatement exists because
the SIH system computes cash_mv from SPAXX alone (pre-settlement balance) without
subtracting the earmarked settlement debit.

**Three response options are available — see `phase_22d8a_final_verdict.md` for recommendation.**
