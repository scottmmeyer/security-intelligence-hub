# Phase 22D.9A — Q5: Operator Impact Assessment

**Phase:** 22D.9A — CW-DAS Settlement-Aware Deployment Audit  
**Date:** 2026-06-02  
**Reference Run:** PAR-20260602-8CF1CB84  
**Basis:** Reported Deployable = $7,658 | Adjusted Deployable = $4,092

---

## 1. Would CW-DAS Allocate Excess Capital?

**Answer: YES — by $3,566.55**

The deployment planner uses `deployable_cash = $7,658.25` as the total allocation budget.
The settlement-correct budget is `$4,091.70`.

```
Excess allocated capital = $7,658.25 - $4,091.70 = $3,566.55
Overallocation factor     = $7,658.25 / $4,091.70 = 1.871×
```

An operator who follows CW-DAS guidance will attempt to purchase $7,658 in equities
when only $4,092 can be safely deployed without breaching the mandate floor at T+1
settlement. The excess $3,566 would cause a mandate breach.

**Magnitude:** Moderate. On a $480K portfolio with a 7.0% mandate floor, this is a
0.74 percentage point breach — from 7.0% (floor) to 6.26% (post-settlement).

---

## 2. Would Recommendations Be Oversized?

**Answer: YES — every single recommended position is oversized by 1.87×**

The rank-weighted proportional allocation formula in `deployment_planner.py`:

```python
raw_alloc_i = (weight_i / total_weight) × deployable_cash
```

Because `deployable_cash` is $7,658.25 (not $4,091.70), each `suggested_add` is inflated
by the same factor of 1.871×.

| Symbol | Reported suggested_add | Adjusted suggested_add | Oversize |
|--------|----------------------|----------------------|---------|
| VRT | $1,102.54 | $589.01 | +$513.53 |
| ARW | $550.71 | $294.17 | +$256.54 |
| ATLC | $447.65 | $239.20 | +$208.45 |
| SNX | $386.97 | $206.78 | +$180.19 |
| PSX | $345.63 | $184.64 | +$160.99 |
| T2 total (13) | $3,943.37 | $2,107.03 | +$1,836.34 |
| T3 total (17) | $2,612.35 | $1,395.66 | +$1,216.69 |
| **TOTAL** | **$7,658.26** | **$4,091.70** | **+$3,566.56** |

The oversizing is uniform across all tiers — it is not concentrated in a specific tier.
The rank ordering of positions is not affected (scoring does not use deployable cash).

---

## 3. Would Dry Powder Calculations Be Misleading?

**Answer: YES — three distinct ways**

### 3a. "Deployable Cash" Card ($7,658)
The UI presents $7,658 as the available dry powder. A new operator, unfamiliar with
T+1 settlement mechanics, would treat this as the maximum safe deployment amount.
The correct figure is $4,092.

### 3b. "Cash Weight Before → After" (8.6% → 7.0%)
This display implies the portfolio will land exactly at the mandate floor after
full deployment — a clean, on-target result. The actual post-settlement outcome
if the full $7,658 is deployed is 6.26%, a mandate breach.

### 3c. "Remaining" (-$0)
The -$0 remaining figure implies all dry powder is perfectly consumed.
In settlement-adjusted terms, $3,566 of the "consumed" dry powder does not
actually exist — it was already committed to PRG purchase settlement.

---

## 4. Would Portfolio Mandate Analytics Be Distorted?

**Answer: YES — the most important downstream metric is wrong**

### Mandate Compliance Projection
The UI shows `cash_after_pct = 7.00%` — exactly at the mandate floor.
This is computed as:

```python
cash_mv_after = cash_mv_before - total_deployed
              = $41,279.15 - $7,658.26
              = $33,620.89
cash_pct_after = $33,620.89 / $480,298.55 × 100 = 7.00%
```

**This is the mandate floor to four decimal places.** It looks correct.

The actual post-settlement cash position is:

```
cash_mv_actual = $41,279.15 - $7,658.26 - $3,566.55 (settlement debit)
               = $30,054.34
cash_pct_actual = $30,054.34 / $480,298.55 × 100 = 6.26%
```

**The mandate compliance projection is false.** It shows 7.00% when the true
post-settlement value is 6.26%.

### Mandate Drift Detection (Next Run)
The next run after full deployment and T+1 settlement will:
1. Ingest SPAXX at ~$30,054 (after settlement deducted)
2. Compute cash_pct ≈ 6.26%
3. Compare against mandate target 7.0%
4. Detect `excess_pct = -0.74%` — **mandate drift below floor**
5. Generate an RC recommendation type (likely MANDATE_DRIFT or BUY_CASH)

This reactive catch happens after the damage is done. There is no proactive warning.

### Dry Powder Exhaustion
Post-deployment, `deployable_mv = 0` (7.0% floor is reached based on reported cash).
The operator has no dry powder. But after settlement, the portfolio is 0.74 pp below
the mandate floor — the system will recommend buying more cash (SPAXX) or not deploying,
which is the opposite of what CW-DAS just recommended.

---

## 5. Scenario Impact Matrix

| Operator Action | Post-Settlement Cash % | Mandate Status | Recommendation Effect |
|----------------|----------------------|----------------|----------------------|
| Deploy nothing | 7.85% | PASS (0.85 pp above floor) | None |
| Deploy adjusted $4,092 | 7.00% | PASS (exactly at floor) | Conservative; correct |
| Deploy reported $7,658 | 6.26% | **FAIL (0.74 pp below)** | **Mandate breach** |
| Deploy $3,000 (partial) | 7.21% | PASS | Safe but suboptimal |
| Deploy $5,500 (partial) | 6.70% | **FAIL (0.30 pp below)** | Breach at T+1 |

**Safe deployment ceiling = $4,091.70.** Any deployment above this threshold will
result in a T+1 mandate breach if executed before settlement clears.

**Breach threshold** = $37,712.60 (adjusted cash) - $33,620.90 (floor) = $4,091.70

---

## 6. Operator Intelligence Defect Classification

| Dimension | Assessment |
|-----------|------------|
| CW-DAS oversizes allocations | YES — by $3,566.55 (1.87×) |
| Mandate breach risk if followed | YES — 7.00% → 6.26% at T+1 |
| Defect visible to operator | NO — no warning, no disclosure |
| Can operator detect it? | Only with deep knowledge of T+1 settlement mechanics |
| Affects rank ordering? | No — CW-DAS scoring is settlement-agnostic |
| Affects tier assignment? | No |
| Self-correcting? | YES — next run post-settlement will detect breach |
| Time window of risk | T = execution day to T+1 settlement (1 business day) |

---

## 7. Probability of Operator Following CW-DAS Guidance Fully

The operator UI presents `$7,658` as "Available to Deploy" and `$7,658` as "Allocated"
with `$0 Remaining` — an unambiguous signal that the full budget should be deployed.
The `cash_after = 7.0%` projection provides false confidence that doing so is mandate-safe.

An operator who:
- Trusts the CW-DAS recommended amounts
- Does not independently understand Fidelity T+1 settlement behavior
- Does not check the PENDING ACTIVITY row in holdings data
- Acts on the same day as the export

...will place trades totaling $7,658 across 31 positions and breach the mandate floor
the next business day.

**This is not an edge case. This is the primary use case of the deployment plan.**

---

## 8. Summary of Operator Harm

| Impact Category | Description | Severity |
|----------------|-------------|----------|
| Capital misallocation | $3,566 deployed that doesn't exist | Material |
| Mandate breach | Cash falls to 6.26% vs 7.00% floor | Material |
| False compliance signal | UI shows 7.0% "after" (correct is 6.26%) | Material |
| Oversized positions | 31 positions each get 1.87× too much | Material |
| No visible warning | Operator has zero indication of the issue | Severe |
| Self-corrects next run | Yes — but only after breach occurs | Mitigating |
