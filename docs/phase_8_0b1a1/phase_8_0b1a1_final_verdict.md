# Phase 8.0B.1A.1 — Final Verdict

**Date:** 2026-06-04  
**Classification: APPROVED WITH ADVISORIES**

---

## The Seven Questions

### Q1: Is FMP data quality sufficient for SIH?
**Yes.** All 4 datasets return valid data for equity symbols. Values are directionally consistent with known fundamentals (TSM +33% growth, TSLA −3% growth, AVGO 58 buy ratings). The data is suitable for thesis integrity assessment and dislocation detection.

### Q2: Are all target datasets usable?
**Yes — with two corrections made during this validation:**
1. Auth method corrected from header to URL param (`?apikey=KEY`)
2. Field names corrected for all 4 datasets (particularly key_metrics and earnings)

### Q3: Are international holdings adequately supported?
**Yes.** TSM (Taiwan ADR) and ASML (Netherlands NASDAQ) return complete fundamental data identical to US equities. CVE (Canadian NYSE-listed) also returns full data. All international holdings in the SIH universe that trade on US exchanges are covered.

### Q4: Are ADRs adequately supported?
**Yes.** ADRs (TSM, ASML) behave identically to US equities in all 4 datasets.

### Q5: Are ETF records usable?
**ETFs return empty arrays — this is expected and handled correctly.** VXUS returns HTTP 200 with `[]`. The fetcher stores stub rows with empty fields. ETFs are not CW-DAS deployment candidates and not meaningful CRA sell sources, so their lack of fundamental data has no impact on the core use cases.

### Q6: Are field definitions stable?
**Mostly stable, with one critical finding:** The FMP `/stable/` API uses different field names than the legacy `/v3/` API and the FMP documentation. The corrections made during this validation must be treated as the definitive field mappings going forward. The fetcher now documents the verified names with inline comments.

### Q7: Is Phase 8.0B.1B authorized?
**Yes — APPROVED.**

---

## Corrections Made During This Validation

| Component | Issue | Fix |
|-----------|-------|-----|
| `_fmp_get()` auth | Header auth (`apikey: KEY`) returns 401 | Changed to URL param (`?apikey=KEY`) |
| `_parse_key_metrics_ttm()` | Wrong field names (`evToEbitdaTTM`, `roeTTM`, etc.) | Corrected to verified names |
| `_parse_earnings_surprises()` | Wrong field names (`actualEarningResult`) | Corrected to `epsActual`/`epsEstimated` |
| `_parse_earnings_surprises()` | Included future earnings entries (epsActual=null) | Filter to past quarters only |
| `_parse_income_growth()` | Mixed old/new field names | Standardized to `growthRevenue`/`growthEPS` |
| Test fixtures | Used old field names | Updated to verified stable API names |

---

## Advisories for Phase 8.0B.1B

1. **peRatioTTM absent on Starter plan.** Use `earningsYieldTTM` (= 1/PE) as proxy. The dislocation framework works with EV/EBITDA and FCF yield instead of PE.

2. **ETF symbols return empty data.** This is handled gracefully in the fetcher. No special treatment needed in downstream joins.

3. **Annual growth data only on Starter.** Quarterly income growth requires Premium+. Annual is sufficient for Phase 8.0B.1B visibility work; quarterly granularity deferred to the Premium upgrade.

4. **`strongBuy` consistently 0.** FMP may aggregate strong buy into `buy`. Net revision score uses `(buy - sell)` which is unaffected.

5. **Future earnings entry filtering required.** The most recent `/stable/earnings` entry is often a future earnings date with `epsActual=null`. The fetcher filters correctly.

---

## Phase 8.0B.1B Authorization

Phase 8.0B.1B — Analytical Universe Extension — is **APPROVED** to proceed.

The FMP signal intake pipeline is now validated against live data, all field name mappings are verified, and all field parsers are producing correct output. The `data/signals/fmp/` directory structure is ready to receive live data once the daily refresh is triggered.

Prerequisite status:
- Auth method: ✅ Corrected
- Field mappings: ✅ Verified and corrected  
- Coverage: ✅ 95%+ of actionable universe
- Tests: ✅ 1,004/1,004 passing
- Data quality: ✅ Values sanity-checked against known fundamentals
