# Phase 22D.8A — Deployable Cash Reconciliation

**Run:** PAR-20260602-8CF1CB84  
**Date:** 2026-06-02  
**Status:** FINDING — Deployable cash overstated by $3,566.55 due to unsettled pending activity

---

## Reported Values (Current System Output)

| Metric | Value | Source |
|--------|-------|--------|
| `total_market_value` | $480,298.55 | `snapshot.total_market_value` |
| `cash_mv` | $41,279.15 | Sum of `is_cash_equivalent=True` holdings |
| `cash_pct` | 8.5945% | `cash_mv / total_mv` |
| `mandate_cash_target_pct` | 7.0% | CONCENTRATED_ALPHA mandate profile |
| `effective_floor_pct` | 7.0% | `max(2.0, 7.0)` |
| `floor_mv` | $33,620.90 | `7.0% × $480,298.55` |
| `excess_mv` | $7,658.25 | `cash_mv − floor_mv` |
| `deployable_mv` | **$7,658.25** | `max(0, cash_mv − floor_mv)` |

---

## Pending Activity Identification

From `holdings.csv`, one row with negative market value:

| Field | Value |
|-------|-------|
| Symbol | `PENDING ACTIVITY` |
| Market Value | **-$3,566.55** |
| `is_cash_equivalent` | `False` |
| `operational_state` | `ACCOUNTING_ADJUSTMENT` |
| Source in raw CSV | Fidelity "Pending activity" row (blank symbol, blank description) |

**Economic meaning:** Fidelity exports pending settlement debits as a standalone negative
market value row. When PRG (PROG HOLDINGS) was purchased at $3,566.55 cost, Fidelity:
- Added PRG to holdings at current market value ($3,622.00)
- Did NOT reduce SPAXX immediately
- Added PENDING ACTIVITY = -$3,566.55 as a T+1 settlement indicator

The SPAXX balance in the export ($41,279.15) is therefore the **pre-settlement balance**.

---

## Adjusted Cash Calculation

### Step 1: Identify the true cash balance

```
reported_cash_mv        = $41,279.15   (SPAXX as exported by Fidelity)
pending_activity_mv     = -$3,566.55   (future SPAXX debit, already in holdings)
adjusted_cash_mv        = $37,712.60   ($41,279.15 + (-$3,566.55))
```

### Step 2: Apply mandate-aware floor (unchanged)

The floor uses `total_market_value = $480,298.55`. This value already includes
PENDING ACTIVITY's -$3,566.55 in the ingestion sum, so the floor is consistent
whether or not we adjust cash_mv.

```
effective_floor_pct     = 7.0%
floor_mv                = 7.0% × $480,298.55 = $33,620.90   (same in both scenarios)
```

### Step 3: Compute adjusted deployable

```
adjusted_deployable_mv  = max(0, $37,712.60 − $33,620.90) = $4,091.70
```

---

## Side-by-Side Comparison

| Metric | Reported | Adjusted | Delta |
|--------|----------|----------|-------|
| `cash_mv` | $41,279.15 | $37,712.60 | -$3,566.55 |
| `cash_pct` | 8.5945% | 7.8541% | -0.7404 pp |
| `floor_mv` | $33,620.90 | $33,620.90 | $0.00 |
| `deployable_mv` | **$7,658.25** | **$4,091.70** | **-$3,566.55** |
| `deployable_pct` | 1.5945% | 0.8519% | -0.7426 pp |

**The overstatement ($3,566.55) is exactly equal to the PENDING ACTIVITY absolute value.**

---

## Notes on Total Market Value

`total_market_value = $480,298.55` was computed at ingestion as an unconditioned sum
of all raw holdings rows, including PENDING ACTIVITY at -$3,566.55.

If PENDING ACTIVITY were excluded from `total_mv`:
- `total_mv` would be $483,865.10
- `floor_mv` would be $33,870.56 (7% × $483,865.10, +$249.66 vs reported)
- Net effect on `deployable_mv` using adjusted cash ($37,712.60 − $33,870.56 = $3,842.04)

However, this alternative scenario is not the current system behavior. The current
system uses `total_mv = $480,298.55` (with PENDING), and `cash_mv = $41,279.15` (without PENDING).

---

## System Behavior Classification

**Q4 Answer: A. IGNORES pending activity**

The system does not include PENDING ACTIVITY in `cash_mv`. The `investable` list
filter at `runner.py:559` excludes `ACCOUNTING_ADJUSTMENT` holdings before they
reach `compute_deployable_cash()`. PENDING ACTIVITY never has the opportunity to
reduce `cash_mv`.

---

## Overstatement Impact Summary

- Operator is shown $7,658 deployable cash
- True post-settlement deployable is $4,092
- Operator deploying the full $7,658 would leave the portfolio below the 7% mandate floor
- After pending settlement, SPAXX will drop to ~$37,713, and deployable will correct automatically
