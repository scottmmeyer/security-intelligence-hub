# Capital Concentration Analysis — Phase 7.5P
**Run:** PAR-20260529-BAF83F16 | **Date:** 2026-05-31  
**Scope:** Concentration metrics for all 4 planner models. No allocation changes.

---

## 1. Concentration Metrics by Model

| Model | Description | Top-1 | Top-3 | Top-5 | Top-10 | Top-1 Name |
|-------|-------------|-------|-------|-------|--------|-----------|
| **A** | Current: CCL=3.0 | **32.2%** | **44.8%** | **55.7%** | **74.2%** | VRT |
| B | Moderate: CCL=2.0 | 24.1% | 40.7% | 50.4% | 71.1% | VRT |
| C | Signal 1:1: CCL=1.0 | 13.7% | 31.6% | 43.6% | 67.1% | VRT |
| D | Flat (direct CW-DAS) | 5.2% | 15.5% | 25.8% | 51.1% | VRT |

**VRT holds the #1 position in all 4 models.** The multiplier determines the *degree* of concentration, not the *winner*.

---

## 2. Top-1 Concentration Detail

### Model A (Current): VRT = 32.2% of pool

```
VRT:     $10,687  ████████████████████████████████  32.2%
ARW:      $2,482  ███████                            7.5%
SNX:      $2,013  ██████                             6.1%
ATLC:     $1,743  █████                              5.3%
PSX:      $1,557  ████                               4.7%
CBOE:     $1,416  ████                               4.3%
AVT:      $1,298  ████                               3.9%
LRCX:     $1,209  ████                               3.6%
CAH:      $1,138  ███                                3.4%
DELL:     $1,072  ███                                3.2%
[10 more] $8,563                                    25.8%
```

One holding receives more than the next 4 combined.

### Model B (Moderate): VRT = 24.1% of pool

```
VRT:      $7,982  ████████████████████████           24.1%
ARW:      $2,780  █████████                           8.4%
SNX:      $2,255  ███████                             6.8%
ATLC:     $1,953  ██████                              5.9%
PSX:      $1,744  █████                               5.3%
CBOE:     $1,587  █████                               4.8%
...
```

### Model C (Signal 1:1): VRT = 13.7% of pool

```
VRT:      $4,537  ██████████████                     13.7%
ARW:      $3,160  ██████████                          9.5%
SNX:      $2,564  ████████                            7.7%
ATLC:     $2,220  ███████                             6.7%
PSX:      $1,982  ██████                              6.0%
...
```

### Model D (Flat): VRT = 5.2% of pool

```
VRT:      $1,741  █████                               5.2%
ARW:      $1,716  █████                               5.2%
SNX:      $1,705  █████                               5.1%
ATLC:     $1,704  █████                               5.1%
...
```

Model D is nearly indistinguishable from equal-weight allocation across 20 candidates.

---

## 3. CCL vs HCA Capital Split

| Model | CCL Capital | HCA Capital | CCL per Candidate | HCA per Candidate | CCL Premium |
|-------|-------------|-------------|-------------------|-------------------|-------------|
| A | $10,687 (32.2%) | $22,488 (67.8%) | $10,687 | $1,184 | **9.0×** |
| B | $7,982 (24.1%) | $25,193 (75.9%) | $7,982 | $1,326 | **6.0×** |
| C | $4,537 (13.7%) | $28,638 (86.3%) | $4,537 | $1,507 | **3.0×** |
| D | $1,741 (5.2%) | $31,434 (94.8%) | $1,741 | $1,654 | **1.1×** |

The "CCL premium" (capital per CCL candidate vs capital per HCA candidate) is directly proportional to the CCL multiplier. Note: CCL count = 1 in this run.

---

## 4. Concentration Curve — Capital Decay Rate

Showing what % of the total pool is consumed as you add more candidates:

| Candidates included | Model A | Model B | Model C | Model D |
|--------------------|---------|---------|---------|---------|
| Top 1 | 32.2% | 24.1% | 13.7% | 5.2% |
| Top 2 | 39.7% | 32.5% | 23.2% | 10.4% |
| Top 3 | 45.8% | 39.3% | 31.0% | 15.6% |
| Top 4 | 51.1% | 45.2% | 37.7% | 20.7% |
| Top 5 | 55.8% | 50.5% | 43.7% | 25.8% |
| Top 10 | 74.2% | 71.1% | 67.1% | 51.1% |
| Top 15 | 88.3% | 87.0% | 85.3% | 75.8% |
| Top 20 | 100.0% | 100.0% | 100.0% | 100.0% |

Model A has the steepest early decay — it front-loads capital to the top candidate most aggressively. Model D is the flattest.

---

## 5. Concentration Ratios — First vs Second

| Model | 1st Place | 2nd Place | 1:2 Ratio | Interpretation |
|-------|-----------|-----------|-----------|----------------|
| A (Current) | VRT $10,687 | ARW $2,482 | **4.31×** | Extreme CCL premium |
| B (Moderate) | VRT $7,982 | ARW $2,780 | **2.87×** | Meaningful CCL premium |
| C (Signal 1:1) | VRT $4,537 | ARW $3,160 | **1.44×** | Signal quality gap only |
| D (Flat) | VRT $1,741 | ARW $1,716 | **1.02×** | Near-parity |

The 1:2 ratio in Model C (1.44×) represents the "pure signal" gap between VRT and ARW — the advantage attributable to VRT's slightly higher CW-DAS score plus rank-1 √rank advantage. Everything above 1.44× in Models A and B is the structural CCL multiplier premium.

---

## 6. Signal-to-Capital Alignment

A well-calibrated system should produce allocations that are reasonably correlated with signal quality (composite score). Over-correlation means the system ignores portfolio construction; under-correlation means it ignores current information.

| Model | r(composite, allocation) | r(weight, allocation) | Interpretation |
|-------|-------------------------|-----------------------|----------------|
| A | 0.33 | **0.89** | Incumbency-dominant |
| B | ~0.40 | ~0.82 | Incumbency-leaning |
| C | **0.67** | ~0.79 | Balanced |
| D | ~0.95 | ~0.04 | Signal-dominant (inverse weight correlation due to sizing term in CW-DAS) |

**Model A's r(composite, alloc) = 0.33 is a low signal-to-allocation correlation.** 67% of allocation variance is explained by factors other than composite quality (primarily: whether the holding happens to be ≥ 1.5% weight and therefore CCL). 

**Model C's r(composite, alloc) = 0.67** is a more balanced signal-to-allocation relationship — the highest-composite candidates receive proportionally more capital, but the √rank decay still creates differentiation.

---

## 7. Concentration vs CONCENTRATED_ALPHA Mandate Fit

The CONCENTRATED_ALPHA mandate, as documented, calls for:
1. Concentration in the highest-conviction positions
2. Capital compounding to build meaningful position sizes
3. Avoidance of over-diversification

Evaluating each model against these criteria:

| Criterion | Model A | Model B | Model C | Model D |
|-----------|---------|---------|---------|---------|
| Concentrates in top-conviction | ✓✓ (32.2% top-1) | ✓ (24.1%) | ~ (13.7%) | ✗ (5.2%) |
| Avoids fragmentation | ✓✓ | ✓ | ~ | ✗ |
| Tracks current signal quality | ✗ (r=0.33) | ~ (r≈0.40) | ✓ (r=0.67) | ✓✓ (r≈0.95) |
| Distinguishes tier quality | ✓✓ | ✓ | ~ | ✗ |

Model A over-serves the concentration mandate at the cost of signal tracking. Model D over-serves signal tracking at the cost of concentration. **Model B or C best balances the two objectives** — concentration is still present and meaningful, but capital distribution is more responsive to current market signals.

For a concentrated alpha mandate specifically: **Model B** (CCL=2.0) maintains strong concentration character (24.1% top-1) while being more defensible on signal quality grounds (the #1 signal name receives materially more capital than in Model A's $2,482 allocation to ARW, at $2,780).

---

## 8. What Would Change Under Model B

| Metric | Model A (Current) | Model B (Proposed) | Delta |
|--------|------------------|-------------------|-------|
| VRT allocation | $10,687 | $7,982 | −$2,705 (−25.3%) |
| ARW allocation | $2,482 | $2,780 | +$298 (+12.0%) |
| Top-1 concentration | 32.2% | 24.1% | −8.1 ppts |
| CCL per-candidate premium | 9.0× avg HCA | 6.0× avg HCA | −33% |
| VRT/ARW ratio | 4.31× | 2.87× | −33% |
| r(composite, alloc) | 0.33 | ~0.40 | +0.07 |
| Rank order | Unchanged | Unchanged | — |

Model B produces the same rank ordering. VRT is still #1. All CCL/HCA tier distinctions are preserved. The only change is that the 3× capital amplification becomes a 2× capital amplification — a less extreme structural premium for portfolio incumbency.

---

## 9. Conclusion

The current system (Model A) delivers the most concentrated capital deployment but does so primarily through incumbency rather than signal quality. One holding (VRT) receives 32.2% of the deployment pool — 9× the average HCA allocation — based on having crossed the 1.5% portfolio weight threshold.

The CONCENTRATED_ALPHA mandate is served, but the model calibration (CCL=3.0) is aggressive. A moderate reduction to CCL=2.0 (Model B) would:
- Preserve the concentrated alpha character
- Reduce the incumbency amplification by 33%
- Increase responsiveness to current signal quality
- Not change any rank ordering
- Not require changes to any scoring formulas or tier logic
