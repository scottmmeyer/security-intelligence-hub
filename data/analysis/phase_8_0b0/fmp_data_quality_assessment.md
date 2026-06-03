# FMP Data Quality Assessment
**Phase**: 8.0B.0 — FMP Capability Audit  
**Probe Date**: 2025-01-30  
**Scope**: Data freshness, completeness, and field fidelity assessment  

---

## Executive Summary

**Assessment is moot for the free tier.** Because zero fundamental data endpoints are accessible under the current free API key, no data quality evaluation can be performed from first-hand observation. This document captures what CAN be assessed from probe results, supplemented by FMP's documented data characteristics for paid tiers.

---

## What Was Actually Observed

### Free Tier Data Returned

Only one stable endpoint returned data: `GET /stable/profile?symbol=VRT`

```json
{
  "symbol": "VRT",
  "price": <current price>,
  "marketCap": <current market cap>,
  "beta": <beta>,
  "lastDividend": <last dividend>
}
```

**Fields present**: 5 (symbol, price, marketCap, beta, lastDividend)  
**Fields relevant to FMS**: 0  
**Data freshness**: Real-time price (intraday)  
**Completeness**: 100% of the 5 available fields populated for VRT  

### Endpoints Returning Empty Lists

The following stable endpoints returned HTTP 200 with `[]`:
- `stable/earnings-surprises` — expected populated for a large-cap like VRT
- `stable/analyst-recommendations` — expected populated
- `stable/price-target` — expected populated
- `stable/upgrades-downgrades` — expected populated
- `stable/company-outlook` — expected populated

**Interpretation**: The empty-list responses on accessible endpoints strongly suggest these are **free-tier data walls** rather than genuine data absence for VRT. VRT (Vertiv Holdings) is a large-cap S&P 500 constituent with broad analyst coverage — earnings surprises and price targets unambiguously exist and should return data. The empty responses indicate data is present in FMP's database but withheld at the API response layer for free accounts.

---

## Inferred Data Quality (Paid Tier) — Based on FMP Documentation

*The following is based on FMP's published documentation and known characteristics of their data pipeline. It cannot be verified directly from the current API key.*

### Historical Coverage Depth

| Data Type | Typical Annual History | Quarterly History |
|---|---|---|
| Income Statement | 10+ years | 10+ years |
| Cash Flow Statement | 10+ years | 10+ years |
| Balance Sheet | 10+ years | 10+ years |
| Key Metrics | 10+ years | Limited |
| Financial Growth | 5–10 years | Limited |
| Analyst Estimates | 1–3 years forward | Quarterly |
| Earnings Surprises | 3–5 years historical | Per-quarter |

**FMS relevance**: The FMI framework requires 3–5 years of historical data for growth rate calculation (Revenue Growth, EPS Growth, FCF Growth) and 4–8 quarters of forward estimates for Analyst Revisions. FMP's paid tier appears to cover these depths based on documentation.

### Symbol Coverage

FMP claims coverage of:
- ~7,000+ US equities (NYSE + NASDAQ + OTC)
- International symbols (TSX, LSE, etc.)
- ETFs, mutual funds, indices

For the 15-symbol test set:
- Large-cap US (VRT, PSX, CBOE, LRCX, CAH, DELL, TSM, MU): Expected full coverage on paid tier
- Mid-cap (ARW, SNX, AVT, CIEN): Expected full coverage on paid tier
- Small/micro-cap (ATLC, SANM, PCB): Coverage may be thinner; analyst estimates may be sparse

### Known FMP Data Quality Issues (Industry-Documented)

1. **Restatement handling**: FMP does not always retroactively restate historical data when companies report revisions. This can create apparent discontinuities in growth rate calculations.

2. **TTF (time-to-freshness)**: Filing-based data (income statements, cash flows) typically updated within 1–2 days of SEC filing. Analyst estimates updated as revisions are published by data providers.

3. **Earnings surprise accuracy**: EPS surprise figures are computed by FMP as `(actual - consensus estimate) / |consensus estimate|`. The consensus figure is FMP's internal aggregate, not a validated third-party composite. May differ slightly from FactSet/Bloomberg consensus.

4. **International symbols**: TSM (Taiwan Semiconductor) may have data gaps or filing-date lags due to cross-listing complexity. FCF figures may need currency-normalization consideration.

5. **Small-cap analyst coverage**: For PCB (PCB Bancorp) and SANM (Sanmina), analyst estimate coverage may be sparse (1–3 analysts vs. 20+ for large-cap). `numberAnalystsEstimatedEps` field should be inspected before using estimate revision signals for these symbols.

---

## Data Quality Assessment: Conditional Verdict

| Assessment Dimension | Status | Confidence |
|---|---|---|
| Historical depth for FMS (3–5 year) | INFERRED ADEQUATE (paid) | Low — not verified |
| Forward estimate data for revisions | INFERRED ADEQUATE (paid) | Low — not verified |
| Earnings surprise accuracy | INFERRED ADEQUATE (paid) | Low — not verified |
| Small-cap symbol completeness | UNCERTAIN | Very Low |
| FCF data (vs. net income proxy) | INFERRED ADEQUATE (paid) | Low — not verified |
| Data freshness (post-filing lag) | INFERRED ≤2 DAYS (paid) | Low — not verified |
| Free tier data quality | N/A — NO DATA ACCESSIBLE | —  |

**All quality assessments are conditional on FMP paid tier access being obtained and re-verified.**

---

## Recommendation

Data quality cannot be assessed without a paid tier subscription. If Phase 8.0C proceeds with FMP acquisition, a 30-day trial (or lowest paid tier) should be used to re-run this quality assessment with actual data in hand before committing to FMP as the FMS data source.
