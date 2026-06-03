# Signal-Underserved Names — Curve Analysis
**Phase 7.5U — Allocation Curve Calibration Audit**
**Run:** PAR-20260601-9CFD7C63 | **Date:** June 1, 2026

---

## Focus Names (from Phase 7.5T)

These five names were identified as the most signal-underserved in the current deployment queue — their capital allocation does not reflect their Pure Signal Score quality.

| Symbol | CW-DAS Rank | CW-DAS Score | Pure Signal Rank | PSS Quality |
|--------|------------|-------------|-----------------|-------------|
| PCB | 12 | 90.75 | 1 | Highest in universe |
| AVT | 7 | 92.12 | 2 | Second highest |
| ATLC | 4 | 93.47 | 3 | Third highest |
| CAH | 9 | 91.62 | 4 | Fourth highest |
| CIEN | 13 | 90.07 | 8 | Top-10 signal quality |

---

## Allocation Under Each Curve (Current Multipliers: CCL=3.0, HCA=1.0)

### PCB — CW-DAS Rank 12, PSS Rank 1

| Model | Alloc $ | vs Baseline | vs Equal-Weight | Signal Served? |
|-------|---------|------------|----------------|---------------|
| A (current) | $805.66 | — | 0.77× | ⚠️ Below equal-weight |
| B (rank^0.35) | $894.71 | +$89.05 (+11.1%) | 0.85× | ⚠️ Still below |
| C (log₂) | $781.96 | −$23.70 (−2.9%) | 0.75× | ❌ WORSE than baseline |
| D (linear) | $1,178.43 | +$372.77 (+46.3%) | 1.12× | ✅ Above equal-weight |

PCB (world-class signal quality) receives only $805.66 under the current curve — 0.77× the equal-weight allocation of $1,069. Model D meaningfully improves this. Models B provides modest improvement. Model C makes it worse.

### AVT — CW-DAS Rank 7, PSS Rank 2

| Model | Alloc $ | vs Baseline | vs Equal-Weight | Signal Served? |
|-------|---------|------------|----------------|---------------|
| A (current) | $1,070.79 | — | 1.00× | ✅ Exactly equal-weight |
| B (rank^0.35) | $1,096.78 | +$25.99 (+2.4%) | 1.03× | ✅ Marginally above |
| C (log₂) | $979.10 | −$91.69 (−8.6%) | 0.92× | ❌ WORSE |
| D (linear) | $1,495.28 | +$424.49 (+39.7%) | 1.40× | ✅ Significantly above |

AVT happens to sit near equal-weight in the current curve because its rank (7) sits in the mid-tier sweet spot. Model D meaningfully serves its signal quality.

### ATLC — CW-DAS Rank 4, PSS Rank 3

| Model | Alloc $ | vs Baseline | vs Equal-Weight | Signal Served? |
|-------|---------|------------|----------------|---------------|
| A (current) | $1,437.27 | — | 1.34× | ✅ Above equal-weight |
| B (rank^0.35) | $1,353.63 | −$83.65 (−5.8%) | 1.27× | ✅ Still above |
| C (log₂) | $1,283.56 | −$153.71 (−10.7%) | 1.20× | ✅ Still above, but lower |
| D (linear) | $1,699.25 | +$261.98 (+18.2%) | 1.59× | ✅ Well above |

ATLC is already above equal-weight because its CW-DAS rank (4) is high. The question from Phase 7.5T is whether it should be rank 1 with CCL-level capital — that is a multiplier/scoring question, not a curve question. Under any curve model, ATLC's HCA tier keeps it in the $1,200–$1,700 range.

### CAH — CW-DAS Rank 9, PSS Rank 4

| Model | Alloc $ | vs Baseline | vs Equal-Weight | Signal Served? |
|-------|---------|------------|----------------|---------------|
| A (current) | $939.22 | — | 0.88× | ⚠️ Slightly below |
| B (rank^0.35) | $998.97 | +$59.75 (+6.4%) | 0.94× | ⚠️ Near equal-weight |
| C (log₂) | $879.41 | −$59.81 (−6.4%) | 0.82× | ❌ WORSE |
| D (linear) | $1,368.19 | +$428.97 (+45.7%) | 1.28× | ✅ Above equal-weight |

CAH at rank 9 receives slightly below equal-weight allocation. Model D meaningfully corrects this. Model C makes it materially worse.

### CIEN — CW-DAS Rank 13, PSS Rank 8

| Model | Alloc $ | vs Baseline | vs Equal-Weight | Signal Served? |
|-------|---------|------------|----------------|---------------|
| A (current) | $768.26 | — | 0.72× | ⚠️ Below equal-weight |
| B (rank^0.35) | $863.47 | +$95.22 (+12.4%) | 0.81× | ⚠️ Still below |
| C (log₂) | $754.31 | −$13.95 (−1.8%) | 0.71× | ❌ Marginally worse |
| D (linear) | $1,111.12 | +$342.86 (+44.7%) | 1.04× | ✅ Near equal-weight |

---

## Summary Matrix

| Symbol | PSS Rank | CW Rank | A_Alloc | B_Alloc | C_Alloc | D_Alloc | Best curve for signal alignment |
|--------|---------|---------|---------|---------|---------|---------|--------------------------------|
| PCB | 1 | 12 | $805.66 | $894.71 | $781.96 | $1,178.43 | D |
| AVT | 2 | 7 | $1,070.79 | $1,096.78 | $979.10 | $1,495.28 | D |
| ATLC | 3 | 4 | $1,437.27 | $1,353.63 | $1,283.56 | $1,699.25 | D |
| CAH | 4 | 9 | $939.22 | $998.97 | $879.41 | $1,368.19 | D |
| CIEN | 8 | 13 | $768.26 | $863.47 | $754.31 | $1,111.12 | D |

**Model D (linear) improves all five signal-underserved names.** Model B provides modest improvements to PCB, CAH, and CIEN but slightly reduces ATLC. Model C (log₂) makes all five names WORSE than the current curve.

---

## Why Does Model C Harm Signal-Underserved Names?

Model C (log₂ decay) falls faster from rank 1 to rank 2 than the sqrt curve (weight at rank 2 = 0.631 vs 0.707 under sqrt). This means the log curve concentrates more capital at rank 1 (VRT) and less at ranks 2–13 — exactly where the signal-underserved names sit. The log₂ curve is fundamentally incompatible with helping mid-tier HCA positions.

---

## How Much Can Curve Changes Help Without Multiplier Changes?

| Improvement metric | Model B | Model D |
|-------------------|---------|---------|
| Avg improvement to focus 5 | +$12 (+1.3%) | +$366 (+38.8%) |
| Names improved | 4 of 5 (ATLC −$84) | 5 of 5 |
| VRT reduction | −$2,071 | −$3,044 |
| Overall HHI improvement | −278 pts (30%) | −318 pts (34%) |

**Important limitation:** Even Model D (linear), which provides the most benefit to signal-underserved names, achieves this by radically redistributing capital in the lower half of the queue. Model D would reduce the bottom 10 positions (ranks 22–31) to receive $57–$567 (vs $476–$573 currently) as a zero-sum trade-off. Some tail positions lose 85–100% of their allocation under Model D.

**The signal alignment problem for PCB, AVT, and CIEN is fundamentally a ranking problem** — these stocks are at ranks 7–13, not ranks 2–4. No curve change can bridge the gap between "rank 13 with great signal quality" and "appropriate capital for signal quality" without also changing the rank order or the multiplier regime.

---

## Conclusion

Curve changes provide marginal improvement for signal-underserved names at best. The meaningful alignment improvements identified in Phase 7.5T (PCB: rank 12→7 under 20% PSS blend; ATLC: rank 4→2) were driven by ranking changes, not curve changes. A curve change alone cannot adequately serve PCB ($806), CIEN ($768), or CAH ($939) — these names need either better ranks or a flatter multiplier structure to receive capital proportional to their signal quality.
