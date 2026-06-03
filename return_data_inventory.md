# Return Data Inventory
**Phase 7.6G — Deliverable Q1**
**Generated:** 2026-06-01
**Run:** PAR-20260601-9CFD7C63

---

## 1. Purpose

This inventory documents all price and return data sources available in the security-intelligence-hub for use in the ESS effectiveness study (Phase 7.6G).

---

## 2. Primary Source: Per-Symbol Daily Price History

**Location:** `data/history/prices/symbol=<TICKER>/prices.csv`
**Status: PRIMARY SOURCE — USED FOR THIS STUDY**

| Attribute | Value |
|-----------|-------|
| Symbols with price files | 2,567 |
| Date range | 2025-05-13 → 2026-05-26 |
| Trading days | ~257 |
| Schema | security_id, symbol, security_type, date, open, high, low, close, **adjusted_close**, volume, dividend, split_ratio, source_provider, created_at_utc |
| Data provider | YAHOO_FINANCE |
| Adjusted for dividends/splits | Yes (`adjusted_close`) |
| Intersection with ESS universe | 2,487 of 2,918 ESS symbols (85.2%) |

**Notes:**
- Price data begins 2025-05-13 (pre-dates earliest ESS archive by 97 days)
- Price data ends 2026-05-26 (6 days before reference date of 2026-06-01)
- This creates a forward-return availability constraint: 30-day returns are available for ESS dates through ~2026-04-25; 60-day returns through ~2026-03-25; 90-day returns through ~2026-02-25

**Forward return coverage achieved:**
| Window | Records with Return Data | % of 54,566 Total |
|--------|--------------------------|-------------------|
| 30-day | 32,805 | 60.1% |
| 60-day | 10,435 | 19.1% |
| 90-day | 7,031 | 12.9% |

---

## 3. Secondary Sources (Not Used for Primary Analysis)

### 3.1 `data/current/security_prices.csv`
**Status: EMPTY — headers only, no data rows**

| Attribute | Value |
|-----------|-------|
| Rows | 0 (headers only) |
| Schema | security_id, symbol, security_type, date, open, high, low, close, adjusted_close, volume, dividend, split_ratio, source_provider, created_at_utc |
| Use | Not usable — no data present |

### 3.2 `data/current/benchmark_returns.csv`
**Status: MINIMAL — 2 data rows**

| Attribute | Value |
|-----------|-------|
| Rows | 2 |
| Schema | benchmark_id, symbol_or_index, date, adjusted_close, cumulative_return, source_provider |
| Use | Not suitable for cross-sectional ESS study |

### 3.3 `data/current/investable_vehicle_returns.csv`
**Status: MINIMAL — 2 data rows**

| Attribute | Value |
|-----------|-------|
| Rows | 2 |
| Schema | vehicle_id, symbol, date, adjusted_close, cumulative_return, source_provider |
| Use | Not suitable — only 2 vehicles |

### 3.4 `data/current/replay_performance_series.csv`
**Status: PRESENT — 80,527 rows, but portfolio-aggregate not security-level**

| Attribute | Value |
|-----------|-------|
| Rows | 80,527 |
| Schema | series_id, replay_id, series_type, date, value, cumulative_return, source, coverage_status |
| Use | Portfolio-level performance series only; not security-level return data |

### 3.5 `data/signals/yahoo/` — Yahoo Supplemental Signals
**Status: PRESENT — current_price and price_target available for recent dates**

| Attribute | Value |
|-----------|-------|
| Dates | 2026-05-14 through 2026-05-29 (5 snapshots) |
| Schema | symbol, price_target, abr, eps_growth_5yr, **current_price**, upside_pct |
| Symbols | 34–955 per snapshot |
| Use | Only May 2026 snapshots available; cannot construct historical return series |

### 3.6 `data/history/benchmarks/`
**Status: PRESENT — benchmark snapshots**

| File | Rows | Use |
|------|------|-----|
| `benchmark_snapshots.csv` | Various | Benchmark level data |
| `benchmark_outcomes.csv` | Various | Benchmark return outcomes |
| `benchmark_registry_history.csv` | Various | Registry |

These files provide market benchmark context but not individual security returns.

---

## 4. Return Computation Method

For this study, forward returns were computed from the per-symbol price history as follows:

**Formula:** `return_Nd = (adjusted_close[T+N] / adjusted_close[T]) - 1`

**Price lookup tolerance:** ±5 calendar days to find nearest trading day for any target date.

**Exclusions:**
- Records where start price = 0 or missing
- Records where forward target date exceeds available price history
- 431 ESS symbols (14.8%) had no price file — excluded from return analysis; included in transition/persistence analysis

---

## 5. Key Limitation: Market Regime Dependency

The entire price history (2025-05-13 → 2026-05-26) covers a **predominantly bullish market period**, with a sharp recovery rally in April–May 2026. This single-regime bias means:

- All ESS categories show positive average returns
- Mean-reversion effects in beaten-down stocks (VERY_BEARISH) produce counter-intuitive short-term returns
- A multi-regime dataset spanning bull, bear, and neutral periods would provide stronger effectiveness evidence

This limitation is documented throughout the analysis reports.

---

## 6. Data Quality Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Completeness | GOOD | 85.2% ESS-to-price match |
| Date coverage | ADEQUATE | 257 trading days; limits 90-day window coverage |
| Accuracy | HIGH | YAHOO_FINANCE adjusted close, dividend/split-adjusted |
| Timeliness | ADEQUATE | Last price is 2026-05-26 (6 days before reference) |
| Regime coverage | LIMITED | Single predominantly-bullish period |
| Return window sufficiency | PARTIAL | 30d good (60%), 60d limited (19%), 90d minimal (13%) |
