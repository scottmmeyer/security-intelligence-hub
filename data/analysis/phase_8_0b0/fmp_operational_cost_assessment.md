# FMP Operational Cost Assessment
**Phase**: 8.0B.0 — FMP Capability Audit  
**Probe Date**: 2025-01-30  
**Scope**: API cost modeling for FMI operationalization at top-25, top-100, and full universe scale  

---

## FMP Pricing Tiers (Current as of Early 2025)

*Note: FMP pricing is subject to change. Verify at financialmodelingprep.com/developer/docs/pricing before committing.*

| Plan | Monthly Price | Calls/Month | Key Data Access | Rate Limit |
|---|---|---|---|---|
| Free | $0 | ~250 (severely restricted) | Basic profile only | Very low |
| Starter | ~$14/mo | 50,000 | Basic financials (annual only, 5yr) | 100 req/min |
| Basic | ~$19/mo | 250,000 | Full financials, growth, analyst est., earnings | 300 req/min |
| Professional | ~$49/mo | 750,000 | + DCF, transcripts, insider trades, bulk | 750 req/min |
| Enterprise | Custom | Unlimited | All endpoints, bulk download, dedicated support | Unlimited |

**Recommended tier for FMI**: Basic (~$19/month) as minimum viable; Professional (~$49/month) if daily full-universe updates are needed.

---

## API Call Model

### Calls Per Symbol (FMS Score Update)

Using the optimized endpoint mapping from `fmp_fms_coverage_report.md`:

| Endpoint | Purpose | Calls |
|---|---|---|
| `stable/financial-growth` | Revenue, EPS, FCF growth (components 1, 2, 5) | 1 |
| `stable/analyst-estimates` | Estimate revisions + forward PEG inputs (components 3, 6) | 1 |
| `stable/earnings-surprises` | Earnings surprise history (component 4) | 1 |
| `stable/key-metrics-ttm` | PEG ratio cross-check (component 6) | 1 |
| `stable/profile` | Sector/type classification for scoring adjustments | 1 |
| **Total (optimized)** | **All 6 FMS components** | **5** |

Full-fidelity path (with income statement + cash flow for data validation):

| Endpoint | Purpose | Calls |
|---|---|---|
| `stable/financial-growth` | Pre-computed growth rates | 1 |
| `stable/income-statement?period=annual` | Revenue/EPS validation | 1 |
| `stable/cash-flow-statement?period=annual` | FCF validation | 1 |
| `stable/analyst-estimates` | Forward estimates + revisions | 1 |
| `stable/earnings-surprises` | EPS surprise history | 1 |
| `stable/key-metrics-ttm` | PEG ratio | 1 |
| `stable/ratios-ttm` | Additional ratio cross-check | 1 |
| `stable/profile` | Classification | 1 |
| **Total (full-fidelity)** | **All 6 FMS components + validation** | **8** |

---

## Monthly Call Budget Scenarios

### Scenario A: Top 25 — Weekly Full Refresh

| Metric | Value |
|---|---|
| Universe size | 25 symbols |
| Refresh frequency | Weekly (4×/month) |
| Calls per symbol | 5 (optimized) |
| **Monthly calls** | **25 × 5 × 4 = 500** |
| % of Basic (250K) budget | 0.2% |
| % of Starter (50K) budget | 1.0% |
| **Recommended plan** | **Starter ($14/mo) is sufficient** |

### Scenario B: Top 100 — Weekly Full Refresh

| Metric | Value |
|---|---|
| Universe size | 100 symbols |
| Refresh frequency | Weekly (4×/month) |
| Calls per symbol | 5 (optimized) |
| **Monthly calls** | **100 × 5 × 4 = 2,000** |
| % of Basic (250K) budget | 0.8% |
| % of Starter (50K) budget | 4.0% |
| **Recommended plan** | **Starter ($14/mo) is sufficient** |

### Scenario C: Full Universe (2,586) — Weekly Full Refresh

| Metric | Value |
|---|---|
| Universe size | 2,586 symbols |
| Refresh frequency | Weekly (4×/month) |
| Calls per symbol | 5 (optimized) |
| **Monthly calls** | **2,586 × 5 × 4 = 51,720** |
| % of Basic (250K) budget | 20.7% |
| % of Starter (50K) budget | 103.4% — **EXCEEDS** |
| **Recommended plan** | **Basic ($19/mo)** |

### Scenario D: Full Universe (2,586) — Daily Refresh

| Metric | Value |
|---|---|
| Universe size | 2,586 symbols |
| Refresh frequency | Daily (22 trading days/month) |
| Calls per symbol | 5 (optimized) |
| **Monthly calls** | **2,586 × 5 × 22 = 284,460** |
| % of Basic (250K) budget | 113.8% — **EXCEEDS** |
| % of Professional (750K) budget | 37.9% |
| **Recommended plan** | **Professional ($49/mo)** |

### Scenario E: Full Universe — Tiered Refresh Strategy (Recommended)

| Tier | Symbols | Refresh | Calls/Month |
|---|---|---|---|
| Tier 1: Active positions (est. 25) | Daily | 25 × 5 × 22 = 2,750 |
| Tier 2: Top 100 conviction candidates | Weekly | 75 × 5 × 4 = 1,500 |
| Tier 3: Full universe (remaining 2,486) | Monthly | 2,486 × 5 × 1 = 12,430 |
| **Total** | **2,586** | **Mixed** | **~16,680** |
| % of Basic (250K) budget | **6.7%** |
| **Recommended plan** | **Basic ($19/mo)** |

**Tiered refresh is the recommended operational approach** — high-frequency updates where they matter (active positions, top conviction candidates), monthly sweeps for the rest.

---

## Cost Comparison: FMP vs. Alternatives

| Provider | Monthly Cost | FMS-relevant Data | Call Limits | Notes |
|---|---|---|---|---|
| **FMP Basic** | **$19/mo** | Full FMS coverage (estimated) | 250K/mo | Primary recommendation |
| FMP Professional | $49/mo | Full + extras | 750K/mo | Only if daily full-universe needed |
| Alpha Vantage Premium | $50/mo | Partial (no analyst estimates) | 75 req/min | Worse value for analyst data |
| Polygon.io Starter | $29/mo | Market data only; no fundamentals | 5 req/min | Not suitable for FMS |
| Yahoo Finance (unofficial) | Free | Unreliable; no analyst revision history | Undefined | Not suitable for production |
| SEC EDGAR (XBRL) | Free | Financials only; no analyst data | None | No analyst estimates, no PEG |
| Quandl/Nasdaq Data Link | $50–200/mo | Strong fundamentals; analyst data extra | 300/min | More expensive |

**FMP Basic at $19/month represents the best cost-to-coverage ratio for the FMI use case**, assuming paid tier access unlocks the endpoints blocked on free tier (to be confirmed in Phase 8.0C).

---

## One-Time Initial Load Estimate

When FMI is first deployed, a historical backfill of 5 years of annual data is needed for all 2,586 symbols:

| Endpoint | Symbols | Periods | Total Calls |
|---|---|---|---|
| `stable/financial-growth` (annual, limit=5) | 2,586 | 1 call each | 2,586 |
| `stable/analyst-estimates` (limit=8) | 2,586 | 1 call each | 2,586 |
| `stable/earnings-surprises` | 2,586 | 1 call each | 2,586 |
| `stable/key-metrics-ttm` | 2,586 | 1 call each | 2,586 |
| **Total initial load** | | | **~10,344 calls** |

At 250,000/month budget, the entire initial backfill fits in **less than 4.1% of a single month's budget**.

---

## Budget Risk Factors

| Risk | Impact | Mitigation |
|---|---|---|
| FMP increases prices or changes tier limits | Medium | Annual contract or price lock if offered |
| Universe grows beyond 2,586 symbols | Low | Tiered strategy scales linearly |
| Analyst estimate endpoints require higher tier | High | Verify in Phase 8.0C before committing |
| FMP endpoint migration breaks existing pipeline | Medium | Pin to stable API; monitor FMP changelog |

---

## Recommendation

**Upgrade the current free key to FMP Basic (~$19/month)** as the minimum investment to validate FMI operationalization. This unlocks:
- Full fundamental data access for all 2,586 universe symbols
- Sufficient call budget for weekly full-universe refresh or daily top-100 refresh
- All 6 FMS components addressable within a single paid tier

**Do not upgrade to Professional until daily full-universe refresh is confirmed as a business requirement** — Basic tier is likely sufficient for the FMI use case at current universe scale.
