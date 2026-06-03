# Phase 7.4C - Conviction Model Validation Report

**Analysis Run:** `PAR-20260530-3A136D4F`  
**Conviction universe:** 19 holdings  
**Top-N analyzed:** 19  

> Analysis only. No formula changes. Objective: determine whether DAS
> over-weights sizing headroom relative to conviction, replay, and composite.

---

## Observation

In the Phase 7.4A output, `ARW`, `PSX`, and `SNX` (all HCA-tier, small positions)
outrank `MU`, `VRT`, `AEIS`, and `CVE` (CCL-tier or larger positions). This
raises the question: is the sizing headroom component over-represented in DAS?

The sizing headroom component is defined as:

```
sizing_c = 15.0 x max(0.0, 1.0 - current_pct / 6.0)
```

A position at 0% weight earns full 15 pts. At 6% it earns 0 pts.
This creates a theoretical spread of **15 points** from smallest to largest position.
The conviction tier spread is **5 points** (CCL=25 vs HCA=20).
Ratio: sizing headroom max spread is **3x** the tier spread.

---

## Section 1 - Factor Contribution Breakdown (Top 20 by DAS)

| Rank | Symbol | DAS | Composite | Replay | Tier | Weight | Signal | Replay+ | Conv | Sizing | Momentum | Pen | Headroom% | Conv% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `ARW` | 92.06 | 4.889 | Y | HCA | 0.91% | 29.3 | 20.0 | 20.0 | 12.7 | 10.0 | -0 | 13.8% | 21.7% |
| 2 | `PSX` | 91.49 | 4.722 | Y | HCA | 0.74% | 28.3 | 20.0 | 20.0 | 13.2 | 10.0 | -0 | 14.4% | 21.9% |
| 3 | `SNX` | 91.44 | 4.778 | Y | HCA | 0.89% | 28.7 | 20.0 | 20.0 | 12.8 | 10.0 | -0 | 14.0% | 21.9% |
| 4 | `AEIS` | 89.91 | 4.714 | Y | CCL | 2.35% | 28.3 | 20.0 | 25.0 | 9.1 | 7.5 | -0 | 10.1% | 27.8% |
| 5 | `LRCX` | 89.63 | 4.500 | Y | HCA | 0.95% | 27.0 | 20.0 | 20.0 | 12.6 | 10.0 | -0 | 14.1% | 22.3% |
| 6 | `SANM` | 89.12 | 4.714 | Y | HCA | 0.67% | 28.3 | 20.0 | 20.0 | 13.3 | 7.5 | -0 | 15.0% | 22.4% |
| 7 | `DELL` | 88.7 | 4.500 | Y | HCA | 1.32% | 27.0 | 20.0 | 20.0 | 11.7 | 10.0 | -0 | 13.2% | 22.5% |
| 8 | `VRT` | 88.27 | 4.556 | Y | CCL | 3.62% | 27.3 | 20.0 | 25.0 | 5.9 | 10.0 | -0 | 6.7% | 28.3% |
| 9 | `CVE` | 78.31 | 4.889 | Y | CCL | 2.41% | 29.3 | 20.0 | 25.0 | 9.0 | 10.0 | -15 | 11.5% | 31.9% |
| 10 | `ASML` | 76.63 | 4.722 | Y | HCA | 0.68% | 28.3 | 20.0 | 20.0 | 13.3 | 10.0 | -15 | 17.4% | 26.1% |
| 11 | `TSM` | 75.94 | 4.444 | Y | CCL | 2.29% | 26.7 | 20.0 | 25.0 | 9.3 | 10.0 | -15 | 12.2% | 32.9% |
| 12 | `STNG` | 74.62 | 4.714 | Y | HCA | 0.47% | 28.3 | 20.0 | 20.0 | 13.8 | 7.5 | -15 | 18.5% | 26.8% |
| 13 | `SIMO` | 74.18 | 4.571 | Y | HCA | 0.30% | 27.4 | 20.0 | 20.0 | 14.3 | 7.5 | -15 | 19.2% | 27.0% |
| 14 | `NVDA` | 71.68 | 4.111 | Y | CCL | 3.20% | 24.7 | 20.0 | 25.0 | 7.0 | 10.0 | -15 | 9.8% | 34.9% |
| 15 | `AVGO` | 71.68 | 4.000 | Y | HCA | 0.93% | 24.0 | 20.0 | 20.0 | 12.7 | 10.0 | -15 | 17.7% | 27.9% |
| 16 | `GTX` | 68.59 | 3.889 | Y | HCA | 1.90% | 23.3 | 20.0 | 20.0 | 10.3 | 10.0 | -15 | 15.0% | 29.2% |
| 17 | `MSFT` | 68.34 | 3.444 | Y | HCA | 0.93% | 20.7 | 20.0 | 20.0 | 12.7 | 10.0 | -15 | 18.5% | 29.3% |
| 18 | `MU` | 68.16 | 4.722 | Y | CCL | 6.04% | 28.3 | 20.0 | 25.0 | 0.0 | 10.0 | -15 | 0.0% | 36.7% |
| 19 | `SBS` | 60.16 | 3.714 | Y | HCA | 3.85% | 22.3 | 20.0 | 20.0 | 5.4 | 7.5 | -15 | 8.9% | 33.2% |

**Column key:** `Signal` = composite-derived (0-30) · `Replay+` = replay bonus (0-20) · `Conv` = tier bonus (0-25) · `Sizing` = headroom bonus (0-15) · `Momentum` = ESS+direction (0-10) · `Pen` = redundancy + concentration penalties · `Headroom%` = sizing component as % of DAS · `Conv%` = conviction component as % of DAS

---

## Section 2 - Average Factor Contribution (Top 20)

| Component | Avg Points | Avg % of DAS | Max Possible | Utilization |
|---|---|---|---|---|
| Signal | 26.71 | 33.9% | 30 | 89% |
| Replay | 20.00 | 25.6% | 20 | 100% |
| Conviction | 21.58 | 27.6% | 25 | 86% |
| Sizing | 10.48 | 13.2% | 15 | 70% |
| Momentum | 9.34 | 11.9% | 10 | 93% |
| Redundancy Penalty | 8.68 | 12.2% | 15 | 58% |
| Conc Penalty | 0.01 | 0.0% | 20 | 0% |

**Key finding:** Sizing headroom averages **10.5 pts (13.2% of DAS)**. Conviction tier averages **21.6 pts (27.6% of DAS)**. Signal averages **26.7 pts**.

Sizing headroom contribution is **0.5x** the conviction tier contribution on average.

---

## Section 3 - Rank Correlation Analysis

### Spearman Rank Correlations (Full Conviction Universe, n=19)

| Correlation | rho | Interpretation |
|---|---|---|
| DAS vs Composite Score | 0.6338 | Strong positive alignment |
| DAS vs Conviction Tier | 0.2504 | DAS slightly favors lower-conviction (HCA) positions |
| DAS vs Sizing Headroom | 0.3583 | Weak alignment |
| Composite vs Sizing Headroom | 0.2702 | Weak alignment |

### Spearman Rank Correlations (Top 20 Only)

| Correlation | rho |
|---|---|
| DAS vs Composite Score | 0.6338 |
| DAS vs Conviction Tier | 0.2504 |
| DAS vs Sizing Headroom | 0.3583 |

**Interpretation of tier correlation sign convention:**
Tier_num = 1 for CCL (highest conviction), 2 for HCA. A *negative* DAS vs tier_num
rho means DAS tends to rank higher-conviction symbols higher — which is desirable.
A *positive* rho means DAS is rewarding lower-conviction symbols more.

---

## Section 4 - Cases Where DAS Materially Disagrees With Conviction Ranking

**Definition:** |DAS rank - conviction rank| >= 3, or HCA symbol ranks
in top 3 while any CCL symbol ranks lower.

| Symbol | Tier | DAS Rank | Conv Rank | Delta | DAS | Composite | Weight | Sizing pts | Sizing% | Root Cause |
|---|---|---|---|---|---|---|---|---|---|---|
| `MU` | CCL | 18 | 2 | +16 | 68.16 | 4.722 | 6.04% | 0.0 | 0.0% | Penalties suppressing DAS |
| `LRCX` | HCA | 5 | 15 | -10 | 89.63 | 4.500 | 0.95% | 12.6 | 14.1% | HCA ranked above CCL by DAS |
| `PSX` | HCA | 2 | 10 | -8 | 91.49 | 4.722 | 0.74% | 13.2 | 14.4% | HCA ranked above CCL by DAS |
| `CVE` | CCL | 9 | 1 | +8 | 78.31 | 4.889 | 2.41% | 9.0 | 11.5% | Penalties suppressing DAS |
| `NVDA` | CCL | 14 | 6 | +8 | 71.68 | 4.111 | 3.20% | 7.0 | 9.8% | Penalties suppressing DAS |
| `DELL` | HCA | 7 | 14 | -7 | 88.7 | 4.500 | 1.32% | 11.7 | 13.2% | HCA ranked above CCL by DAS |
| `ARW` | HCA | 1 | 7 | -6 | 92.06 | 4.889 | 0.91% | 12.7 | 13.8% | HCA ranked above CCL by DAS |
| `TSM` | CCL | 11 | 5 | +6 | 75.94 | 4.444 | 2.29% | 9.3 | 12.2% | Penalties suppressing DAS |
| `SNX` | HCA | 3 | 8 | -5 | 91.44 | 4.778 | 0.89% | 12.8 | 14.0% | HCA ranked above CCL by DAS |
| `SANM` | HCA | 6 | 11 | -5 | 89.12 | 4.714 | 0.67% | 13.3 | 15.0% | HCA ranked above CCL by DAS |
| `VRT` | CCL | 8 | 4 | +4 | 88.27 | 4.556 | 3.62% | 5.9 | 6.7% | Composite + sizing combination |

**DAS rank vs conviction rank summary:**

| Symbol | Tier | DAS Rank | Conv Rank | Delta | Sizing pts | Conviction pts |
|---|---|---|---|---|---|---|
| `ARW` | HCA | 1 | 7 | -6 <-- | 12.7 | 20.0 |
| `PSX` | HCA | 2 | 10 | -8 <-- | 13.2 | 20.0 |
| `SNX` | HCA | 3 | 8 | -5 <-- | 12.8 | 20.0 |
| `AEIS` | CCL | 4 | 3 | +1 | 9.1 | 25.0 |
| `LRCX` | HCA | 5 | 15 | -10 <-- | 12.6 | 20.0 |
| `SANM` | HCA | 6 | 11 | -5 <-- | 13.3 | 20.0 |
| `DELL` | HCA | 7 | 14 | -7 <-- | 11.7 | 20.0 |
| `VRT` | CCL | 8 | 4 | +4 <-- | 5.9 | 25.0 |
| `CVE` | CCL | 9 | 1 | +8 <-- | 9.0 | 25.0 |
| `ASML` | HCA | 10 | 9 | +1 | 13.3 | 20.0 |
| `TSM` | CCL | 11 | 5 | +6 <-- | 9.3 | 25.0 |
| `STNG` | HCA | 12 | 12 | 0 | 13.8 | 20.0 |
| `SIMO` | HCA | 13 | 13 | 0 | 14.3 | 20.0 |
| `NVDA` | CCL | 14 | 6 | +8 <-- | 7.0 | 25.0 |
| `AVGO` | HCA | 15 | 16 | -1 | 12.7 | 20.0 |
| `GTX` | HCA | 16 | 17 | -1 | 10.3 | 20.0 |
| `MSFT` | HCA | 17 | 19 | -2 | 12.7 | 20.0 |
| `MU` | CCL | 18 | 2 | +16 <-- | 0.0 | 25.0 |
| `SBS` | HCA | 19 | 18 | +1 | 5.4 | 20.0 |

---

## Section 5 - HCA Symbols Ranked Above CCL Symbols

The following HCA-tier symbols appear in the top 6 by DAS, ranking above
some CCL symbols (`AEIS`, `VRT`, `CVE`, `TSM`, `NVDA`, `MU`):

| Symbol | DAS Rank | DAS | Weight | Signal | Conv | Sizing | Momentum | Why ranked above CCL? |
|---|---|---|---|---|---|---|---|---|
| `ARW` | 1 | 92.06 | 0.91% | 29.3 | 20.0 | 12.7 | 10.0 | Sizing=12.7pts (small pos); Signal=29.3pts (high comp) |
| `PSX` | 2 | 91.49 | 0.74% | 28.3 | 20.0 | 13.2 | 10.0 | Sizing=13.2pts (small pos); Signal=28.3pts (high comp) |
| `SNX` | 3 | 91.44 | 0.89% | 28.7 | 20.0 | 12.8 | 10.0 | Sizing=12.8pts (small pos); Signal=28.7pts (high comp) |
| `LRCX` | 5 | 89.63 | 0.95% | 27.0 | 20.0 | 12.6 | 10.0 | Sizing=12.6pts (small pos) |
| `SANM` | 6 | 89.12 | 0.67% | 28.3 | 20.0 | 13.3 | 7.5 | Sizing=13.3pts (small pos); Signal=28.3pts (high comp) |

**Mechanism:** These HCA symbols have small current positions, earning near-maximum
sizing headroom (approaching 15 pts). Combined with their high composite scores,
the total exceeds what CCL symbols earn despite the 5-pt tier gap.

---

## Section 6 - Numerical Illustration of Sizing vs Conviction Trade-off

For two hypothetical positions with identical composite (4.7) and replay support:

| Attribute | Position A (CCL, 3%) | Position B (HCA, 0.8%) |
|---|---|---|
| Signal | 28.2 | 28.2 |
| Replay | 20.0 | 20.0 |
| Conviction | **25.0** (CCL) | **20.0** (HCA) |
| Sizing | 7.5 | 13.0 |
| Momentum | 10.0 | 10.0 |
| **DAS** | **90.7** | **91.2** |

**Result:** Position B (HCA) wins by 0.5 pts despite CCL carrying a 5-pt tier advantage over HCA.

The sizing headroom gap (13.0 vs 7.5 = **+5.5 pts for B**)
more than offsets the conviction tier gap (25 vs 20 = **+5 pts for A**).
At 0.8% vs 3.0%, the headroom advantage is 5.5 pts vs the 5-pt tier gap.

---

## Section 7 - Recommended Adjustments

> These are analytical recommendations only. No formula changes were made.

### Finding 1: Sizing headroom can override conviction tier

- The sizing component (max 15 pts) creates a spread of up to **15 pts**
  between a 0% and 6% position.
- The conviction tier spread is only **5 pts** (CCL=25 vs HCA=20).
- Any HCA symbol with a position < ~1.5% and composite > 4.0 can outrank a
  CCL symbol at 3%+ weight with a similar or slightly lower composite.

**Option A — Cap sizing headroom contribution:**
  Reduce sizing max from 15 to 8-10. This narrows the headroom spread to within
  the conviction tier gap range.

**Option B — Scale conviction tier advantage:**
  Widen the tier spread: CCL=30, HCA=18. Increases the conviction gap from 5 to 12 pts,
  ensuring CCL symbols can only be outranked by HCA symbols with materially better signals.

**Option C — Add a conviction multiplier:**
  Apply a tier multiplier to the final DAS: CCL x 1.05, HCA x 1.00.
  This preserves relative scoring within tiers while enforcing cross-tier ordering.

**Option D — Accept current behavior as correct (if philosophy agrees):**
  If small HCA positions with high composites are genuinely better *deployment*
  candidates (more room to grow), then the current DAS accurately reflects
  deployment opportunity rather than intrinsic conviction quality. This is a
  philosophy question: is DAS ranking *where to put capital* or *which holdings
  are most important to the portfolio*?

### Finding 2: Composite-DAS alignment is strong

Spearman rho(DAS, composite) = 0.6338. This is moderate
alignment — the formula correctly rewards high composite scores.

### Finding 3: Tier-DAS alignment depends on position size

Spearman rho(DAS, tier_num) = 0.2504.
The DAS formula is **slightly inverting** conviction tier ordering when sizing headroom
differences are large (>2% weight differential between CCL and HCA symbols).

### Recommended decision framework

If the goal of DAS is to rank **deployment attractiveness** (where cash will have
the most impact on portfolio construction):
  - Current formula is defensible: small positions have more room to grow.
  - Consider Option A or B to prevent HCA from systematically outranking CCL.

If the goal is to rank **conviction quality** (which positions deserve more capital
because they are the most important holdings):
  - Current formula under-weights tier; Option B or C is most appropriate.

**Key question for the portfolio manager:**
> Is ARW (HCA, 0.91%, composite 4.89) a better deployment target than
> VRT (CCL, 3.62%, composite 4.56)? If yes, the DAS formula is correct.
> If no — VRT should rank higher as a core conviction holding — adjust
> the sizing weight or tier spread.

---

*Analysis only. No formula changes made. Findings are advisory.*
