# FVI Scoring Methodology

Repository: security-intelligence-hub  
Date: 2026-06-09

## Purpose

Define the advisory-only Fund Vehicle Intelligence (FVI) scoring model for SIH. FVI evaluates the quality of a fund vehicle relative to its peer group, independent of sleeve allocation decisions.

---

## Scoring Principle

FVI answers: "Given that I need exposure to this category, is this the best available vehicle?"

It does NOT answer: "Should I have exposure to this category?" (that is the allocation/recommendation system's domain).

---

## FVI Score Construction

### Composite Score: 0–100

| Dimension | Weight | Description |
|---|---|---|
| Risk-Adjusted Performance | 25% | Peer-relative Sharpe, Sortino, or information ratio over 3Y and 5Y |
| Raw Performance Persistence | 20% | Consistency of outperformance across multiple periods (not just cumulative) |
| Cost Efficiency | 20% | Expense ratio percentile within peer group (lower = better) |
| Downside Protection | 15% | Max drawdown percentile and downside capture ratio vs peer median |
| Manager / Process Quality | 10% | Manager tenure, style consistency, AUM stability (active funds only; index funds receive neutral 50/100 on this dimension) |
| Structural Characteristics | 10% | Tracking error (for index), liquidity, bid-ask spread, AUM trend |

**Notes:**
- For index ETFs: Manager Quality is replaced with Tracking Efficiency.
- For digital asset ETFs: Performance Persistence and Downside Protection are most relevant; Manager Quality is replaced with Issuer Stability.
- Weights are configurable in `config/fvi_scoring_config.yaml` (proposed new file).

---

## FVI Tier Assignment

| FVI Score | Tier | Meaning |
|---|---|---|
| 80–100 | ELITE | Top-quintile peer vehicle; strong retain signal regardless of allocation pressure |
| 60–79 | HIGH | Above-median; retain unless significant allocation reduction needed |
| 40–59 | MEDIUM | Near-median; standard allocation-driven decisions apply |
| 20–39 | LOW | Below-median; replacement consideration appropriate on sleeve reduction |
| 0–19 | WEAK | Bottom-quintile; vehicle-quality case for replacement even before allocation-driven reduction |

---

## Active vs Passive Fund Treatment

### Active Funds (DODFX, FMCSX, FCPGX, FIGFX)

Full scoring across all dimensions. Manager quality and process stability are material factors. Peer group is same-category active funds.

### Index ETFs (VOO, VB, VO, VEA, VWO)

Simplified scoring:
- Cost Efficiency has higher effective weight (cheaper index = almost always better)
- Manager Quality replaced with Tracking Efficiency (tracking error vs benchmark)
- Performance Persistence shows near-identical trend for same index; instead: compare index quality (e.g., FTSE vs MSCI vs S&P for same category)

Benchmark: for a Vanguard S&P 500 ETF, the relevant quality question is cost and tracking, not alpha.

### Digital Asset ETFs (FBTC, FETH, FSOL, XRP)

Simplified scoring:
- Cost Efficiency and Issuer Stability are primary (e.g., Fidelity vs smaller issuer)
- Performance is essentially identical for same underlying exposure
- Structural: ETF vs ETP vs trust structure matters

---

## Illustrative FVI Scores (Advisory Estimates — Not Based on Live Provider Data)

These scores are advisory estimates for the current portfolio based on publicly available knowledge as of June 2026. They require validation against actual peer-relative data once a data source is integrated.

| Symbol | Peer Category | Estimated FVI Score | Estimated Tier | Confidence |
|---|---|---|---|---|
| VOO | US Large Blend ETF | ~90 | ELITE | High — lowest cost S&P 500 ETF |
| FXAIX | US Large Blend MF | ~88 | ELITE | High — zero expense ratio Fidelity index fund |
| VB | US Small Blend ETF | ~85 | ELITE | High — near-lowest cost small cap ETF |
| VO | US Mid Blend ETF | ~85 | ELITE | High — near-lowest cost mid cap ETF |
| BND | US Core Bond ETF | ~82 | ELITE | High — low cost broad bond market |
| BNDX | World Bond ETF | ~80 | ELITE | High — low cost hedged international bonds |
| VEA | Foreign Large Blend ETF | ~82 | ELITE | High — low cost developed market ETF |
| VWO | Diversified EM ETF | ~80 | ELITE | High — leading emerging market index ETF |
| DODFX | Foreign Large Value MF | ~75 | HIGH | Medium — strong active manager, reasonable fees |
| FBTC | Bitcoin Spot ETF | ~72 | HIGH | Medium — leading issuer (Fidelity), competitive fee |
| FETH | Ethereum Spot ETF | ~68 | HIGH | Medium — established issuer |
| FMCSX | US Mid Active MF | ~55 | MEDIUM | Low — active mid cap has mixed record |
| FCPGX | US Small Growth MF | ~52 | MEDIUM | Low — active small cap has mixed record |
| XRP | XRP ETF | ~45 | MEDIUM | Low — newer instrument, limited track record |
| FSOL | Solana ETF | ~38 | LOW | Low — very new, concentrated risk |

**Important disclaimer:** These are advisory estimates based on general category knowledge. Actual FVI scores require integration with a peer-relative data provider (Morningstar, Lipper, or equivalent) to compute category percentiles.

---

## Data Requirements for Full Implementation

| Dimension | Data Needed | Potential Source |
|---|---|---|
| Risk-Adjusted Performance | 3Y/5Y Sharpe, Sortino vs peer median | Morningstar, Lipper |
| Performance Persistence | Rolling 1Y returns over 5 years | Morningstar |
| Cost Efficiency | Expense ratio; peer expense percentile | Morningstar, fund prospectus |
| Downside Protection | Max drawdown, downside capture | Morningstar, Bloomberg |
| Manager Quality | Manager tenure, AUM stability | Morningstar, fund disclosure |
| Structural | Tracking error, bid-ask spread | Bloomberg, Morningstar |

For Phase 1 FVI implementation, a simplified three-factor model is sufficient:
1. Expense ratio percentile (available from fund prospectus data)
2. Category-relative 3Y risk-adjusted return percentile
3. Downside capture percentile

This can be implemented with manual/semi-automated data for the 15 fund vehicles in the current portfolio — full universe coverage is not required for Phase 1.
