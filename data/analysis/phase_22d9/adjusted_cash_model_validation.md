# Phase 22D.9 — Workstream C: Adjusted Cash Model Validation

**Phase:** 22D.9 — Settlement-Aware Deployable Cash  
**Date:** 2026-06-02  
**Reference Run:** PAR-20260602-8CF1CB84  
**Source Data:** Phase 22D.8A forensic audit (validated)

---

## 1. Model Statement

The **adjusted cash model** proposes that, whenever negative `ACCOUNTING_ADJUSTMENT` rows
are present in a portfolio export, the deployable cash calculation should reflect the
post-settlement cash balance rather than the current SPAXX balance.

**Formula:**

$$\text{adjusted\_cash\_mv} = \text{cash\_equivalent\_mv} + \sum_{i \in \text{ACCOUNTING\_ADJ, MV}<0} \text{MV}_i$$

Because all observed adjustment MVs are negative, this sum subtracts the pending debits:

$$\text{adjusted\_deployable\_mv} = \max\bigl(0,\ \text{adjusted\_cash\_mv} - \text{floor\_mv}\bigr)$$

---

## 2. Input Values (Run PAR-20260602-8CF1CB84)

| Field | Value | Source |
|-------|-------|--------|
| `total_market_value` | $480,298.55 | `ingestion.py` line 416 (unconditioned sum) |
| SPAXX (brokerage sub-account) | $69.51 | Holdings row, is_cash_equivalent=True |
| SPAXX (individual sub-account) | $41,209.64 | Holdings row, is_cash_equivalent=True |
| `cash_equivalent_mv` (sum of SPAXX) | $41,279.15 | `deployment_queue.py` line 427 |
| PENDING ACTIVITY row MV | -$3,566.55 | operational_state=ACCOUNTING_ADJUSTMENT |
| `mandate_cash_target_pct` | 7.0% | concentrated_alpha_profile.yaml |
| `effective_floor_pct` | 7.0% | no override in effect |
| `floor_mv` | $33,620.90 | $480,298.55 × 7.0% ÷ 100 |

---

## 3. Reported (Pre-Settlement) Calculation

These are the numbers the current system produces. They are correct per the existing model.

| Step | Formula | Value |
|------|---------|-------|
| Cash MV (SPAXX) | sum of is_cash_equivalent=True | **$41,279.15** |
| Cash % | $41,279.15 / $480,298.55 × 100 | **8.59%** |
| Floor MV | $480,298.55 × 7.0% | **$33,620.90** |
| Deployable MV | max(0, $41,279.15 - $33,620.90) | **$7,658.25** |

---

## 4. Adjusted (Post-Settlement) Calculation

These are the numbers the adjusted model would produce. They reflect the expected cash
balance after T+1 settlement of the PRG purchase.

| Step | Formula | Value |
|------|---------|-------|
| Cash MV (SPAXX, pre-settlement) | $41,279.15 | — |
| Pending Settlement Debit | -$3,566.55 (ACCOUNTING_ADJUSTMENT row) | — |
| **Adjusted Cash MV** | $41,279.15 + (-$3,566.55) | **$37,712.60** |
| **Adjusted Cash %** | $37,712.60 / $480,298.55 × 100 | **7.85%** |
| Floor MV (unchanged) | $480,298.55 × 7.0% | **$33,620.90** |
| **Adjusted Deployable MV** | max(0, $37,712.60 - $33,620.90) | **$4,091.70** |

---

## 5. Overstatement Quantification

| Metric | Reported | Adjusted | Delta |
|--------|----------|----------|-------|
| Cash MV | $41,279.15 | $37,712.60 | -$3,566.55 |
| Cash % | 8.59% | 7.85% | -0.74pp |
| Deployable MV | $7,658.25 | $4,091.70 | -$3,566.55 |

The overstatement in deployable cash ($3,566.55) equals the absolute value of the
PENDING ACTIVITY row exactly. This is always the case because:
- Floor MV is unchanged (it depends on `total_market_value`, not `cash_mv`)
- Deployable = cash - floor
- ∴ Δ(deployable) = Δ(cash) = ACCOUNTING_ADJUSTMENT MV

---

## 6. PRG Purchase Context

The PENDING ACTIVITY row tracks the T+1 settlement debit for the PRG (PROG HOLDINGS)
purchase executed on 2026-06-02.

| Field | Value |
|-------|-------|
| PRG shares | held as of export |
| PRG market value | $3,622.00 |
| PRG cost (settlement basis) | $3,566.55 |
| PENDING ACTIVITY MV | -$3,566.55 |
| Match to PRG cost | Exact |

Fidelity's behavior: the position is credited at market value ($3,622.00) immediately,
but the cash debit of $3,566.55 is shown as PENDING ACTIVITY until T+1 settlement.
The $55.45 spread represents unrealized gain on PRG since execution.

---

## 7. Floor Asymmetry (Documented Pre-Existing Issue)

`total_market_value` is computed in `ingestion.py` line 416 as an unconditioned sum,
including the -$3,566.55 ACCOUNTING_ADJUSTMENT row:

> $480,298.55 includes the negative pending debit.

This means `floor_mv` is slightly underestimated:
- True total_market_value (without pending) = $480,298.55 + $3,566.55 = $483,865.10
- Reported floor_mv = $33,620.90 (based on $480,298.55)
- True floor_mv = $33,870.56 (based on $483,865.10)
- Understatement of floor = -$249.66

This is a second-order effect ($250 vs $3,567 primary gap) and is NOT addressed by
Option B. The operator should be aware that both the denominator and numerator are
affected by the PENDING ACTIVITY row, but the primary distortion is in the numerator
(cash_mv is overstated by $3,566.55 while the denominator error is only $249.66).

---

## 8. Model Validation Result

The adjusted cash model is **arithmetically sound** and **directionally correct**.

- The formula is straightforward (no division, no rounding ambiguity)
- The result ($4,091.70) is a tighter, more conservative deployment constraint
- It does not undershoot: $4,091.70 > $0, mandate is not violated even post-settlement
- Post-settlement, both figures will converge to approximately $4,145 once SPAXX is debited

**Validation status: PASS**  
The adjusted calculation produces a number that is materially different from the reported
figure ($3,566.55 difference) and that better represents the operator's true deployment
capacity on the day of export.
