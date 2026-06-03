# FMP Endpoint Inventory
**Phase**: 8.0B.0 — FMP Capability Audit  
**Probe Date**: 2025-01-30  
**API Key Tier**: Free (unregistered / starter tier)  
**Test Symbol**: VRT  

---

## Summary

FMP underwent a major API restructuring in 2024. All v3/v4 endpoints are now classified as **"Legacy"** and are inaccessible to free-tier users. The replacement **Stable API** (`/stable/...`) requires a paid subscription for all fundamental data endpoints.

**Net result: 0 out of 25 tested endpoints return usable financial data on the free tier.**

---

## Probe Results: v3 / v4 Endpoints (Legacy)

All v3/v4 endpoints return the following error regardless of endpoint type:

```
"Error Message": "Legacy Endpoint : Due to Legacy endpoints being no longer 
supported - This endpoint is only available for legacy users who have signed 
up prior to [migration date]. Please switch to our new endpoints."
```

| Endpoint Name | Path | HTTP Status | FMS Component Served | Result |
|---|---|---|---|---|
| income_statement_annual | `/v3/income-statement/{sym}?period=annual` | 403 | Revenue Growth, EPS Growth | BLOCKED |
| income_statement_quarter | `/v3/income-statement/{sym}?period=quarter` | 403 | Revenue/EPS History | BLOCKED |
| cashflow_annual | `/v3/cash-flow-statement/{sym}?period=annual` | 403 | FCF Growth | BLOCKED |
| cashflow_quarter | `/v3/cash-flow-statement/{sym}?period=quarter` | 403 | FCF History | BLOCKED |
| balance_sheet_annual | `/v3/balance-sheet-statement/{sym}?period=annual` | 403 | Balance sheet | BLOCKED |
| key_metrics_annual | `/v3/key-metrics/{sym}?period=annual` | 403 | PEG, PE, FCF metrics | BLOCKED |
| key_metrics_ttm | `/v3/key-metrics-ttm/{sym}` | 403 | Forward PEG (TTM) | BLOCKED |
| financial_growth | `/v3/financial-growth/{sym}?period=annual` | 403 | Revenue Growth, EPS Growth, FCF Growth | BLOCKED |
| ratios_annual | `/v3/ratios/{sym}?period=annual` | 403 | PE, PEG ratios | BLOCKED |
| ratios_ttm | `/v3/ratios-ttm/{sym}` | 403 | Forward PEG (TTM) | BLOCKED |
| analyst_estimates | `/v3/analyst-estimates/{sym}` | 403 | Analyst Estimate Revisions | BLOCKED |
| earnings_surprises | `/v3/earnings-surprises/{sym}` | 403 | Earnings Surprise | BLOCKED |
| profile | `/v3/profile/{sym}` | 403 | Company metadata, Forward PE | BLOCKED |
| quote | `/v3/quote/{sym}` | 403 | Real-time price/PE | BLOCKED |
| analyst_recommendations | `/v3/analyst-stock-recommendations/{sym}` | 403 | Buy/hold/sell counts | BLOCKED |
| price_target_summary | `/v4/price-target-summary?symbol={sym}` | 403 | Price targets | BLOCKED |
| upgrades_downgrades | `/v4/upgrades-downgrades?symbol={sym}` | 403 | Analyst rating changes | BLOCKED |
| historical_earnings | `/v3/historical/earning_calendar/{sym}` | 403 | Earnings dates | BLOCKED |
| discounted_cashflow | `/v3/discounted-cash-flow/{sym}` | 403 | DCF valuation | BLOCKED |
| enterprise_values | `/v3/enterprise-values/{sym}` | 403 | EV metrics | BLOCKED |
| etf_holders | `/v3/etf-stock-exposure/{sym}` | 403 | ETF exposure | BLOCKED |
| institutional_holders | `/v3/institutional-holder/{sym}` | 403 | Institutional ownership | BLOCKED |
| shares_float | `/v4/shares_float?symbol={sym}` | 403 | Float data | BLOCKED |
| income_growth | `/v3/income-statement-growth/{sym}` | 403 | Revenue/EPS growth | BLOCKED |
| cashflow_growth | `/v3/cash-flow-statement-growth/{sym}` | 403 | FCF growth | BLOCKED |

---

## Probe Results: Stable API Endpoints (New)

| Endpoint Name | Path | HTTP Status | FMS Component Served | Result |
|---|---|---|---|---|
| income-statement | `/stable/income-statement?symbol={sym}` | 402 | Revenue Growth, EPS Growth | PAYMENT REQUIRED |
| income-statement (annual) | `/stable/income-statement?symbol={sym}&period=annual` | 402 | Revenue History | PAYMENT REQUIRED |
| income-statement (quarter) | `/stable/income-statement?symbol={sym}&period=quarter` | 402 | EPS History | PAYMENT REQUIRED |
| balance-sheet-statement | `/stable/balance-sheet-statement?symbol={sym}` | 402 | Balance sheet | PAYMENT REQUIRED |
| cash-flow-statement | `/stable/cash-flow-statement?symbol={sym}` | 402 | FCF Growth | PAYMENT REQUIRED |
| key-metrics | `/stable/key-metrics?symbol={sym}` | 402 | PEG, PE, FCF | PAYMENT REQUIRED |
| key-metrics-ttm | `/stable/key-metrics-ttm?symbol={sym}` | 402 | Forward PEG (TTM) | PAYMENT REQUIRED |
| ratios | `/stable/ratios?symbol={sym}` | 402 | PE, PEG ratios | PAYMENT REQUIRED |
| ratios-ttm | `/stable/ratios-ttm?symbol={sym}` | 402 | Forward PEG (TTM) | PAYMENT REQUIRED |
| financial-growth | `/stable/financial-growth?symbol={sym}` | 402 | All 3 growth metrics | PAYMENT REQUIRED |
| analyst-estimates | `/stable/analyst-estimates?symbol={sym}` | 402 | Analyst Estimate Revisions | PAYMENT REQUIRED |
| **earnings-surprises** | `/stable/earnings-surprises?symbol={sym}` | **200** | Earnings Surprise | **ACCESSIBLE BUT EMPTY** |
| **profile** | `/stable/profile?symbol={sym}` | **200** | Basic company data | **OK (limited fields)** |
| quote | `/stable/quote?symbol={sym}` | 402 | Real-time price/PE | PAYMENT REQUIRED |
| analyst-recommendations | `/stable/analyst-stock-recommendations?symbol={sym}` | 200 | Analyst ratings | ACCESSIBLE BUT EMPTY |
| price-target | `/stable/price-target?symbol={sym}` | 200 | Analyst price targets | ACCESSIBLE BUT EMPTY |
| price-target-summary | `/stable/price-target-summary?symbol={sym}` | 402 | Price target summary | PAYMENT REQUIRED |
| upgrades-downgrades | `/stable/upgrades-downgrades?symbol={sym}` | 200 | Rating changes | ACCESSIBLE BUT EMPTY |
| earnings-calendar | `/stable/earnings?symbol={sym}` | 402 | Earnings dates | PAYMENT REQUIRED |
| company-outlook | `/stable/company-outlook?symbol={sym}` | 200 | Company summary | ACCESSIBLE BUT EMPTY |
| stock-list | `/stable/stock-list` | 402 | Universe list | PAYMENT REQUIRED |

---

## Free-Tier Accessible Endpoints: Detail

### `stable/profile` — ONLY ENDPOINT RETURNING DATA

Fields available on free tier:
```
symbol, price, marketCap, beta, lastDividend
```

Fields NOT available (require payment):
```
revenue, netIncome, eps, pe, pegRatio, fcf, revenueGrowth, epsGrowth,
forwardPE, analystCount, targetPrice, earningsSurprise, priceToFCF, ...
```

**Assessment**: The profile endpoint returns only 5 superficial fields — price, market cap, beta, and last dividend. **None of these fields map to any FMS component.**

### `stable/earnings-surprises` + several others — EMPTY LISTS

These endpoints return HTTP 200 but with an empty array `[]`. It is unclear whether this is a free-tier data restriction or a data-availability issue specific to VRT on this plan tier. Functionally equivalent to blocked.

---

## Endpoint Availability Summary

| Category | Endpoints Tested | Accessible (data returned) | Useful for FMS |
|---|---|---|---|
| v3/v4 (legacy) | 25 | 0 | 0 |
| Stable (new) | 20 | 6* | 0 |
| **Total** | **45** | **6*** | **0** |

*6 stable endpoints return HTTP 200, but 5 of those return empty lists. Only `stable/profile` returns data, but the fields are not useful for FMS.

---

## FMP API Migration Context

FMP completed an API migration in 2024 that:
1. Deprecated all `/api/v3/` and `/api/v4/` endpoints for non-legacy users
2. Introduced a new `/stable/` endpoint namespace as the replacement
3. Placed all fundamental data (financials, metrics, growth rates, analyst data) behind paid tiers on the stable API
4. Preserved only superficial market data (basic profile) on the free stable tier

The free tier as it exists today is not usable for financial data retrieval beyond basic price/market-cap lookups.
