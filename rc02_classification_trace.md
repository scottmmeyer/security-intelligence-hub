# RC-02 Classification Trace

**Date:** 2026-06-09  
**Issue:** Persistent RC-02 FAIL — BSVN, STNG, SIMO classified as `asset_class=UNKNOWN`

---

## Classification Pipeline

```
Portfolio CSV (Fidelity)
    ↓
ingestion.py — parse_fidelity_csv()
    ↓  ALL holdings initialized with asset_class=UNKNOWN
PortfolioHolding(asset_class="UNKNOWN", geography="UNKNOWN", ...)

    ↓
enrichment.py — enrich_holdings()
    Priority 1: analytical_universe.csv lookup    ← MISS for BSVN/STNG/SIMO
    Priority 2: _ETF_OVERRIDES table              ← MISS (not in table)
    Priority 3: Cash heuristic                    ← MISS (not cash)
    ↓  Falls through — asset_class stays UNKNOWN

    ↓
alignment.py — compute_alignment()
    UNKNOWN holdings NOT mapped to any L1 node
    L1 sum < 100%

    ↓
reconciliation.py — _rc02_allocation_totals()
    nonzero_unknown holdings → status = FAIL
```

---

## Why Each Symbol Was UNKNOWN

### Root Cause: Absent from `data/current/analytical_universe.csv`

The analytical universe (2,473 entries) is the primary classification source. All three symbols were absent because:

1. They are not tracked in the SIH scoring pipeline (no ESS/Zacks/Danelfin scoring data in analytical_universe.csv)
2. They are not ETFs or cash instruments (so `_ETF_OVERRIDES` doesn't cover them)
3. No prior manual override existed

### Confirmed Absent

| Symbol | In analytical_universe.csv | In _ETF_OVERRIDES |
|---|---|---|
| BSVN | No | No |
| STNG | No | No |
| SIMO | No | No |

### Signal / Company Profile Data Available

The signals pipeline DID have data for these symbols:

| Symbol | security_metadata sector | country | company_profile location |
|---|---|---|---|
| BSVN | Financial Services / Banks - Regional | United States | Oklahoma City, OK, US |
| STNG | Energy / Oil & Gas Midstream | Monaco | Monaco (NYSE-listed) |
| SIMO | Technology / Semiconductors | Hong Kong | Hong Kong (ADR) |

These fields were available in `data/signals/security_metadata/latest_security_metadata.csv` and `data/signals/company_profile/latest_company_profile.csv` but are NOT read by `enrich_holdings()` — the enrichment function only reads `analytical_universe.csv` and `_ETF_OVERRIDES`.

---

## Why They Don't Appear in analytical_universe.csv

The analytical universe is built from the SIH scoring pipeline recalculation. These three symbols lack sufficient signal coverage (ESS scoring eligibility) to be included in the recalculation seed `SEED_20260520_D9E58D7F`. They are held in the portfolio but sit below the scoring/replay eligibility threshold for the analytical universe.

---

## Impact of UNKNOWN Classification

- **Allocation:** 1.35pp of portfolio excluded from L1 sum
- **Recommendations:** No direct impact — UNKNOWN holdings are still scored via Zacks/Danelfin where available
- **Reconciliation:** RC-02 status = FAIL (hard failure for any non-zero UNKNOWN position)
- **UI:** "RECONCILIATION FAIL" badge displayed on every Portfolio Alignment load
