# VRT Curve Sensitivity Analysis
**Phase 7.5U — Allocation Curve Calibration Audit**
**Run:** PAR-20260601-9CFD7C63 | **Date:** June 1, 2026

---

## VRT Profile

| Field | Value |
|-------|-------|
| CW-DAS rank | 1 |
| Deployment tier | TIER_1 (CCL) |
| CW-DAS score | 95.5 |
| Conviction component | 35.0 pts (CCL rate) |
| Signal component | 27.33 pts |
| Replay component | 20.0 pts |
| Sizing component | 3.17 pts |
| Momentum component | 10.0 pts |
| Current weight | 3.62% |
| Headroom to warn | 39.6% |

---

## VRT Allocation Under Each Curve (Current Multipliers: CCL=3.0, HCA=1.0)

| Curve Model | Formula | VRT Alloc $ | VRT % of Pool | Delta vs Current |
|-------------|---------|------------|--------------|-----------------|
| **A — Current** | score × mult / sqrt(rank) | **$8,810.94** | 26.59% | — |
| B — Moderate | score × mult / rank^0.35 | **$6,740.20** | 20.34% | **−$2,070.74** |
| C — Balanced | score × mult / log₂(rank+1) | **$9,135.19** | 27.56% | **+$324.25** |
| D — Linear | score × mult × (1−(rank−1)/31) | **$5,766.52** | 17.40% | **−$3,044.42** |

### Key Finding: Log Decay Increases VRT Concentration

Model C (log₂ decay) is counterintuitively **more concentrated at rank 1** than the current sqrt curve. The log₂ weight function decays faster from rank 1 to rank 2:

| Rank | sqrt weight | log₂ weight | Difference |
|------|------------|------------|-----------|
| 1 | 1.0000 | 1.0000 | — |
| 2 | 0.7071 | 0.6309 | log₂ is **10.8% lower** at rank 2 |
| 3 | 0.5774 | 0.5000 | log₂ is **13.4% lower** at rank 3 |
| 5 | 0.4472 | 0.3869 | log₂ is **13.5% lower** at rank 5 |
| 10 | 0.3162 | 0.2891 | log₂ is **8.6% lower** at rank 10 |
| 31 | 0.1796 | 0.2000 | log₂ is **11.4% higher** at rank 31 |

The log curve is steeper at the top and flatter at the bottom relative to sqrt. This makes VRT even more dominant and gives tail positions more weight — the opposite of what "balanced concentration" should mean.

**Only Models B and D reduce VRT allocation.** Model C must be disqualified as a "less concentrated" alternative.

---

## How Much of VRT's Concentration is Rank vs Curve?

### Direct Decomposition

The formula gives VRT a weight of:

$$w_{\text{VRT}} = 95.5 \times 3.0 \div \sqrt{1} = 286.50$$

**Step 1: Remove the multiplier (CCL → HCA, same curve)**
$$w_{\text{VRT,no mult}} = 95.5 \times 1.0 \div \sqrt{1} = 95.50$$
→ VRT allocation without CCL mult = **$3,569.67** (41% of current $8,811)

**Step 2: Change the curve (keep current mult)**
Under rank^0.35 with CCL=3.0: VRT weight = 95.5 × 3.0 / 1^0.35 = 286.50 (identical to current — rank 1 is unaffected)
→ VRT's raw weight does not change when the curve changes. What changes is the total pool weight, which dilutes VRT's share.

| Scenario | VRT weight | Total weight pool | VRT alloc | VRT % |
|---------|-----------|-----------------|----------|-------|
| A — Current mult + sqrt curve | 286.50 | 3,566 | $8,811 | 26.59% |
| A_no_mult — No CCL mult + sqrt curve | 95.50 | 2,849 | $3,570 | 10.77% |
| B — Current mult + rank^0.35 curve | 286.50 | 4,439 | $6,740 | 20.34% |
| D — Current mult + linear curve | 286.50 | 4,640 | $5,767 | 17.40% |

VRT's weight in the numerator never changes between curve models (rank 1 always contributes its full score × mult). Only the denominator (total weight pool) changes. Flatter curves increase the denominator more, reducing VRT's proportional share.

### Quantified Attribution

| Change | VRT reduction | % of maximum possible reduction |
|--------|--------------|-------------------------------|
| Curve → rank^0.35 (no mult change) | −$2,071 | 24% |
| Mult → 1.75/1.25 (no curve change) | −$4,020 | 46% |
| Both together (S3: B curve + 1.75/1.25) | −$5,283 | 60% |
| Maximum (no mult, log curve): | ~$3,800 | — |

---

## VRT Allocation Range Across Scenarios

| Scenario | VRT Alloc | VRT % |
|---------|----------|-------|
| Highest: Model C, current mult | $9,135 | 27.6% |
| Baseline: Model A, current mult | $8,811 | 26.6% |
| Moderate: Model B, current mult | $6,740 | 20.3% |
| Phase 7.5Q: Model A, 1.75/1.25 mult | $4,791 | 14.5% |
| Both: Model B, 1.75/1.25 mult | $3,528 | 10.6% |
| Linear curve: Model D, current mult | $5,767 | 17.4% |
| Flat: equal-weight (31 positions) | $1,069 | 3.2% |

---

## Verdict

VRT's rank-1 concentration is **not primarily a curve problem**. VRT's raw weight (286.50) is unchanged across all curve models because it is at rank 1 and the rank-1 curve value is always 1.0. The allocation reduction under Models B and D comes entirely from the denominator expansion (other positions getting more weight), not from VRT's own weight reduction.

The conviction multiplier (CCL=3.0) is the structural source. Without it, VRT would hold ~$3,570 under the current curve — consistent with its rank-1 position but without tier dominance. The multiplier accounts for **$5,241** of VRT's current $8,811 allocation (59.5%).

**If VRT concentration is the target, the multiplier must be addressed.** Curve changes alone reduce it by at most 35% (via the denominator mechanism), while the multiplier reduction produces a 46% reduction by directly lowering VRT's numerator weight.
