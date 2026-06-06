# FMP Signal Quality Assessment — Phase 8.0B.1C

## Coverage Summary (2,463 FULL/PARTIAL symbols)

| Field | Coverage | Null % | Negative % | Signal Quality |
|-------|----------|--------|-----------|----------------|
| EV/EBITDA | 2,463/2,463 | 0% | 15.4% | ⭐⭐⭐ Good |
| ROE | 2,463/2,463 | 0% | 26.5% | ⭐⭐ Moderate |
| ROIC | 2,463/2,463 | 0% | 21.1% | ⭐⭐⭐ Good |
| FCF Yield | 2,463/2,463 | 0% | 21.2% | ⭐⭐⭐ Good |
| Beat Rate | 2,463/2,463 | 0% | 0% | ⭐⭐⭐⭐ Excellent |
| Latest EPS Surprise | 2,439/2,463 | 1% | 25.4% | ⭐⭐⭐ Good |
| Revenue Growth | 2,463/2,463 | 0% | 25.1% | ⭐⭐⭐ Good |
| EPS Growth | 2,463/2,463 | 0% | 39.3% | ⭐⭐ Moderate |
| Rev Acceleration | 2,462/2,463 | 0% | 62.6% | ⭐⭐ Moderate |
| Consensus Label | 2,442/2,463 | 0.9% | 0% | ⭐⭐⭐ Good |
| Net Buy Score | 2,442/2,463 | 0.9% | 3.2% | ⭐⭐⭐ Good |
| P/E TTM | 0/2,463 | **100%** | — | ❌ Unavailable (Starter plan) |

---

## Per-Field Assessment

### Beat Rate (8-quarter)
**Quality: EXCELLENT**
- 0% null, 0% negative values — cleanest field in the dataset
- Measures how consistently a company exceeds analyst expectations
- Strong predictive relationship: a company beating 87.5%+ of estimates shows consistent execution quality
- **Suitable for conviction modifier**

### Revenue Growth (YoY Q1)
**Quality: GOOD**
- 0% null, 25% negative (downturns, cyclicals) — valid data
- Directly measures business momentum
- Risk: cyclical companies (energy, materials) can show temporary revenue decline without business deterioration
- **Suitable for thesis integrity gate; less suitable for raw scoring**

### ROIC (Return on Invested Capital)
**Quality: GOOD**
- 0% null, 21% negative (levered firms, recently loss-making)
- Best profitability metric for capital efficiency — more informative than ROE which is distorted by leverage
- DELL (−363% ROE) vs DELL (18.5% ROIC) demonstrates ROE's distortion risk
- **ROIC preferred over ROE for any scoring application**

### FCF Yield
**Quality: GOOD**
- 0% null, 21% negative (capex-heavy firms, growth-stage companies)
- Measures real cash generation — less susceptible to accounting manipulation than EPS
- Risk: capex cycles create temporary negative FCF that doesn't indicate business weakness
- **Suitable as supporting evidence, not primary signal**

### Net Buy Score / Consensus Label
**Quality: GOOD**
- 0.9% null
- Note: This field is from FMP's analyst grade data, which duplicates in a different form what ESS/Zacks already capture. Using this in scoring would create circular self-reinforcement with the consensus layer.
- **NOT suitable for scoring — already captured in Layer 1**

### ROE (Return on Equity)
**Quality: MODERATE**
- Severely distorted by leverage and share buybacks (DELL: −363%)
- ROIC is strictly superior for capital efficiency measurement
- **Not recommended for scoring; use ROIC instead**

### Revenue Acceleration
**Quality: MODERATE**
- 62.6% negative values — most companies aren't accelerating at any given moment
- Useful as directional indicator but noisy as a scoring input
- **Suitable for display/thesis classification only**

### EPS Growth
**Quality: MODERATE**
- 39.3% negative values; susceptible to non-recurring items
- Less reliable than revenue growth due to accounting flexibility
- **Not recommended for primary scoring**

### EV/EBITDA
**Quality: GOOD for ANOMALY DETECTION**
- 15.4% negative (distressed companies — EV negative or EBITDA negative)
- Not directly usable as a conviction signal (high EV/EBITDA could mean expensive or fast-growing)
- Best use: anomaly flag (EV/EBITDA > 100x with declining revenue = DATA_ANOMALY)
- **Not suitable for conviction scoring; good for anomaly detection (already implemented)**

### P/E TTM
**Quality: UNAVAILABLE**
- 100% null on FMP Starter plan
- Cannot be used until subscription upgrade

---

## Ranked Candidates for Conviction Modifier

If a conviction modifier is implemented, the best candidate metrics in order of suitability:

| Rank | Metric | Why |
|------|--------|-----|
| 1 | **Beat Rate** | Cleanest data, proven execution signal, 0% null |
| 2 | **ROIC** | Capital efficiency, not distorted by leverage |
| 3 | **Revenue Growth** | Business momentum, but sector-adjusted needed |
| 4 | **FCF Yield** | Real cash generation, but capex cycle risk |

**Avoid in scoring:** ROE (leverage distortion), EPS Growth (accounting flexibility), Net Buy Score (duplicates ESS), P/E (unavailable), Revenue Acceleration (too noisy).

---

## Key Finding: Beat Rate is the Best Candidate

Beat Rate has a unique property no other FMP metric shares: it is **analyst-consensus-normalized**. A 100% beat rate means the company has consistently exceeded what the analyst consensus expected. This directly validates the consensus layer — it answers "has this consensus been right about this company historically?"

This makes beat rate uniquely complementary to CII Layer 1 (Analyst Consensus) rather than competing with it.
