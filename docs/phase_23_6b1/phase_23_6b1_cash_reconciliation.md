# Phase 23.6B.1 — Cash Reconciliation

**Date:** 2026-06-04  
**PAR Run:** PAR-20260604-A47BD0AF  

---

## Full Cash Calculation Trace

### Source: SPAXX (Fidelity Government Money Market)

| Field | Value |
|-------|-------|
| Symbol | SPAXX |
| Market Value | $44,049.40 |
| Operational State | CASH_EQUIVALENT |
| is_cash_equivalent | True |
| Security Type | (money market) |

SPAXX is correctly classified as cash. This is the sole cash source in the deployment calculation.

### Cash Target Floor

| Field | Formula | Value |
|-------|---------|-------|
| Portfolio MV | — | $479,086.31 |
| Mandate Cash Target | Config (CONCENTRATED_ALPHA) | 7.0% |
| Floor MV | $479,086.31 × 7.0% | $33,536.04 |

### Excess and Deployable Calculation

| Step | Formula | Value |
|------|---------|-------|
| Cash MV | SPAXX balance | $44,049.40 |
| Cash % | $44,049 / $479,086 | 9.1945% |
| Floor MV | 7.0% × $479,086 | $33,536.04 |
| Excess MV | $44,049 − $33,536 | **$10,513.36** |
| Excess % | 9.1945% − 7.0% | 2.1945% |
| Settlement Adjustment | None applied | $0 |
| **Deployable MV** | Excess MV − Settlement | **$10,513.36** |
| **Deployable %** | | **2.1945%** |

### Is $10.5K Correct?

**Yes — $10,513.36 is arithmetically correct** given the SPAXX balance and the 7% mandate floor.

No stale data is involved. The SPAXX balance is live from the uploaded portfolio file (`Portfolio_Positions_Jun-04-2026 (4).csv`).

---

## PENDING ACTIVITY Anomaly

The holdings include:

| Field | Value |
|-------|-------|
| Symbol | PENDING ACTIVITY |
| Market Value | $10,204.59 |
| Operational State | ACTIVE_POSITION |
| is_cash_equivalent | False |

**This $10,204.59 is not being used as a settlement adjustment.** The system classifies PENDING ACTIVITY as `ACTIVE_POSITION` when its market value is positive. In Phase 22D.10, the settlement offset logic applies only to rows with **negative** market values (accounting adjustments for pending purchase settlements). Positive PENDING ACTIVITY rows represent unsettled *sale* proceeds — cash that has been economically created but not yet settled into SPAXX.

**Net effect on deployable cash:**
- If the $10,204 in PENDING ACTIVITY represents sale proceeds that will settle into SPAXX shortly, the *true* deployable position is approximately **$10,513 + $10,204 = $20,717**.
- The system correctly reports $10,513 based on current SPAXX balance — it does not predict future settlement inflows.

**Classification:** The $10,513 figure is correct per the model's design. The $10,204 PENDING ACTIVITY creating potential understatement of true deployable cash is a known structural characteristic, not a defect in this run.

---

## Why SPAXX Appears in CRA Capital Pool (Defect)

The capital source builder identifies SPAXX (mv=$44,049) as a LOW_CONVICTION_REDUCTION candidate because:
1. Its `opportunity_flag` = HOLD
2. It has no replay support
3. Its position % ≥ de minimis threshold (9.1% >> 1% threshold)

**This is a defect.** SPAXX is `is_cash_equivalent=True` and should be excluded from all sell candidate categories. The capital source builder does not check `is_cash_equivalent` or `operational_state` before categorizing holdings.

The 25% sizing heuristic generates: $44,049 × 0.25 = **$11,012** erroneously added to the capital pool.
