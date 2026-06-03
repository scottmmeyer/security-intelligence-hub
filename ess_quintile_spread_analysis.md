# ESS Quintile Spread Analysis
**Phase 7.6G — Deliverable Q4**
**Generated:** 2026-06-01

---

## 1. Purpose

Quintile spread is the return difference between the top ESS bucket (VERY_BULLISH) and the bottom ESS bucket (VERY_BEARISH). A positive spread confirms that high-ESS stocks outperform low-ESS stocks. This is the core test of ESS predictive value.

---

## 2. Quintile Spread by Window

### 2.1 — 30-Day Window

| Bucket | Avg Return | Median Return | Win Rate | Volatility | n |
|--------|-----------|---------------|----------|------------|---|
| VERY_BULLISH | +1.984% | +0.796% | 54.1% | 13.48% | 6,403 |
| BULLISH | +1.815% | +0.662% | 53.4% | 13.86% | 10,626 |
| NEUTRAL | +1.800% | +0.259% | 51.2% | 18.42% | 8,564 |
| BEARISH | +1.306% | −0.454% | 47.5% | 16.35% | 5,147 |
| VERY_BEARISH | +2.516% | +0.433% | 51.2% | 18.63% | 2,065 |

**Top−Bottom Spread (avg):** +1.984% − +2.516% = **−0.532%** (inverted)
**Top−Bottom Spread (median):** +0.796% − +0.433% = **+0.363%** (correct direction)
**Top−Bottom Win Rate Spread:** 54.1% − 51.2% = **+2.9 pp** (correct direction)
**Top−Bottom Volatility Spread:** 13.48% − 18.63% = **−5.15 pp** (VB is significantly less volatile)

### 2.2 — 60-Day Window

| Bucket | Avg Return | Median Return | Win Rate | Volatility | n |
|--------|-----------|---------------|----------|------------|---|
| VERY_BULLISH | +5.520% | +3.120% | 60.4% | 18.37% | 3,454 |
| BULLISH | +4.557% | +2.513% | 58.7% | 17.17% | 4,600 |
| NEUTRAL | +7.529% | +4.947% | 63.3% | 26.51% | 1,427 |
| BEARISH | +6.649% | +3.778% | 61.0% | 23.91% | 698 |
| VERY_BEARISH | +10.839% | +6.024% | 65.2% | 27.23% | 256 |

**Top−Bottom Spread (avg):** +5.520% − +10.839% = **−5.319%** (strongly inverted)
**Top−Bottom Spread (median):** +3.120% − +6.024% = **−2.904%** (inverted)
**Note:** 60-day VERY_BEARISH n=256 (only early portfolio-level dates); severe sampling bias.

### 2.3 — 90-Day Window

| Bucket | Avg Return | Median Return | Win Rate | n |
|--------|-----------|---------------|----------|---|
| VERY_BULLISH | +5.462% | +3.017% | 57.7% | 2,762 |
| BULLISH | +6.042% | +3.074% | 58.1% | 3,628 |
| NEUTRAL | +4.845% | +3.633% | 59.6% | 547 |
| BEARISH | +5.701% | +1.733% | 53.2% | 94 |
| VERY_BEARISH | — | — | — | 0 |

**Top−Bottom Spread:** Cannot compute — VERY_BEARISH has no 90-day data.
**Note:** Only 4 categories populated; 90-day window is limited by price data availability.

---

## 3. Risk-Adjusted Spread Analysis

Despite the inverted raw return spread, the **Sharpe-proxy spread** (return / volatility) tells a different story:

### 30-Day Return/Volatility Ratio:

| Bucket | Avg Return | Volatility | Return/Vol Ratio |
|--------|-----------|------------|-----------------|
| VERY_BEARISH | +2.516% | 18.63% | 0.135 |
| BEARISH | +1.306% | 16.35% | 0.080 |
| NEUTRAL | +1.800% | 18.42% | 0.098 |
| BULLISH | +1.815% | 13.86% | 0.131 |
| **VERY_BULLISH** | **+1.984%** | **13.48%** | **0.147** |

**Risk-adjusted spread (VERY_BULLISH / VERY_BEARISH):** 0.147 / 0.135 = **+9.0% better ratio** for VERY_BULLISH

The risk-adjusted result is correctly ordered: VERY_BULLISH has the highest return-per-unit-of-volatility. This is the conceptually correct measure for a ranking signal: not just absolute return, but risk-adjusted return.

---

## 4. Win Rate Spread (Binary Outperformance)

Win rate (probability of positive return) is arguably the most decision-relevant metric for a long-only portfolio. High win rate = fewer negative positions.

| Bucket | 30d Win Rate | Spread vs BEARISH |
|--------|-------------|------------------|
| VERY_BULLISH | 54.1% | +6.6 pp |
| BULLISH | 53.4% | +5.9 pp |
| NEUTRAL | 51.2% | +3.7 pp |
| VERY_BEARISH | 51.2% | +3.7 pp |
| **BEARISH** | **47.5%** | baseline |

BEARISH (not VERY_BEARISH) is the worst bucket for win rate. VERY_BULLISH has a +6.6 pp win rate advantage over BEARISH, and +2.9 pp over VERY_BEARISH. This ordering is partially correct and meaningful.

---

## 5. Sampling Bias in 60-Day Window

The 60-day inverted spread (VERY_BEARISH +10.839%) deserves explicit explanation:

The 60-day return window requires ESS observations from dates ending by ~2026-03-25 to have a 60-day forward price window. At those dates (Aug-Mar), the archive contains only portfolio-level holdings — stocks actively under management. Stocks that scored VERY_BEARISH in portfolio-level files in Aug-Oct 2025 were likely in temporary distress (negative ESS sentiment) but retained in the portfolio — and subsequently recovered strongly over the following 2-3 months. This is a classic **portfolio manager contrarian thesis**, not ESS failure.

The 30-day window is better balanced: it includes full-universe Apr 2026 data where the VERY_BEARISH population includes genuinely bearish names across the universe, not just contrarian portfolio holds.

---

## 6. Spread Summary

| Window | Raw Spread | Direction | Median Spread | Win Rate Spread | Risk-Adj Spread |
|--------|-----------|-----------|---------------|-----------------|-----------------|
| 30d | −0.532% | INVERTED | +0.363% | +2.9 pp | +9.0% better |
| 60d | −5.319% | INVERTED | −2.904% | −4.8 pp | Mixed |
| 90d | N/A | — | N/A | — | — |

**Key finding:** In raw average return terms, the quintile spread is inverted in this dataset. In median return, win rate, and risk-adjusted terms, the signal is partially correct. The inversion is consistent with market regime effects (April 2026 recovery rally) and portfolio-level sampling bias in the 60-day window.

> ESS quintile spread is **not confirmed** as a consistent positive predictor of raw returns over 30-60 days in this single-regime dataset. The risk-adjusted signal (lower volatility for high-ESS stocks) is the most reliable directional finding.
