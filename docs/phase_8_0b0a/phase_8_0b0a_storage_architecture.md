# Phase 8.0B.0A — Storage Architecture

**Date:** 2026-06-04  

---

## Storage Format Recommendation: CSV (consistent with existing SIH pattern)

### Rationale

SIH uses CSV for all signal storage:
- `data/signals/zacks/` — CSV files per refresh date
- `data/signals/danelfin/` — CSV files per refresh date
- `data/signals/yahoo/` — CSV files per refresh date
- `data/current/analytical_universe.csv` — master signal join

FMP signals should follow the identical pattern. No new storage format decisions required.

**CSV is appropriate because:**
- All consumers (analytical_universe rebuild, PAR runner) read CSV
- Row counts are small (689–5,000 rows)
- No query complexity — always full table scans
- Deterministic, auditable, human-readable
- Consistent with `_latest_sourced_date()` staleness detection

---

## Directory Structure

```
data/signals/fmp/
  daily/
    fmp_key_metrics_{YYYY-MM-DD}.csv     # P/E, EV/EBITDA, FCF yield
    fmp_ratios_{YYYY-MM-DD}.csv          # Gross margin, FCF margin
    fmp_grades_consensus_{YYYY-MM-DD}.csv # Net revision direction
  quarterly/
    fmp_earnings_surprises_{YYYY-QN}.csv # EPS surprise history (8Q)
    fmp_income_growth_{YYYY-QN}.csv      # Revenue/EPS growth (4Q)
    fmp_financial_scores_{YYYY}.csv      # Piotroski, Altman (annual)
  latest/
    latest_fmp_key_metrics.csv           # Symlink/copy of most recent daily
    latest_fmp_earnings_surprises.csv    # Most recent quarterly
    latest_fmp_income_growth.csv         # Most recent quarterly
    latest_fmp_grades_consensus.csv      # Most recent daily
```

**Pattern matches existing:**
```
data/signals/danelfin/
  2026-06-04_danelfin_scores.csv
  latest_danelfin.csv  ← latest symlink
```

---

## Schema for Each Output File

### fmp_key_metrics_{date}.csv
```
symbol, snapshot_date, sourced_date, pe_ratio_ttm, ev_ebitda_ttm, 
price_to_fcf_ttm, fcf_yield_ttm, roe_ttm, roic_ttm, earnings_yield_ttm,
revenue_per_share_ttm, net_income_per_share_ttm
```

### fmp_earnings_surprises_{year}_{q}.csv
```
symbol, snapshot_date, sourced_date,
eps_surprise_q1_pct, eps_surprise_q2_pct, eps_surprise_q3_pct,
eps_surprise_q4_pct, eps_surprise_q5_pct, eps_surprise_q6_pct,
eps_surprise_q7_pct, eps_surprise_q8_pct,
beats_last_8q, beat_rate_8q, latest_eps_actual, latest_eps_estimate
```

### fmp_income_growth_{year}_{q}.csv
```
symbol, snapshot_date, sourced_date,
revenue_growth_q1_yoy, revenue_growth_q2_yoy, revenue_growth_q3_yoy, revenue_growth_q4_yoy,
eps_growth_q1_yoy, eps_growth_q2_yoy, eps_growth_q3_yoy, eps_growth_q4_yoy,
revenue_acceleration (q1 - q4 slope), gross_profit_growth_q1_yoy
```

### fmp_grades_consensus_{date}.csv
```
symbol, snapshot_date, sourced_date,
strong_buy_count, buy_count, hold_count, sell_count, strong_sell_count,
net_buy_score (strong_buy + buy - sell - strong_sell),
consensus_label
```

---

## Storage Footprint Estimates

| Dataset | Per-Symbol Row Size | 689 Symbols | 2,500 Symbols | 5,000 Symbols |
|---------|-------------------|-------------|---------------|---------------|
| key_metrics daily | ~200 bytes | **138 KB/day** | 500 KB/day | 1 MB/day |
| earnings_surprises quarterly | ~400 bytes | 276 KB/quarter | 1 MB/quarter | 2 MB/quarter |
| income_growth quarterly | ~300 bytes | 207 KB/quarter | 750 KB/quarter | 1.5 MB/quarter |
| grades_consensus daily | ~150 bytes | 103 KB/day | 375 KB/day | 750 KB/day |
| **Daily total** | | **~241 KB/day** | ~875 KB/day | 1.75 MB/day |
| **Annual total** (daily + quarterly) | | **~95 MB/year** | ~350 MB/year | 700 MB/year |

Storage is negligible at all scales. No partitioning or compression required.

---

## Retention Policy

| Data Type | Retention | Reason |
|-----------|----------|--------|
| Daily key_metrics | **90 days of daily snapshots** | Enables valuation trend analysis |
| Daily grades_consensus | **90 days** | Tracks revision momentum |
| Quarterly earnings/growth | **3 years** (12 quarters) | Enables long-term growth trend analysis |
| Latest symlinks | Always current | Used by analytical_universe rebuild |

**Historical vs Latest Only:**

Both are needed:
- **Latest** — consumed by analytical_universe rebuild and scoring
- **Historical** — enables dislocation framework ("P/E was 25x, now 14x = compressed")

The historical depth requirement is modest (90 days for valuation, 12 quarters for growth). This is easily accommodated in CSV files with minimal storage.

---

## Integration Point with Analytical Universe

FMP data joins into the analytical universe at the `snapshot_date` field on `symbol`. The rebuild script reads `latest_fmp_*.csv` files and adds FMP columns to analytical_universe.csv, identical to how Zacks/Danelfin/Yahoo data is joined today.

No new join logic required. Same CSV-keyed symbol join as existing providers.
