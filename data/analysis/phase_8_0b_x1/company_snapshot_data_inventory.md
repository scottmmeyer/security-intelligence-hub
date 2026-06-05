# Company Snapshot Data Inventory — Phase 8.0B.X.1

## Objective
Inventory all available data sources for company name, headquarters, and business description enrichment.

## Sources Evaluated

### 1. security_metadata (existing)
- File: `data/signals/security_metadata/latest_security_metadata.csv`
- Columns: symbol, sector, industry, country, quote_type, sourced_date
- Status: **In use — covers 2,556 symbols**
- Gaps: No company name, no HQ city/state, no business description

### 2. analytical_universe (existing)
- File: `data/current/analytical_universe.csv`
- Columns: symbol, sector, industry, market_cap_bucket, security_type, country, ...
- Status: **In use for cap tier enrichment (Phase 8.0B.X)**
- Gaps: No company name, no HQ, no business description

### 3. Yahoo Finance / yfinance ticker.info (existing provider)
- Module: `src/scoring/fetch_security_metadata.py` uses yfinance
- Available fields confirmed via live API test:
  - `longName` — full legal company name
  - `city` — HQ city
  - `state` — HQ state/province (US/CA, abbreviated)
  - `country` — HQ country
  - `longBusinessSummary` — full business description (500–2000 chars)
  - `industry`, `sector` — already captured
- Status: **Provider already in use. New fetch module needed for profile fields.**
- Coverage: 9/9 validation symbols confirmed (VRT, DELL, ARW, PSX, CAH, SNX, TSM, ASML, CVE)

### 4. FMP (Financial Modeling Prep)
- Status: Available (Phase 8.0B.1A), but introduces dependency on paid endpoint
- Decision: **NOT used** — yfinance already provides equivalent data at no additional cost

### 5. Danelfin, Zacks
- Status: Signal-only providers. No company profile data available.

## Selected Source: Yahoo Finance / yfinance

**Rationale:**
- Already an approved data provider in SIH
- No new API key or subscription required
- Coverage confirmed across all validation symbols
- Consistent with `fetch_security_metadata.py` conventions
- Data quality sufficient for display-only use case

## Storage Plan
- New output: `data/signals/company_profile/`
- Files: `YYYY-MM-DD_company_profile.csv` + `latest_company_profile.csv`
- Columns: symbol, long_name, city, state, country, business_summary, sourced_date
