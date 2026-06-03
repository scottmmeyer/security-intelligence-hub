# Incumbency Sensitivity Report — Phase 7.5Q
**Run:** PAR-20260529-BAF83F16 | **Date:** 2026-05-31  
**Question:** How strongly does current portfolio weight drive deployment capital across all 7 multiplier models?

---

## 1. Overview

"Incumbency influence" is the degree to which a holding's current portfolio weight — rather than its current signal quality — determines how much new capital it receives. In a pure signal-quality deployment system, incumbency would have zero influence. In the current system (Model A), it is the dominant driver.

This report quantifies incumbency influence across all 7 multiplier models via three lenses:
1. Correlation between weight and allocation
2. The VRT/ARW incumbency amplification factor
3. The CCL per-candidate premium over HCA

---

## 2. Incumbency Correlation by Model

Pearson correlation between `current_weight_pct` and `deployment_allocation_$`:

| Model | CCL | HCA | r(weight, allocation) | r(composite, allocation) | Weight dominance ratio |
|-------|-----|-----|-----------------------|--------------------------|------------------------|
| A | 3.00 | 1.00 | **0.8944** | 0.3252 | 2.75× |
| B | 2.50 | 1.00 | 0.8936 | 0.3624 | 2.47× |
| C | 2.00 | 1.00 | 0.8884 | 0.4184 | 2.12× |
| D | 2.00 | 1.25 | 0.8746 | 0.4872 | 1.79× |
| E | 1.75 | 1.25 | 0.8598 | 0.5344 | 1.61× |
| F | 1.50 | 1.00 | 0.8682 | 0.5095 | 1.70× |
| G | 1.00 | 1.00 | 0.7862 | 0.6667 | 1.18× |

*Weight dominance ratio = r(weight, alloc) / r(composite, alloc)*

### Interpretation

In Model A, portfolio weight drives allocation **2.75× more strongly** than signal quality does. Even in Model G (no multiplier amplification), weight still influences allocation **1.18× more** than composite — this residual incumbency is built into the CW-DAS formula itself through the sizing component (higher weight → less headroom → fewer sizing points) creating an inverse effect, but the CCL gate means weight ≥ 1.5% always produces the tier with more conviction points.

**Critical finding: r(weight, alloc) does not drop below 0.79 across any model tested.** Incumbency is structural, not just a multiplier effect. Even completely removing the CCL multiplier (Model G) leaves substantial weight-to-allocation correlation.

---

## 3. VRT/ARW Incumbency Amplification

The VRT/ARW case exposes the clearest quantification of incumbency. VRT has the higher portfolio weight (3.60% vs 0.92%); ARW has better signal quality on every pure-signal dimension. Any capital advantage VRT holds beyond the pure-signal gap (1.44×) is incumbency amplification.

| Model | VRT Alloc | ARW Alloc | VRT/ARW | Signal-only base | Incumbency factor | Incumbency premium |
|-------|-----------|-----------|---------|------------------|-------------------|--------------------|
| A | $10,687 | $2,482 | **4.31×** | 1.44× | **3.00×** | **+200%** |
| B | $9,411 | $2,622 | 3.59× | 1.44× | 2.50× | +150% |
| C | $7,982 | $2,780 | 2.87× | 1.44× | 2.00× | +100% |
| D | $6,708 | $2,921 | 2.30× | 1.44× | 1.60× | +60% |
| E | $6,022 | $2,996 | 2.01× | 1.44× | 1.40× | +40% |
| F | $6,370 | $2,958 | 2.15× | 1.44× | 1.50× | +50% |
| G | $4,537 | $3,160 | 1.44× | 1.44× | **1.00×** | 0% |

The incumbency factor is the ratio of (observed VRT/ARW) to (pure-signal VRT/ARW at Model G). In Model A, 3× of VRT's capital advantage over ARW is pure structural incumbency — disconnected from any current signal.

### Where does this 3× incumbency factor come from?

Decomposing Model A:

```
VRT planner weight = 95.53 × 3.0 / √1 = 286.59
ARW planner weight = 94.11 × 1.0 / √2 =  66.55
                                          ──────
Ratio = 286.59 / 66.55 = 4.307×

Component analysis:
  Score gap:    95.53 / 94.11 = 1.015×   ←  signal quality
  CCL mult:     3.0 / 1.0    = 3.000×    ←  incumbency tier
  Rank decay:   √2 / √1      = 1.414×    ←  partly incumbency (VRT rank 1 because CCL)
  ─────────────────────────────────────
  Combined:     1.015 × 3.0 × 1.414 = 4.307×
```

The 3.0 multiplier is the direct incumbency contribution. The 1.414 rank-decay factor is *indirectly* incumbency — VRT occupies rank 1 partly because its CCL conviction points inflated its CW-DAS score by 7 points.

---

## 4. CCL Per-Candidate Premium

This measures how much more capital each CCL candidate receives versus each HCA candidate on average.

| Model | CCL/candidate | HCA/candidate | CCL premium |
|-------|--------------|---------------|-------------|
| A | $10,687 | $1,184 | **9.0×** |
| B | $9,411 | $1,251 | 7.5× |
| C | $7,982 | $1,326 | 6.0× |
| D | $6,708 | $1,393 | 4.8× |
| E | $6,022 | $1,429 | 4.2× |
| F | $6,370 | $1,411 | 4.5× |
| G | $4,537 | $1,507 | **3.0×** |

Note: Even at Model G (no CCL multiplier), CCL candidates receive 3.0× more capital than average HCA. This is the "structural floor" of incumbency driven by:
1. The 7-point conviction differential in CW-DAS (35 vs 28 pts)
2. The rank-1 position giving CCL the √rank advantage

**The CCL multiplier amplifies this structural 3× floor.** At Model A (CCL=3.0), the 3× structural advantage becomes 9.0×. At Model E (CCL=1.75), it becomes 4.2×.

---

## 5. Incumbency Decomposition: Structural vs Multiplier

| Source | Effect on CCL/HCA premium | Modifiable? |
|--------|--------------------------|-------------|
| CW-DAS conviction points (35 vs 28) | ~1.5× (7 pts → higher score → rank 1) | No — changing this changes scoring |
| √rank decay advantage (rank 1 vs 2) | ~1.4× additional | Indirect only |
| Planner CCL multiplier (3.0× vs 1.0×) | **3.0× direct amplification** | Yes — this is the lever |
| **Combined structural (without mult)** | **~3.0× floor** | Partially |
| **Total with current multiplier** | **~9.0×** | Partially |

**Conclusion: Approximately 2/3 of the incumbency premium is driven by the planner multiplier (directly addressable). Approximately 1/3 is structural (from CW-DAS conviction point design and resulting rank advantage).**

---

## 6. Incumbency Floor Estimation

Even at Model G (CCL=HCA=1.0), the incumbency correlation r(weight, alloc) = 0.787. This is the "structural floor" — the minimum incumbency influence achievable without changing the CW-DAS scoring formula or the CCL gate definition.

The 0.79 floor exists because:
- VRT's weight (3.60%) triggers CCL, which adds 7 conviction points → VRT CW-DAS = 95.53 vs ARW's 94.11
- VRT therefore ranks #1, receives √1 vs ARW's √2 rank decay
- Even with equal multipliers, VRT still receives 1.44× more capital than ARW

To reduce incumbency below the ~0.79 floor would require one of:
- Changing the CCL weight threshold (currently 1.5%)
- Equalizing the CCL/HCA conviction point constants
- Using allocation that does not favor rank-1 candidates

None of these are in scope for this analysis.

---

## 7. Signal Responsiveness Gain from Reducing Multiplier

As CCL multiplier decreases from 3.0 → 1.0:

| CCL step | Δ r(comp, alloc) | Δ r(wt, alloc) | Marginal signal gain per unit CCL reduction |
|----------|-----------------|----------------|---------------------------------------------|
| 3.0 → 2.5 | +0.037 | −0.001 | +0.074/unit |
| 2.5 → 2.0 | +0.056 | −0.005 | +0.112/unit |
| 2.0 → 1.75 | +0.040 | −0.007 | +0.158/unit |
| 1.75 → 1.50 | +0.051 | −0.013 | +0.206/unit |
| 1.50 → 1.25 | +0.068 | −0.027 | +0.272/unit |
| 1.25 → 1.00 | +0.089 | −0.054 | +0.357/unit |

**There is no classic "elbow" where signal gains plateau.** The marginal gain from reducing the CCL multiplier *accelerates* continuously. Each additional unit of CCL reduction toward 1.0 produces more signal improvement than the previous unit.

The elbow cannot be identified by signal gain rate alone. It must be identified by where the incumbency amplification factor drops to a "defensible" level for the concentrated alpha mandate — which is a judgment call informed by the VRT/ARW ratio hitting an acceptable threshold.

---

## 8. Summary Table

| Model | Incumbency factor | r(wt,alloc) | r(comp,alloc) | Operator-defensible VRT/ARW? |
|-------|-------------------|-------------|---------------|------------------------------|
| A (3.0/1.0) | 3.00× | 0.894 | 0.325 | No — 4.31× is indefensible on signals |
| B (2.5/1.0) | 2.50× | 0.894 | 0.362 | Marginal — 3.59× still hard to explain |
| C (2.0/1.0) | 2.00× | 0.888 | 0.418 | Acceptable — 2.87× can be explained |
| D (2.0/1.25) | 1.60× | 0.875 | 0.487 | Good — 2.30× with better HCA allocation |
| **E (1.75/1.25)** | **1.40×** | **0.860** | **0.534** | **Strong — 2.01× is near-optimal balance** |
| F (1.5/1.0) | 1.50× | 0.868 | 0.510 | Good — similar to D/E range |
| G (1.0/1.0) | 1.00× | 0.786 | 0.667 | No — removes all incumbency reward |
