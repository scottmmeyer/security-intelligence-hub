# Phase 8.0B.1B — Null Handling Review

## Null Handling Policy

All FMP fields follow the same null convention used by existing SIH signal files:
- Empty string `""` = not available / not returned by API
- `"None"` and `"nan"` are normalized to `""` during enrichment
- No sentinel values (−999, 0, etc.) are used to indicate missing data
- Downstream consumers check `if row.get("field"):` — empty string is falsy in Python and JavaScript

## Field-Level Null Analysis (Validation Set — 11 equity symbols)

| Field | Null Rate | Reason |
|-------|-----------|--------|
| `pe_ratio_ttm` | 100% | Not returned by FMP Starter plan `/key-metrics-ttm` endpoint. Field retained in schema. |
| All other key_metrics | 0% | Fully populated for equity symbols |
| All grades_consensus | 0% | Fully populated for equity symbols |
| All earnings_surprises | 0% | Fully populated; older quarters may be absent for recent IPOs |
| All income_growth | 0% | Fully populated |
| ETF fields | 100% | Correct — ETF_NOT_APPLICABLE symbols have no fundamental data |

## Null Scenarios by Symbol Type

### Large/Mid/Small Cap US Equities
- Expected: 0% nulls except `pe_ratio_ttm`
- Confirmed: 0/10 nulls in validation set (excluding pe_ratio)

### ADRs (International listed on US exchanges)
- Expected: 0% nulls — FMP indexes by US ticker
- Confirmed: TSM, ASML, CVE all 0% nulls

### Micro-cap / Recent IPO
- Expected: PARTIAL coverage; some quarterly history may be absent
- Earnings surprises: fewer than 8 quarters available → denominator adjusted
- Income growth: may have 1–2 quarters vs. 4 → acceleration field may be null

### REITs
- Expected: PARTIAL; key_metrics and grades typically available, earnings_surprises may be sparse
- Beat rate denominator adjusted for available quarters

### ETFs / Funds (in analytical universe)
- Coverage = ETF_NOT_APPLICABLE
- All FMP fields = empty string

### Portfolio-only holdings not in analytical universe (e.g., VXUS, FXAIX)
- Not in `analytical_universe.csv` → no `security_type` lookup
- FMP returns no data for broad ETF tickers
- Coverage = NO_DATA
- All FMP fields = empty string
- **This is correct behavior** — these are not deployment candidates

## Negative Value Handling

Negative values are valid financial data and must NOT be treated as nulls:

| Symbol | Field | Value | Interpretation |
|--------|-------|-------|---------------|
| DELL | roe_ttm | −3.63 | Negative book equity (leveraged buybacks) — valid |
| CAH | roe_ttm | −0.56 | Accounting write-downs — valid |
| PSX | revenue_growth_q1_yoy | −0.076 | Revenue decline — valid |
| CVE | revenue_growth_q1_yoy | −0.140 | Commodity cycle — valid |
| TSLA | revenue_growth_q1_yoy | −0.029 | Business softness — valid |

Implementation: `_get()` helper returns None only for `"", "None", "nan"`. Negative numeric strings are preserved as-is.

## pe_ratio_ttm Advisory

`pe_ratio_ttm` is 100% null and will remain so until FMP subscription is upgraded beyond Starter tier. Options:
1. Accept null for Phase 8.0B.1B (recommended — field is in schema, ready for future)
2. Derive P/E from `earnings_yield_ttm` (P/E ≈ 1/earnings_yield when positive) — acceptable approximation
3. Upgrade FMP subscription — not yet authorized

**Recommendation: Accept null. Document as known gap. Do not derive or substitute.**
