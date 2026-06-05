# Phase 8.0B.0A — Data Freshness Strategy

**Date:** 2026-06-04  

---

## Freshness Requirements by Data Type

### 1. Earnings Surprise History (last 8 quarters)
**How often does it change?** Once per quarter, after earnings reporting date.

**Current data latency:** FMP updates earnings within 24–48 hours of reporting.

| Cadence | Rationale |
|---------|-----------|
| **Quarterly refresh** (after each earnings season) | EPS actuals don't change after reporting. Refresh 4× per year: Jan, Apr, Jul, Oct |
| **Trigger-based refresh** | For symbols with upcoming earnings (from `/earnings-calendar`), refresh within 24h of report date |

**SIH Implementation:** Quarterly batch + event-triggered for individual symbols near reporting dates.

**Storage retention:** Keep all 8 quarters (2 years). Immutable once written.

---

### 2. Revenue and EPS Growth (Quarterly YoY/QoQ)
**How often does it change?** Once per quarter, after financial statements filed.

| Cadence | Rationale |
|---------|-----------|
| **Quarterly refresh** | Growth rates are derived from income statements. Update after each quarter's 10-Q/10-K filing |
| **Not daily** | Growth doesn't change between quarters |

**SIH Implementation:** Same quarterly batch as earnings surprises. Can be triggered by the same refresh event.

**Storage retention:** Keep 4 quarters (1 year) for acceleration detection.

---

### 3. Valuation Metrics (P/E, EV/EBITDA, FCF Yield)
**How often does it change?** TTM metrics update as price changes daily. Denominator (earnings, EBITDA) updates quarterly.

| Cadence | Rationale |
|---------|-----------|
| **Daily refresh** | P/E changes every day with price movement. A 15% price drop changes the valuation signal materially |
| **Pre-market (04:00)** | Must be available before PAR runs |

**SIH Implementation:** Daily refresh as part of the morning signal refresh window. Same pattern as Danelfin/Zacks daily refresh.

**Note:** TTM denominator is from last quarter's financials. If price drops 15% (AVGO scenario), the P/E drops from 25x to 21x — this is a meaningful signal change that requires daily observation.

---

### 4. Estimate Revisions (Analyst Upgrades/Downgrades)
**How often does it change?** Continuously — analysts issue upgrades/downgrades after events.

| Cadence | Rationale |
|---------|-----------|
| **Daily refresh** | An upgrade/downgrade can happen any market day, especially around earnings |
| **Rolling 90-day window** | Only the trailing 90 days of revisions are actionable for near-term momentum |

**SIH Implementation:** Daily refresh. Pull last 90 days of grades/consensus. Use net upgrade count as signal.

---

### 5. Financial Quality Ratios (Gross Margin, FCF Margin)
**How often does it change?** Quarterly with financial filings.

| Cadence | Rationale |
|---------|-----------|
| **Quarterly refresh** | Margins are calculated from quarterly financials |
| **Daily TTM ratios** | TTM ratios update as each new quarter is added |

**SIH Implementation:** Ratios TTM (daily) captures rolling changes as new quarters roll in. Historical ratio snapshots quarterly.

---

### 6. Financial Scores (Piotroski F-Score)
**How often does it change?** Annual — Piotroski is a full-year assessment.

| Cadence | Rationale |
|---------|-----------|
| **Annual refresh** | F-Score based on full-year financials (FY) |

---

## Recommended Refresh Calendar

```
DAILY (pre-market, 04:00–04:15):
  - key_metrics_ttm (valuation: P/E, EV/EBITDA, FCF yield)
  - ratios_ttm (quality: gross margin, FCF margin)  
  - upgrades_downgrades_consensus (estimate revision direction)
  - earnings_calendar (upcoming earnings dates)

WEEKLY (Sunday, off-market):
  - analyst_estimates (forward EPS/revenue estimates, limit=1)
  - grades (last 90 days of individual upgrades/downgrades)

QUARTERLY (first Monday after each earnings season start):
  - earnings (last 8 quarters of EPS surprises)
  - income_statement_growth (4 quarters of growth rates)
  - financial_scores (Piotroski, Altman Z)

ANNUAL (January):
  - earnings_surprises_bulk (full year)
  - income_statement_growth_bulk (full year)
```

---

## Staleness Detection Pattern (mirrors refresh_signals.py)

SIH already has a staleness detection pattern in `refresh_signals.py`:
```python
def _latest_sourced_date(latest_csv: Path) -> str | None:
    # reads sourced_date from latest CSV file
```

FMP signals should follow identical pattern:
```
data/signals/fmp/
  latest_fmp_key_metrics.csv        (daily; contains sourced_date)
  latest_fmp_earnings_surprises.csv (quarterly; contains sourced_date)
  latest_fmp_income_growth.csv      (quarterly; contains sourced_date)
  latest_fmp_grades_consensus.csv   (daily; contains sourced_date)
```

The `ensure_signals_fresh()` function in `refresh_signals.py` would be extended to check each FMP file's staleness using the same `_latest_sourced_date()` function.

---

## Freshness SLA for Pre-Market PAR Runs

| Signal | Must Be Fresh By | Refresh Window |
|--------|-----------------|---------------|
| FMP key_metrics_ttm | 04:00 market open | 03:30–03:55 |
| FMP grades_consensus | 04:00 market open | 03:30–03:55 |
| FMP earnings_surprises | Next trading day after earnings | Within 24h of report |
| FMP income_growth | Within 1 week of quarter close | Weekly batch |

**SLA: Valuation and revision metrics are pre-market fresh. Earnings history and growth rates are quarterly-fresh.**
