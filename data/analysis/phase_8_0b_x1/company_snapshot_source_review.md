# Company Snapshot Source Review — Phase 8.0B.X.1

## Source: Yahoo Finance (yfinance ticker.info)

### Field Review

| Field | Yahoo Key | Status | Notes |
|-------|-----------|--------|-------|
| Company Name | `longName` | ✓ Available | Full legal name |
| HQ City | `city` | ✓ Available | e.g., "Round Rock" |
| HQ State | `state` | ✓ Available | Abbreviated (TX, OH). Empty for non-US |
| HQ Country | `country` | ✓ Available | Full name (United States, Taiwan) |
| Business Description | `longBusinessSummary` | ✓ Available | 500–2000 chars; needs truncation |

### Validation Results (Live API Test — June 4, 2026)

| Symbol | Company Name | HQ | Desc Length |
|--------|-------------|-----|-------------|
| VRT | Vertiv Holdings Co | Westerville, OH, United States | 1,047 |
| DELL | Dell Technologies Inc. | Round Rock, TX, United States | 1,835 |
| ARW | Arrow Electronics, Inc. | Centennial, CO, United States | 1,194 |
| PSX | Phillips 66 | Houston, TX, United States | 1,810 |
| CAH | Cardinal Health, Inc. | Dublin, OH, United States | 1,421 |
| SNX | TD SYNNEX Corporation | Fremont, CA, United States | 1,399 |
| TSM | Taiwan Semiconductor Manufacturing Company Limited | Hsinchu City, Taiwan | 1,025 |
| ASML | ASML Holding N.V. | Veldhoven, Netherlands | 1,459 |
| CVE | Cenovus Energy Inc. | Calgary, AB, Canada | 983 |

**Result: 9/9 symbols fully populated.**

### Business Summary Truncation Strategy

Raw Yahoo descriptions are 500–2000 characters. UI target is 100–250 characters.

Truncation logic:
1. Split on `. ` (sentence boundary)
2. Take first sentence(s) up to 250 chars
3. Strip boilerplate patterns (`"... and its subsidiaries"`, repetitive legal text)
4. Append `"…"` if truncated

### HQ Format Strategy

Compose from `city`, `state`, `country`:
- US/Canada: `"{city}, {state}, {country}"` → `"Round Rock, TX, United States"`
- International: `"{city}, {country}"` → `"Veldhoven, Netherlands"`
- Missing: `"Unknown"`

### Data Refresh Strategy

- Company profiles change infrequently (quarterly at most)
- Refresh via `scripts/refresh_signals.py` with a `company_profile` provider
- Smart-refresh: skip symbols already in latest cache
- Rate limit: 0.3–1.2s delay between symbols (consistent with security_metadata)

### Limitations

- ETFs/Funds: Yahoo longBusinessSummary often absent; display gracefully with `"—"` or fund-type note
- Foreign ADRs: Company names may be in English translation; acceptable for operator use
- State field absent for non-US companies; handled in HQ composition
