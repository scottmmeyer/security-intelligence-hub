# Phase 8.0B.0 — FMP Capability Inventory

**Date:** 2026-06-04  
**FMP API Key:** Present in .env  
**Base URL:** https://financialmodelingprep.com/stable/

---

## Tier 1: High-Relevance Endpoints for SIH

### Analyst Estimates and Price Targets
| Endpoint | What It Provides | SIH Relevance |
|----------|-----------------|---------------|
| `/analyst-estimates` | Revenue/EPS/EBITDA forward estimates by period | **HIGH** — forward growth visibility |
| `/price-target-summary` | Price target stats (high/low/avg/count) per symbol | **HIGH** — richer than Yahoo ABR alone |
| `/price-target-consensus` | Consensus price target with high/low/median | **HIGH** — upside potential |
| `/grades` | Individual analyst upgrades/downgrades | **HIGH** — revision momentum |
| `/grades-historical` | Historical grade changes | **HIGH** — revision trend |
| `/grades-consensus` | Summary of strong buy/buy/hold/sell counts | **HIGH** — sentiment breadth |
| `/upgrades-downgrades-consensus-bulk` | Bulk analyst consensus for all symbols | **HIGH** — coverage efficient |

### Financial Statements — Growth
| Endpoint | What It Provides | SIH Relevance |
|----------|-----------------|---------------|
| `/income-statement-growth` | YoY/QoQ revenue, EPS, gross profit growth rates | **HIGH** — growth trajectory |
| `/financial-growth` | Comprehensive growth: revenue, EPS, FCF, EBITDA | **HIGH** — multi-factor growth |
| `/income-statement-ttm` | Trailing twelve months income statement | **HIGH** — current period context |
| `/cash-flow-statement-ttm` | TTM cash flow (FCF calculable) | **HIGH** — FCF yield |
| `/key-metrics-ttm` | TTM P/E, EV/EBITDA, FCF yield, ROIC, ROE | **VERY HIGH** — primary valuation metrics |
| `/ratios-ttm` | TTM financial ratios (gross margin, FCF margin) | **HIGH** — quality metrics |
| `/income-statement-growth-bulk` | Bulk growth data across all symbols | **HIGH** — efficient at scale |

### Earnings Data
| Endpoint | What It Provides | SIH Relevance |
|----------|-----------------|---------------|
| `/earnings` (per symbol) | EPS estimate vs actual, date, surprise % | **VERY HIGH** — earnings reaction analysis |
| `/earnings-calendar` | Upcoming earnings dates | **MEDIUM** — timing awareness |
| `/earnings-surprises-bulk` | Bulk annual earnings surprises | **HIGH** — systematic surprise tracking |

### Key Metrics and Valuation
| Endpoint | What It Provides | SIH Relevance |
|----------|-----------------|---------------|
| `/key-metrics` (annual/quarterly) | Historical P/E, EV/EBITDA, P/S, P/B, FCF yield | **VERY HIGH** — valuation history |
| `/key-metrics-ttm-bulk` | TTM key metrics for all symbols at once | **VERY HIGH** — most efficient |
| `/ratios` | Historical profitability, liquidity, efficiency | **HIGH** — quality metrics |
| `/ratios-ttm-bulk` | TTM ratios bulk | **HIGH** — efficient coverage |
| `/enterprise-values` | Enterprise value over time | **MEDIUM** — context for EV multiples |
| `/discounted-cash-flow` | FMP DCF estimate | **LOW** — model-dependent |
| `/financial-scores` | Piotroski F-Score, Altman Z-Score | **MEDIUM** — quality screening |

### Financial Statement Raw Data
| Endpoint | What It Provides | SIH Relevance |
|----------|-----------------|---------------|
| `/income-statement` | Full income statement (quarterly/annual) | **MEDIUM** — raw data for derived metrics |
| `/cash-flow-statement` | Full cash flow statement | **HIGH** — FCF calculation |
| `/balance-sheet-statement` | Full balance sheet | **MEDIUM** — debt/equity context |
| `/income-statement-bulk` | Bulk income statements | **HIGH** — efficient |

---

## Tier 2: Moderate-Relevance Endpoints

### Company and Market Data
| Endpoint | What It Provides | SIH Relevance |
|----------|-----------------|---------------|
| `/profile` | Company profile, market cap, beta | **MEDIUM** — already partially covered |
| `/historical-price-eod` | Historical price data | **LOW** — SIH has replay data |
| `/ratings-snapshot` | FMP internal ratings composite | **LOW** — redundant with existing signals |
| `/historical-ratings` | FMP historical composite rating | **LOW** — limited incremental value |

### Institutional and Insider
| Endpoint | What It Provides | SIH Relevance |
|----------|-----------------|---------------|
| `/insider-trading` | Insider buy/sell activity | **MEDIUM** — signal context |
| `/institutional-ownership` | 13F institutional holder data | **MEDIUM** — ownership context |

### Sector/Industry Performance
| Endpoint | What It Provides | SIH Relevance |
|----------|-----------------|---------------|
| `/sector-pe-snapshot` | Sector P/E multiples | **MEDIUM** — relative valuation context |
| `/historical-sector-pe` | Historical sector P/E | **MEDIUM** — cheap/expensive sector signal |

---

## Tier 3: Low-Relevance Endpoints

- Forex, Crypto, Commodities — out of scope for equity portfolio
- Senate/House trading — interesting but not scoring-relevant
- COT reports — futures positioning, not equity-relevant
- ETF holdings detailed breakdowns — duplicative with existing decomposition
- DCF detailed inputs — too model-dependent
- News APIs — not integrated into scoring framework
- Technical indicators — SIH uses replay-based validity, not TA

---

## Key FMP Metrics Not Available Elsewhere in SIH

| Metric | FMP Endpoint | Uniqueness |
|--------|-------------|-----------|
| Forward P/E (NTM) | `/key-metrics-ttm` or `/analyst-estimates` | **Unique** — not in Yahoo, Zacks, Danelfin |
| EV/EBITDA | `/key-metrics-ttm` | **Unique** |
| FCF Yield | `/key-metrics-ttm` (FCF / market cap) | **Unique** |
| Revenue Growth YoY | `/income-statement-growth` | **Unique** |
| EPS Growth YoY | `/income-statement-growth` | **Unique** (Yahoo field unfilled) |
| Revenue Acceleration | `/income-statement-growth` (sequential QoQ comparison) | **Unique** |
| Earnings Surprise % | `/earnings` | **Unique** |
| Earnings Surprise History | `/earnings-surprises-bulk` | **Unique** |
| Estimate Revision Direction | `/grades` (upgrades/downgrades) | **Unique** |
| Gross Margin % | `/ratios-ttm` | **Unique** |
| FCF Margin % | `/ratios-ttm` (FCF/Revenue) | **Unique** |
| ROIC | `/key-metrics-ttm` | **Unique** |
| ROE | `/key-metrics-ttm` | **Unique** |
| Piotroski F-Score | `/financial-scores` | **Unique** |
| Analyst Count | `/price-target-summary` | Partially duplicative (Yahoo has ABR) |
