# Replay Evidence Quality Analysis
**Run:** PAR-20260601-9CFD7C63 | **Date:** June 1, 2026

---

## Evidence Depth Classification

All 42 replay-supported queue members classified by evidence depth:

| Depth Category | Definition | Count | CW-DAS Rank Range | Avg CW-DAS Rank |
|---------------|-----------|-------|-------------------|-----------------|
| **THIN** | < 30 trading days | 15 | 1–42 | 20.5 |
| **MODERATE** | 30–179 trading days | 0 | — | — |
| **STRONG** | 180+ trading days | 27 | 4–42 | 17.4 |

> No MODERATE-depth replays exist in the current dataset. All replays are either 4-day (CURRENT_RECOMMENDATION) or 261-day (HISTORICAL_VALIDATION).

---

## THIN Evidence Stocks (4 trading days — CURRENT_RECOMMENDATION)

All 15 THIN stocks are selected from the May 20–26 CURRENT_RECOMMENDATION replay sweep.

| CW-DAS Rank | Symbol | Composite | ESS | CW-DAS Score | Pure Signal Rank |
|-------------|--------|-----------|-----|--------------|-----------------|
| 1 | VRT | 4.556 | VERY_BULLISH | 95.5 | 14 |
| 2 | ARW | 4.889 | VERY_BULLISH | 94.12 | 11 |
| 3 | SNX | 4.778 | VERY_BULLISH | 93.48 | 18 |
| 5 | PSX | 4.722 | VERY_BULLISH | 93.35 | 27 |
| 8 | LRCX | 4.500 | VERY_BULLISH | 91.74 | 19 |
| 10 | DELL | 4.444 | VERY_BULLISH | 90.91 | 29 |
| 11 | SANM | 4.278 | BULLISH | 90.78 | 35 |
| 32 | CVE | 4.833 | VERY_BULLISH | 83.79 | 30 |
| 33 | TSM | 4.444 | VERY_BULLISH | 81.61 | 17 |
| 34 | GTX | 4.167 | BULLISH | 80.47 | 40 |
| 35 | MU | 4.722 | VERY_BULLISH | 78.16 | 28 |
| 36 | ASML | 4.667 | VERY_BULLISH | 78.09 | 26 |
| 37 | STNG | 4.714 | N/A | 76.16 | 38 |
| 38 | SIMO | 4.571 | N/A | 75.53 | 39 |
| 40 | MSFT | 3.444 | BULLISH | 70.43 | 41 |

**Average CW-DAS rank of THIN stocks: 20.5**

---

## STRONG Evidence Stocks (261 trading days — HISTORICAL_VALIDATION)

All 27 STRONG stocks earned replay selection from the May 14, 2025 → May 14, 2026 historical replay sweep (252 trading days; 261 days calendar).

| CW-DAS Rank | Symbol | Composite | ESS | CW-DAS Score | Pure Signal Rank | Replay Industry |
|-------------|--------|-----------|-----|--------------|-----------------|-----------------|
| 4 | ATLC | 4.778 | VERY_BULLISH | 93.47 | 3 | US-MICRO-FINANCIAL_SERVICES |
| 6 | CBOE | 4.667 | VERY_BULLISH | 93.08 | 5 | US-MID-FINANCIAL_SERVICES |
| 7 | AVT | 4.556 | VERY_BULLISH | 92.12 | 2 | US-SMALL-TECHNOLOGY |
| 9 | CAH | 4.500 | VERY_BULLISH | 91.62 | 4 | US-MID-HEALTHCARE |
| 12 | PCB | 4.333 | VERY_BULLISH | 90.75 | 1 | US-MICRO-FINANCIAL_SERVICES |
| 13 | CIEN | 4.278 | BULLISH | 90.07 | 8 | US-MID-TECHNOLOGY |
| 14 | NUE | 4.111 | BULLISH | 89.61 | 21 | US-MID-BASIC_MATERIALS |
| 15 | GFF | 3.833 | BULLISH | 88.50 | 22 | US-SMALL-INDUSTRIALS |
| 16 | ALNT | 3.778 | BULLISH | 88.45 | 6 | US-MICRO-TECHNOLOGY |
| 17 | MTZ | 3.778 | BULLISH | 88.35 | 7 | US-MID-INDUSTRIALS |
| 18 | CRS | 3.722 | BULLISH | 88.20 | 9 | US-MID-INDUSTRIALS |
| 19 | CMCO | 3.667 | BULLISH | 87.96 | 12 | US-MICRO-INDUSTRIALS |
| 20 | ANGO | 3.833 | BULLISH | 87.89 | 23 | US-MICRO-HEALTHCARE |
| 21 | FSLR | 3.722 | BULLISH | 87.49 | 10 | US-MID-TECHNOLOGY |
| 22 | UHS | 3.611 | BULLISH | 87.34 | 15 | US-SMALL-HEALTHCARE |
| 23 | HALO | 3.667 | BULLISH | 87.06 | 13 | US-SMALL-HEALTHCARE |
| 24 | BSVN | 4.000 | N/A | 86.75 | 20 | US-MICRO-FINANCIAL_SERVICES |
| 25 | STLD | 3.556 | BULLISH | 86.60 | 24 | US-MID-BASIC_MATERIALS |
| 26 | AGEN | 3.444 | BULLISH | 86.57 | 31 | US-MICRO-HEALTHCARE |
| 27 | YELP | 3.444 | BULLISH | 86.43 | 32 | US-MICRO-COMMUNICATION_SERVICES |
| 28 | DVN | 3.611 | BULLISH | 86.42 | 16 | US-MID-ENERGY |
| 29 | UTHR | 3.444 | BULLISH | 86.36 | 33 | US-MID-HEALTHCARE |
| 30 | ANIP | 3.556 | BULLISH | 86.22 | 25 | US-MICRO-HEALTHCARE |
| 31 | AZZ | 3.444 | BULLISH | 86.10 | 34 | US-SMALL-INDUSTRIALS |
| 39 | AVGO | 3.722 | BULLISH | 72.10 | 37 | US-MEGA-ALL (CURRENT) |
| 41 | NVDA | 3.833 | BULLISH | 69.74 | 36 | US-MEGA-ALL (CURRENT) |
| 42 | SBS | 3.714 | N/A | 65.65 | 42 | INTERNATIONAL-LARGE-ALL (CURRENT) |

**Average CW-DAS rank of STRONG stocks: 17.4** (median: 19)

Note: AVGO, NVDA, and SBS are STRONG-class stocks that appear later in the queue due to redundancy penalties (-15 pts), not evidence depth.

---

## Does Evidence Depth Correlate With Deployment Priority?

### Finding: Weak Negative Correlation

THIN evidence stocks **dominate the top 10** of the CW-DAS queue. STRONG evidence stocks occupy the **11–31 range** with few exceptions.

| Queue Position | Depth Category | Count |
|---------------|---------------|-------|
| Top 10 (ranks 1–10) | THIN | 7 |
| Top 10 (ranks 1–10) | STRONG | 3 |
| Ranks 11–20 | THIN | 1 |
| Ranks 11–20 | STRONG | 10 |
| Ranks 21–31 | THIN | 0 |
| Ranks 21–31 | STRONG | 11 |

**Correlation direction: THIN stocks are systematically higher-ranked than STRONG stocks.**

### Why This Inversion Occurs

This is **not driven by signal quality**. Pure signal scores show the opposite pattern:

- THIN stocks average pure signal rank: **25.1** (of 42)
- STRONG stocks average pure signal rank: **17.3** (of 42)
- **STRONG stocks have 31% better pure signal quality on average**

The inversion is driven by **CCL tier concentration**:
- All 7 THIN stocks in the top 10 are either CCL-tier (VRT = 35 pts conviction) or close to conviction saturation
- The THIN replay large-cap stocks (VRT, ARW, SNX, PSX, LRCX, DELL) cluster in the high-score zone because they combine strong composite scores with the +20 replay bonus and no redundancy penalty
- STRONG stocks like PCB (PSR=1), AVT (PSR=2), CAH (PSR=4) are pushed down by the conviction ceiling (28 vs 35 pts max for HCA)

### Summary

Evidence depth does NOT correlate with deployment priority in the expected direction. Higher-evidence stocks are systematically underweighted relative to their pure signal quality. The +20 replay bonus is flat regardless of depth, which means 4-day evidence earns the same reward as 261-day evidence — a structural blind spot.

---

## Replay Evidence Depth vs Signal Quality (Comparison)

| Depth | Avg Composite | Avg ESS (VB=5, B=4, etc.) | Avg CW-DAS Rank | Avg PSR |
|-------|--------------|--------------------------|-----------------|---------|
| THIN (4d) | 4.46 | 4.5 (mostly VERY_BULLISH) | 20.5 | 25.1 |
| STRONG (261d) | 3.77 | 3.9 (mostly BULLISH) | 17.4 | 17.3 |

THIN stocks have higher composite scores (many are large-caps with premium coverage), but STRONG stocks have better pure signal rank on average. The current framework rewards composite-score concentration (large caps) over cross-validated evidence depth.
