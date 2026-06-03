# Conviction Influence Analysis — Phase 7.5O
**Run:** PAR-20260529-BAF83F16 | **Date:** 2026-05-31 | **Queue size:** 42 candidates (31 eligible after OW blocks)

---

## 1. Conviction Scoring Architecture

The system produces conviction points through two separate, independent mechanisms:

### Layer 1: CW-DAS Score (0–103 range; penalty-adjusted)

`CW-DAS = Signal(0–30) + Replay(0–20) + Conviction(0–35) + Sizing(0–8) + Momentum(0–10) − Redundancy(0–15) − Concentration(0–20)`

| Component | Driver | Range |
|-----------|--------|-------|
| Signal | `composite_score / 5 × 30` | 0–30 |
| Replay | binary gate: `replay_supported` | 0 or 20 |
| Conviction | narrative_tier: CCL=35, HCA=28, other=10 | 0–35 |
| Sizing | `8 × max(0, 1 − weight_pct / 6.0)` | 0–8 |
| Momentum | ESS + signal direction convergence | 0, 4, 7.5, 10 |

### Layer 2: Deployment Planner Weight

`planner_weight_i = cw_das_score_i × conviction_mult_i / √rank_i`

| Tier | conviction_mult | Rank effect |
|------|-----------------|-------------|
| CORE_CONVICTION_LEADER | **3.0** | ÷ √1 = 1.00 (rank 1) |
| HIGH_CONVICTION_ANCHOR | **1.0** | ÷ √rank |

The planner weight determines proportional share of deployable cash. This is a **second, independent amplification** of tier status beyond the CW-DAS score.

---

## 2. Factor Variance in the Top 20 Queue

| Factor | Range | Variance | Interpretation |
|--------|-------|----------|----------------|
| Signal component | 22.00 – 29.33 | **5.87** | Largest variation — reflects actual signal quality |
| Conviction component | 28.0 – 35.0 | **2.45** | Binary split: VRT (CCL=35) vs all others (HCA=28) |
| Sizing component | 3.20 – 7.95 | **0.97** | Weight-driven, pure incumbency inverse |
| Replay component | 20.0 – 20.0 | 0.00 | No variation — all 20 pass replay gate |
| Momentum component | 10.0 – 10.0 | 0.00 | No variation — all 20 have BULLISH signal + BULLISH ESS |
| Redundancy penalty | 0.0 – 0.0 | 0.00 | No variation — no OW nodes in this run |

**Finding:** Signal quality drives the most within-tier CW-DAS differentiation. Conviction tier is a binary step function (VRT vs everyone else), not a continuous measure.

---

## 3. Factor Correlations with Portfolio Weight (top 20)

| Correlation | r | Interpretation |
|-------------|---|----------------|
| weight_pct ↔ conviction_points | **+0.8731** | High weight strongly predicts CCL tier |
| weight_pct ↔ sizing_component | **−1.0000** | Perfect inverse: bigger position = less headroom |
| weight_pct ↔ composite_score | +0.4771 | Moderate: larger positions tend to have better signals |
| composite_score ↔ signal_component | +1.0000 | Perfect: signal is a linear transform of composite |

### What the 0.87 correlation means

The high correlation between portfolio weight and conviction points is an **artifact of a single binary threshold:**
- Any holding with weight ≥ 1.5% + BULLISH + replay + composite ≥ 4.0 + trim < 30 → CCL (35 pts)
- Any holding below 1.5% weight → HCA (28 pts)

In this run, VRT is the sole CCL at 3.60% weight. Remove VRT and the correlation collapses to zero (all remaining candidates score 28 pts identically).

---

## 4. Incumbency Influence by Factor

### Factor A: Conviction points (28 vs 35) — INCUMBENCY-DRIVEN

The CCL gate requires portfolio weight ≥ 1.5%. This is the primary incumbency signal.

- **VRT (3.60%):** Passes CCL gate → conviction = 35/35
- **ARW (0.92%):** Fails CCL gate by 0.58% → conviction = 28/35
- **DELL (1.32%):** Fails CCL gate by 0.18% → conviction = 28/35

ARW needs only **$2,754 more invested** to cross the CCL threshold. At that point it would earn 35/35 conviction points — despite having equal signal quality to current CCL holders.

| CCL gate condition | VRT | ARW | Passes? |
|-------------------|-----|-----|---------|
| signal_direction == BULLISH | ✓ | ✓ | Both |
| replay_supported == True | ✓ | ✓ | Both |
| composite_score ≥ 4.0 | 4.56 ✓ | 4.89 ✓ | Both |
| percent_of_portfolio ≥ 1.5% | 3.60% ✓ | 0.92% **✗** | VRT only |
| trim_priority_score < 30 | 1.62 ✓ | 0.41 ✓ | Both |

ARW fails CCL on a **single condition** — portfolio weight.

### Factor B: Sizing component (3.20 vs 6.78) — INCUMBENCY-DRIVEN (inverse)

Larger positions have less headroom to the 6% WARN threshold, producing lower sizing scores. This partially counteracts the conviction advantage.

- VRT sizing = 3.20 (only 40% headroom at 3.60% weight)
- ARW sizing = 6.78 (84.7% headroom at 0.92% weight)

Incumbency adds +7 conviction pts but subtracts −3.58 sizing pts from VRT vs ARW. **Net CW-DAS incumbency effect: +3.42 points** (of the 1.42-point actual gap, this overstates; the difference is also partially due to ARW's higher composite score canceling out the advantage).

### Factor C: Deployment planner multiplier — INCUMBENCY-DRIVEN (dominant)

The deployment planner applies a **second layer of CCL amplification** independent of CW-DAS:

| Calculation | VRT (CCL) | ARW (HCA) |
|-------------|-----------|-----------|
| CW-DAS score | 95.53 | 94.11 |
| Conviction mult | **3.0** | **1.0** |
| Rank decay (÷√rank) | ÷ √1 = 1.00 | ÷ √2 = 0.707 |
| Deployment weight | **286.59** | **66.55** |
| Raw allocation | $8,822 | $2,049 |

VRT's deployment weight is **4.31× ARW's** despite only a 1.42-point CW-DAS score advantage.

---

## 5. What Primarily Drives Conviction Score?

### CW-DAS Score (0–100)

| Driver | VRT vs field | Ranking influence |
|--------|-------------|-------------------|
| **Signal quality (composite)** | VRT is mid-table (rank 1 but 4.56 composite vs ARW's 4.89) | Primary differentiator among HCA candidates |
| **Replay support** | Universal — no differentiation | Gate, not differentiator |
| **Conviction tier (CCL/HCA)** | 35 vs 28 = +7 pts for VRT | Binary step; separates VRT from field |
| **Sizing (headroom)** | VRT low (3.20) due to large position | Partially offsets conviction advantage |
| **Momentum (ESS)** | Universal (all 10.0) | No differentiation in this run |

**Answer: Signal quality (composite) primarily differentiates among HCA candidates. Conviction tier (CCL vs HCA) is the dominant factor only at the boundary between VRT and the rest.**

### Capital Deployment (dollars allocated)

| Driver | Contribution to VRT/ARW gap |
|--------|----------------------------|
| CW-DAS score difference (1.42 pts) | Minor (~2%) |
| Conviction planner multiplier (3.0 vs 1.0) | **Primary (~70%)** |
| Rank decay (rank 1 vs rank 2) | Secondary (~18%) |
| Remaining proportional effects | Residual (~10%) |

**Answer: Capital deployment is primarily driven by the 3× planner multiplier for CCL, not by signal quality.**

---

## 6. Incumbency Counterfactuals

### If ARW had weight ≥ 1.5% (CCL-eligible):
- ARW CW-DAS: still ≈ 94.11 (no change to score, only tier changes)
- ARW conviction_points: 28 → **35**
- ARW CW-DAS: 94.11 + 7 - (sizing adjustment) ≈ unchanged for new deployment weight calc
- ARW planner weight: 66.55 → **199.64** (3× mult)
- ARW allocation: $2,049 → **$5,470**
- VRT allocation: $8,822 → **$7,852** (redistributed)
- New VRT/ARW ratio: **1.44× vs current 4.31×**

### If CCL conviction_mult = 1.0 (same as HCA — no tier amplification):
- VRT planner weight: 286.59 → **95.53** (just the CW-DAS score)
- ARW planner weight: 66.55 → 66.55 (unchanged)
- New ratio based on weights: 95.53 / 66.55 = **1.44×**

### If ARW's composite were identical to VRT's (4.5556):
- ARW CW-DAS: 27.33 + 20 + 28 + 6.78 + 10 = **92.11**
- ARW planner weight: 92.11 / √2 = **65.12**
- New ratio: 286.59 / 65.12 = **4.40×** (essentially unchanged)

**Key insight:** The VRT/ARW allocation gap is almost entirely insensitive to signal quality differences. It is dominated by the CCL planner multiplier (3× amplification).

---

## 7. Summary: Nature of Incumbency in This System

| Mechanism | Type | Effect |
|-----------|------|--------|
| 1.5% weight gate for CCL | **Incumbency gate** | Existing large positions earn higher conviction tier |
| Conviction_points 35 vs 28 | **Tier benefit** | +7 CW-DAS points for CCL vs HCA (6.7% score uplift) |
| Planner conviction_mult 3× | **Capital amplification** | CCL receives 3× weight in capital allocation formula |
| Sizing headroom inverse | **Incumbency offset** | Larger positions receive less capital on a per-point basis |

**Net incumbency effect:** The sizing offset (−3.58 pts) does not cancel the conviction tier benefit (+7 pts). More importantly, the deployment planner's 3× multiplier creates capital concentration in CCL positions that is not reflected in the CW-DAS score itself.

**Whether this rewards: (A) Signal quality, (B) Replay evidence, (C) Existing portfolio size, or (D) Classification status:**
- Within the HCA tier: **A (signal quality)** differentiates most
- CCL vs HCA boundary: **C (existing portfolio size)** — the 1.5% weight gate is the decisive condition
- Capital allocation: **D (classification status)** — the 3× planner multiplier concentrates capital in CCL regardless of signal differences
