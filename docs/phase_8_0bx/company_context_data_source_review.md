# Company Context Data Source Review

**Date:** 2026-06-04

---

## Recommended Implementation Strategy

Use a **tiered fallback approach**:

1. **Primary:** `security_metadata` (already fetched, highest quality sector/industry)
2. **Fallback for name:** `holdings.description` (available in every analysis run)
3. **Fallback for market cap:** `analytical_universe.market_cap_bucket`
4. **For HQ and description:** FMP `/stable/profile` (deferred to Phase 8.0B.1B)

This means Phase 8.0B.X can ship immediately with 5/7 fields, and the remaining 2 (HQ city + business description) follow when FMP profile is integrated.

---

## Source Decision by Field

### Company Name
**Source:** `holdings[].description` (from PAR analysis run)  
**Format:** Fidelity-style — e.g. "VERTIV HOLDINGS CO COM CL A"  
**Cleaning required:** Strip trailing "COM CL A", "INC COM USD1", "SPON ADS EACH REP 5 ORD TWD10" etc.  
**UI label:** Symbol + cleaned description → "VRT — Vertiv Holdings"  
**Fallback:** Symbol only if description is empty

**Cleaning approach (client-side JS):**
```js
function _cleanCompanyName(desc, symbol) {
    if (!desc) return symbol;
    return desc
        .replace(/\s+(COM|INC|CORP|LTD|CO|PLC|GROUP|HOLDINGS?)(\s+.+)?$/i, "")
        .replace(/\s+CL\s+[A-Z]$/i, "")
        .replace(/\s+SPON\s+ADS.*/i, " ADR")
        .trim();
}
```

### Sector
**Source:** `security_metadata_by_symbol[sym].sector`  
**Quality:** HIGH — "Industrials", "Technology", "Consumer Cyclical"  
**Fallback:** `holdings[].sector` (broad, uppercase)  
**Fallback 2:** "Unknown"

### Industry
**Source:** `security_metadata_by_symbol[sym].industry`  
**Quality:** HIGH — "Electrical Equipment & Parts", "Semiconductors", "Auto Manufacturers"  
**Fallback:** `holdings[].industry` (broad, same as sector usually)  
**Fallback 2:** "Unknown"

### Country
**Source:** `security_metadata_by_symbol[sym].country`  
**Quality:** HIGH — "United States", "Taiwan", "Netherlands", "Canada"  
**Fallback:** Derive from `holdings[].geography` (US/INTERNATIONAL)  
**Fallback 2:** "Unknown"

### Market Cap Category
**Source:** `holdings[].market_cap_bucket` from analysis run  
**Quality:** HIGH — MEGA / LARGE / MID / SMALL / MICRO  
**No fallback needed** — always populated

### Headquarters City — Phase 8.0B.1B
**Source:** FMP `/stable/profile?symbol=X` → `city`, `state`, `country`  
**Deferred:** Not available from current data sources  
**Display in current phase:** "—" or omit field  
**FMP profile available:** Confirmed HTTP 200 on free plan

### Business Description — Phase 8.0B.1B
**Source:** FMP `/stable/profile?symbol=X` → `description` (truncated to 250 chars)  
**Deferred:** Not available from current data sources  
**Display in current phase:** "—" or omit field

---

## Data Flow for Phase 8.0B.X (Immediate)

```
analysis run JSON (already sent to browser)
  └── holdings[symbol].description    → company name (clean)
  └── holdings[symbol].sector         → sector (fallback)
  └── holdings[symbol].market_cap_bucket → cap tier

GET /api/security-metadata            (NEW endpoint)
  └── Reads latest_security_metadata.csv
  └── Returns {symbol → {sector, industry, country}}
  └── Called once on analysis load
```

No new data fetching required for Phase 8.0B.X. Security metadata is already on disk.

---

## ETF Handling

ETFs (VXUS, FXAIX, VOO, VB, etc.) are **not in security_metadata**.  
Display: "Exchange-Traded Fund" for sector/industry, country from AU if available.  
Market cap: "N/A" or from holdings  
Name: Use `holdings.description` directly (e.g. "FIDELITY 500 INDEX FUND")
