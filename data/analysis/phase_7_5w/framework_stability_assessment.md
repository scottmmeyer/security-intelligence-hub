# Q8: Framework Stability Assessment

## Sizing_c Sensitivity Analysis

Sizing_c = 8.0 × max(0, 1 - weight% / 6.0)
This component provides 0–8 points and decreases as weight grows.

| Weight% | Sizing_c | Max Reduction from Baseline |
|---------|----------|----------------------------|
| 0.5% | 7.333 | 0.667 |
| 1.0% | 6.667 | 1.333 |
| 2.0% | 5.333 | 2.667 |
| 3.0% | 4.000 | 4.000 |
| 4.0% | 2.667 | 5.333 |
| 5.0% | 1.333 | 6.667 |
| 6.0% | 0.000 | 8.000 |
| 7.0% | 0.000 | 8.000 |
| 8.0% | 0.000 | 8.000 |

## Concentration Penalty (conc_pen) Sensitivity

Conc_pen = min((weight% - 6.0) × 4.0, 20.0) for weight% > 6.0

| Weight% | Conc_pen | Score Impact |
|---------|----------|-------------|
| 6.0% | 0.0 | -0.0 pts |
| 6.5% | 2.0 | -2.0 pts |
| 7.0% | 4.0 | -4.0 pts |
| 7.5% | 6.0 | -6.0 pts |
| 8.0% | 8.0 | -8.0 pts |
| 9.0% | 12.0 | -12.0 pts |
| 10.0% | 16.0 | -16.0 pts |
| 11.0% | 20.0 | -20.0 pts |

## CCL vs HCA Score Comparison

At baseline weights, CCL symbols carry conviction_c=35 vs HCA conviction_c=28.
Combined with CCL_CONVICTION_MULT=1.75 in the planner, CCL symbols receive structural advantage.

| Symbol | Tier | Baseline Score | Conviction_c | Sizing_c | Weight% |
|--------|------|---------------|-------------|---------|--------|
| VRT | CCL | 95.35 | 35.0 | 3.02 | 3.7384% |
| ARW | HCA | 94.11 | 28.0 | 6.78 | 0.9143% |
| ATLC | HCA | 93.51 | 28.0 | 6.84 | 0.8682% |
| SNX | HCA | 93.46 | 28.0 | 6.79 | 0.9097% |
| PSX | HCA | 93.32 | 28.0 | 6.99 | 0.7577% |

## Rank Stability Under +$5k Trade Increments

Tests how much capital it takes to move a symbol out of rank #1.

| Add to VRT ($) | VRT Score | VRT Rank | New Rank#1 Symbol |
|---------------|----------|---------|-----------------|
| $0 | 95.35 | #1 | VRT |
| $2,000 | 94.79 | #1 | VRT |
| $4,000 | 94.22 | #1 | VRT |
| $6,000 | 93.66 | #2 | ARW |
| $8,000 | 93.10 | #6 | ARW |
| $10,000 | 92.54 | #6 | ARW |
| $15,000 | 88.77 | #14 | ARW |
| $20,000 | 84.56 | #31 | ARW |

## Stability Verdict

**Scoring formula evaluation:**
- Sizing_c range: 0.0 – 8.0 pts (gradual linear decay)
- Conc_pen range: 0.0 – 20.0 pts (activates only above WARN threshold)
- CCL conviction bonus: +7 pts over HCA (35 vs 28)
- Both weight-dependent penalties combined can reduce score by up to 28 pts

The framework uses gradual, continuous penalties — not step-function cutoffs.
This creates smooth rank transitions rather than abrupt displacements.