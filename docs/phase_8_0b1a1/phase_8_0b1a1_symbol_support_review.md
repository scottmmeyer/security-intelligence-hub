# Phase 8.0B.1A.1 — Symbol Support Review

**Date:** 2026-06-04  

---

## US Equities (VRT, DELL, ARW, AVGO, PSX, TSLA)

**Result: Full support across all 4 datasets.**

All US-listed equities returned complete data:
- key_metrics_ttm: 6/9 fields (after field name correction)
- grades_consensus: 5/5 fields
- earnings: 7–8 quarters of history
- income_growth: 4 annual periods

---

## International ADRs (TSM, ASML)

**Result: Full support — identical to US equities.**

TSM (Taiwan Semiconductor, NYSE) and ASML (ASML Holding, NASDAQ) both returned complete fundamental data across all 4 datasets. International companies with US exchange listings are treated as US equities by FMP on the Starter plan.

Sample validation:
- TSM income_growth: revenue_growth_q1 = +32.97% (2025 FY) — plausible for TSMC
- ASML grades: buy=25, hold=16, sell=3 — reasonable sell-side coverage
- TSM earnings: 8 quarters of data, EPS beats visible

---

## Cross-Listed Canadian Equities (CVE)

**Result: Full support.**

Cenovus Energy (CVE, NYSE-listed) returned complete data across all datasets. Canadian companies with NYSE/NASDAQ listings are covered on the Starter plan.

---

## ETFs (VXUS)

**Result: HTTP 200 but empty arrays for all datasets. Expected.**

Vanguard Total International ETF (VXUS) returns no fundamental data — ETFs have no earnings calls, no income statements, no analyst coverage in the same sense as equities. FMP returns HTTP 200 with `[]` (empty array) rather than an error.

**Implication for SIH:** ~20 ETF positions in the portfolio will have null FMP data. The fetcher stores stub rows with empty fields. Downstream consumers treat empty as "no FMP data available" and fall back to current behavior. This is correct and expected.

**ETFs that are relevant to SIH:** VB, VOO, VO, FXAIX, VEA, BNDX (broad index ETFs held for exposure). None of these benefit from fundamental analysis — they are correctly excluded from FMP scoring.

---

## Policy-Designated Symbols (TSLA)

**Result: Full support — same as any US equity.**

TSLA returned data across all 4 datasets. Policy (DO_NOT_SELL) doesn't affect FMP data availability. The fetcher fetches data for all symbols regardless of policy status.

---

## Symbol Type Classification Summary

| Symbol Type | Examples | FMP Support | Notes |
|------------|---------|------------|-------|
| US large-cap equity | VRT, DELL, AVGO, TSLA | ✅ Full | All 4 datasets |
| US mid/small-cap equity | ARW, PSX | ✅ Full | All 4 datasets |
| International ADR (US-listed) | TSM, ASML | ✅ Full | Treated as US equities |
| Canadian (US-listed) | CVE | ✅ Full | NYSE-listed → covered |
| US-listed ETF | VXUS | ⚠ Empty | HTTP 200, no fundamental data |
| Broad index mutual fund | FXAIX | ⚠ Expected empty | Fund, not equity |
| Micro-cap / OTC | (not tested) | ⚠ Unknown | May have gaps |

---

## Implications for SIH Universe

SIH's ~689-symbol analytical universe contains approximately:
- ~580 US equities → full FMP coverage expected
- ~80 international ADRs (TSM, ASML, CVE, SBS, etc.) → full coverage expected  
- ~20 ETFs/funds → empty data (expected, handled gracefully)
- ~10 micro-cap / OTC → unknown, assume partial

**Expected effective coverage: ~95% of actionable universe**

ETFs and funds are not deployment candidates in CW-DAS (ETF security_type is excluded from the deployment queue), so their lack of FMP data has no impact on the core use cases.
