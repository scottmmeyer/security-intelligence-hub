# Phase 8.0B.1A.1 — Null Rate Analysis

**Date:** 2026-06-04  

---

## key_metrics_ttm Null Rate

After correcting field names, the actual field presence for a US equity (VRT):

| Field | FMP Name | Present | Value Example |
|-------|---------|---------|--------------|
| ev_ebitda_ttm | evToEBITDATTM | ✅ | 53.41 |
| fcf_yield_ttm | freeCashFlowYieldTTM | ✅ | 0.0186 (1.86%) |
| roe_ttm | returnOnEquityTTM | ✅ | 0.421 (42.1%) |
| roic_ttm | returnOnInvestedCapitalTTM | ✅ | 0.203 (20.3%) |
| earnings_yield_ttm | earningsYieldTTM | ✅ | 0.0126 (PE≈79x) |
| price_to_fcf_ttm | evToFreeCashFlowTTM | ✅ | 54.3 |
| pe_ratio_ttm | peRatioTTM | ❌ ABSENT | Requires Premium+ plan |
| revenue_per_share_ttm | revenuePerShareTTM | ❌ ABSENT | Not in stable response |
| net_income_per_share_ttm | netIncomePerShareTTM | ❌ ABSENT | Not in stable response |

**Corrected null rate for key_metrics on Starter: 3/9 (33%) after field name fix**

**Impact on scoring:** The two most important valuation metrics for the dislocation framework are present:
- `freeCashFlowYieldTTM` ✅ — directly usable
- `earningsYieldTTM` ✅ — 1/PE equivalent, usable as PE proxy
- `evToEBITDATTM` ✅ — primary enterprise value multiple

The absent `peRatioTTM` can be derived from `earningsYieldTTM` (PE = 1 / earningsYield).

---

## grades_consensus Null Rate

**All 5 count fields present for all 9 equity symbols.** Null rate: **0%** for equities.

**Notable:** `strongBuy` is 0 for all symbols. FMP appears to not distinguish strong buy from regular buy for many brokerages. The `buy` count subsumes both, making the effective signal the net of `buy - sell`.

VXUS: 100% null (ETF — expected).

---

## earnings Null Rate

| Field | Null Rate (equities) | Reason |
|-------|---------------------|--------|
| `epsActual` (latest entry) | ~12% null | Most recent entry = future earnings |
| `epsActual` (past entries) | ~2% null | Very rare missing data |
| `epsEstimated` | ~0% | Estimates always present |
| `revenueActual` | ~5% null | Some companies don't report revenue estimates |
| `revenueEstimated` | ~2% null | |

The fetcher filters to `epsActual is not None` entries before computing beat rate — this correctly handles the future earnings row.

---

## income_statement_growth Null Rate

**All primary growth fields present for all 9 equity symbols.**

| Field | Null Rate | Notes |
|-------|----------|-------|
| growthRevenue | 0% | All equities |
| growthEPS | ~5% | A few symbols have null on one quarter |
| growthGrossProfit | 0% | All equities |
| VXUS | 100% | ETF — no income statement |

---

## Null Handling Policy

The fetcher stores missing fields as empty strings in CSV (not "None" or "0"). Downstream consumers must treat empty as "data unavailable" — never as zero. This is the same pattern used by Yahoo supplemental (`eps_growth_5yr` is often empty).

Null-safe consumption: if `fmp_ev_ebitda_ttm` is empty, the scoring system falls back to existing behavior (no FMP input). This is the fail-open consumption pattern established in the architecture review.
