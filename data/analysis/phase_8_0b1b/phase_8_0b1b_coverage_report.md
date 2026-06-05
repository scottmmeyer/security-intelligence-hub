# Phase 8.0B.1B — Coverage Report

## Coverage Basis

FMP data has been fetched for the **12 validation symbols only** at this phase. The full analytical universe (2,473 symbols) requires a bulk fetch via `scripts/refresh_signals.py` (pending Phase 8.0B.1B authorization to run at scale).

The infrastructure handles all symbols — coverage reflects fetch completeness, not capability gaps.

## Current Coverage (Validation Set — 12 Symbols)

| Status | Count | % | Symbols |
|--------|-------|---|---------|
| FULL | 11 | 91.7% | VRT, DELL, ARW, PSX, CAH, SNX, TSM, ASML, CVE, TSLA, AVGO |
| PARTIAL | 0 | 0.0% | — |
| ETF_NOT_APPLICABLE | 0 | 0.0% | — (VXUS not in analytical universe) |
| NO_DATA | 1 | 8.3% | VXUS (ETF, not in analytical universe; FMP returns no data) |

## Full Universe Coverage (Current State — Pre-Bulk-Fetch)

| Status | Count | % | Notes |
|--------|-------|---|-------|
| FULL | 11 | 0.4% | Validation set only |
| PARTIAL | 0 | 0.0% | — |
| ETF_NOT_APPLICABLE | 8 | 0.3% | Unit Trust Funds (EPD, ET, MPLX, etc.) |
| NO_DATA | 2,455 | 99.2% | Not yet fetched |

## Projected Coverage After Bulk Fetch

Based on validation set results and FMP Starter plan coverage characteristics:

| Status | Projected Count | Projected % | Basis |
|--------|----------------|-------------|-------|
| FULL | ~1,800–2,000 | ~75–80% | US equities + major international ADRs |
| PARTIAL | ~100–200 | ~4–8% | Small/micro caps with partial data |
| ETF_NOT_APPLICABLE | ~8 | 0.3% | Unit Trust Funds |
| NO_DATA | ~250–500 | ~10–20% | Micro caps, recent IPOs, pink sheets |

### Notes on Expected Coverage Gaps

- **US Common Stock (large/mid/small cap):** Expected FULL coverage (~95%)
- **Depository Receipts (ADRs):** FULL coverage confirmed for TSM, ASML, CVE — expected ~80–90% ADR coverage
- **Common Stock (REIT):** Expected PARTIAL (FMP returns key_metrics but earnings_surprises may be sparse for smaller REITs)
- **Unit Trust Funds:** ETF_NOT_APPLICABLE (no fundamental data from FMP)
- **Micro-cap domestic:** PARTIAL or NO_DATA expected for bottom ~15% by market cap

## Coverage Classification Logic

```python
def classify_coverage(sym, security_type, km, gr, es, ig):
    if security_type in ETF_LIKE_TYPES:
        return "ETF_NOT_APPLICABLE"
    has_km = ev_ebitda or roe or roic populated
    has_gr = consensus_label populated
    has_es = beat_rate_8q populated
    has_ig = revenue_growth_q1_yoy populated
    if all 4 populated: return "FULL"
    if any 1+ populated: return "PARTIAL"
    return "NO_DATA"
```

## ETF Classification

ETF/FUND types in the analytical universe that receive `ETF_NOT_APPLICABLE`:
- Unit Trust Fund (EPD, ET, MPLX, AB, CQP, etc.)
- Common Stock marked as ETF/FUND (rare)

Portfolio-only holdings not in analytical universe (e.g., VXUS, VOO, BND, FXAIX, DODFX):
- Not in `analytical_universe.csv`
- FMP returns no fundamental data
- Coverage = `NO_DATA`
- **This is correct** — these are benchmark/diversification holdings, not deployment candidates
