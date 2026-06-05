# Company Context Inventory

**Date:** 2026-06-04

---

## Required Fields

| Field | Required Display |
|-------|-----------------|
| Company Name | Full or display name |
| Sector | GICS sector |
| Industry | Sub-sector / industry group |
| Headquarters | City, Country |
| Country | Country of domicile |
| Market Cap Category | MEGA / LARGE / MID / SMALL / MICRO |
| Short Business Description | Max 250 chars |

---

## Available Data Sources

### Source 1: `data/signals/security_metadata/latest_security_metadata.csv`
Fields: `symbol`, `sector`, `industry`, `country`, `quote_type`, `sourced_date`  
Coverage: 2,556 symbols (fetched via Yahoo Finance)  
Freshness: As of 2026-05-15  
Quality: **HIGH** — granular GICS-aligned industry (e.g. "Electrical Equipment & Parts", "Semiconductors")

Sample values:
| Symbol | Sector | Industry | Country |
|--------|--------|---------|---------|
| VRT | Industrials | Electrical Equipment & Parts | United States |
| DELL | Technology | Computer Hardware | United States |
| AVGO | Technology | Semiconductors | United States |
| TSM | Technology | Semiconductors | Taiwan |
| ASML | Technology | Semiconductor Equipment & Materials | Netherlands |
| CVE | Energy | Oil & Gas Integrated | Canada |
| ARW | Technology | Electronics & Computer Distribution | United States |
| TSLA | Consumer Cyclical | Auto Manufacturers | United States |

ETFs (VXUS, FXAIX): **NOT FOUND** in security_metadata.

### Source 2: `PAR/holdings.csv` — `description` field
Contains Fidelity-style security description (raw).  
Example: "VERTIV HOLDINGS CO COM CL A", "TAIWAN SEMICONDUCTOR MANUFACTURING SPON ADS EACH REP 5 ORD TWD10"

This is the **best available company name** source — it comes directly from the portfolio upload.

### Source 3: `data/current/analytical_universe.csv`
Fields: `sector`, `industry` (broad; e.g. "INDUSTRIALS", "TECHNOLOGY"), `country`, `geography`, `market_cap_bucket`  
**Lower granularity than security_metadata** (industry = same as sector for most entries).

### Source 4: PAR Analysis Run (already in frontend)
The analysis run JSON sent to the UI includes `holdings[]` with:
- `description` — company name from Fidelity upload
- `sector` — from AU (broad category)
- `industry` — from AU (broad category)
- `market_cap_bucket` — MEGA / LARGE / MID / SMALL / MICRO

### Source 5: FMP `/stable/profile?symbol=X`
Fields available via FMP: company name, description, headquarters city, state, industry (precise), sector  
Coverage: Available on all plans (confirmed in live probe — HTTP 200)  
**Not yet fetched** — but accessible immediately with existing key.

---

## Gap Analysis

| Required Field | Available Source | Gap |
|---------------|-----------------|-----|
| Company Name | `holdings.description` (Fidelity text) | Format is noisy; needs cleaning |
| Sector | `security_metadata.sector` | ✅ Good quality |
| Industry | `security_metadata.industry` | ✅ Good quality |
| Country | `security_metadata.country` | ✅ Good quality |
| Headquarters City | ❌ Not in any current source | Need FMP profile or yfinance |
| Market Cap Category | `analytical_universe.market_cap_bucket` | ✅ Available |
| Business Description | ❌ Not in any current source | Need FMP profile or yfinance |

---

## Summary

Five of seven fields are available today from existing sources. Two fields — **headquarters city** and **business description** — require either FMP profile or a new yfinance fetch. The FMP `/stable/profile` endpoint returns both and is already accessible.
