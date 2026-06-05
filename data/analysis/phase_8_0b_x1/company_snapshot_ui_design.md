# Company Snapshot UI Design — Phase 8.0B.X.1

## Section Name Change

| Before | After |
|--------|-------|
| Company Context | Company Snapshot |

## Display Fields (in order)

| Position | Label | Data Source | Fallback |
|----------|-------|-------------|---------|
| 1 | Company | `long_name` from company_profile | Symbol |
| 2 | Headquarters | city + state + country | "Unknown" |
| 3 | Sector | `sector` from security_metadata | "—" |
| 4 | Industry | `industry` from security_metadata | "—" |
| 5 | Business | `business_summary` (truncated ≤250 chars) | "—" |
| 6 | Country | `country` from security_metadata | "—" |
| 7 | Cap Tier | `market_cap_bucket` from analytical_universe | (omit row) |

## Layout

```
┌──────────────────────────────────────────────────┐
│ COMPANY SNAPSHOT                                 │
│                                                  │
│ Company      Dell Technologies Inc.              │
│ Headquarters Round Rock, TX, United States       │
│ Sector       Technology                          │
│ Industry     Computer Hardware                   │
│ Business     Dell Technologies provides          │
│              enterprise servers, storage, PCs,   │
│              and AI infrastructure solutions.    │
│ Country      United States                       │
│ Cap Tier     [LARGE]                             │
└──────────────────────────────────────────────────┘
```

## CSS Changes

- Section title text: "Company Context" → "Company Snapshot"
- `.dq-cs-val.dq-cs-business` — spans 2 columns, italic styling, wraps naturally
- `.dq-cs-badge` — unchanged (Cap Tier pill)
- Grid remains 2-column (label | value) layout

## Suppression Rules

- Render section even if company profile data is missing (show "Unknown")
- Only fully suppress if: no sector, no industry, no country, AND not an ETF/Fund AND no profile data
- ETF/Fund: show "Exchange-Traded Fund" in sector field, no business description

## API Response Shape

`GET /api/security-metadata` returns per symbol:
```json
{
  "DELL": {
    "sector": "Technology",
    "industry": "Computer Hardware",
    "country": "United States",
    "quote_type": "EQUITY",
    "market_cap_bucket": "LARGE",
    "security_type": "EQUITY",
    "long_name": "Dell Technologies Inc.",
    "hq": "Round Rock, TX, United States",
    "business_summary": "Dell Technologies provides enterprise servers, storage systems, networking equipment, PCs, and IT solutions globally."
  }
}
```
