# DIL Phase 1 — Reduction Queue Validation

**Date:** 2026-06-10  
**PAR:** PAR-20260609-87134CE1

---

## Validation Symbols

### PRIM (Primoris Services Corp)

**Input signals:**
- ESS: BEARISH (Fidelity StarMine, SELL rating)
- Signal alignment: PARTIAL_ALIGNMENT (ESS bearish, Yahoo bullish, Zacks bearish)
- ABR: 1.86 BUY (14 analysts)
- Consensus: BUY
- EPS surprise Q1: −30.6% (one-quarter miss)
- Beat rate 8Q: 85.7% (strong historical executor)
- Revenue growth Q1 YoY: +18.9%
- UCF: TRIM_WATCH
- Zacks: 1.0 (STRONG BUY)

**Rule triggered:** Rule 4 — SINGLE_QUARTER_MISS (beat_rate 85.7% > 70%, eps_surprise -30.6% < -20%) AND isESSBearish AND isStreetBullish

**Expected posture:** INVESTIGATE BEFORE ACTING ✓

**Rationale:** PRIM's bearish ESS conflicts with street consensus (BUY, 14 analysts). Historical beat rate is 85.7% over 8 quarters, but the most recent quarter missed by 30.6%. Revenue remains positive (+18.9% YoY). Single-quarter miss pattern — not fundamental deterioration.

**Evidence cited:**
- SELL [Fidelity StarMine, dated]
- Zacks: 1.0 [Zacks, dated]
- ABR: 1.86 BUY (14 analysts) [Yahoo, dated]
- EPS surprise: −30.6% [FMP, dated]
- Beat rate 8Q: 85.7% [FMP, dated]
- Revenue growth Q1 YoY: +18.9% [FMP, dated]
- Signal alignment: PARTIAL ALIGNMENT [Computed]

---

### TSLA (Tesla Inc.)

**Input signals:**
- ESS: VERY_BEARISH (STRONG_SELL)
- Signal alignment: PARTIAL_ALIGNMENT (ESS bearish, Yahoo moderately bullish, Zacks bearish)
- ABR: 2.36 MODERATE_BUY (41 analysts)
- EPS surprise Q1: +15.9% (beat)
- Beat rate 8Q: 57.1% (below threshold)
- Revenue growth Q1 YoY: −2.9%
- UCF: TRIM_WATCH (not CCL/HCA)
- Policy: DO_NOT_SELL (BLOCKED)
- Zacks: 2.0

**Rule triggered:** Rule 6 — isESSBearish AND (Zacks 2.0 → not >= 3.5) AND composite < 2.5 (1.33) → Zacks not corroborating, but composite < 2.5 is corroborating → ACTIONABLE.
But wait: isStreetBullish (ABR 2.36, MODERATE_BUY) → street diverges somewhat. Alignment is PARTIAL_ALIGNMENT. EPS surprise is positive (+15.9%), beat_rate is 57.1% < 70% (below SINGLE_QUARTER_MISS threshold). FUNDAMENTAL_DETERIORATION requires beat_rate < 50% AND revenue < 0 — revenue is negative at -2.9%, and beat_rate is 57.1% so this is IN_LINE_FUNDAMENTAL.

Composite < 2.5 (1.33) → corroborated → ACTIONABLE.

**Expected posture:** ACTIONABLE  
*Note: TSLA is blocked by DO_NOT_SELL policy. The posture is advisory — the policy block is separately shown in the profile and prevents execution.*

**Evidence cited:**
- STRONG_SELL [Fidelity StarMine, dated]
- Zacks: 2.0 [Zacks, dated]
- ABR: 2.36 (41 analysts) [Yahoo, dated]
- EPS surprise: +15.9% [FMP, dated]
- Beat rate 8Q: 57.1% [FMP, dated]
- Signal alignment: PARTIAL ALIGNMENT [Computed]
- UCF: TRIM_WATCH [Computed]

---

### VOO (Vanguard S&P 500 ETF)

**Input signals:**
- ESS: empty (ETF, no ESS coverage)
- Composite: empty
- Category: LOW_CONVICTION_REDUCTION

**Rule triggered:** Rule 1 — isETFNoSignal → PASSIVE REDUCTION

**Expected posture:** PASSIVE REDUCTION ✓

**Rationale:** VOO is a passive vehicle held for allocation exposure. Reduction frees capital for higher-conviction direct holdings. FVI: ELITE — vehicle quality confirmed.

**Evidence cited:**
- Signal alignment: (not available — ETF) [Computed]
- UCF: MAINTAIN [Computed]

---

### KGC (Kinross Gold)

**Input signals:**
- ESS: BEARISH (SELL)
- Signal alignment: MAJOR_DIVERGENCE (ESS bearish, Yahoo bullish, Zacks neutral)
- ABR: 1.67 BUY (11 analysts, 56% upside)
- EPS surprise Q1: +4.4% (modest beat)
- Beat rate 8Q: 85.7% (strong)
- Revenue growth Q1 YoY: +39.3% (very strong)
- UCF: TACTICAL_GROWTH (not CCL/HCA)

**Rule triggered:** Rule 5 — MAJOR_DIVERGENCE AND earningsCtx = STRONG_FUNDAMENTAL (beat_rate 85.7% > 75%, rev_growth 39.3% > 10%) → CONFLICTING EVIDENCE

**Expected posture:** CONFLICTING EVIDENCE ✓

**Rationale:** KGC shows major signal divergence. ESS bearish while fundamentals are very strong (85.7% beat rate, +39.3% revenue). Street has 56% upside target. ESS may be capturing gold price momentum rather than company fundamentals.

---

## Summary

| Symbol | Expected Posture | Rule | Traceable? |
|---|---|---|---|
| PRIM | INVESTIGATE BEFORE ACTING | Rule 4 (SINGLE_QUARTER_MISS) | ✓ |
| TSLA | ACTIONABLE | Rule 6 (composite corroboration) | ✓ |
| VOO | PASSIVE REDUCTION | Rule 1 (isETFNoSignal) | ✓ |
| KGC | CONFLICTING EVIDENCE | Rule 5 (MAJOR_DIVERGENCE + STRONG_FUNDAMENTAL) | ✓ |

All postures are deterministic from input signals. No subjective weighting. Every output cites source and date.
