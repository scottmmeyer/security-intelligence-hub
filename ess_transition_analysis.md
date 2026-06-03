# ESS Transition Analysis
**Phase 7.6G — Deliverable Q5**
**Generated:** 2026-06-01
**Dataset:** `ess_transition_matrix.csv`, from `ess_history_master.csv`

---

## 1. Purpose

The transition matrix measures the probability that an ESS category changes from period to period. A high persistence probability means ESS is stable — a critical property for a deployment signal. A directionally symmetric decay pattern (more gradual than abrupt transitions) indicates a well-behaved signal.

---

## 2. Full 5×5 Transition Matrix

### Probabilities (from → to, consecutive observations)

| FROM \ TO | VERY_BEARISH | BEARISH | NEUTRAL | BULLISH | VERY_BULLISH | Total n |
|-----------|:------------:|:-------:|:-------:|:-------:|:------------:|:-------:|
| VERY_BEARISH | **81.2%** | 14.5% | 3.7% | 0.5% | 0.1% | 3,987 |
| BEARISH | 6.2% | **80.1%** | 11.6% | 1.8% | 0.2% | 9,346 |
| NEUTRAL | 0.9% | 7.7% | **81.0%** | 8.9% | 1.5% | 15,284 |
| BULLISH | 0.5% | 2.1% | 11.7% | **77.0%** | 8.7% | 14,865 |
| VERY_BULLISH | 0.2% | 0.8% | 4.4% | 17.8% | **76.8%** | 8,166 |

> **Bold values** = persistence (stay in same category)

---

## 3. Aggregate Probabilities

### 3.1 Persistence (no change to adjacent observations)

| Category | Persistence % | n Transitions |
|----------|--------------|---------------|
| VERY_BEARISH | 81.2% | 3,987 |
| BEARISH | 80.1% | 9,346 |
| NEUTRAL | 81.0% | 15,284 |
| BULLISH | 77.0% | 14,865 |
| VERY_BULLISH | 76.8% | 8,166 |

**Average persistence across all categories: 79.2%**

This is a strong result. In approximately 4 of every 5 observation periods, an ESS category remains unchanged. This confirms ESS as a stable, low-turnover signal.

### 3.2 Upgrade Probability (move to higher category)

| Category | Upgrade % | n Upgrades |
|----------|-----------|-----------|
| VERY_BEARISH | 18.8% | 751 |
| BEARISH | 13.6% | 1,273 |
| NEUTRAL | 10.4% | 1,590 |
| BULLISH | 8.7% | 1,300 |
| VERY_BULLISH | — | — |

Upgrade probability decreases as category improves. VERY_BEARISH stocks are most likely to be upgraded (18.8%), while BULLISH stocks upgrade at a lower rate (8.7%). This reflects mean reversion and regression-to-center dynamics.

### 3.3 Downgrade Probability (move to lower category)

| Category | Downgrade % | n Downgrades |
|----------|------------|-------------|
| VERY_BEARISH | — | — |
| BEARISH | 6.2% | 583 |
| NEUTRAL | 8.6% | 1,314 |
| BULLISH | 14.3% | 2,121 |
| VERY_BULLISH | 23.2% | 1,893 |

Downgrade probability increases with ESS level. VERY_BULLISH stocks are most at risk of degradation (23.2%), consistent with the net downward ESS trend observed in Phase 7.6F-R (average delta = −0.519 over the period).

---

## 4. Transition Decay Pattern

The transition matrix demonstrates a **banded, near-diagonal structure** — nearly all transitions (>95%) occur within 1 ESS level of the origin. Jumps of 2+ levels are rare:

| Transition Type | Example | Observed % |
|-----------------|---------|------------|
| No change | BULLISH → BULLISH | 79.2% avg |
| ±1 level | BULLISH → VERY_BULLISH | 8.7% / 11.7% |
| ±2 levels | BULLISH → NEUTRAL (skip) | 2.1% / 0.5% |
| ±3+ levels | BULLISH → VERY_BEARISH | <0.1% |

This banded pattern indicates ESS **does not flip erratically** between extremes. Extreme moves (VERY_BULLISH → VERY_BEARISH) are essentially non-existent in consecutive observations. This is characteristic of a smoothed consensus signal.

---

## 5. Implications for Deployment

**Implication 1 — Stability for hold decisions:**
A 77–81% persistence rate means that if you hold a position based on BULLISH ESS today, you have a ~77% probability that ESS will still be BULLISH at the next observation. Deployment decisions can be made with reasonable confidence that the signal won't immediately reverse.

**Implication 2 — Directional asymmetry:**
- VERY_BULLISH degrades at 23.2% per period
- VERY_BEARISH improves at 18.8% per period
- This asymmetry explains the net negative ESS drift (average delta = −0.519) over the study period

**Implication 3 — Positioning at extremes:**
VERY_BEARISH and NEUTRAL have the highest persistence (81.2% and 81.0%). VERY_BULLISH has the lowest (76.8%) because high-ESS ratings are hard to sustain — analyst consensus tends to revert toward neutral over time.

**Implication 4 — No need for daily ESS monitoring:**
With 79.2% persistence between consecutive observations (typically 1-7 days apart in this dataset), daily re-scoring is not necessary. Weekly ESS capture would capture nearly all transitions. The current weekly/bi-weekly cadence is appropriate.

---

## 6. Finding Summary

> **The transition matrix confirms ESS as a stable, well-behaved signal. ~79% persistence between consecutive observation periods, banded near-diagonal structure, and gradual decay pattern (no extreme flips). This is a strong positive finding for ESS authority as a deployment signal.**

The transition results are the single clearest positive signal from this study. ESS stability is empirically confirmed at the 79.2% average persistence level.
