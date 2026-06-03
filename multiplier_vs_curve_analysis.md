# Multiplier vs Curve Analysis
**Phase 7.5U — Allocation Curve Calibration Audit**
**Run:** PAR-20260601-9CFD7C63 | **Date:** June 1, 2026

---

## Overview

This analysis isolates and quantifies the relative contributions of (1) the CCL conviction multiplier and (2) the allocation curve shape to portfolio concentration. Six scenarios are evaluated against the baseline.

---

## Six Scenarios Evaluated

| Scenario | Curve | CCL Mult | HCA Mult | Description |
|---------|-------|---------|---------|-------------|
| **S1** (baseline) | sqrt / rank^0.5 | 3.0 | 1.0 | Current production |
| **S2** | sqrt / rank^0.5 | 1.75 | 1.25 | Phase 7.5Q reduced mult only |
| **S3** | rank^0.35 | 1.75 | 1.25 | Moderate curve + reduced mult |
| **S4** | log₂(rank+1) | 1.75 | 1.25 | Balanced curve + reduced mult |
| **S5** | linear | 1.75 | 1.25 | Linear curve + reduced mult |
| **S6** | log₂(rank+1) | 1.0 | 1.0 | Balanced curve + no mult |

---

## Concentration Results by Scenario

| Scenario | VRT Alloc | VRT % | ARW Alloc | R1/R2 Ratio | Top-3 % | HHI | Eff N |
|---------|----------|-------|----------|------------|--------|-----|-------|
| S1 — curr curve, curr mult | $8,810.94 | 26.59% | $2,046.75 | 4.30× | 37.77% | 924.63 | 10.82 |
| S2 — curr curve, 1.75/1.25 | $4,791.11 | 14.46% | $2,384.91 | 2.01× | 27.49% | 504.74 | 19.81 |
| S3 — ModB, 1.75/1.25 | $3,528.12 | 10.65% | $1,948.65 | 1.81× | 21.59% | 405.99 | 24.63 |
| S4 — BalC, 1.75/1.25 | $4,997.82 | 15.08% | $2,219.79 | 2.25× | 27.05% | 502.65 | 19.89 |
| S5 — LinD, 1.75/1.25 | $2,966.31 | 8.95% | $2,020.82 | 1.47× | 20.90% | 449.60 | 22.24 |
| S6 — BalC, no mult | $3,730.61 | 11.26% | $2,319.74 | 1.61× | 23.77% | 427.29 | 23.40 |

---

## Factor Attribution — HHI

### Isolating Each Factor

| Change tested | From | To | HHI Delta | % of baseline HHI |
|--------------|------|----|-----------|------------------|
| Mult only (S1→S2) | sqrt, 3.0/1.0 | sqrt, 1.75/1.25 | 924.63 → 504.74 | **−419.89 (45.4%)** |
| Curve only (S1→C + curr mult) | sqrt, 3.0/1.0 | log₂, 3.0/1.0 | 924.63 → 960.05 | **+35.42 (+3.8%)** |
| Curve only (S1→B + curr mult) | sqrt, 3.0/1.0 | rank^0.35, 3.0/1.0 | 924.63 → 646.24 | **−278.39 (30.1%)** |
| Both (S1→S3) | sqrt, 3.0/1.0 | rank^0.35, 1.75/1.25 | 924.63 → 405.99 | **−518.64 (56.1%)** |
| Both (S1→S4) | sqrt, 3.0/1.0 | log₂, 1.75/1.25 | 924.63 → 502.65 | **−421.98 (45.6%)** |

### Key Findings

1. **Multiplier change alone (S1→S2): HHI drops 419 points (45%).**
   Reducing CCL from 3.0 to 1.75 and HCA from 1.0 to 1.25 dramatically reduces concentration. This is the single largest lever available within the current framework.

2. **Curve change to log₂ (S1→C curve): HHI INCREASES 35 points (+4%).**
   The log₂ curve is MORE concentrated than sqrt, not less. It would make things worse at rank 1 while slightly flattening the tail. This is a counterintuitive but critical finding.

3. **Curve change to rank^0.35 (S1→B curve): HHI drops 278 points (30%).**
   This is meaningful but smaller than the multiplier effect. The rank^0.35 curve achieves improvement by flattening the decay across ranks 2–31, which increases the denominator of VRT's allocation fraction.

4. **Both changes (S1→S3): HHI drops 519 points (56%).**
   Combining reduced multipliers with a flatter curve achieves the most improvement. But the incremental benefit from the curve change above the mult-only change is $518.64 − $419.89 = **$98.75 pts** — only about 10% additional improvement beyond what the multiplier change achieves alone.

---

## Factor Attribution — VRT Allocation

| Change tested | VRT Before | VRT After | VRT Delta |
|--------------|-----------|-----------|-----------|
| Baseline (S1) | $8,810.94 | — | — |
| Mult only (S1→S2) | $8,810.94 | $4,791.11 | **−$4,019.83** |
| Curve only → log₂ (S1→C) | $8,810.94 | $9,135.19 | **+$324.25** (WORSE) |
| Curve only → rank^0.35 (S1→B) | $8,810.94 | $6,740.20 | **−$2,070.74** |
| Curve only → linear (S1→D) | $8,810.94 | $5,766.52 | **−$3,044.42** |
| Both → S3 (ModB + 1.75/1.25) | $8,810.94 | $3,528.12 | **−$5,282.82** |
| Both → S5 (LinD + 1.75/1.25) | $8,810.94 | $2,966.31 | **−$5,844.63** |

### Attribution Calculation

Using S3 (rank^0.35 + 1.75/1.25) as the combined case:
- Total VRT reduction achievable (S3): $8,811 → $3,528 = −$5,283
- Mult-only contribution: −$4,020 (76.1% of total reduction)
- Curve-only contribution (rank^0.35): −$2,071 (39.2% of total reduction)
- Interaction term: +$808 (these effects partially cancel — the curve's denominator mechanism is reduced when the mult is also smaller)

**The multiplier explains 76% of VRT's excess concentration (above equal-weight). The curve explains 39%. These sum to more than 100% because of negative interaction — they partially overlap.**

---

## Comparative Impact on ARW (Rank 2)

As VRT shrinks, how much do ranks 2+ benefit?

| Scenario | ARW Alloc | vs Baseline |
|---------|----------|------------|
| S1 (baseline) | $2,046.75 | — |
| S2 (mult only) | $2,384.91 | +$338.16 (+16.5%) |
| S3 (ModB + reduced mult) | $1,948.65 | −$98.10 (−4.8%) |
| S4 (BalC + reduced mult) | $2,219.79 | +$173.04 (+8.5%) |

When mult is reduced but curve is steepened (S3), ARW actually loses capital vs baseline because rank^0.35 benefits lower ranks more than rank 2. The multiplier reduction benefits rank 2 (ARW) the most of any single change.

---

## Which Factor is Primary?

### Evidence Summary

| Evidence | Multiplier | Curve |
|----------|-----------|-------|
| HHI reduction from change alone | 419.89 pts (45%) | 278.39 pts (30%) |
| VRT alloc reduction from change alone | $4,020 (46%) | $2,071 (24%) |
| Effect direction is correct | ✅ Always reduces concentration | ⚠️ Log₂ curve INCREASES it |
| Improvement to signal-underserved names | ✅ Yes (via rank changes in PSS blend) | ✅ Only Model D (radically) |
| Curve model that helps most | — | Model B (rank^0.35) |
| Interacts with other factor | Multiplicatively | Additively (weaker) |

### Multiplier is the Primary Factor

The multiplier produces:
- 45% HHI reduction vs 30% for the best alternative curve (rank^0.35)
- 46% VRT reduction vs 24% for the best alternative curve
- The multiplier's effect operates in the numerator of VRT's weight, directly changing VRT's allocation — not just diluting it through denominator expansion
- The log₂ curve (a common "alternative") actually worsens concentration — the multiplier has no such paradox

### Curve Has a Secondary but Real Effect

The rank^0.35 curve does produce a 30% HHI improvement independently. This is not negligible. However:
- It operates only through the denominator mechanism (raising other positions' weights)
- It does not address the CCL tier boundary — VRT's weight stays at 286.50 regardless of curve
- Its benefit is partly undermined when combined with multiplier reduction (negative interaction)
- The correct curve shape is non-obvious: log₂ is worse, sqrt is moderate, rank^0.35 is better, linear is most radical

### Phase 7.5Q Reduced Multiplier Remains the Stronger Lever

The Phase 7.5Q recommendation (CCL=1.75, HCA=1.25) would:
- Reduce HHI from 924 to 505 (45% drop)
- Reduce VRT from $8,811 to $4,791 (46% drop)
- Increase effective position count from 10.82 to 19.81
- Preserve all existing ranks and framework logic

This single change has nearly the same impact as changing both multipliers AND the curve shape simultaneously (S4: HHI=502, eff_n=19.89 — nearly identical to S2: HHI=505, eff_n=19.81).
