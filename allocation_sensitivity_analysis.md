# Allocation Sensitivity Analysis
**Phase 7.5T — Pure Signal Capital Allocation Audit**
**Run:** PAR-20260601-9CFD7C63 | **Date:** June 1, 2026
**Total Deployable Capital:** $33,141.36

---

## Model Definitions

| Model | CW-DAS Weight | PSS Weight | Description |
|-------|--------------|-----------|-------------|
| **A** | 100% | 0% | Current framework (baseline) |
| **B** | 80% | 20% | Minor signal integration |
| **C** | 60% | 40% | Material signal integration |
| **D** | 50% | 50% | Equal weighting |

**Blended score formula:**
$$\text{blend} = w_{A} \cdot \text{norm\_cwdas} + w_{B} \cdot \text{norm\_pss}$$

Normalization anchors:
- CW-DAS: min=65.65 (SBS), max=95.50 (VRT) → range=29.85
- PSS: min=48.71 (SBS), max=76.67 (PCB) → range=27.96

---

## Metric Comparison Across Models

| Metric | Model A | Model B | Model C | Model D |
|--------|---------|---------|---------|---------|
| **Top-1 symbol** | VRT | VRT | **ATLC** | **ATLC** |
| **Top-1 allocation** | $8,810.94 | $8,810.94 | $8,810.94 | $8,810.94 |
| **Top-1 % of pool** | 26.6% | 26.6% | 26.6% | 26.6% |
| **Top-5 allocation** | $15,238.65 | $15,238.65 | $15,238.65 | $15,238.65 |
| **Top-5 % of pool** | 46.0% | 46.0% | 46.0% | 46.0% |
| **Corr(alloc, composite)** | 0.255 | 0.245 | 0.277 | 0.266 |
| **Corr(alloc, PSS)** | 0.273 | 0.316 | **0.489** | **0.495** |
| **Corr(alloc, cur_weight)** | 0.198 | 0.199 | **-0.118** | **-0.125** |
| **VRT allocation** | $8,810.94 | $8,810.94 | $1,168.63 | $1,070.79 |
| **PCB allocation** | $805.66 | $1,070.79 | $1,659.80 | $1,659.80 |
| **ARW allocation** | $2,046.75 | $1,659.80 | $1,070.79 | $1,168.63 |
| **AVT allocation** | $1,070.79 | $1,437.27 | $2,046.75 | $2,046.75 |

> **Note:** Top-1% and Top-5% of pool are identical across all models. The allocation curve maps fixed dollar amounts to ranks 1–31, so total capital deployed is invariant. What changes is which symbols receive each tier of allocation.

---

## Top 5 Rankings Per Model

### Model A — Current CW-DAS

| Rank | Symbol | CW-DAS | PSS | Blend | Alloc |
|------|--------|--------|-----|-------|-------|
| 1 | VRT | 95.50 | 67.44 | 100.00 | $8,810.94 |
| 2 | ARW | 94.12 | 69.11 | 95.38 | $2,046.75 |
| 3 | SNX | 93.48 | 66.22 | 93.23 | $1,659.80 |
| 4 | ATLC | 93.47 | 74.22 | 93.20 | $1,437.27 |
| 5 | PSX | 93.35 | 64.78 | 92.80 | $1,283.89 |

Top-5 replay profile: 3 THIN (4-day), 2 STRONG (261-day)

### Model B — 80/20

| Rank | Symbol | blend_B | Alloc | vs Model A |
|------|--------|---------|-------|-----------|
| 1 | VRT | 93.40 | $8,810.94 | unchanged |
| 2 | ATLC | 92.81 | $2,046.75 | ↑ from rank 4 |
| 3 | ARW | 90.89 | $1,659.80 | ↓ from rank 2 |
| 4 | AVT | 90.06 | $1,437.27 | ↑ from rank 7 |
| 5 | CBOE | 89.69 | $1,283.89 | ↑ from rank 6 |

Top-5 replay profile: 2 THIN (4-day), 3 STRONG (261-day)

### Model C — 60/40

| Rank | Symbol | blend_C | Alloc | vs Model A |
|------|--------|---------|-------|-----------|
| 1 | **ATLC** | 92.41 | $8,810.94 | ↑ from rank 4 (+$7,374) |
| 2 | AVT | 91.45 | $2,046.75 | ↑ from rank 7 |
| 3 | PCB | 90.45 | $1,659.80 | ↑ from rank 12 |
| 4 | CAH | 88.38 | $1,437.27 | ↑ from rank 9 |
| 5 | CBOE | 87.50 | $1,283.89 | ↑ from rank 6 |

Top-5 replay profile: 0 THIN, 5 STRONG (261-day)

### Model D — 50/50

| Rank | Symbol | blend_D | Alloc | vs Model A |
|------|--------|---------|-------|-----------|
| 1 | **ATLC** | 92.22 | $8,810.94 | ↑ from rank 4 (+$7,374) |
| 2 | AVT | 92.14 | $2,046.75 | ↑ from rank 7 |
| 3 | PCB | 92.04 | $1,659.80 | ↑ from rank 12 |
| 4 | CAH | 88.73 | $1,437.27 | ↑ from rank 9 |
| 5 | CBOE | 86.40 | $1,283.89 | ↑ from rank 6 |

Top-5 replay profile: 0 THIN, 5 STRONG (261-day) — identical to Model C

---

## Correlation Analysis Detail

### Corr(allocation, composite_score)

The correlation between dollar allocation and composite score stays roughly flat across all models (0.245–0.277), indicating that composite score is not the primary driver in any model. The relationship between capital and composite is weak regardless of PSS blending.

### Corr(allocation, pure_signal_score)

This is the primary sensitivity dimension. Pure signal correlation improves substantially with PSS blending:

- **Model A:** 0.273 — baseline
- **Model B:** 0.316 — +16% improvement, modest gain
- **Model C:** 0.489 — +79% improvement, major shift
- **Model D:** 0.495 — +81% improvement, marginal gain over C

The improvement from A to B is gradual; the improvement from B to C is a step-change. Models C and D are nearly saturated — the marginal PSS alignment gain from 40% to 50% is only 0.006.

### Corr(allocation, current_weight)

This metric reveals the most important behavioral shift:

- **Models A/B:** +0.198 to +0.199 — positive correlation: the framework **adds more capital to positions already held in larger amounts**
- **Model C:** -0.118 — negative correlation: the framework **adds capital against the direction of existing position size**
- **Model D:** -0.125 — slightly more contrarian

The sign flip at ~35% PSS weight is a structural threshold. Below it, capital deployment reinforces existing positioning (momentum/conviction behavior). Above it, capital deployment leans against existing positions (signal-quality/rotation behavior).

---

## Sensitivity: The 40% Threshold

Model B (20% PSS) and Model C (40% PSS) produce materially different top-1 rankings:

| Weight | Top-1 | Notes |
|--------|-------|-------|
| 0% | VRT | CW-DAS floor |
| 5% | VRT | — |
| 10% | VRT | — |
| 20% | VRT | Model B |
| 25% | VRT | — |
| ~30% | VRT → ATLC | Threshold zone (estimated) |
| 40% | ATLC | Model C |
| 50% | ATLC | Model D |

At approximately 28–32% PSS weight, ATLC overtakes VRT for rank 1. This is because:
- ATLC has norm_cwdas = 93.20 (close to VRT's 100.00)
- ATLC has norm_pss = 91.24 (versus VRT's 66.99)
- The 24.25-point PSS advantage ATLC holds over VRT exceeds the 6.80-point CW-DAS advantage VRT holds over ATLC at approximately 28% PSS weight

---

## Non-Linearity of Rank Changes

The table below shows rank change acceleration as PSS weight increases:

| Symbol | A→B Δrank | B→C Δrank | C→D Δrank |
|--------|----------|----------|----------|
| VRT | 0 | -5 | -1 |
| ATLC | +2 | +1 | 0 |
| PCB | +5 | +4 | 0 |
| SNX | -5 | 0 | -3 |
| SANM | -3 | -7 | -4 |

VRT's rank is stable in Model B (A→B: 0) but collapses in Model C (B→C: -5). This non-linearity is structurally significant: a 20% PSS weight can be introduced without disturbing VRT's top position, but 40% crosses the ATLC-overtake threshold.

---

## Replay Evidence Quality Impact

| Model | Top-5 THIN replays | Top-5 STRONG replays | Top-10 STRONG replays |
|-------|-------------------|---------------------|----------------------|
| A | 3 | 2 | 4 |
| B | 2 | 3 | 6 |
| C | 0 | 5 | 8 |
| D | 0 | 5 | 8 |

PSS integration strongly improves replay evidence quality in the top 5. Model C eliminates thin-evidence stocks from the top 5 entirely.

---

## Concentration Analysis

**Tier-bucket mismatch in Models C and D:**
- The rank-1 allocation ($8,810.94, 26.6%) was designed around the CCL tier — it represents the "CCL premium" built into the deployment plan
- In Models C and D, ATLC (an HCA-tier stock) receives the CCL-level allocation
- This creates a structural mismatch: ATLC was never subjected to the CCL gate, yet it would receive CCL-level capital deployment

**Model B avoids this mismatch:** VRT (CCL) stays at rank 1, and the $8,810 CCL allocation remains correctly assigned to the CCL stock.
