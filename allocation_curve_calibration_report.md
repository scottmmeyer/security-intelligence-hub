# Allocation Curve Calibration Report
**Phase 7.5U — Final Verdict**
**Run:** PAR-20260601-9CFD7C63 | **Date:** June 1, 2026

---

## Answer to the Primary Question

> "Is the deployment framework primarily distorted by the conviction multiplier, or by the shape of the capital allocation curve itself?"

### **F. MULTIPLIER_IS_PRIMARY_ISSUE**

The CCL conviction multiplier (currently 3.0×) is the dominant source of allocation concentration. The curve shape is a secondary contributor. The evidence is unambiguous.

---

## Evidence

### 1. The Allocation Formula

```
weight_i = deployment_score_i × conviction_mult_i / sqrt(rank_i)

conviction_mult:  CCL = 3.0  |  HCA = 1.0
```

At rank 1 (VRT), the sqrt(1) = 1.0 term contributes nothing. The curve's decay function is irrelevant at rank 1. VRT's weight is entirely determined by its score (95.5) and its multiplier (3.0).

**VRT weight = 95.5 × 3.0 / 1.0 = 286.50**
**ARW weight = 94.12 × 1.0 / √2 = 66.55**
**Observed ratio = 286.50 / 66.55 = 4.30×**

If VRT had the HCA multiplier (1.0): ratio = 95.50 / 66.55 = **1.43×**

The CCL multiplier produces 3.00× of the 4.30× rank-1/rank-2 ratio. The curve shape produces the remaining 1.43×.

### 2. HHI Reduction by Factor

| Change | HHI Before | HHI After | Delta | % Reduction |
|--------|-----------|-----------|-------|------------|
| Baseline | 924.63 | — | — | — |
| Mult only: CCL 3.0→1.75, HCA 1.0→1.25 | 924.63 | 504.74 | **−419.89** | **45.4%** |
| Best curve only: rank^0.35 (keep mult) | 924.63 | 646.24 | **−278.39** | **30.1%** |
| Log₂ curve only (keep mult) | 924.63 | 960.05 | **+35.42** | **−3.8% (WORSE)** |
| Best combination: rank^0.35 + 1.75/1.25 | 924.63 | 405.99 | **−518.64** | **56.1%** |
| Mult only vs best combination | — | — | **+98.75** | Curve adds only +11% |

The multiplier change alone produces 45.4% HHI improvement. Adding the best curve change produces only 11% additional improvement on top of that. The marginal value of fixing the curve — after fixing the multiplier — is modest.

### 3. VRT Allocation Reduction by Factor

| Factor | VRT Before | VRT After | Delta |
|--------|-----------|-----------|-------|
| Multiplier only (CCL 3.0→1.75) | $8,810.94 | $4,791.11 | **−$4,020 (46%)** |
| Best curve only (rank^0.35) | $8,810.94 | $6,740.20 | **−$2,071 (24%)** |
| Log₂ curve only | $8,810.94 | $9,135.19 | **+$324 (WORSE)** |
| Both: rank^0.35 + 1.75/1.25 | $8,810.94 | $3,528.12 | **−$5,283 (60%)** |

The multiplier change is 1.9× more effective than the best curve change at reducing VRT's allocation.

### 4. Counterintuitive Curve Findings

Not all alternative curves reduce concentration. The log₂(rank+1) decay function, often considered a "smoother" alternative, is actually **steeper at the top** than the current sqrt:

| Rank | sqrt weight | log₂ weight |
|------|------------|------------|
| 2 | 0.707 | 0.631 (11% lower than sqrt) |
| 5 | 0.447 | 0.387 (13% lower than sqrt) |
| 31 | 0.180 | 0.200 (11% higher than sqrt) |

The log₂ curve concentrates more capital at rank 1 and slightly more in the tail — the opposite of what is needed. Any proposal to switch to log decay would worsen the VRT concentration problem.

Only rank^0.35 (flatter than sqrt) and linear decay produce genuine concentration reduction. Of these, rank^0.35 is more practical.

### 5. Signal-Underserved Names (PCB, AVT, ATLC, CAH, CIEN)

| Name | PSS Rank | Curve B gain | Curve D gain |
|------|---------|------------|------------|
| PCB | 1 | +$89 (+11%) | +$373 (+46%) |
| AVT | 2 | +$26 (+2%) | +$424 (+40%) |
| ATLC | 3 | −$84 (−6%) | +$262 (+18%) |
| CAH | 4 | +$60 (+6%) | +$429 (+46%) |
| CIEN | 8 | +$95 (+12%) | +$343 (+45%) |

Curve changes alone do not adequately address the signal-underserved problem. ATLC is actually hurt by the moderate curve (B). Model C (log₂) harms all five names. Only Model D (linear) provides material improvement, but at the cost of drastically cutting tail positions (ranks 22–31 lose 12–88% of current allocation).

**The signal-underserved problem is a ranking problem, not a curve problem.** The only sustainable fix is through rank order (as Phase 7.5T recommended via PSS blend) or through the multiplier structure.

---

## Verdict: F. MULTIPLIER_IS_PRIMARY_ISSUE

### Acceptance Criteria Review

| Criterion | Status |
|-----------|--------|
| 1. No code changes | ✅ Analysis only |
| 2. No scoring changes | ✅ Analysis only |
| 3. Uses June 1 signals and latest run | ✅ PAR-20260601-9CFD7C63 |
| 4. Uses current deployment rankings | ✅ Ranks 1–31 unchanged |
| 5. Quantifies current curve concentration | ✅ HHI=924.63, Top-1=26.59%, EffN=10.82 |
| 6. Tests multiple curve alternatives | ✅ 4 curves: sqrt, rank^0.35, log₂, linear |
| 7. Separates curve effects from multiplier effects | ✅ Direct factor attribution computed |
| 8. Quantifies VRT concentration source | ✅ Mult=59.5% of VRT alloc, curve=secondary |
| 9. Evaluates PCB, AVT, ATLC, CAH, CIEN | ✅ Per-name per-model analysis |
| 10. Returns evidence-based recommendation | ✅ F. MULTIPLIER_IS_PRIMARY_ISSUE |

---

## Guidance by Verdict Option

| Option | Status | Reason |
|--------|--------|--------|
| A. KEEP_CURRENT_CURVE | Not recommended | HHI=925 is in high-concentration band; VRT at 26.6% is a structural risk |
| B. REDUCE_CURVE_STEEPNESS | Not recommended as standalone | Rank^0.35 improves HHI 30% but curve change alone is insufficient |
| C. REDUCE_MULTIPLIER_ONLY | **Endorsed** (Phase 7.5Q) | Achieves 45% HHI improvement; single, clean change to one parameter |
| D. REDUCE_BOTH | Optional enhancement | Adds 11% marginal improvement over mult-only; combined HHI=406, EffN=24.6 |
| E. CURVE_IS_PRIMARY_ISSUE | Rejected | Data shows multiplier contributes 45% HHI reduction vs 30% for best curve |
| **F. MULTIPLIER_IS_PRIMARY_ISSUE** | **CONFIRMED** | Multiplier is 1.5× more impactful than the best curve change; log₂ curve worsens concentration |

---

## Recommended Action Sequence (Priority Order)

### Priority 1 (Phase 7.5Q): Reduce conviction multiplier
- CCL: 3.0 → 1.75
- HCA: 1.0 → 1.25
- Impact: HHI 924 → 505, VRT $8,811 → $4,791, EffN 10.8 → 19.8
- This is the single highest-leverage change available

### Priority 2 (optional): Switch curve from sqrt to rank^0.35
- Impact (standalone): HHI 924 → 646, VRT $8,811 → $6,740
- Impact (after multiplier change): HHI 505 → 406, EffN 19.8 → 24.6
- The curve improvement is real but modest compared to the multiplier change

### Priority 3 (structural): Incorporate PSS blend (Phase 7.5T recommendation)
- Impact: Improves corr(alloc, PSS) +16%, improves PCB/AVT/ATLC rank placement
- Works on the ranking dimension, not the multiplier or curve dimension

### Do NOT Do
- Switch to log₂ decay — this increases VRT concentration and harms all signal-underserved names
- Switch to linear decay (Model D) as a standalone change — radical redistribution from tail positions without addressing the CCL tier structure

---

## Supporting Data Summary

| Metric | S1 (current) | S2 (mult only) | S3 (curve+mult) | S6 (curve, no mult) |
|--------|-------------|---------------|----------------|-------------------|
| VRT alloc | $8,810.94 | $4,791.11 | $3,528.12 | $3,730.61 |
| VRT % | 26.59% | 14.46% | 10.65% | 11.26% |
| R1/R2 ratio | 4.30× | 2.01× | 1.81× | 1.61× |
| Top-3 % | 37.77% | 27.49% | 21.59% | 23.77% |
| HHI | 924.63 | 504.74 | 405.99 | 427.29 |
| Effective N | 10.82 | 19.81 | 24.63 | 23.40 |
