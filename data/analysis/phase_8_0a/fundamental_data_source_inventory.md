# Fundamental Data Source Inventory
**Phase 8.0A | Q1: What reliable sources are available for fundamental momentum data?**

Generated: 2026-06-02 | Run ID: Phase-8.0A

---

## Purpose

The SIH currently operates exclusively on consensus/sentiment signals (ESS, Zacks, Danelfin). This inventory documents the available sources for adding a fundamental intelligence dimension — covering revenue, earnings, estimates, and valuation.

---

## Source Inventory

### 1. SEC EDGAR — Official Filing Database

| Field | Value |
|-------|-------|
| Coverage | All US-listed public companies |
| Data Types | 10-K (annual), 10-Q (quarterly), 8-K (earnings releases), DEF 14A |
| Freshness | Filing date + 1-2 days (near real-time) |
| Cost | Free |
| Licensing | Public domain |
| Automation | Fully automatable via EDGAR full-text search API and bulk data downloads |
| URL | https://www.sec.gov/cgi-bin/browse-edgar |
| XBRL | Structured financial data available since ~2009 via `/data/companyfacts/` API |
| Limitations | Raw/unstructured; requires parsing or XBRL extraction; no estimates |

**Use Case**: Source of record for historical actuals. Revenue, EPS, FCF from 10-K/10-Q. Earnings beat/miss requires comparison to analyst estimates (separate source needed).

---

### 2. Yahoo Finance (Free Tier)

| Field | Value |
|-------|-------|
| Coverage | ~50,000 global symbols |
| Data Types | Price, fundamentals, estimates (annual/quarterly), earnings history |
| Freshness | Real-time price; fundamentals updated post-filing (1-3 day lag) |
| Cost | Free (rate-limited) |
| Licensing | Personal/educational use; commercial use requires agreement |
| Automation | Unofficial API via `yfinance` Python library; subject to breakage |
| Beat/Miss | Limited — provides analyst consensus EPS vs actual |
| Limitations | Rate limiting; unofficial API only; commercial licensing uncertainty |

**Use Case**: Rapid fundamental data collection. Already used in the portfolio_manager project. Viable for prototyping Phase 8.0A.

---

### 3. StockAnalysis.com (stockanalysis.com)

| Field | Value |
|-------|-------|
| Coverage | ~10,000+ US symbols |
| Data Types | Income statement, balance sheet, cash flow, ratios, analyst forecasts |
| Freshness | Post-filing update, sourced from Fiscal.ai and S&P Global |
| Cost | Free tier: historical financials; Pro tier: full forecasts, estimates |
| Licensing | Free for non-commercial research use |
| Automation | No official API; scraping possible but rate-limited |
| Beat/Miss | Not directly available (estimates only) |
| Limitations | No programmatic API; Pro required for forward estimate details |

**Use Case**: Best human-readable summary for Phase 8.0A research. Used as primary research source in this phase.

---

### 4. Finnhub.io

| Field | Value |
|-------|-------|
| Coverage | US + global equities |
| Data Types | Fundamentals, earnings calendar, surprise history, estimate revisions, economic data |
| Freshness | Near real-time; earnings updates within hours |
| Cost | Free tier: 60 calls/minute, basic fundamentals; Premium: full history, revisions |
| Licensing | Free tier commercial-friendly; paid tiers for production |
| Automation | Full REST API; Python SDK available |
| Beat/Miss | **Yes** — earnings surprise endpoint provides actuals vs estimates |
| Estimate Revisions | Available in premium tier |
| URL | https://finnhub.io |

**Use Case**: Best programmatic option for earnings beat/miss history and estimate data. Free tier provides sufficient data for prototype Phase 8.0A.

---

### 5. Alpha Vantage

| Field | Value |
|-------|-------|
| Coverage | US equities + FX, crypto |
| Data Types | Income statement, balance sheet, earnings, EPS estimates |
| Freshness | Quarterly update lag |
| Cost | Free tier: 500 calls/day; Premium: full coverage |
| Licensing | Commercial use allowed with attribution |
| Automation | REST API with Python integration |
| Beat/Miss | Basic — provides quarterly EPS actuals vs estimates |
| Estimate Revisions | Not available |

**Use Case**: Supplement for earnings history (beat/miss %). Lower data quality than Finnhub but free for higher volume.

---

### 6. Financial Modeling Prep (FMP)

| Field | Value |
|-------|-------|
| Coverage | Global equities |
| Data Types | Full financials, DCF, ratios, earnings surprises, analyst estimates, price targets |
| Freshness | Same-day post-filing |
| Cost | Free tier: 250 calls/day; Starter: $19/month; Premium: $69+/month |
| Licensing | Commercial use allowed |
| Automation | Full REST API with Python wrapper |
| Beat/Miss | **Yes** — earnings surprise endpoint |
| Estimate Revisions | **Yes** — analyst estimates with revision history |
| Ratios | **Yes** — Forward PE, PEG, EV/EBITDA, FCF Yield, P/S |
| URL | https://financialmodelingprep.com |

**Use Case**: Best single-source for production FMI pipeline. FMP covers all required FMI fields (revenue, EPS, estimates, beat/miss, revisions, valuation ratios) with a reasonable API. **Recommended primary production source.**

---

### 7. LSEG (London Stock Exchange Group) / Refinitiv

| Field | Value |
|-------|-------|
| Coverage | Global equities (broadest) |
| Data Types | I/B/E/S estimates, revision history, earnings surprises, consensus, StarMine scores |
| Freshness | Near real-time |
| Cost | Institutional pricing ($50,000+/year typical) |
| Licensing | Institutional license required |
| Automation | LSEG Data Library (Python), Eikon API |
| Beat/Miss | **Yes** — institutional quality |
| Estimate Revisions | **Yes** — best-in-class |
| Notes | Already used for ESS data in SIH |

**Use Case**: Already partially integrated (ESS source). The same LSEG subscription that provides ESS may also provide fundamental estimate data. **Worth investigating as a coverage extension of existing subscription.**

---

### 8. Zacks Investment Research

| Field | Value |
|-------|-------|
| Coverage | US equities |
| Data Types | EPS consensus, estimate revision counts, earnings surprises, rank |
| Freshness | Daily estimate updates |
| Cost | Zacks Research Wizard / Data: $299+/month |
| Licensing | Institutional/commercial agreement |
| Automation | Zacks Data Feed API |
| Beat/Miss | **Yes** — historical surprise data |
| Estimate Revisions | **Yes** — proprietary estimate revision score is core to Zacks model |

**Use Case**: Zacks rank already ingested in SIH. The revision count data that drives Zacks' rank is a form of fundamental momentum signal. Accessing the underlying revision data would complete the picture. **Synergy with existing Zacks integration.**

---

## Coverage Comparison Matrix

| Source | Revenue/ EPS | Estimates | Revisions | Beat/Miss | Valuation | Cost | API |
|--------|-------------|-----------|-----------|-----------|-----------|------|-----|
| SEC EDGAR | ✅ Actuals | ❌ | ❌ | ❌ | ❌ | Free | ✅ |
| Yahoo Finance | ✅ | ✅ Basic | ❌ | ✅ Basic | ✅ | Free | ⚠️ Unofficial |
| StockAnalysis | ✅ | ✅ | ❌ | ❌ | ✅ | Free | ❌ |
| Finnhub | ✅ | ✅ | ✅ Premium | ✅ | ✅ | Freemium | ✅ |
| Alpha Vantage | ✅ | ✅ Basic | ❌ | ✅ Basic | ✅ | Freemium | ✅ |
| **FMP** | **✅** | **✅** | **✅** | **✅** | **✅** | **$19+/mo** | **✅** |
| LSEG/Refinitiv | ✅ | ✅ | ✅ Best | ✅ | ✅ | Institutional | ✅ |
| Zacks | Limited | ✅ | ✅ | ✅ | ✅ | $299+/mo | ✅ |

---

## Phase 8.0A Data Sourcing Approach

For this phase (evidence and framework design only), fundamental data was gathered manually from:
- **StockAnalysis.com** — income statement history, analyst forecasts, valuation ratios
- **SEC EDGAR** — company profile and filing references
- No automated API calls made in this phase

**For Phase 8.0B (production FMI):**
- **Primary recommended source: Financial Modeling Prep (FMP)** at ~$19/month for Starter tier
- Covers all required fields: historical financials, forward estimates, revision data, beat/miss history, valuation ratios
- Has clean Python API — integrable with existing SIH data pipeline architecture
- Alternative: Finnhub free tier for earnings surprises + Alpha Vantage for historical actuals

---

## Automation Feasibility Assessment

| Signal Type | Source | Feasibility | Notes |
|-------------|--------|-------------|-------|
| Revenue (trailing) | SEC EDGAR XBRL | High | Structured XML, free |
| EPS (trailing) | SEC EDGAR XBRL | High | Structured XML, free |
| Revenue estimates | FMP or Finnhub | High | API available |
| EPS estimates | FMP or Finnhub | High | API available |
| Estimate revisions (count) | FMP Premium / Zacks | Medium | Requires paid tier |
| Beat/miss history | Finnhub or FMP | High | Available in both |
| Forward PE / PEG / EV/EBITDA | FMP or Yahoo Finance | High | Standard endpoints |
| FCF Yield | Calculated from FCF + market cap | High | Derivable from EDGAR |
| Guidance trend | 8-K filings parsing | Low | Requires NLP/parsing |

---

## Recommendation Summary

| Priority | Source | Action |
|----------|--------|--------|
| Highest | **Financial Modeling Prep ($19/mo)** | Integrate as FMI primary source in Phase 8.0B |
| High | **LSEG** (extend existing subscription) | Confirm if estimate revision data is included |
| Medium | **Finnhub (free tier)** | Use for earnings beat/miss in Phase 8.0B prototype |
| Low | **SEC EDGAR XBRL** | Archive backup for actuals |
| Low | **Yahoo Finance (yfinance)** | Development/prototype only |

**FMI data acquisition requires ~$19–$299/month depending on revision data depth required.**
