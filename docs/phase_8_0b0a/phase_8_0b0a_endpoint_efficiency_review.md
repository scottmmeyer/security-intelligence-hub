# Phase 8.0B.0A — Endpoint Efficiency Review

**Date:** 2026-06-04  
**Probe results:** Live API probe with current key (HTTP 402 on all fundamentals → FREE plan confirmed)

---

## Endpoint Efficiency Matrix

### Tier 1: Bulk Endpoints (Ultimate plan required)

| Endpoint | Coverage | Payload/Call | Cadence | Verdict |
|----------|---------|-------------|---------|---------|
| `/earnings-surprises-bulk?year=YYYY` | Global | All symbols for 1 year | **1 call/year** | **Highest efficiency** — one call gets surprise history |
| `/income-statement-growth-bulk?year=YYYY&period=Q1` | Global | All symbols for 1 quarter | **4 calls/year** (one per quarter) | **Highest efficiency** for growth data |
| `/key-metrics-ttm-bulk` | Global | All symbols, latest TTM | **1 call/day** | **Highest efficiency** for valuation |
| `/ratios-ttm-bulk` | Global | All symbols, latest TTM ratios | **1 call/day** | **Highest efficiency** for quality |
| `/upgrades-downgrades-consensus-bulk` | Global | All symbols, consensus grades | **1 call/day** | **Highest efficiency** for revisions |
| `/income-statement-bulk?year=YYYY&period=QN` | Global | All symbols, one period | **4 calls/year** | Raw income for derived calculations |

**Verdict on bulk: Ultimate plan ($99/mo) makes FMP integration trivially scalable.** The entire fundamental refresh for 689–5,000 symbols costs 4–6 calls/day.

---

### Tier 2: Per-Symbol Endpoints (Starter plan sufficient)

| Endpoint | Coverage | Rows Returned | Call Volume (689 syms) | Cadence | Verdict |
|----------|---------|--------------|----------------------|---------|---------|
| `/earnings?symbol=X&limit=8` | Global | 8 quarters of EPS/revenue actuals + estimates | 689 | Quarterly | ✅ Very efficient — compact payload |
| `/income-statement-growth?symbol=X&limit=4` | US (Starter) | 4 quarters of growth rates | 689 | Quarterly | ✅ Small, deterministic payload |
| `/key-metrics-ttm?symbol=X` | US (Starter) | 1 row, ~30 fields | 689 | Daily | ✅ Fast per-call |
| `/grades?symbol=X` | US (Starter) | List of upgrades/downgrades | 689 | Weekly | ✅ Small payload |
| `/grades-consensus?symbol=X` | Global | 1 row, buy/hold/sell counts | 689 | Weekly | ✅ Very compact |
| `/analyst-estimates?symbol=X&limit=4` | US (Starter) | 4 periods of forward estimates | 689 | Quarterly | ✅ Small |
| `/financial-scores?symbol=X` | Global | 1 row, Piotroski + Altman | 689 | Quarterly | ✅ Annual update sufficient |
| `/profile?symbol=X` | Global (Free!) | 1 row, company profile | 689 | Monthly | ✅ Accessible on FREE plan |

---

### Tier 3: Endpoints to Skip

| Endpoint | Reason to Skip |
|----------|---------------|
| `/discounted-cash-flow` | Model-dependent, high variance, not deterministic |
| `/income-statement` (raw) | Derived data; use growth + key_metrics instead |
| `/balance-sheet-statement` | Not needed for v1 scoring; use ratios_ttm |
| `/cash-flow-statement` | Use key_metrics FCF yield instead of raw CF |
| `/ratios` (historical) | Use ratios_ttm for current; historical adds little |
| `/enterprise-values` | EV covered by key_metrics_ttm |

---

## Recommended Ingestion Method by Endpoint

### With Starter Plan ($19/mo) — Per-Symbol Approach

```
Daily refresh (689 calls × 1 endpoint = 689 calls/day):
  /key-metrics-ttm → fmp_key_metrics_{date}.csv

Weekly refresh (689 calls × 2 endpoints = 1,378 calls/week):
  /grades-consensus → fmp_grades_consensus_{date}.csv
  /analyst-estimates (limit=1) → fmp_analyst_estimates_{date}.csv

Quarterly refresh (689 calls × 3 endpoints = 2,067 calls/quarter):
  /earnings (limit=8) → fmp_earnings_{date}.csv
  /income-statement-growth (limit=4) → fmp_income_growth_{date}.csv
  /financial-scores → fmp_financial_scores_{date}.csv

TOTAL: ~3,400 API calls at peak quarter; ~800 calls/day normal operations
COST AT 300/min: ~11 minutes at peak; < 3 minutes daily
```

### With Ultimate Plan ($99/mo) — Bulk Approach

```
Daily refresh (4–6 total calls):
  /key-metrics-ttm-bulk → fmp_key_metrics_bulk_{date}.csv
  /ratios-ttm-bulk → fmp_ratios_bulk_{date}.csv
  /upgrades-downgrades-consensus-bulk → fmp_grades_bulk_{date}.csv

Quarterly refresh (3 bulk calls):
  /earnings-surprises-bulk?year=2026 → fmp_earnings_surprises_bulk_{year}.csv
  /income-statement-growth-bulk?year=2026&period=Q2 → fmp_income_growth_bulk_{year_q}.csv

TOTAL: 4–6 calls/day, 7–9 calls/quarter
COST: Negligible at any scale
```

---

## Plan Recommendation for Phase 8.0B.1

**Start with Starter ($19/mo) per-symbol approach.** This is:
- Sufficient for 689 symbols
- Consistent with existing refresh_signals.py per-symbol pattern
- Easy to validate before upgrading
- $19/mo is trivial cost for the value delivered

**Upgrade path:** When universe exceeds 2,000 symbols or when bulk efficiency becomes operationally necessary, upgrade to Ultimate ($99/mo). No code redesign required — bulk endpoints produce the same CSV format but in one call.

---

## HTTP 402 Interpretation

All endpoints returning 402 are inaccessible on the FREE plan because they require:
- Starter: Annual fundamentals, US coverage
- Starter+: Quarterly period data
- Premium/Ultimate: Historical depth + bulk

The current key must be **upgraded to at least Starter** before any FMP fundamental integration can be tested or deployed.

**Action required before Phase 8.0B.1 can begin: Upgrade FMP plan to Starter or above.**
