# Phase 8.0B.1A.1 — Raw Payload Inventory

**Date:** 2026-06-04  
**API:** FMP `/stable/` (URL param auth: `?apikey=KEY`)  
**Note:** Auth method corrected from header (`apikey: KEY`) to URL param during this validation.

---

## Dataset 1: key_metrics_ttm

**Endpoint:** `GET /stable/key-metrics-ttm?symbol={sym}`  
**VRT sample payload (full field list):**

```json
{
  "symbol": "VRT",
  "marketCap": 124420527679,
  "enterpriseValueTTM": 125462527679,
  "evToSalesTTM": 11.570404824962651,
  "evToOperatingCashFlowTTM": 48.193649475281376,
  "evToFreeCashFlowTTM": 54.3245411037021,
  "evToEBITDATTM": 53.41331162629316,
  "netDebtToEBITDATTM": 0.44361190344416535,
  "currentRatioTTM": 1.4943479562808804,
  "incomeQualityTTM": 1.064483153418384,
  "returnOnAssetsTTM": 0.11629763956985395,
  "returnOnEquityTTM": 0.4206122683076591,
  "returnOnInvestedCapitalTTM": 0.20306113814170204,
  "earningsYieldTTM": 0.012564101286078185,
  "freeCashFlowYieldTTM": 0.018562049551488945,
  ...32 more fields...
}
```

**Key finding:** `peRatioTTM` is **absent** on Starter plan. Primary valuation field must shift to `earningsYieldTTM` (= 1/PE), `evToEBITDATTM`, and `freeCashFlowYieldTTM`.

---

## Dataset 2: grades_consensus

**Endpoint:** `GET /stable/grades-consensus?symbol={sym}`  
**VRT sample:**

```json
[{"strongBuy": 0, "buy": 18, "hold": 1, "sell": 0, "strongSell": 0}]
```

**AVGO sample (high conviction):**
```json
[{"strongBuy": 0, "buy": 51, "hold": 7, "sell": 0, "strongSell": 0}]
```

**TSLA sample (mixed):**
```json
[{"strongBuy": 0, "buy": 32, "hold": 33, "sell": 16, "strongSell": 0}]
```

---

## Dataset 3: earnings (surprises)

**Endpoint:** `GET /stable/earnings?symbol={sym}&limit=8`  
**VRT sample (latest 2 entries):**

```json
[
  {"symbol":"VRT","date":"2026-07-29","epsActual":null,"epsEstimated":1.42,
   "revenueActual":null,"revenueEstimated":3371765000,"lastUpdated":"2026-06-04"},
  {"symbol":"VRT","date":"2026-04-22","epsActual":1.17,"epsEstimated":1.0,
   "revenueActual":2649500000,"revenueEstimated":2638842000,"lastUpdated":"2026-06-04"}
]
```

**Key finding:** Most recent entry has `epsActual=null` (future earnings). Fetcher must filter to past quarters only.

**Field name correction:** `epsActual`/`epsEstimated` (not `actualEarningResult`/`estimatedEarning` as originally assumed).

---

## Dataset 4: income_statement_growth

**Endpoint:** `GET /stable/income-statement-growth?symbol={sym}&limit=4`  
**VRT sample (latest 2 periods):**

```json
[
  {"symbol":"VRT","date":"2025-12-31","fiscalYear":"2025","period":"FY",
   "growthRevenue":0.27685,"growthEPS":1.64393,"growthGrossProfit":0.27680,...},
  {"symbol":"VRT","date":"2024-12-31","fiscalYear":"2024","period":"FY",
   "growthRevenue":0.16735,"growthEPS":0.09090,"growthGrossProfit":0.24044,...}
]
```

**Available growth fields (33 total):** growthRevenue, growthCostOfRevenue, growthGrossProfit, growthGrossProfitRatio, growthEBITDA, growthOperatingIncome, growthNetIncome, growthEPS, growthEPSDiluted, growthWeightedAverageShsOut, growthEBIT, and more.
