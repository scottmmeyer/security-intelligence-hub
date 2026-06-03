# Phase 8.0B.0 Final Verdict
**Phase**: 8.0B.0 — FMP Capability Audit  
**Probe Date**: 2025-01-30  
**Question**: Can the free Financial Modeling Prep (FMP) API supply the data required for the FMI framework?  

---

## VERDICT: CONDITIONALLY VIABLE — REQUIRES PAID TIER

FMP **cannot** supply FMI data on the free tier. FMP **can** supply FMI data on the Basic paid tier (~$19/month), subject to Phase 8.0C verification.

---

## Evidence Summary

### What the Probe Found

| Test | Result |
|---|---|
| v3/v4 endpoints (25 tested) | ALL BLOCKED — "Legacy Endpoint" error (HTTP 403) |
| Stable API fundamentals (17 tested) | ALL BLOCKED — HTTP 402 Payment Required |
| Stable API misc (3 tested) | Accessible but returned empty lists |
| Only accessible endpoint with data | `stable/profile` — 5 basic fields (price, marketCap, beta, lastDividend, symbol) |
| FMS-relevant data returned | ZERO fields across all 15 test symbols |

### Root Cause: FMP API Migration

In 2024, FMP deprecated all v3/v4 endpoints for non-legacy users and introduced a new `/stable/` API. The `/stable/` API places all fundamental data (financials, growth rates, analyst estimates, earnings data, key metrics) behind a paid subscription wall. The free tier retains only a stripped-down profile endpoint.

---

## Per-Component Verdict

| FMS Component | Free Tier | Paid Tier (est.) | Confidence |
|---|---|---|---|
| 1. Revenue Growth | ❌ Not accessible | ✅ Available via `stable/financial-growth` | Medium |
| 2. EPS Growth | ❌ Not accessible | ✅ Available via `stable/financial-growth` | Medium |
| 3. Analyst Estimate Revisions | ❌ Not accessible | ⚠️ Available via `stable/analyst-estimates` — sparse for micro-caps | Medium |
| 4. Earnings Surprise | ❌ Not accessible (empty list on free) | ✅ Available via `stable/earnings-surprises` | Medium |
| 5. FCF Growth | ❌ Not accessible | ✅ Available via `stable/financial-growth` | Medium |
| 6. Forward PEG | ❌ Not accessible | ✅ Available via `stable/key-metrics-ttm` | Medium |

**All confidence ratings are "Medium" because paid tier access was not directly tested.** Paid tier estimates are based on FMP documentation and industry knowledge. Phase 8.0C must verify.

---

## Research Question Answers

**Q1: Which endpoints are available under the current free plan?**  
Only `stable/profile` (5 basic fields: symbol, price, marketCap, beta, lastDividend). All fundamental endpoints are blocked.

**Q2: Per-symbol availability of required data fields?**  
Zero availability across all 15 test symbols for any FMS-relevant field. Uniform blocking.

**Q3: Coverage percentage across the symbol set?**  
0% for all 11 data dimensions assessed. No exceptions.

**Q4: Data freshness?**  
Only the profile endpoint returned data; it appears to be real-time (intraday price). Fundamental data freshness cannot be assessed — no fundamental data was returned.

**Q5: Rate limits and operational constraints?**  
No rate limiting was observed because all requests fail at the authorization layer before reaching rate limiters. At the Basic paid tier (~$19/month), FMP documents 250,000 calls/month and ~300 req/min — sufficient for weekly full-universe FMS refresh.

**Q6: Can all 6 FMS components be populated from FMP?**  
**No — not on the free tier.**  
**Estimated yes — on the Basic paid tier (~$19/month)**, with the caveat that analyst estimate coverage may be sparse for micro-cap symbols (ATLC, PCB) and FCF metrics require special handling for financial-sector symbols.

**Q7: Monthly API consumption estimate?**  
- Top 25 symbols, weekly: ~500 calls/month (0.2% of Basic budget)  
- Top 100 symbols, weekly: ~2,000 calls/month (0.8% of Basic budget)  
- Full 2,586 universe, weekly: ~51,720 calls/month (20.7% of Basic budget)  
- Full 2,586 universe, daily: ~284,460 calls/month (exceeds Basic; needs Professional at $49/month)  
- **Recommended tiered strategy**: ~16,680 calls/month (6.7% of Basic budget)

---

## Key Risks

| Risk | Severity | Status |
|---|---|---|
| Paid tier still doesn't unlock all needed endpoints | HIGH | Unverified — requires Phase 8.0C |
| Analyst estimate data sparse for micro-caps | MEDIUM | Expected; acceptable with null handling |
| FMP prices increase | LOW | Manageable; $19/month is low cost |
| FCF metric meaningless for financials (ATLC, PCB, CBOE) | MEDIUM | Addressable by sector-aware null substitution |
| Free tier permanently insufficient | CONFIRMED | Not a risk — it's a known fact |

---

## Comparison to Phase 8.0A.1 Recommendation

Phase 8.0A.1 identified FMP at ~$19/month as the recommended data source for FMI operationalization. This probe **partially validates** that recommendation:

- ✅ FMP's **endpoint architecture** maps cleanly to all 6 FMS components (on paid tier)
- ✅ FMP's **call volume economics** are favorable at $19/month for all realistic operational scenarios
- ✅ FMP's **field naming** (`revenueGrowth`, `epsgrowth`, `freeCashFlowGrowth`, `pegRatioTTM`, `numberAnalystsEstimatedEps`, `actualEarningResult`, `estimatedEarning`) aligns directly with FMS score computation needs
- ⚠️ FMP's **actual data quality** (freshness, completeness, accuracy) on the paid tier remains **unverified**
- ⚠️ FMP's **analyst estimate tier restrictions** (some paid plans may still block analyst data) are **unverified**

The $19/month Basic tier is the **go/no-go decision point** for Phase 8.0C.

---

## Recommended Next Steps

### Immediate (Phase 8.0C prerequisite)
1. **Upgrade FMP API key** to Basic tier (~$19/month) at `financialmodelingprep.com`
2. **Re-run probe** using `scripts/phase_8_0b0_fmp_probe.py` with upgraded key
3. **Verify paid tier access** to all 6 FMS component endpoints
4. **Spot-check data quality** for VRT, LRCX, MU (large-cap), ATLC (micro-cap), TSM (ADR) before committing

### Phase 8.0C Scope (If Upgrade Confirmed Viable)
1. Design FMP data ingestion pipeline (schema, caching, refresh schedule)
2. Implement FMS score computation logic from FMP fields
3. Back-test FMS scores against historical price performance
4. Wire FMS scores into SIH conviction model

### Alternative Path (If FMP Paid Tier Fails)
If Phase 8.0C confirms FMP paid tier is also insufficient (e.g., analyst estimates blocked at Basic tier):
- **Primary alternative**: Alpha Vantage ($50/mo) for fundamentals + SEC EDGAR for earnings filings
- **Secondary alternative**: Yahoo Finance (unofficial) for prototyping only (not production-grade)
- **Long-term alternative**: Intrinio ($79–99/month) — stronger analyst data coverage

---

## Deliverables Written (Phase 8.0B.0)

| File | Status |
|---|---|
| `data/analysis/phase_8_0b0/fmp_endpoint_inventory.md` | ✅ Complete |
| `data/analysis/phase_8_0b0/fmp_symbol_coverage_matrix.csv` | ✅ Complete |
| `data/analysis/phase_8_0b0/fmp_data_quality_assessment.md` | ✅ Complete |
| `data/analysis/phase_8_0b0/fmp_rate_limit_analysis.md` | ✅ Complete |
| `data/analysis/phase_8_0b0/fmp_fms_coverage_report.md` | ✅ Complete |
| `data/analysis/phase_8_0b0/fmp_operational_cost_assessment.md` | ✅ Complete |
| `data/analysis/phase_8_0b0/phase_8_0b0_final_verdict.md` | ✅ Complete |

---

## Phase 8.0B.0 — COMPLETE

**Probe scripts retained**:
- `scripts/phase_8_0b0_fmp_probe.py` — v3/v4 + stable API endpoint probe
- `scripts/phase_8_0b0_stable_probe.py` — stable API deep probe

**Raw results**: `/tmp/fmp_full_results.json`, `/tmp/fmp_stable_results.json` (temporary; will not persist across sessions)
