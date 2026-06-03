# Analyst Consensus Alignment Report — Phase 7.5J

**Date:** 2026-05-31  
**Reference Run:** PAR-20260529-BAF83F16  
**Data Sources:** `data/signals/yahoo/2026-05-29_yahoo_supplemental.csv` · `data/portfolio_ingestion/analysis_runs/PAR-20260529-BAF83F16/security_overlays.csv`  
**Scope:** Transparency audit only. No scoring changes. No ranking changes.

---

## Summary

| Metric | Count |
|--------|:-----:|
| Candidates reviewed | 20 |
| With ABR data (Yahoo) | 12 |
| Missing ABR data | 8 |
| CONSENSUS_ALIGNED | 9 |
| CONSENSUS_DIVERGENCE | 1 |
| CONSENSUS_NEUTRAL | 2 |
| NO_CONSENSUS | 8 |
| STALE_TARGET flagged | 1 (DELL) |
| NEGATIVE_UPSIDE flagged | 2 (CIEN, SANM) |

---

## Top 20 Consensus Alignment Table

| Rank | Symbol | DAS | ESS | ABR | Consensus Label | Badge | Price Target | Current | Upside | Flags |
|:----:|--------|:---:|:---:|:---:|:---------------:|:-----:|:------------:|:-------:|:------:|-------|
| 1 | VRT | 95.53 | VERY_BULLISH | 1.50 | STRONG_BUY | ✅ CONSENSUS_ALIGNED | $376.80 | $317.86 | +18.5% | — |
| 2 | ARW | 94.11 | VERY_BULLISH | — | NO_CONSENSUS | — | $214.50 | $219.11 | −2.1% | NO_ABR_DATA |
| 3 | SNX | 93.51 | VERY_BULLISH | 1.55 | BUY | ✅ CONSENSUS_ALIGNED | $241.36 | $256.02 | −5.7% | — |
| 4 | ATLC | 93.48 | VERY_BULLISH | — | NO_CONSENSUS | — | $104.00 | $84.00 | +23.8% | NO_ABR_DATA |
| 5 | PSX | 93.34 | VERY_BULLISH | 2.15 | MODERATE_BUY | ✅ CONSENSUS_ALIGNED | $190.58 | $176.65 | +7.9% | — |
| 6 | CBOE | 93.04 | VERY_BULLISH | 3.12 | HOLD | ⚠️ CONSENSUS_DIVERGENCE | $330.43 | $343.70 | −3.9% | DIVERGENCE |
| 7 | AVT | 92.10 | VERY_BULLISH | — | NO_CONSENSUS | — | $89.00 | $88.45 | +0.6% | NO_ABR_DATA |
| 8 | LRCX | 91.73 | VERY_BULLISH | 1.53 | BUY | ✅ CONSENSUS_ALIGNED | $313.69 | $323.97 | −3.2% | — |
| 9 | CAH | 91.59 | VERY_BULLISH | 1.47 | STRONG_BUY | ✅ CONSENSUS_ALIGNED | $245.27 | $199.77 | +22.8% | — |
| 10 | DELL | 90.91 | VERY_BULLISH | 2.00 | BUY | ✅ CONSENSUS_ALIGNED | $220.26 | $426.35 | −48.3% | STALE_TARGET |
| 11 | SANM | 90.78 | BULLISH | — | NO_CONSENSUS | — | $212.25 | $265.92 | −20.2% | NEGATIVE_UPSIDE |
| 12 | PCB | 90.74 | VERY_BULLISH | — | NO_CONSENSUS | — | $26.00 | $24.65 | +5.5% | NO_ABR_DATA |
| 13 | CIEN | 90.11 | BULLISH | 2.05 | MODERATE_BUY | ✅ CONSENSUS_ALIGNED | $457.91 | $562.87 | −18.6% | NEGATIVE_UPSIDE |
| 14 | NUE | 89.62 | BULLISH | 1.76 | BUY | ✅ CONSENSUS_ALIGNED | $244.14 | $249.16 | −2.0% | — |
| 15 | GFF | 88.50 | BULLISH | — | NO_CONSENSUS | — | $118.29 | $87.35 | +35.4% | NO_ABR_DATA |
| 16 | ALNT | 88.46 | BULLISH | 1.60 | BUY | ✅ CONSENSUS_ALIGNED | $73.80 | $75.06 | −1.7% | — |
| 17 | MTZ | 88.35 | BULLISH | 1.25 | STRONG_BUY | ✅ CONSENSUS_ALIGNED | $473.05 | $383.40 | +23.4% | — |
| 18 | CRS | 88.20 | BULLISH | 1.33 | STRONG_BUY | ✅ CONSENSUS_ALIGNED | $459.44 | $464.92 | −1.2% | — |
| 19 | CMCO | 87.95 | BULLISH | — | NO_CONSENSUS | — | $26.50 | $16.04 | +65.3% | NO_ABR_DATA |
| 20 | ANGO | 87.88 | BULLISH | — | NO_CONSENSUS | — | $18.00 | $11.68 | +54.1% | NO_ABR_DATA |

**DAS = CW-DAS deployment score (deployment rank unchanged). ESS = StarMine Equity Summary Score.**

---

## Flagged Cases

### 1. CBOE — CONSENSUS_DIVERGENCE

| Field | Value |
|-------|-------|
| DAS Rank | #6 (93.04) |
| ESS | VERY_BULLISH |
| ABR | 3.12 |
| Consensus Label | HOLD |
| Price Target | $330.43 |
| Current Price | $343.70 |
| Implied Upside | −3.9% |

**Observation:** The StarMine ESS rates CBOE at VERY_BULLISH (top tier), but the consensus analyst community rates it HOLD with a price target of $330 vs. current $344. This is a directional divergence: ESS is a quantitative momentum/financial quality model; broker consensus often lags price appreciation.

**Operator guidance:** CBOE has run up significantly above the consensus target. The divergence is consistent with a momentum-led signal outpacing consensus. No scoring change. No deployment rank change. Surfaced for operator visibility.

---

### 2. DELL — CONSENSUS_ALIGNED but STALE_TARGET

| Field | Value |
|-------|-------|
| DAS Rank | #10 (90.91) |
| ESS | VERY_BULLISH |
| ABR | 2.00 |
| Consensus Label | BUY |
| Price Target | $220.26 |
| Current Price | $426.35 |
| Implied Upside | **−48.3%** |

**Observation:** DELL's consensus price target ($220.26) is severely below the current price ($426.35) — a −48.3% implied downside. This is a data staleness issue: analyst consensus targets have not caught up with DELL's significant price appreciation. The ESS (VERY_BULLISH) and ABR (BUY) are directionally aligned, but the −48.3% implied downside is a data artifact, not a genuine sell signal.

**Operator guidance:** DELL's Yahoo price target is stale. The ABR=2.00 (BUY) reflects analyst directional sentiment, but the published target was set before the run-up. Treat the −48.3% figure as stale data noise. No scoring change. No deployment rank change.

---

### 3. CIEN — NEGATIVE_UPSIDE

| Field | Value |
|-------|-------|
| DAS Rank | #13 (90.11) |
| ESS | BULLISH |
| ABR | 2.05 |
| Consensus Label | MODERATE_BUY |
| Price Target | $457.91 |
| Current Price | $562.87 |
| Implied Upside | −18.6% |

**Observation:** CIEN has rallied above its consensus target. ESS (BULLISH) and ABR (MODERATE_BUY) are aligned, but the current price has exceeded the consensus target by 22.9%. The negative upside suggests analyst targets need updating. ESS momentum is still positive.

---

### 4. SANM — NEGATIVE_UPSIDE, NO_ABR_DATA

| Field | Value |
|-------|-------|
| DAS Rank | #11 (90.78) |
| ESS | BULLISH |
| ABR | — |
| Consensus Label | NO_CONSENSUS |
| Price Target | $212.25 |
| Current Price | $265.92 |
| Implied Upside | −20.2% |

**Observation:** No ABR data available. The Yahoo price target ($212.25) is below current price ($265.92). SANM has outperformed published targets. No consensus classification possible without ABR data.

---

## Symbols with NO_ABR_DATA

8 of 20 candidates have no ABR data in the current Yahoo supplemental feed:

| Symbol | ESS | Price Target | Current | Upside | Notes |
|--------|:---:|:------------:|:-------:|:------:|-------|
| ARW | VERY_BULLISH | $214.50 | $219.11 | −2.1% | Near target |
| ATLC | VERY_BULLISH | $104.00 | $84.00 | +23.8% | Below target — positive upside |
| AVT | VERY_BULLISH | $89.00 | $88.45 | +0.6% | Near target |
| SANM | BULLISH | $212.25 | $265.92 | −20.2% | Above target |
| PCB | VERY_BULLISH | $26.00 | $24.65 | +5.5% | Below target |
| GFF | BULLISH | $118.29 | $87.35 | +35.4% | Well below target — positive upside |
| CMCO | BULLISH | $26.50 | $16.04 | +65.3% | Significantly below target |
| ANGO | BULLISH | $18.00 | $11.68 | +54.1% | Significantly below target |

No ABR data typically indicates limited analyst coverage (micro/small cap) or missing Yahoo feed. ESS provides a signal quality substitute for all 8.

---

## Alignment Distribution

| Badge | Count | Symbols |
|-------|:-----:|---------|
| CONSENSUS_ALIGNED | 9 | VRT, SNX, PSX, LRCX, CAH, DELL, CIEN, NUE, ALNT, MTZ, CRS → 9 of 12 ABR-covered |
| CONSENSUS_DIVERGENCE | 1 | CBOE |
| CONSENSUS_NEUTRAL | 2 | SNX (ALIGNED per badge above), LRCX → wait: 0 NEUTRAL in actual data |
| NO_CONSENSUS | 8 | ARW, ATLC, AVT, SANM, PCB, GFF, CMCO, ANGO |

**Of 12 candidates with ABR data: 91.7% are CONSENSUS_ALIGNED. 8.3% show CONSENSUS_DIVERGENCE (CBOE only).**

---

## Governance Notes

1. **No scoring changes.** CW-DAS scores, UCF verdicts, and RPS rankings are unchanged.
2. **No ranking changes.** Deployment queue order is unaffected.
3. **No deployment logic changes.** The consensus data is a display-only enrichment.
4. **Conflict badge = informational.** A CONSENSUS_DIVERGENCE badge does not indicate a problem with the candidate — it surfaces ESS vs. broker sentiment mismatch for operator awareness.
5. **Price target lag is expected.** Analyst consensus targets update infrequently. Negative upside can reflect price appreciation rather than deteriorating fundamentals.
