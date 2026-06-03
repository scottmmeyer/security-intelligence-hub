# Phase 22D.9A — Q3: Cash Reconciliation

**Phase:** 22D.9A — CW-DAS Settlement-Aware Deployment Audit  
**Date:** 2026-06-02  
**Run:** PAR-20260602-8CF1CB84  
**Methodology:** Phase 22D.8A adjusted cash model

---

## Input Data

| Source | Field | Value |
|--------|-------|-------|
| Fidelity CSV (Jun 02, 2026) | SPAXX — General Brokerage (X20548022) | $69.51 |
| Fidelity CSV (Jun 02, 2026) | SPAXX — Individual TOD (Z35123695) | $41,209.64 |
| Fidelity CSV (Jun 02, 2026) | PENDING ACTIVITY (Z35123695) | -$3,566.55 |
| `ingestion.py` line 416 | `total_market_value` | $480,298.55 |
| `deployment_queue.py` line 427 | `cash_mv` (SPAXX only, is_cash_equivalent=True) | $41,279.15 |
| `deployment_queue.py` line 434 | `floor_mv` (7.0% × $480,298.55) | $33,620.90 |
| `deployment_queue.py` line 439 | `deployable_mv` (reported) | $7,658.25 |

---

## Reported (Pre-Settlement) Calculation

Current system output — accounting-correct, pre-settlement snapshot.

$$\text{cash\_mv} = \$41{,}279.15 \quad \text{(SPAXX balances only)}$$

$$\text{cash\_pct} = \frac{\$41{,}279.15}{\$480{,}298.55} \times 100 = 8.59\%$$

$$\text{floor\_mv} = \$480{,}298.55 \times 7.0\% = \$33{,}620.90$$

$$\text{deployable\_mv} = \max(0,\ \$41{,}279.15 - \$33{,}620.90) = \$7{,}658.25$$

---

## Adjusted (Settlement-Aware) Calculation

Phase 22D.8A methodology: subtract negative ACCOUNTING_ADJUSTMENT rows from cash_mv.

$$\text{adjusted\_cash\_mv} = \text{cash\_mv} + \sum_{i \in \text{ACCT\_ADJ, MV}<0} \text{MV}_i$$

$$= \$41{,}279.15 + (-\$3{,}566.55) = \$37{,}712.60$$

$$\text{adjusted\_cash\_pct} = \frac{\$37{,}712.60}{\$480{,}298.55} \times 100 = 7.85\%$$

$$\text{floor\_mv (unchanged)} = \$33{,}620.90$$

$$\text{adjusted\_deployable\_mv} = \max(0,\ \$37{,}712.60 - \$33{,}620.90) = \$4{,}091.70$$

---

## Side-by-Side Comparison: Reported vs Adjusted

| Metric | Reported | Adjusted | Delta | % Change |
|--------|----------|----------|-------|----------|
| Cash MV | $41,279.15 | $37,712.60 | -$3,566.55 | -8.64% |
| Cash % | 8.59% | 7.85% | -0.74 pp | — |
| Floor MV | $33,620.90 | $33,620.90 | $0 | unchanged |
| **Deployable MV** | **$7,658.25** | **$4,091.70** | **-$3,566.55** | **-46.57%** |
| Deployable % | 1.59% | 0.85% | -0.74 pp | — |

**The overstatement in deployable cash is $3,566.55 — exactly equal to `|PENDING ACTIVITY|`.**

---

## CW-DAS Allocation Overstatement

Because the deployment planner uses `deployable_cash` as the proportional budget,
each `suggested_add` is oversized by the same factor:

$$\text{oversize\_factor} = \frac{\$7{,}658.25}{\$4{,}091.70} = 1.871\times$$

| Position | Reported suggested_add | Adjusted suggested_add | Overstatement |
|----------|----------------------|----------------------|---------------|
| VRT (T1) | $1,102.54 | $589.01 | +$513.53 |
| ARW (T2) | $550.71 | $294.17 | +$256.54 |
| ATLC (T2) | $447.65 | $239.20 | +$208.45 |
| SNX (T2) | $386.97 | $206.78 | +$180.19 |
| PSX (T2) | $345.63 | $184.64 | +$160.99 |
| T2 total (13) | $3,943.37 | $2,107.03 | +$1,836.34 |
| T3 total (17) | $2,612.35 | $1,395.66 | +$1,216.69 |
| **TOTAL** | **$7,658.26** | **$4,091.70** | **+$3,566.56** |

---

## Post-Deployment Cash Position Scenarios

### Scenario A: Operator deploys NOTHING (holds)
| Timing | Cash MV | Cash % | At Mandate? |
|--------|---------|--------|-------------|
| Today (pre-settlement) | $41,279.15 | 8.59% | YES (8.59% ≥ 7.0%) |
| After T+1 settlement | $37,712.60 | 7.85% | YES (7.85% ≥ 7.0%) |

### Scenario B: Operator deploys ADJUSTED figure ($4,091.70)
| Timing | Cash MV | Cash % | At Mandate? |
|--------|---------|--------|-------------|
| Today (pre-deployment) | $41,279.15 | 8.59% | YES |
| After deployment (pre-settlement) | $37,187.45 | 7.74% | YES |
| After T+1 settlement | $33,620.90 | 7.00% | YES (exactly at floor) |

### Scenario C: Operator deploys REPORTED figure ($7,658.25) — CW-DAS guidance
| Timing | Cash MV | Cash % | At Mandate? |
|--------|---------|--------|-------------|
| Today (pre-deployment) | $41,279.15 | 8.59% | YES |
| After deployment (pre-settlement) | $33,620.89 | 7.00% | YES (appears on-target) |
| After T+1 settlement | **$30,054.34** | **6.26%** | **NO — MANDATE BREACH** |

```
Breach calculation:
  cash_after_deployment = $41,279.15 - $7,658.26 = $33,620.89
  T+1 settlement debit  = -$3,566.55
  final cash            = $33,620.89 - $3,566.55 = $30,054.34
  final cash %          = $30,054.34 / $480,298.55 = 6.26%
  mandate floor         = 7.00%
  shortfall             = 0.74 pp = $3,566.55 in dollar terms
```

---

## Summary: Which Number Should Drive CW-DAS?

| | Deployable Figure | Post-Settlement Cash % | Mandate Compliant? |
|-|-------------------|----------------------|-------------------|
| Reported (current) | $7,658.25 | 6.26% | **NO** |
| Adjusted (proposed) | $4,091.70 | 7.00% | YES |
| Zero (conservative) | $0 | 7.85% | YES |

Following CW-DAS guidance as currently calibrated will result in a mandate breach
of 0.74 percentage points at T+1 settlement — if the operator executes the full
recommended deployment.
