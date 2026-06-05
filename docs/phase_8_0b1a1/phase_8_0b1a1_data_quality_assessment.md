# Phase 8.0B.1A.1 — Data Quality Assessment

**Date:** 2026-06-04  

---

## Assessment by Dataset

### 1. key_metrics_ttm — Quality: GOOD (with field name fix)

**Strengths:**
- HTTP 200 for 100% of equity symbols
- `evToEBITDATTM`, `freeCashFlowYieldTTM`, `earningsYieldTTM`, `returnOnEquityTTM`, `returnOnInvestedCapitalTTM` all present and populated
- 30+ fields available beyond the target schema
- Consistent across US, ADR, and Canadian listings

**Weaknesses/Findings:**
- `peRatioTTM` absent on Starter plan — requires workaround (use earningsYieldTTM as PE proxy)
- Field names diverge from documentation and legacy API (corrected in fetcher)
- `revenuePerShareTTM` and `netIncomePerShareTTM` absent

**Verdict: Usable for dislocation framework (EV/EBITDA, FCF yield, ROE, ROIC all present).**

---

### 2. grades_consensus — Quality: EXCELLENT

**Strengths:**
- Perfect 5/5 field coverage for all 9 equity symbols
- Analyst counts are meaningful (VRT=19, AVGO=58, TSLA=81 analysts)
- Consistent across symbol types

**Weaknesses:**
- `strongBuy` = 0 for all symbols (FMP may aggregate into `buy`)
- This means the net_buy_score = (buy - sell) works correctly

**Verdict: Ready to use as-is.**

---

### 3. earnings (surprises) — Quality: GOOD (with future-entry handling)

**Strengths:**
- 8 entries returned for all equity symbols
- `epsActual`, `epsEstimated` present and consistent
- Revenue actuals also available (not in current schema but available)
- International ADRs (TSM, ASML) return full earnings history

**Weaknesses/Findings:**
- Most recent entry always has `epsActual=null` (future earnings date included)
- Field names corrected: `epsActual`/`epsEstimated` (not `actualEarningResult`/`estimatedEarning`)
- After filtering out future entries, typically 7/8 past quarters available

**Verdict: Usable after filtering to past quarters only (fetcher corrected).**

---

### 4. income_statement_growth — Quality: EXCELLENT

**Strengths:**
- 4 annual periods for all equity symbols
- `growthRevenue`, `growthEPS`, `growthGrossProfit` all present
- 33 growth fields available (EBITDA growth, operating income growth, etc.)
- International symbols (TSM: +32.97% revenue, ASML: +15.58%) return plausible values

**Weaknesses:**
- Annual periods only on Starter plan (quarterly requires Premium+)
- This is sufficient for thesis integrity assessment (trend detection works on annual)

**Verdict: Ready to use as-is. Annual granularity is sufficient for Phase 8.0B.1B.**

---

## Sanity Check: Do Values Make Sense?

| Symbol | FMP Data | Expected | Assessment |
|--------|---------|----------|-----------|
| VRT | FCF yield 1.86%, ROE 42.1% | Premium industrial, high ROE expected | ✅ Plausible |
| AVGO | EV/EBITDA 53.4x | Semiconductor premium valuation | ✅ Plausible |
| TSM | Revenue growth +32.97% | TSMC 2025 AI-driven growth | ✅ Matches known data |
| TSLA | Revenue growth −2.9% | Tesla 2025 challenges | ✅ Matches known data |
| ARW | Revenue growth +10.5% | Arrow Electronics recovery | ✅ Plausible |
| TSLA | Grades: buy=32, hold=33, sell=16 | Mixed analyst sentiment | ✅ Correct |
| AVGO | Grades: buy=51, hold=7, sell=0 | High conviction | ✅ Correct |

All sampled values are directionally consistent with publicly known fundamentals.

---

## Auth Method Correction

**Finding:** The FMP `/stable/` API requires URL query parameter auth (`?apikey=KEY`). Header auth (`apikey: KEY`) returns HTTP 401 Invalid API Key. This was discovered during this validation phase.

**Resolution:** The fetcher `_fmp_get()` was corrected to append `apikey=KEY` as a URL parameter. All tests updated accordingly.

**This was a latent defect in Phase 8.0B.1A that would have blocked all live data flows.** Phase 8.0B.1A.1 successfully caught and corrected it before Phase 8.0B.1B.
