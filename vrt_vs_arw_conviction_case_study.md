# VRT vs ARW Conviction Case Study — Phase 7.5O
**Run:** PAR-20260529-BAF83F16 | **Date:** 2026-05-31  
**Question:** Why does VRT receive $8,822 recommended deployment vs ARW's $2,049?

---

## 1. Every Conviction Input

### VRT — Vertiv Holdings Co

| Input | Value | Source |
|-------|-------|--------|
| Portfolio weight | **3.6019%** | holdings.csv → `percent_of_portfolio` |
| Market value | $17,008.75 | holdings.csv → `market_value` |
| Composite score | **4.5556 / 5.0** | analytical_universe.csv → weighted ESS/Zacks/Danelfin |
| ESS score text | **VERY_BULLISH** | signal_snapshot.csv → `ess_score_text` |
| Signal direction | **BULLISH** | security_overlays → `signal_direction` |
| Replay supported | **True** | security_overlays → `replay_supported` |
| Trim priority score | **1.62** | trim_intelligence.py → `trim_priority_score` |
| Strategic classification | **HIGH_CONVICTION_RETAIN** | trim_intelligence.py → `_classify_holding()` |
| Narrative tier | **CORE_CONVICTION_LEADER** | trim_intelligence.py → `_assign_narrative_tiers()` |
| UCF label | **CORE_CONVICTION_LEADER** | unified_conviction.py → `build_ucf_verdicts()` |
| In OW node | **False** | deployment_queue.py → `_holding_in_ow_node()` |
| Headroom to WARN (6%) | **40.0%** | = max(0, 1 − 3.60/6.0) × 100 |

### ARW — Arrow Electronics, Inc.

| Input | Value | Source |
|-------|-------|--------|
| Portfolio weight | **0.9169%** | holdings.csv → `percent_of_portfolio` |
| Market value | $4,330.00 | holdings.csv → `market_value` |
| Composite score | **4.8889 / 5.0** | analytical_universe.csv → weighted ESS/Zacks/Danelfin |
| ESS score text | **VERY_BULLISH** | signal_snapshot.csv → `ess_score_text` |
| Signal direction | **BULLISH** | security_overlays → `signal_direction` |
| Replay supported | **True** | security_overlays → `replay_supported` |
| Trim priority score | **0.41** | trim_intelligence.py → `trim_priority_score` |
| Strategic classification | **HIGH_CONVICTION_RETAIN** | trim_intelligence.py → `_classify_holding()` |
| Narrative tier | **HIGH_CONVICTION_ANCHOR** | trim_intelligence.py → `_assign_narrative_tiers()` |
| UCF label | **HIGH_CONVICTION_ANCHOR** | unified_conviction.py → `build_ucf_verdicts()` |
| In OW node | **False** | deployment_queue.py → `_holding_in_ow_node()` |
| Headroom to WARN (6%) | **84.7%** | = max(0, 1 − 0.92/6.0) × 100 |

---

## 2. Every Point Contribution — CW-DAS Score

### Formula
`CW-DAS = Signal + Replay + Conviction + Sizing + Momentum − Redundancy − Concentration`

### VRT CW-DAS = 95.53

| Component | Calculation | Points |
|-----------|-------------|--------|
| Signal | 4.5556 / 5.0 × 30 | **27.33** |
| Replay | replay_supported = True → 20 | **20.00** |
| Conviction | narrative_tier = CCL → 35 | **35.00** |
| Sizing | 8 × (1 − 3.6019 / 6.0) = 8 × 0.400 | **3.20** |
| Momentum | ESS = VERY_BULLISH (contains "BULLISH") AND signal = BULLISH → 10 | **10.00** |
| Redundancy penalty | in_ow_node = False → 0 | **0.00** |
| Concentration penalty | weight 3.60% < 6.0% → 0 | **0.00** |
| **Total** | | **95.53** |

### ARW CW-DAS = 94.11

| Component | Calculation | Points |
|-----------|-------------|--------|
| Signal | 4.8889 / 5.0 × 30 | **29.33** |
| Replay | replay_supported = True → 20 | **20.00** |
| Conviction | narrative_tier = HCA → 28 | **28.00** |
| Sizing | 8 × (1 − 0.9169 / 6.0) = 8 × 0.847 | **6.78** |
| Momentum | ESS = VERY_BULLISH AND signal = BULLISH → 10 | **10.00** |
| Redundancy penalty | in_ow_node = False → 0 | **0.00** |
| Concentration penalty | weight 0.92% < 6.0% → 0 | **0.00** |
| **Total** | | **94.11** |

---

## 3. The 7-Point Conviction Difference — Root Cause

### What determines CCL vs HCA tier?

`src/portfolio/trim_intelligence.py → _assign_narrative_tiers() → _tier_for()`

CCL requires ALL five conditions:

| Condition | VRT | ARW |
|-----------|-----|-----|
| signal_direction == "BULLISH" | ✓ 3.6019% | ✓ |
| replay_supported == True | ✓ | ✓ |
| composite_score ≥ 4.0 | ✓ 4.5556 | ✓ 4.8889 |
| **percent_of_portfolio ≥ 1.5%** | **✓ 3.60%** | **✗ 0.92%** |
| trim_priority_score < 30.0 | ✓ 1.62 | ✓ 0.41 |

**ARW fails on a single condition: portfolio weight (0.92% < 1.5%).** All other conditions are satisfied. ARW's composite score (4.89) and trim score (0.41) are each better than VRT's.

Because ARW does not qualify for CCL, it falls to HCA (via `strategic_classification == "HIGH_CONVICTION_RETAIN"` → HCA path). This produces:
- VRT conviction_points = **35** (CCL constant: `_CCL_CONVICTION = 35.0`)
- ARW conviction_points = **28** (HCA constant: `_HCA_CONVICTION = 28.0`)
- Difference: **−7 points**

### Component-by-component gap

| Component | VRT | ARW | Difference (VRT − ARW) |
|-----------|-----|-----|------------------------|
| Signal | 27.33 | 29.33 | **−2.00** (ARW is better) |
| Replay | 20.00 | 20.00 | 0.00 |
| Conviction | **35.00** | **28.00** | **+7.00** |
| Sizing | 3.20 | 6.78 | **−3.58** (ARW is better) |
| Momentum | 10.00 | 10.00 | 0.00 |
| Penalties | 0.00 | 0.00 | 0.00 |
| **CW-DAS total** | **95.53** | **94.11** | **+1.42** |

The conviction tier advantage (+7.00) is partially offset by ARW's superior signal quality (−2.00) and lower weight giving more sizing headroom (−3.58). Net CW-DAS advantage for VRT: only **+1.42 points**.

---

## 4. Penalties and Bonuses

**Penalties applied to VRT:** None  
**Penalties applied to ARW:** None  
**Bonuses applied to either:** None  
(No OW nodes in this run; neither position is at concentration thresholds)

---

## 5. Capital Allocation — From CW-DAS to Dollars

### Deployment planner formula

`planner_weight_i = cw_das_score_i × conviction_mult_i / √rank_i`

Where:
- `conviction_mult`: CCL = **3.0**, HCA = **1.0**  (`src/portfolio/deployment_planner.py`: `_CCL_CONVICTION_MULT`, `_HCA_CONVICTION_MULT`)
- `√rank_i`: rank decay — discounts lower-ranked candidates

### VRT planner weight

`95.53 × 3.0 / √1 = 95.53 × 3.0 / 1.000 = 286.59`

### ARW planner weight

`94.11 × 1.0 / √2 = 94.11 × 1.0 / 1.414 = 66.55`

### Weight ratio

`286.59 / 66.55 = 4.307×`

### Cash allocation

Total eligible deployment weights sum to **1,077.69** across 31 eligible candidates.  
Total deployable cash: **$33,175.19**

| Symbol | Weight | Share of pool | Allocation | Cap (to 6% WARN) | Final |
|--------|--------|---------------|-----------|-----------------|-------|
| VRT | 286.59 | 26.59% | $8,822 | $11,324 | **$8,822** |
| ARW | 66.55 | 6.17% | $2,049 | $24,003 | **$2,049** |

- VRT is **not capped** — $8,822 is below its headroom cap of $11,324
- ARW is **not capped** — $2,049 is well below its headroom cap of $24,003
- The 4.31× allocation gap reflects the weight ratio exactly

---

## 6. Why VRT Receives 35/35 Conviction Points

1. **Portfolio weight = 3.60%** — exceeds the 1.5% CCL threshold by 2.10 percentage points
2. **BULLISH signal** — passes CCL gate condition 1
3. **Replay supported** — passes CCL gate condition 2
4. **Composite 4.5556 ≥ 4.0** — passes CCL gate condition 3
5. **Trim score 1.62 < 30** — passes CCL gate condition 5

With all CCL conditions satisfied, `_tier_for()` returns `"CORE_CONVICTION_LEADER"`, and `compute_cw_das()` assigns `conviction_c = _CCL_CONVICTION = 35.0`.

## 7. Why ARW Receives 28/35 Conviction Points

1. **Portfolio weight = 0.92%** — falls short of the 1.5% CCL threshold by **0.58 percentage points**
2. All other CCL conditions are satisfied (signal, replay, composite, trim)
3. Because weight < 1.5%, `_tier_for()` evaluates the HCA path: `strategic_classification == "HIGH_CONVICTION_RETAIN"` → **True**
4. Result: `"HIGH_CONVICTION_ANCHOR"` → `compute_cw_das()` assigns `conviction_c = _HCA_CONVICTION = 28.0`

---

## 8. The 7-Point Breakdown

| Source | Points | Code location |
|--------|--------|---------------|
| CCL conviction constant (`_CCL_CONVICTION`) | 35.0 | `deployment_queue.py` line 48 |
| HCA conviction constant (`_HCA_CONVICTION`) | 28.0 | `deployment_queue.py` line 49 |
| **Difference** | **7.0** | |
| CCL gate condition that separates them | weight ≥ 1.5% | `trim_intelligence.py` → `_tier_for()` |

---

## 9. Counterfactual Analysis

### Would ARW become 35/35 if weight exceeded 1.5%?

**Yes.** If ARW's portfolio weight were ≥ 1.5%, all five CCL conditions would be satisfied. ARW would receive narrative_tier = CORE_CONVICTION_LEADER and conviction_points = 35/35.

ARW currently needs **$2,754 more invested** (= 0.58% × $472,219 total portfolio) to cross the CCL threshold.

### If ARW were CCL today (counterfactual):

| Metric | Current | If ARW were CCL |
|--------|---------|-----------------|
| ARW conviction_points | 28 | 35 |
| ARW CW-DAS score | 94.11 | ~101.11 (approx, before sizing adjustment) |
| ARW planner weight | 66.55 | 199.64 (94.11 × 3.0 / √2) |
| ARW suggested_add | $2,049 | **$5,470** |
| VRT suggested_add | $8,822 | **$7,852** |
| VRT/ARW ratio | 4.31× | **1.44×** |

Elevating ARW to CCL would reduce VRT's capital advantage from **4.31× to 1.44×**, driven almost entirely by the planner's 3× CCL multiplier.

### Would any other factor change the outcome?

No. In the current run:
- Neither VRT nor ARW has OW nodes, trim suppression, concentration penalties, or signal differences that would change the conviction tier
- ARW has a **better composite score** and **better signal quality** than VRT — these qualities already flow through to ARW's higher signal component (29.33 vs 27.33) and are insufficient to overcome the tier gap
- The only scenario that changes the tier outcome is portfolio weight crossing 1.5%

---

## 10. The Precise Accounting of the 4.31× Capital Gap

| Layer | Mechanism | Amplification factor |
|-------|-----------|---------------------|
| CW-DAS score | VRT scores 1.42 pts more (95.53 vs 94.11) | 1.015× |
| Planner tier multiplier | CCL mult=3.0 vs HCA mult=1.0 | 3.000× |
| Rank decay | VRT rank 1 (÷√1=1.0) vs ARW rank 2 (÷√2=0.707) | 1.414× |
| **Combined** | 1.015 × 3.000 × 1.414 | **4.31×** |

The **3.0 CCL conviction multiplier in the deployment planner** is the primary driver of the capital gap. The CW-DAS score difference alone would produce only a 1.5% capital advantage, not a 331% advantage.
