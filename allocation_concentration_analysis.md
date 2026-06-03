# Allocation Concentration Analysis
**Phase 7.5U — Allocation Curve Calibration Audit**
**Run:** PAR-20260601-9CFD7C63 | **Date:** June 1, 2026

---

## Current Allocation Formula

The deployment planner uses a rank-weighted proportional allocation:

$$w_i = \text{score}_i \times \text{mult}_i \div \sqrt{\text{rank}_i}$$

Where conviction multipliers are:
- CCL (TIER_1): `mult = 3.0`
- HCA (TIER_2/TIER_3): `mult = 1.0`

Each position receives capital proportional to its weight:

$$\text{alloc}_i = \text{total\_cash} \times \frac{w_i}{\sum_j w_j}$$

---

## Concentration Metrics — Current Curve (Model A)

| Metric | Value |
|--------|-------|
| Total deployed | $33,141.36 |
| Funded positions | 31 |
| Top-1 (VRT) share | **26.59%** |
| Top-3 share (VRT/ARW/SNX) | **37.77%** |
| Top-5 share | **45.98%** |
| Top-10 share | **61.25%** |
| HHI | **924.63** |
| Effective position count | **10.82** |

**Interpretation:** Despite 31 funded positions, the portfolio behaves as if it holds approximately 11 equal-weight positions. This is a highly concentrated allocation — more than a quarter of deployed capital goes to a single position.

---

## Key Ratios

| Ratio | Value | Interpretation |
|-------|-------|---------------|
| Rank 1 / Rank 2 | **4.30x** | VRT receives 4.3× more capital than ARW |
| Rank 2 / Rank 3 | **1.23x** | Compression normal within HCA tier |
| Rank 1 / Rank 5 | **6.86x** | VRT receives 6.9× more than PSX (same HCA tier as ARW) |
| Rank 1 / Median | **12.96x** | VRT receives 13× the median allocation |
| Rank 2 / Rank 5 | **1.59x** | Moderate differentiation within top-5 HCA positions |

The 4.30x ratio between rank 1 and rank 2 is the primary structural feature. Within the HCA tier (ranks 2–31), the progression is much more gradual (rank 2/3 = 1.23x, rank 2/5 = 1.59x).

---

## Concentration Source Decomposition

### Two Contributors to the Rank-1/Rank-2 Gap

**Contributor 1: The CCL conviction multiplier**
- VRT weight = 95.5 × 3.0 / sqrt(1) = **286.50**
- ARW weight = 94.12 × 1.0 / sqrt(2) = **66.55**
- Observed ratio: 286.50 / 66.55 = **4.30x**

**Counterfactual: What if VRT had HCA mult (1.0)?**
- VRT weight = 95.5 × 1.0 / sqrt(1) = **95.50**
- ARW weight = 66.55 (unchanged)
- Ratio: 95.50 / 66.55 = **1.43x**

**The CCL multiplier (3.0) contributes 3.00x of the 4.30x rank-1/rank-2 ratio.**
The curve's sqrt(rank) shape contributes only the remaining 1.43x.

### Attribution Summary

| Source | Contribution to Rank-1/2 Ratio |
|--------|-------------------------------|
| CCL conviction multiplier (3.0x) | 3.00× of the 4.30× gap |
| Sqrt(rank) curve shape | 1.43× residual (score gap only) |
| Total observed | **4.30×** |

The multiplier contributes (4.30 − 1.43) / (4.30 − 1.0) = **87% of the excess** rank-1/rank-2 concentration above a flat curve.

---

## How Much Concentration is from Ranking vs Curve?

This question requires separating the rank-order effect from the curve-shape effect.

### Rank-order effect
Even with a perfectly flat allocation (equal weight to all 31 positions), rank 1 would receive 1/31 = 3.2% of capital. The current 26.6% top-1 share represents an **8.1x multiplier above equal-weight**. This is pure structural concentration driven by the formula.

### Curve-shape effect (within HCA tier)
Within ranks 2–31 (all HCA), the sqrt(rank) curve creates a range from 6.18% (rank 2) to 1.44% (rank 31) — a 4.3x spread over 30 positions. This is moderate but gradual differentiation. The curve shape's contribution to intra-HCA concentration is meaningful but not extreme.

### Multiplier effect (CCL vs HCA)
The 3.0x CCL multiplier is applied only to rank 1. This is a structural step function — VRT gets 3x the weight of any same-score HCA position at the same rank. With a 1.5x score advantage (VRT=95.5 vs ARW=94.12), the net effect is a **4.30x allocation gap**.

### Verdict
**The multiplier creates the cliff.** The curve creates the slope. The 4.30x rank-1/rank-2 gap is primarily a multiplier artifact. Without the 3.0x CCL multiplier, the same curve would produce only a 1.43x ratio.

---

## Comparison Across Curve Models

| Model | Curve Formula | VRT Alloc | VRT % | HHI | Effective N |
|-------|--------------|-----------|-------|-----|-------------|
| A (current) | score × mult / sqrt(rank) | $8,810.94 | 26.59% | 924.63 | 10.82 |
| B (moderate) | score × mult / rank^0.35 | $6,740.20 | 20.34% | 646.24 | 15.47 |
| C (balanced) | score × mult / log₂(rank+1) | $9,135.19 | 27.56% | 960.05 | 10.42 |
| D (linear) | score × mult × (1 − (rank−1)/31) | $5,766.52 | 17.40% | 606.85 | 16.48 |

**Counterintuitive finding:** Model C (log₂ decay) produces MORE concentration than the current curve, not less. The log₂ function falls faster than sqrt between ranks 1 and 2 (log₂ weight ratio = 0.631 vs sqrt weight ratio = 0.707), making rank 1 even more dominant. This means log decay is not a "gentler" alternative — it is steeper at the top.

The only curve models that reduce concentration are Model B (rank^0.35) and Model D (linear). But see Q6 for multiplier attribution — curve changes alone do not address the primary driver.

---

## Institutional Context

**HHI reference points:**

| HHI Range | Interpretation |
|-----------|---------------|
| < 100 | Highly diversified |
| 100–250 | Moderate diversification |
| 250–500 | Moderate concentration |
| 500–1000 | High concentration |
| > 1000 | Extreme concentration (monopoly-like) |

Current HHI of **924.63** falls in the **high concentration** band, approaching extreme. For a 31-position deployment plan, the benchmark equal-weight HHI would be 31 × (100/31)² = **322.6**. The current HHI is **2.87x** the equal-weight baseline.
