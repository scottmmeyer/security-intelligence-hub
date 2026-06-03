# Concentrated Alpha Philosophy Validation Report — Phase 7.5P
**Run:** PAR-20260529-BAF83F16 | **Date:** 2026-05-31  
**Scope:** Read-only analysis. No scoring changes. No allocation changes. No ranking changes.

---

## Question 1: What Investment Philosophy Does the Current Planner Implement?

**Classification: A — Reinforce Existing Winners**

*with a hybrid signal-quality component*

### Evidence

The current planner assigns capital via:

```
planner_weight = cw_das_score × conviction_mult / √rank
```

Where `conviction_mult = 3.0 (CCL) or 1.0 (HCA)`, and CCL qualification requires `portfolio_weight ≥ 1.5%`.

This means:
- **A holding must already be large** to qualify for the tier that gets concentrated capital
- Once large, it receives a 3× multiplier that is independent of current signal quality
- Signal quality (composite, ESS, Zacks, Danelfin) flows through CW-DAS score but is not the gating criterion for the multiplier

### Capital Distribution Evidence

| Metric | Value |
|--------|-------|
| CCL candidates in top 20 | **1 of 20** (VRT only) |
| CCL capital share | **32.2%** of $33,175 pool |
| HCA candidates in top 20 | 19 of 20 |
| HCA capital share | 67.8% split 19 ways |
| VRT vs avg HCA allocation | **9.0× more capital than average HCA** |
| VRT CW-DAS vs ARW CW-DAS | 95.53 vs 94.11 (+1.5% signal advantage) |
| VRT vs ARW capital | $10,687 vs $2,482 (**4.31× capital advantage**) |

### Signal-quality ranking discrepancy

| Rank | By Composite Score | By Capital Allocated (Model A) |
|------|--------------------|---------------------------------|
| 1 | ARW (4.8889) | VRT ($10,687) |
| 2 | SNX (4.7778) | ARW ($2,482) |
| 3 | ATLC (4.7778) | SNX ($2,013) |
| 4 | PSX (4.7222) | ATLC ($1,743) |
| 5 | CBOE (4.6667) | PSX ($1,557) |
| 6 | **VRT (4.5556)** | CBOE ($1,416) |

**VRT ranks 6th by composite score but receives 1st-place capital.** This is the defining characteristic of a Reinforce Existing Winners philosophy: position size, not signal quality, determines who receives concentrated new capital.

### Philosophy classification rationale

| Factor | Reinforce Existing Winners | Maximize Opportunity | Current System |
|--------|---------------------------|---------------------|----------------|
| Tier assigned by position size? | ✓ | ✗ | ✓ |
| Capital proportional to signals? | ✗ | ✓ | Partially |
| Multiplier independent of signals? | ✓ | ✗ | ✓ |
| √rank decay? | Marginal | Strong | Marginal (CCL absorbs it) |

**Verdict: The current planner is a Reinforce Existing Winners model that uses signal quality as a ranking mechanism (CW-DAS score, which flows to rank and the score numerator) but uses portfolio weight as the tier-gating criterion for concentrated capital.** Signal quality shapes the relative ordering within a tier; portfolio weight determines which tier a candidate occupies.

---

## Question 2: Top 20 Capital Distribution

### Full table — all 20 candidates

| # | Symbol | Tier | CW-DAS | UCF | Composite | ESS | Replay | Weight% | Allocation |
|---|--------|------|--------|-----|-----------|-----|--------|---------|------------|
| 1 | VRT | CCL | 95.53 | CORE_CONVICTION_LEADER | 4.5556 | VERY_BULLISH | ✓ | 3.60% | **$10,687** |
| 2 | ARW | HCA | 94.11 | HIGH_CONVICTION_ANCHOR | 4.8889 | VERY_BULLISH | ✓ | 0.92% | $2,482 |
| 3 | SNX | HCA | 93.51 | HIGH_CONVICTION_ANCHOR | 4.7778 | VERY_BULLISH | ✓ | 0.86% | $2,013 |
| 4 | ATLC | HCA | 93.48 | HIGH_CONVICTION_ANCHOR | 4.7778 | VERY_BULLISH | ✓ | 0.89% | $1,743 |
| 5 | PSX | HCA | 93.34 | HIGH_CONVICTION_ANCHOR | 4.7222 | VERY_BULLISH | ✓ | 0.75% | $1,557 |
| 6 | CBOE | HCA | 93.04 | HIGH_CONVICTION_ANCHOR | 4.6667 | VERY_BULLISH | ✓ | 0.72% | $1,416 |
| 7 | AVT | HCA | 92.10 | HIGH_CONVICTION_ANCHOR | 4.5556 | VERY_BULLISH | ✓ | 0.93% | $1,298 |
| 8 | LRCX | HCA | 91.73 | HIGH_CONVICTION_ANCHOR | 4.5000 | VERY_BULLISH | ✓ | 0.95% | $1,209 |
| 9 | CAH | HCA | 91.59 | HIGH_CONVICTION_ANCHOR | 4.5000 | VERY_BULLISH | ✓ | 1.06% | $1,138 |
| 10 | DELL | HCA | 90.91 | HIGH_CONVICTION_ANCHOR | 4.4444 | VERY_BULLISH | ✓ | 1.32% | $1,072 |
| 11 | SANM | HCA | 90.78 | HIGH_CONVICTION_ANCHOR | 4.2778 | BULLISH | ✓ | 0.66% | $1,021 |
| 12 | PCB | HCA | 90.74 | HIGH_CONVICTION_ANCHOR | 4.3333 | VERY_BULLISH | ✓ | 0.94% | $977 |
| 13 | CIEN | HCA | 90.11 | HIGH_CONVICTION_ANCHOR | 4.2778 | BULLISH | ✓ | 1.17% | $932 |
| 14 | NUE | HCA | 89.62 | HIGH_CONVICTION_ANCHOR | 4.1111 | BULLISH | ✓ | 0.79% | $893 |
| 15 | GFF | HCA | 88.50 | HIGH_CONVICTION_ANCHOR | 3.8333 | BULLISH | ✓ | 0.37% | $852 |
| 16 | ALNT | HCA | 88.46 | HIGH_CONVICTION_ANCHOR | 3.7778 | BULLISH | ✓ | 0.16% | $825 |
| 17 | MTZ | HCA | 88.35 | HIGH_CONVICTION_ANCHOR | 3.7778 | BULLISH | ✓ | 0.23% | $799 |
| 18 | CRS | HCA | 88.20 | HIGH_CONVICTION_ANCHOR | 3.7222 | BULLISH | ✓ | 0.10% | $775 |
| 19 | CMCO | HCA | 87.95 | HIGH_CONVICTION_ANCHOR | 3.6667 | BULLISH | ✓ | 0.03% | $752 |
| 20 | ANGO | HCA | 87.88 | HIGH_CONVICTION_ANCHOR | 3.8333 | BULLISH | ✓ | 0.84% | $733 |

### Capital by tier

| Tier | Candidates | Capital | Share |
|------|-----------|---------|-------|
| CCL | 1 | $10,687 | **32.2%** |
| HCA | 19 | $22,488 | 67.8% |
| **Total** | **20** | **$33,175** | 100% |

A single CCL holding receives 32.2% of the entire deployment pool. The remaining 67.8% is distributed across 19 HCA candidates.

---

## Question 3: Alternative Philosophy Comparison

### Model definitions

| Model | CCL Mult | HCA Mult | Rank Decay | Philosophy |
|-------|----------|----------|------------|-----------|
| A | **3.0** | 1.0 | √rank | Current: Reinforce Existing Winners |
| B | **2.0** | 1.0 | √rank | Moderate Concentration |
| C | **1.0** | 1.0 | √rank | Signal First: CW-DAS determines all |
| D | 1.0 | 1.0 | **none** | Opportunity First: pure CW-DAS, flat |

### Top 10 allocations by model

| Rank | A (Current) | Alloc | B (Moderate) | Alloc | C (Signal 1:1) | Alloc | D (Flat) | Alloc |
|------|------------|-------|-------------|-------|---------------|-------|---------|-------|
| 1 | VRT (CCL) | $10,687 | VRT (CCL) | $7,982 | VRT (CCL) | $4,537 | VRT | $1,741 |
| 2 | ARW | $2,482 | ARW | $2,780 | ARW | $3,160 | ARW | $1,716 |
| 3 | SNX | $2,013 | SNX | $2,255 | SNX | $2,564 | SNX | $1,705 |
| 4 | ATLC | $1,743 | ATLC | $1,953 | ATLC | $2,220 | ATLC | $1,704 |
| 5 | PSX | $1,557 | PSX | $1,744 | PSX | $1,982 | PSX | $1,701 |
| 6 | CBOE | $1,416 | CBOE | $1,587 | CBOE | $1,804 | CBOE | $1,696 |
| 7 | AVT | $1,298 | AVT | $1,454 | AVT | $1,653 | AVT | $1,679 |
| 8 | LRCX | $1,209 | LRCX | $1,355 | LRCX | $1,540 | LRCX | $1,672 |
| 9 | CAH | $1,138 | CAH | $1,275 | CAH | $1,450 | CAH | $1,670 |
| 10 | DELL | $1,072 | DELL | $1,201 | DELL | $1,365 | DELL | $1,657 |

**Key observation: The rank order is identical across all 4 models.** VRT holds rank 1 in all models because its CW-DAS score (95.53) is the highest. The multiplier changes *magnitude* of allocation, not *order*. This is because VRT wins the CW-DAS competition legitimately — only the capital amount varies.

### VRT vs ARW ratio by model

| Model | VRT Allocation | ARW Allocation | Ratio | VRT CCL Premium |
|-------|---------------|----------------|-------|-----------------|
| A (Current) | $10,687 | $2,482 | **4.31×** | Yes: 3.0× mult |
| B (Moderate) | $7,982 | $2,780 | **2.87×** | Yes: 2.0× mult |
| C (Signal 1:1) | $4,537 | $3,160 | **1.44×** | No mult difference |
| D (Flat) | $1,741 | $1,716 | **1.02×** | None |

At Model C (equal multipliers), the 1.44× ratio accurately reflects the actual CW-DAS + rank advantage VRT holds through signal quality. Model D (flat) produces near-parity (1.02×), reflecting the fact that VRT's actual CW-DAS is only marginally better (95.53 vs 94.11).

---

## Question 4: ARW vs VRT — Rational PM Perspective

**A rational PM looking only at signal quality would choose ARW first.**

### Signal quality dimensions

| Dimension | VRT | ARW | Winner |
|-----------|-----|-----|--------|
| Composite score (0–5) | 4.5556 | **4.8889** | ARW |
| Signal component (CW-DAS pts) | 27.33 | **29.33** | ARW |
| Trim priority score (lower=better) | 1.62 | **0.41** | ARW |
| Sizing headroom | 3.20 | **6.78** | ARW |
| ESS momentum | VERY_BULLISH | VERY_BULLISH | Tie |
| Replay support | ✓ | ✓ | Tie |
| Portfolio weight | **3.60%** | 0.92% | VRT (incumbency) |

**On every signal-quality dimension that is independent of portfolio weight, ARW scores equal or better than VRT.** ARW wins 4 of 4 pure-signal dimensions. VRT wins only on portfolio weight, which is the incumbency factor rather than a current market signal.

### The PM's choice question

**Framing A — maximize current opportunity:**  
A PM allocating new cash toward the best current risk-reward opportunity — based on composite research quality, analyst confidence, and momentum alignment — would choose ARW. ARW has the higher composite (4.89 > 4.56), better trim score (0.41 < 1.62), and more sizing headroom to build toward.

**Framing B — reinforce portfolio conviction:**  
A PM managing a concentrated alpha portfolio who believes in compounding existing core positions would choose VRT. VRT is the established Core Conviction Leader. Adding to a 3.60% position vs building a 0.92% position is a question of conviction compounding vs new idea deployment.

**Conclusion:** The correct choice depends on the portfolio mandate. For a concentrated alpha mandate (which this system claims), VRT is the defensible choice *because of its existing size*. But a PM would recognize that this decision is driven by **past decisions** (having accumulated 3.60% in VRT) rather than **current information** (which favors ARW on every forward-looking signal dimension).

The current system makes this choice implicitly and automatically without surfacing the tradeoff.

---

## Question 5: Incumbency Analysis — Quantified

### Correlation table

| Correlation | Value | Interpretation |
|-------------|-------|----------------|
| `weight_pct` → `conviction_points` | **0.8731** | Position size strongly drives tier assignment |
| `weight_pct` → `allocation$ (Model A)` | **0.8944** | Current allocation is highly weight-correlated |
| `weight_pct` → `allocation$ (Model C)` | **0.7862** | Signal-first model reduces but doesn't eliminate incumbency correlation |
| `composite` → `allocation$ (Model A)` | **0.3252** | Current model weakly correlated with signal quality |
| `composite` → `allocation$ (Model C)` | **0.6667** | Signal-first model doubles composite-to-allocation correlation |

### Incumbency concentration math

| Metric | Value |
|--------|-------|
| VRT position weight | 3.60% |
| CCL threshold (1.5%) crossed by | **2.10 percentage points** above threshold |
| Average HCA position weight | 0.72% |
| Average HCA capital allocation | $1,184 |
| VRT capital allocation | $10,687 |
| VRT premium over avg HCA | **9.0×** |
| VRT premium over ARW (best HCA signal) | **4.31×** |

### How incumbency flows through the system

**Layer 1 — Tier gate (`trim_intelligence.py`):**  
`weight ≥ 1.5%` → CCL (35 pts) vs HCA (28 pts) → 7-point CW-DAS difference  
VRT is CCL because it already has 3.60% weight. ARW has 0.92% — no amount of signal quality overrides this gate.

**Layer 2 — Planner multiplier (`deployment_planner.py`):**  
CCL gets 3.0× multiplier, HCA gets 1.0×. This is applied *after* the CW-DAS score is computed, so it amplifies the tier advantage independently of signal content.

**Layer 3 — Rank 1 position:**  
VRT occupies rank 1 partly because of its higher CW-DAS score (driven by CCL tier), which means it avoids the √2 decay that ARW (rank 2) receives.

**Combined incumbency amplification: 1.015 × 3.0 × 1.414 = 4.31×**

Only 1.5% of the 4.31× gap is attributable to current signal quality. The remaining 2.87× is structural incumbency advantage.

---

## Question 6: Concentration Outcome by Model

| Model | Top-1 | Top-5 | Top-10 | VRT share | Philosophy |
|-------|-------|-------|--------|-----------|-----------|
| A: Current | **32.2%** | 55.7% | 74.2% | **32.2%** | Reinforce Existing Winners |
| B: Moderate | 24.1% | 50.4% | 71.1% | 24.1% | Moderate Concentration |
| C: Signal 1:1 | 13.7% | 43.6% | 67.1% | 13.7% | Signal-Weighted Concentration |
| D: Flat | 5.2% | 25.8% | 51.1% | 5.2% | Opportunity Parity |

### What "CONCENTRATED_ALPHA" mandate implies

The mandate calls for concentrating capital in the highest-conviction positions. This has two interpretations:

**Interpretation 1 — Conviction = accumulated position size:** The portfolio already expresses conviction through weight. More new capital goes to the largest existing position. → Model A is consistent.

**Interpretation 2 — Conviction = current signal quality:** The highest-conviction position is the one with the best signals today. Capital concentrates toward the highest-composite candidates. → Model C is more consistent.

**Which model best matches the stated mandate?**  
Model A (current) produces the most concentrated output (32.2% to a single holding) but drives that concentration via incumbency, not current signal. Model C produces meaningful concentration (13.7% to rank 1 out of 20) while reflecting actual signal quality. Model B occupies a credible middle ground.

---

## Question 7: Recommendation

### VERDICT: REDUCE MULTIPLIER (Model B — CCL=2.0, HCA=1.0)

**Rationale:**

**Why not KEEP CURRENT (Model A):**
1. The 4.31× capital gap between VRT and ARW is not proportional to their conviction signal difference (95.53 vs 94.11 = 1.5% advantage)
2. ARW wins on every signal dimension independently of incumbency — a 4.31× allocation disadvantage for the top-signal name in the run is difficult to justify on investment merit
3. r(composite, allocation) = 0.33 — the current model is poorly correlated with signal quality. Allocations are substantially determined by portfolio weight (r=0.89)
4. One holding (VRT) receiving 32.2% of a deployment pool is extreme concentration even for a concentrated alpha mandate

**Why not REMOVE MULTIPLIER (Model C):**
1. The concentrated alpha mandate does call for differentiated treatment between established core positions and new conviction builds
2. The 1.44× ratio that emerges from equal multipliers correctly reflects actual signal quality advantage — this is appropriate but may underweight the strategic importance of compounding core positions
3. Removing differentiation entirely loses the mechanism that prevents the system from fragmenting capital across 20+ equal-quality candidates

**Why not RESTRUCTURE TIER LOGIC:**
1. The tier logic itself (CCL = weight ≥ 1.5% + signal gates) is coherent — established positions with maintained strong signals deserve preferential treatment
2. The problem is the *magnitude* of the multiplier (3×), not the existence of the tier distinction

**Model B argument:**
- VRT allocation: $7,982 (vs $10,687 current) — still #1 by a substantial margin
- ARW allocation: $2,780 (vs $2,482 current) — slightly more capital to the top-signal name
- VRT/ARW ratio: 2.87× (vs 4.31×) — still meaningful CCL premium, not parity
- Top-1 concentration: 24.1% (vs 32.2%) — still concentrated, not fragmented
- r(composite, alloc) would increase toward 0.40+ — better signal-to-allocation tracking

**Model B preserves:**
- CCL tier distinction (VRT still gets tier-1 priority capital)
- Rank decay (rank 1 vs rank 2 still matters)
- Concentrated alpha character (single holding > 24% of pool)

**Model B reduces:**
- Incumbency amplification from 4.31× to 2.87× (a 33% reduction in the structural gap)
- The degree to which allocation is divorced from current signal quality

---

## Summary

| Question | Finding |
|----------|---------|
| Q1: Philosophy | **Reinforce Existing Winners** — position size gates concentrated capital |
| Q2: Distribution | 1 CCL holding (VRT) receives 32.2% of pool; 19 HCA candidates share 67.8% |
| Q3: Alternatives | Models A–C produce identical rank order; multiplier changes magnitude only |
| Q4: ARW vs VRT | Rational PM signal analysis favors ARW on 4 of 4 signal dimensions |
| Q5: Incumbency | r(weight, alloc) = 0.89; r(composite, alloc) = 0.33 — incumbency dominates |
| Q6: Concentration | Model A (32.2% top-1) most concentrated; Model C (13.7%) signal-consistent |
| Q7: Recommendation | **REDUCE MULTIPLIER** — CCL=2.0 preserves concentrated alpha intent while reducing incumbency over-amplification |
