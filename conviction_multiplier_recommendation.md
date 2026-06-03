# Conviction Multiplier Recommendation — Phase 7.5Q
**Run:** PAR-20260529-BAF83F16 | **Date:** 2026-05-31  
**Objective:** Determine the multiplier structure that best expresses "Reward conviction, but do not allow incumbency to dominate opportunity quality."

---

## Recommendation

### MODERATE_REDUCTION

**Proposed configuration: CCL = 1.75, HCA = 1.25**

This corresponds to **Model E** in the sensitivity study.

---

## 1. What the Evidence Shows

### The full model spectrum

| Model | CCL | HCA | VRT/ARW | Top-1% | r(comp,alloc) | Incumbency factor | Total score |
|-------|-----|-----|---------|--------|---------------|-------------------|-------------|
| A | 3.00 | 1.00 | 4.31× | 32.2% | 0.325 | 3.00× | 19 |
| B | 2.50 | 1.00 | 3.59× | 28.4% | 0.362 | 2.50× | 25 |
| C | 2.00 | 1.00 | 2.87× | 24.1% | 0.418 | 2.00× | 30 |
| D | 2.00 | 1.25 | 2.30× | 20.2% | 0.487 | 1.60× | 32 |
| **E** | **1.75** | **1.25** | **2.01×** | **18.2%** | **0.534** | **1.40×** | **34** |
| F | 1.50 | 1.00 | 2.15× | 19.2% | 0.510 | 1.50× | 34 |
| G | 1.00 | 1.00 | 1.44× | 13.7% | 0.667 | 1.00× | 35 |

### Why Model G is not the answer

Model G scores highest numerically (35/50) because the rubric rewards signal alignment. But Model G removes all meaningful incumbency reward:
- VRT/ARW = 1.44× — this is pure CW-DAS score difference, with no CCL premium
- CCL designation becomes cosmetic — having earned Core Conviction Leader status produces no capital advantage beyond what the CW-DAS score already captures
- A concentrated alpha mandate *requires* some amplification for established core positions

### Why Model A is the problem

Model A's current configuration:
- Delivers 4.31× more capital to VRT than ARW
- 3.00× of that gap is pure incumbency amplification
- r(composite, alloc) = 0.325 — allocation is only weakly correlated with current signal quality
- ARW, the #1 composite-scored candidate in the queue, receives $2,482 vs VRT's $10,687
- An operator cannot defend this from signals alone

---

## 2. The Elbow Analysis

The marginal gain from reducing CCL multiplier does **not** produce a classic elbow — gains accelerate continuously from 3.0 → 1.0. The elbow must therefore be defined by the "defensibility threshold": where does the VRT/ARW incumbency amplification reach a level that can be justified by the mandate?

```
CCL Mult → VRT/ARW ratio → Incumbency amplification over signal quality
 3.00  →  4.31×  →  3.00×    ← Not defensible
 2.50  →  3.59×  →  2.50×    ← Hard to defend
 2.00  →  2.87×  →  2.00×    ← Acceptable; "CCL deserves double"
 1.75  →  2.01×  →  1.40×    ← Near-optimal; minimal, defensible premium
 1.50  →  2.15×  →  1.50×    ← Acceptable (regression from E due to no HCA boost)
 1.00  →  1.44×  →  1.00×    ← Removes all incumbency reward
```

**The functional elbow is at CCL ≈ 1.75:** This is where the incumbency factor drops to 1.40× — meaning the system still rewards established conviction by 40% over signals alone, but the 3× structural inflation is eliminated.

Below 1.75, each additional unit of reduction becomes increasingly difficult to justify in a concentrated alpha context, because the CCL designation is delivering progressively less reward for what was designed to be the portfolio's most important tier distinction.

---

## 3. Why Model E (CCL=1.75, HCA=1.25) Is the Optimal Configuration

### Concentrated Alpha criterion

- Top-1 concentration = **18.2%** — the single most important position still receives nearly 1-in-5 dollars deployed
- CCL per-candidate premium = **4.2× avg HCA** — meaningful differentiation maintained
- VRT still receives **rank #1** and the largest single allocation in every run

✓ Concentrated alpha character preserved.

### Signal responsiveness criterion

- r(composite, alloc) = **0.534** — up from 0.325 in Model A (+64% improvement)
- r(CW-DAS, alloc) = **0.781** — CW-DAS score now strongly predicts allocation
- ARW allocation rises from $2,482 to **$2,996** — the top-signal candidate receives meaningful capital

✓ Allocation is now defensible from signals.

### Operator intuition criterion

- VRT/ARW = **2.01×** — an operator can explain this: "VRT is our CCL; it gets approximately double the capital of our best HCA candidate"
- The gap is no longer 4.31× which requires explaining three stacked layers of mechanism

✓ Ratio is intuitive and explainable.

### Why HCA=1.25 matters

Model E uses HCA=1.25 (vs HCA=1.00 in most other models). This lifts all HCA candidates proportionally, improving:
- r(composite, alloc) improves more than in Model F (1.50/1.00) because HCA candidates that have higher-quality signals benefit
- Capital diversification improves — HCA candidates collectively receive more capital per name
- The CCL-vs-HCA distinction narrows to a genuinely earned 4.2× premium (from 9.0×)

Model F (CCL=1.50, HCA=1.00) achieves similar VRT/ARW ratio (2.15×) but with r(comp,alloc)=0.510 vs Model E's 0.534 — Model E is slightly better on signal alignment at a similar VRT/ARW level.

---

## 4. Comparison to Mandate Criteria

**Mandate: "Reward conviction, but do not allow incumbency to dominate opportunity quality."**

| Criterion | Model A | Model E (proposed) | Verdict |
|-----------|---------|-------------------|---------|
| Rewards existing conviction | ✓✓ (4.31× VRT premium) | ✓ (2.01× VRT premium) | E maintains reward |
| Does not allow incumbency to dominate | ✗ (3.0× amplification) | ✓ (1.4× amplification) | E resolves the problem |
| Tracks current opportunity quality | ✗ (r=0.33) | ✓ (r=0.53) | +64% improvement |
| Maintains concentrated character | ✓✓ (32% top-1) | ✓ (18% top-1) | Slightly less extreme |
| Operator-explainable | ✗ | ✓ | Fully resolved |

---

## 5. Concrete Change Required

**If adopted, one configuration change:**

```python
# src/portfolio/deployment_planner.py
_CCL_CONVICTION_MULT: float = 1.75   # was 3.0
_HCA_CONVICTION_MULT: float = 1.25   # was 1.0
```

**No other changes required:**
- CW-DAS formula: unchanged
- CCL gate (weight ≥ 1.5%): unchanged
- Conviction point constants (CCL=35, HCA=28): unchanged
- Tier assignment logic: unchanged
- Ranking algorithm: unchanged
- Eligibility criteria: unchanged

Rank order in this specific run: **unchanged** — VRT remains rank 1, ARW remains rank 2 under all 7 models.

---

## 6. Impact on PAR-20260529-BAF83F16

| Metric | Current (Model A) | Proposed (Model E) | Change |
|--------|------------------|--------------------|--------|
| VRT allocation | $10,687 | $6,022 | −$4,665 (−43.7%) |
| ARW allocation | $2,482 | $2,996 | +$514 (+20.7%) |
| SNX allocation | $2,013 | $2,431 | +$418 (+20.8%) |
| VRT/ARW ratio | 4.31× | 2.01× | −2.30× |
| Top-1 concentration | 32.2% | 18.2% | −14.0 ppts |
| Top-5 concentration | 55.7% | 46.5% | −9.2 ppts |
| CCL capital share | 32.2% | 18.2% | −14.0 ppts |
| r(composite, alloc) | 0.325 | 0.534 | +0.209 |

---

## 7. Alternative Consideration: Model D (CCL=2.0, HCA=1.25)

If the operator prefers a less aggressive change from current, Model D is the next-best option:
- VRT/ARW = 2.30× (vs 2.01× in E) — slightly more concentrated
- r(comp,alloc) = 0.487 (vs 0.534 in E) — slightly less signal responsive
- Top-1 = 20.2% (vs 18.2% in E)

Model D is suitable if the operator wants to preserve stronger CCL concentration while still meaningfully reducing the incumbency amplification from 3.0× to 1.6×. It scores 32/50 vs 34/50 for Model E.

---

## 8. Rejected Options

**KEEP_CURRENT (Model A):** Rejected. The 4.31× VRT/ARW gap is not defensible from signals. r(composite, alloc) = 0.325 means allocation is predominantly incumbency-driven. This fails the mandate test directly.

**MAJOR_REDUCTION below CCL=1.5:** Produces diminishing returns on concentrated alpha character. Below CCL=1.5, the CCL tier distinction approaches cosmetic — producing only 3–4× per-candidate premium over HCA, which does not meaningfully differentiate a "Core Conviction Leader" from a "High Conviction Anchor."

**REMOVE_MULTIPLIER (Model G):** Rejected. Eliminates all incumbency reward. CCL designation becomes meaningless from a capital allocation standpoint. Conflicts with the concentrated alpha mandate.

---

## 9. Conclusion

The current multiplier structure (CCL=3.0, HCA=1.0) was designed to concentrate capital aggressively in established core positions. The evidence shows it over-concentrates relative to current signal quality: 300% of the VRT/ARW capital gap is pure incumbency amplification with zero connection to current market signals.

The proposed structure (CCL=1.75, HCA=1.25) reduces incumbency amplification from 3.0× to 1.4× while:
- Preserving CCL's capital priority (2.01× VRT premium vs 1.44× signal-only)
- Improving signal tracking by 64% (r from 0.325 to 0.534)
- Maintaining concentration character (18.2% top-1 allocation)
- Producing explainable operator-facing ratios

**This configuration best expresses: "Reward conviction, but do not allow incumbency to dominate opportunity quality."**
