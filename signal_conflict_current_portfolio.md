# Signal Conflict — Current Portfolio Analysis

**Date:** 2026-06-15  
**PAR:** PAR-20260615-FF5E50AF

---

## Deployment Queue — Conflict Matrix

| Rank | Symbol | ESS | Zacks | Dan | FMP Summary | Sell% | Conflict Level | Advisory |
|------|--------|-----|-------|-----|-------------|-------|---------------|---------|
| #1 | VRT | VERY_BULLISH | 4.0 | 7 | 18B/1H/0S (n=19) | 0.0% | **L0 FULL_ALIGNMENT** | — |
| #2 | ATLC | VERY_BULLISH | 4.0 | 6 | 5B/1H/0S (n=6) | 0.0% | **L0 FULL_ALIGNMENT** | — |
| #3 | DELL | VERY_BULLISH | 5.0 | 5 | 26B/17H/2S (n=45) | 4.4% | L2 MODERATE | `CONFLICTING_SIGNAL` |
| #4 | LRCX | VERY_BULLISH | 4.0 | 6 | 39B/10H/1S (n=50) | 2.0% | L2 MODERATE | `CONFLICTING_SIGNAL` |
| #5 | PCB | VERY_BULLISH | 3.0 | 7 | 1B/4H/0S (n=5) | 0.0% | L1 MILD | `HOLD_CONSENSUS` |
| #6 | CAH | VERY_BULLISH | 4.0 | 5 | 18B/15H/0S (n=33) | 0.0% | L1 MILD | `HIGH_HOLD_RATIO` |
| #7 | SANM | BULLISH | 4.0 | 8 | 5B/10H/2S (n=17) | 11.8% | L2 MODERATE | `CONFLICTING_SIGNAL` |
| #8 | MTZ | BULLISH | 3.0 | 9 | 32B/4H/0S (n=36) | 0.0% | **L0 FULL_ALIGNMENT** | — |
| #9 | CRS | BULLISH | 4.0 | 8 | 14B/6H/1S (n=21) | 4.8% | L2 MODERATE | `CONFLICTING_SIGNAL` |
| #10 | NUE | BULLISH | 5.0 | 7 | 18B/11H/3S (n=32) | 9.4% | L2 MODERATE | `CONFLICTING_SIGNAL` |

**Deployment queue L2 count:** 5 of 10 (DELL, LRCX, SANM, CRS, NUE)  
**Deployment queue fully aligned:** 3 of 10 (VRT, ATLC, MTZ)  
**No Level 3 or Level 4 in deployment queue**

### Notable Observations

**SANM (#7):** Buy minority (29.4%), hold majority (58.8%), 2 sell votes. This is the weakest buy conviction in the queue by buy-ratio despite a BUY consensus label. Zacks=4 and Danelfin=8 offset this. Advisory warranted.

**NUE (#10):** 3 sell votes — highest sell count in the queue. Operator research identified Trading Central (score 98) = Buy vs Refinitiv/Verus (score 86) = Sell. If this is confirmed, NUE should be classified as **L4 (Severe Conflict — named sources disagree)**. FMP aggregate alone shows L2.

**PCB (#5):** HOLD consensus (1 buy, 4 holds). Small coverage universe (n=5). The single buy rating keeps it at L1 rather than L2. No explicit sells. Lower-confidence signal universe.

---

## Current Holdings — Conflict Analysis

### Holdings WITH Sell Votes (FMP data)

| Symbol | FMP | Sell% | Conflict | Notes |
|--------|-----|-------|---------|-------|
| **TSLA** | 32B/34H/15S (n=81) | **18.5%** | **L3 SIGNIFICANT** | Highest sell count in portfolio. Nearly equal buys and holds. 15 sell votes. |
| **AVT** | 6B+1SB/9H/4S (n=20) | **20.0%** | **L3 SIGNIFICANT** | Highest sell proportion in portfolio. Only 35% buy rate. ESS unknown (attribution winner). |
| **GTX** | 3B/3H/2S (n=8) | **25.0%** | **L3 SIGNIFICANT** | HOLD consensus + 2 sells from 8 analysts. |
| **CBOE** | 12B+2SB/13H/4S (n=31) | 12.9% | L2 MODERATE | 4 sell votes but also 2 strong buys. |
| **FSLR** | 44B/22H/7S (n=73) | 9.6% | L2 MODERATE | Large coverage, 7 sell votes. |
| **NUE** | 18B/11H/3S (n=32) | 9.4% | L2 MODERATE | Also in deployment queue. |
| **SANM** | 5B/10H/2S (n=17) | 11.8% | L2 MODERATE | Also in deployment queue. |
| ARW | 6B/9H/2S (n=17) | 11.8% | L2 MODERATE | Historical WINNER×3 despite sells. |
| PSX | 20B/13H/2S (n=35) | 5.7% | L2 MODERATE | 2 sell votes; historical WINNER. |
| DELL | 26B/17H/2S (n=45) | 4.4% | L2 MODERATE | 2 sell votes; attribution mixed. |
| MU | 57B/11H/2S (n=70) | 2.9% | L2 MODERATE | Strong buy base; 2 sell minority. |
| NVDA | 58B+2SB/16H/3S (n=79) | 3.8% | L2 MODERATE | Very strong buy base; 3 sell votes. |
| STLD | 15B/11H/1S (n=27) | 3.7% | L2 MODERATE | — |
| UHS | 18B/23H/2S (n=43) | 4.7% | L2 MODERATE | 2 sells; hold-heavy (53.5%). |
| CVE | 11B/15H/1S (n=27) | 3.7% | L2 MODERATE | 1 sell; hold-heavy. |
| SNX | 18B+1SB/4H/1S (n=24) | 4.2% | L2 MODERATE | Strong buy base. |
| HALO | 17B/9H/1S (n=27) | 3.7% | L2 MODERATE | — |
| FIS | 21B+1SB/14H/1S (n=37) | 2.7% | L2 MODERATE | ESS=BEARISH — full conflict. |
| SBS | 2B/4H/1S (n=7) | 14.3% | L2/L3 | HOLD consensus + sells. |
| CRS | 14B/6H/1S (n=21) | 4.8% | L2 MODERATE | In deployment queue. |
| LRCX | 39B/10H/1S (n=50) | 2.0% | L2 MODERATE | In deployment queue. |

### Holdings Fully Aligned (no sell votes, BUY consensus)

VRT, ATLC, MTZ, CAH, MSFT (66B/16H/0S), NVDA is near-aligned, PCB (HOLD — L1)

---

## Reduction Queue — Conflict Analysis

Based on PAR-20260615-FF5E50AF recommendations for REDUCE_OVERWEIGHT:

Symbols currently flagged for reduction are not explicitly captured in this PAR (no active REDUCE recommendations in the current run). The prior recommendation records show FIS was a REDUCED target — FIS has **ESS=BEARISH**, Zacks=3.0 (NEUTRAL), and 1 sell vote. The bearish ESS is the primary concern, which the system already acted on via reduction recommendations.

---

## Priority Conflict Flags for Current Portfolio

### Immediate Attention (L3)

| Symbol | Issue | Recommended Flag |
|--------|-------|-----------------|
| **TSLA** | 15 explicit sell votes (18.5% sell rate) | `SIGNIFICANT_CONFLICT — 18.5% bearish` |
| **AVT** | 4 explicit sell votes (20% sell rate), only 35% buy rate | `SIGNIFICANT_CONFLICT — 20% bearish` |
| **GTX** | HOLD consensus + 2/8 sell (25% sell rate) | `SIGNIFICANT_CONFLICT — HOLD + 25% sell` |

### Advisory (L2, high sell proportion)

| Symbol | Sell% | Recommended Flag |
|--------|-------|-----------------|
| CBOE | 12.9% | `CONFLICTING_SIGNAL` |
| SBS | 14.3% | `CONFLICTING_SIGNAL` |
| SANM | 11.8% | `CONFLICTING_SIGNAL` |
| ARW | 11.8% | `CONFLICTING_SIGNAL` |
| FSLR | 9.6% | `CONFLICTING_SIGNAL` |
| NUE | 9.4% | `CONFLICTING_SIGNAL` (see NUE case study) |

### Special Case (L4 candidate by operator annotation)

| Symbol | Issue | Status |
|--------|-------|--------|
| **NUE** | Trading Central (98) = Buy vs Refinitiv/Verus (86) = Sell per operator research | Requires operator annotation to confirm L4 |
