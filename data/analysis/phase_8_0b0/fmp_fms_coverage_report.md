# FMP FMS Coverage Report
**Phase**: 8.0B.0 — FMP Capability Audit  
**Probe Date**: 2025-01-30  
**Framework**: Fundamental Momentum Score (FMS) — 6-component model from Phase 8.0A.1  

---

## FMS Component Mapping: Free Tier

| # | FMS Component | Required Data | FMP Endpoint (Stable) | Free Tier Status | Paid Tier Status |
|---|---|---|---|---|---|
| 1 | Revenue Growth | Annual revenue × 4 periods | `stable/income-statement?period=annual` | **BLOCKED (402)** | Available |
| 2 | EPS Growth | Diluted EPS × 4 periods | `stable/income-statement?period=annual` | **BLOCKED (402)** | Available |
| 3 | Analyst Estimate Revisions | EPS estimates + analyst count, current vs. 90-day-ago | `stable/analyst-estimates` | **BLOCKED (402)** | Available (unverified) |
| 4 | Earnings Surprise | Actual vs. estimate, trailing 4 quarters | `stable/earnings-surprises` | **EMPTY (free wall)** | Available |
| 5 | FCF Growth | Free cash flow × 4 annual periods | `stable/cash-flow-statement?period=annual` | **BLOCKED (402)** | Available |
| 6 | Forward PEG | forwardPE / LTM EPS growth | `stable/key-metrics-ttm` + `stable/ratios-ttm` | **BLOCKED (402)** | Available |

**Free Tier FMS Coverage: 0 / 6 components (0%)**  
**Paid Tier FMS Coverage (estimated): 6 / 6 components (100%) — subject to Phase 8.0C verification**

---

## Component-by-Component Analysis

### Component 1: Revenue Growth

**Definition**: Year-over-year revenue growth, trailing 3–5 years. Used to assess whether revenue trajectory is accelerating or decelerating.

**Required fields**:
- `revenue` from annual income statement, 4–5 consecutive years

**FMP endpoint**: `stable/income-statement?symbol={sym}&period=annual&limit=5`

**Free tier**: BLOCKED (HTTP 402)

**Paid tier field**: `revenue` field present in income-statement response. Pre-computed `revenueGrowth` also available in `stable/financial-growth` as shortcut — avoids manual year-over-year calculation.

**Alternative FMP field**: `stable/financial-growth` returns `revenueGrowth` directly for each annual period. This is the cleanest implementation path.

**Coverage on free tier**: 0 / 15 symbols (0%)  
**Coverage on paid tier**: Expected 15 / 15 (100%) — large/mid-cap US symbols fully covered

---

### Component 2: EPS Growth

**Definition**: Year-over-year diluted EPS growth, trailing 3–5 years.

**Required fields**:
- `epsdiluted` from annual income statement, 4–5 consecutive years

**FMP endpoint**: `stable/income-statement?symbol={sym}&period=annual&limit=5`

**Free tier**: BLOCKED (HTTP 402)

**Paid tier field**: `epsdiluted` + `eps` (basic). Pre-computed `epsgrowth` also available in `stable/financial-growth`.

**Coverage on free tier**: 0 / 15 symbols (0%)  
**Coverage on paid tier**: Expected 15 / 15 (100%)

**Note on small-cap**: PCB (PCB Bancorp) — EPS history availability uncertain; may have <5 years of data as a smaller bank. `numberAnalystsEstimatedEps` should be checked.

---

### Component 3: Analyst Estimate Revisions

**Definition**: Change in consensus EPS estimate over trailing 90 days. A positive revision (upgrades exceeding downgrades) is a momentum signal.

**Required fields**:
- Current consensus EPS estimate: `estimatedEpsAvg`
- Analyst count: `numberAnalystsEstimatedEps`
- Historical estimates (90-day-ago baseline): requires storing prior pulls or using FMP's estimate history

**FMP endpoint**: `stable/analyst-estimates?symbol={sym}&limit=8`

**Free tier**: BLOCKED (HTTP 402)

**Paid tier fields**: FMP returns `estimatedEpsAvg`, `estimatedEpsHigh`, `estimatedEpsLow`, `numberAnalystsEstimatedEps` per reporting period.

**Revision signal construction**: FMP provides point-in-time estimate values by date. To compute the 90-day revision, the pipeline must store the previous estimate and diff against the current one. FMP does NOT provide a pre-computed "revision delta" field — this must be derived from two sequential pulls.

**Coverage on free tier**: 0 / 15 symbols (0%)  
**Coverage on paid tier**: Expected 12–14 / 15 (80–93%) — PCB and ATLC may have sparse or no analyst coverage

---

### Component 4: Earnings Surprise

**Definition**: (Actual EPS − Consensus Estimate) / |Consensus Estimate|, trailing 4 quarters. Persistent positive surprises indicate a company systematically beating expectations.

**Required fields**:
- `actualEarningResult`, `estimatedEarning` per quarter

**FMP endpoint**: `stable/earnings-surprises?symbol={sym}`

**Free tier**: HTTP 200 returned but **empty list []** for VRT — consistent with a free-tier data wall.

**Paid tier fields**: `date`, `symbol`, `actualEarningResult`, `estimatedEarning` per quarter. Surprise percentage must be computed: `(actual - estimated) / abs(estimated)`.

**Coverage on free tier**: 0 / 15 symbols (0%)  
**Coverage on paid tier**: Expected 14–15 / 15 (93–100%) — major US symbols have earnings data

---

### Component 5: FCF Growth

**Definition**: Year-over-year free cash flow growth, trailing 3–5 years. FCF growth distinguishes genuine cash generation from earnings managed through accruals.

**Required fields**:
- `freeCashFlow` = `operatingCashFlow` − `capitalExpenditure` from cash flow statement, 4–5 years

**FMP endpoint**: `stable/cash-flow-statement?symbol={sym}&period=annual&limit=5`

**Free tier**: BLOCKED (HTTP 402)

**Paid tier fields**: `operatingCashFlow`, `capitalExpenditure`, `freeCashFlow` (pre-computed). Pre-computed `freeCashFlowGrowth` also in `stable/financial-growth` — preferred path.

**Coverage on free tier**: 0 / 15 symbols (0%)  
**Coverage on paid tier**: Expected 14–15 / 15 (93–100%)

**Note**: Financial institutions (ATLC, PCB, CBOE) report cash flows differently — `freeCashFlow` may be less meaningful for bank-type entities. FCF component may need to be nulled/substituted for financials.

---

### Component 6: Forward PEG

**Definition**: Forward Price-to-Earnings-Growth ratio = (Forward PE) / (Projected 1-year EPS Growth). Lower PEG = better value for growth.

**Required fields**:
- `forwardPE` or TTM PE + next-year estimate
- Forward EPS growth rate

**FMP endpoints**: 
- `stable/key-metrics-ttm` → `pegRatioTTM`, `peRatioTTM`
- `stable/ratios-ttm` → `pegRatioTTM` (redundant cross-check)
- `stable/analyst-estimates` → `estimatedEpsAvg` (forward year) for DIY forward PEG construction

**Free tier**: BLOCKED (HTTP 402) for key-metrics-ttm and ratios-ttm

**Paid tier fields**: `pegRatioTTM` is available as a pre-computed field on both `key-metrics-ttm` and `ratios-ttm`. Note: FMP's TTM PEG uses trailing growth, not strictly forward — for true forward PEG, manual construction from `analyst-estimates` is needed.

**Coverage on free tier**: 0 / 15 symbols (0%)  
**Coverage on paid tier**: Expected 13–15 / 15 (87–100%) — PEG undefined for negative-earnings symbols (ATLC potentially)

---

## FMS Coverage Summary

### Free Tier
```
Component 1 (Revenue Growth):         0/15 symbols  (0%)
Component 2 (EPS Growth):             0/15 symbols  (0%)
Component 3 (Analyst Revisions):      0/15 symbols  (0%)
Component 4 (Earnings Surprise):      0/15 symbols  (0%)
Component 5 (FCF Growth):             0/15 symbols  (0%)
Component 6 (Forward PEG):            0/15 symbols  (0%)

OVERALL FMS COVERAGE (FREE): 0%
```

### Estimated Paid Tier Coverage (Basic, ~$19/month)
```
Component 1 (Revenue Growth):         15/15 symbols (100%)
Component 2 (EPS Growth):             15/15 symbols (100%)
Component 3 (Analyst Revisions):      12-14/15      (80-93%) — thin coverage on micro-caps
Component 4 (Earnings Surprise):      14-15/15      (93-100%)
Component 5 (FCF Growth):             14-15/15      (93-100%) — financials may need handling
Component 6 (Forward PEG):            13-15/15      (87-100%) — undefined for negative earners

ESTIMATED OVERALL FMS COVERAGE (PAID): 87–97%
Note: All paid-tier estimates are UNVERIFIED — require Phase 8.0C confirmation.
```

---

## Symbol-Specific FMS Concerns

| Symbol | Concern | Affected Component(s) |
|---|---|---|
| ATLC (Atlanticus Holdings) | Micro-cap; may have sparse analyst coverage | 3, 6 |
| PCB (PCB Bancorp) | Small bank; FCF metric less meaningful | 5 |
| CBOE (CBOE Global Markets) | Financial; FCF definition differs | 5 |
| TSM (Taiwan Semiconductor) | ADR/foreign filer; potential data lag | 1, 2, 5 |

---

## Endpoint-to-Component Mapping (Optimal Paid Tier)

For minimal API calls per symbol:

```
stable/financial-growth         → Components 1 (revenueGrowth), 2 (epsgrowth), 5 (freeCashFlowGrowth)
stable/analyst-estimates        → Components 3 (estimate revisions), 6 (forward PEG construction)
stable/earnings-surprises       → Component 4 (actualEarningResult, estimatedEarning)
stable/key-metrics-ttm          → Component 6 (pegRatioTTM cross-check)
stable/income-statement         → Components 1, 2 (fallback if financial-growth missing)
stable/cash-flow-statement      → Component 5 (fallback if financial-growth missing)
```

**Minimum API calls per symbol for full FMS**: 4–6 (using `financial-growth` shortcut for components 1/2/5)
