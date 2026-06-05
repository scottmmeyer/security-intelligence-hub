# Phase 8.0B.0 — Gap Analysis

**Date:** 2026-06-04  

---

## Summary

SIH currently has strong signal quality (ESS, Zacks, Danelfin, Yahoo ABR, Replay) but **zero fundamental context**. It can tell you whether analysts like a stock and whether the signal has historically produced returns — but it cannot tell you why, whether the business is improving or deteriorating, or whether a price decline represents a buying opportunity or a deteriorating thesis.

FMP fills every major fundamental gap.

---

## Gap Classification

### Completely Absent in SIH

| Metric | FMP Source | Value Classification | Scoring Use Case |
|--------|-----------|---------------------|-----------------|
| Forward P/E (NTM) | key-metrics-ttm | **HIGH** | Valuation gate; context for "is this cheap?" |
| EV/EBITDA (TTM/NTM) | key-metrics-ttm | **HIGH** | Primary valuation for non-GAAP businesses |
| FCF Yield | key-metrics-ttm | **HIGH** | Quality + valuation combined; supports CW-DAS sizing |
| Revenue Growth YoY | income-statement-growth | **HIGH** | Core growth signal for CW-DAS momentum component |
| Revenue Acceleration | income-statement-growth (sequential) | **HIGH** | Differentiates improving vs decelerating growth |
| EPS Growth YoY | income-statement-growth | **HIGH** | Earnings quality signal for conviction scoring |
| Earnings Surprise % | earnings per symbol | **VERY HIGH** | Explains price reactions; validates thesis |
| Earnings Surprise History (3–8 quarters) | earnings-surprises-bulk | **VERY HIGH** | Persistent beat pattern = conviction amplifier |
| Estimate Revision Direction | grades (upgrades/downgrades) | **HIGH** | Near-term signal for CW-DAS momentum |
| Gross Margin % | ratios-ttm | **HIGH** | Business quality signal; thematic clustering |
| FCF Margin % | ratios-ttm | **HIGH** | Differentiates high-quality vs capital-intensive |
| ROIC | key-metrics-ttm | **MEDIUM** | Long-term quality signal |
| ROE | key-metrics-ttm | **MEDIUM** | Return quality |
| Piotroski F-Score | financial-scores | **MEDIUM** | Systematic quality screen |
| Upcoming Earnings Date | earnings-calendar | **MEDIUM** | Risk management; timing context |
| Analyst Count (coverage depth) | price-target-summary | **MEDIUM** | Signal quality weight (thin coverage = higher uncertainty) |
| EV/Sales | key-metrics-ttm | **MEDIUM** | Growth stock valuation |
| Price/Book | key-metrics-ttm | **MEDIUM** | Value stock valuation |
| Altman Z-Score | financial-scores | **LOW** | Distress screening |

---

### Partially Duplicated (Incremental Value Only)

| Metric | SIH Has | FMP Adds |
|--------|---------|---------|
| Price Target | Yahoo ABR/target | FMP has high/low/median/count; richer distribution |
| Analyst Consensus | Yahoo ABR normalized | FMP grades-consensus has buy/hold/sell counts |
| EPS Growth 5yr | Yahoo field (unfilled for most) | FMP provides actual historical growth rates |

---

### Not Needed (Duplicate or Out of Scope)

| Metric | Reason |
|--------|--------|
| FMP DCF valuation | Model-dependent; not deterministic enough for scoring |
| Technical indicators | SIH uses replay, not TA |
| Historical price data | Already in replay layer |
| FMP composite ratings | Redundant with ESS + Danelfin |
| Crypto/Forex/Commodities | Out of scope for equity portfolio |
| COT reports | Futures positioning; not equity portfolio relevant |

---

## Value Map by SIH Consumer

| SIH System | Current Gap | FMP Would Provide |
|-----------|------------|------------------|
| **CW-DAS signal component (55%)** | ESS-only; no fundamental validation | Revenue growth + earnings surprise → earnings momentum component |
| **CW-DAS momentum component (10%)** | ESS direction + signal direction only | Estimate revisions + earnings surprise % → true momentum signal |
| **CW-DAS sizing component (8%)** | Headroom below WARN threshold only | FCF yield + valuation could inform target weights |
| **STI trim classification** | Thematic overlap only; no fundamental divergence | Deteriorating growth + declining margins → thesis break signal |
| **CRA SIGNAL_DETERIORATION** | ESS only; no cause analysis | Earnings miss + downward revisions → confirms thesis break |
| **CRA TAX_AWARE_EXIT** | Loss identification only | Quality context prevents harvesting "good stocks temporarily down" |
| **Conviction scoring (CCL/HCA)** | Replay + composite only | Persistent beat history + accelerating growth = true conviction amplifier |
| **"Stock on Sale" (new)** | Not possible today | Valuation compression + strong growth = new high-value signal type |

---

## Overall Gap Assessment

**SIH is missing all of the fundamental layer.** It has strong signal intelligence (analysts say buy) but cannot validate whether the business justifies the signal. This creates two failure modes:

1. **False positives:** A stock with BULLISH ESS and replay support but deteriorating fundamentals gets deployed into.
2. **False negatives:** A stock after an earnings dip (temporarily cheap) gets mis-classified as BEARISH when it's actually a buying opportunity.

FMP directly addresses both failure modes.
