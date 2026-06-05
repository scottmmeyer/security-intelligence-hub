# Phase 8.0B.1A.1 — Field Inventory

**Date:** 2026-06-04  
**Source:** Live probe against FMP `/stable/` API

---

## Critical Finding: Field Names Differ from Documentation

The FMP `/stable/` API uses different field names than the legacy `/v3/` API and the FMP documentation. **The fetcher has been corrected** based on this validation.

---

## Dataset 1: key_metrics_ttm — Field Mapping

| Our Field Name | FMP /stable/ Field | Available on Starter | Notes |
|---------------|--------------------|---------------------|-------|
| `ev_ebitda_ttm` | `evToEBITDATTM` | ✅ Yes | Doc says `evToEbitdaTTM` — WRONG |
| `fcf_yield_ttm` | `freeCashFlowYieldTTM` | ✅ Yes | Confirmed present |
| `roe_ttm` | `returnOnEquityTTM` | ✅ Yes | Doc says `roeTTM` — WRONG |
| `roic_ttm` | `returnOnInvestedCapitalTTM` | ✅ Yes | Doc says `roicTTM` — WRONG |
| `earnings_yield_ttm` | `earningsYieldTTM` | ✅ Yes | Inverse of P/E |
| `price_to_fcf_ttm` | `evToFreeCashFlowTTM` | ✅ Yes | EV/FCF, not P/FCF |
| `pe_ratio_ttm` | `peRatioTTM` | ❌ Absent | Not returned on Starter plan |
| `revenue_per_share_ttm` | `revenuePerShareTTM` | ❌ Absent | Not in stable response |
| `net_income_per_share_ttm` | `netIncomePerShareTTM` | ❌ Absent | Not in stable response |

**Additional fields available but not in current schema:**
- `evToSalesTTM`, `evToOperatingCashFlowTTM`, `netDebtToEBITDATTM`
- `currentRatioTTM`, `incomeQualityTTM`, `grahamNumberTTM`
- `returnOnAssetsTTM`, `returnOnCapitalEmployedTTM`
- `capexToOperatingCashFlowTTM`, `freeCashFlowToEquityTTM`
- `daysOfSalesOutstandingTTM`, `cashConversionCycleTTM`

---

## Dataset 2: grades_consensus — Field Mapping

| Our Field | FMP Field | Available | Notes |
|-----------|-----------|-----------|-------|
| `strong_buy_count` | `strongBuy` | ✅ | Confirmed |
| `buy_count` | `buy` | ✅ | Confirmed |
| `hold_count` | `hold` | ✅ | Confirmed |
| `sell_count` | `sell` | ✅ | Confirmed |
| `strong_sell_count` | `strongSell` | ✅ | Confirmed |
| `total_analysts` | Derived | ✅ | Sum of above |
| `net_buy_score` | Derived | ✅ | (sb+b) - (s+ss) |
| `consensus_label` | Derived | ✅ | BUY/HOLD/SELL |

**Note:** `strongBuy` is consistently 0 for all 9 equity symbols. FMP may aggregate into `buy` for many analysts.

---

## Dataset 3: earnings — Field Mapping

| Our Field | FMP Field | Available | Notes |
|-----------|-----------|-----------|-------|
| `latest_eps_actual` | `epsActual` | ✅ | Corrected from `actualEarningResult` |
| `latest_eps_estimate` | `epsEstimated` | ✅ | Corrected from `estimatedEarning` |
| Revenue fields | `revenueActual`, `revenueEstimated` | ✅ | Available but not in current schema |
| `latest_eps_surprise_pct` | Derived | ✅ | |
| `q1..q8_surprise_pct` | Derived | ✅ | |
| `beats_last_8q` | Derived | ✅ | |
| `beat_rate_8q` | Derived | ✅ | |

**Key implementation note:** Most recent entry has `epsActual=null` (future earnings date). The fetcher filters to past quarters only before computing beat rate.

---

## Dataset 4: income_statement_growth — Field Mapping

| Our Field | FMP Field | Available | Notes |
|-----------|-----------|-----------|-------|
| `revenue_growth_q{1-4}_yoy` | `growthRevenue` | ✅ | Confirmed |
| `eps_growth_q{1-4}_yoy` | `growthEPS` | ✅ | Also `growthEPSDiluted` available |
| `gross_profit_growth_q1_yoy` | `growthGrossProfit` | ✅ | Confirmed |
| `revenue_acceleration` | Derived | ✅ | q1_yoy - q4_yoy |

**Additional growth fields available:** growthEBITDA, growthOperatingIncome, growthNetIncome, growthCostOfRevenue, growthOperatingExpenses (33 total).

---

## Auth Method Finding

The FMP `/stable/` API requires URL query parameter auth:
```
GET /stable/key-metrics-ttm?symbol=VRT&apikey=KEY
```

Header auth (`apikey: KEY`) returns **HTTP 401 Invalid API Key** on the `/stable/` endpoint. The fetcher has been corrected to use URL param auth.
