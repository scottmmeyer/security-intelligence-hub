# Conviction Transparency Recommendation — Phase 7.5O
**Run:** PAR-20260529-BAF83F16 | **Date:** 2026-05-31  
**Scope:** Operator trust assessment — can operators currently explain the VRT vs ARW capital gap?

---

## 1. The Trust Question

> "Why did the system recommend $8,822 into VRT but only $2,049 into ARW?"

An operator looking at the current UI sees:
- VRT: rank #1, CW-DAS 95.53, Conviction 35/35, $8,822 recommended
- ARW: rank #2, CW-DAS 94.11, Conviction 28/35, $2,049 recommended

The current UI shows conviction component score numbers but does not explain:
1. Why VRT has 35/35 and ARW has 28/35
2. How conviction points translate to dollars allocated
3. That there is a second amplification layer (the 3× planner multiplier) independent of conviction points

---

## 2. Can Operators Currently Answer the Question?

| Question | Current UI | Answer Available? |
|----------|-----------|-------------------|
| Why is VRT rank 1? | CW-DAS breakdown shown | ✓ Partially — score visible |
| Why is VRT conviction 35 vs ARW 28? | CCL/HCA tier labels shown | ✗ No — tier label shown, no gate explanation |
| What is CCL vs HCA? | Not explained in UI | ✗ No |
| Why is VRT CCL but ARW HCA? | Not shown | ✗ No |
| Why does VRT get 4.31× more capital? | Not explained | ✗ No |
| Is the 3× planner multiplier documented? | Not visible to operator | ✗ No |

**Assessment: Operators cannot currently explain the allocation gap from UI alone.** They can observe that VRT has more conviction points, but cannot determine *why* or *how much of the capital gap this causes*.

---

## 3. Is the Behavior Intentional Concentrated Alpha Design?

**Yes.** The design is documented and intentional. Evidence:

### Evidence A: CW-DAS design document (`capital_deployment_queue_design.md`)
> "CCL=35, HCA=28: The 7-point CCL/HCA spread ensures that at any realistic position size difference (≤5%), CCL conviction will exceed HCA sizing advantage."

The design explicitly acknowledges that CCL conviction points override sizing headroom.

### Evidence B: Deployment planner design (`deployment_planner.py` docstring)
> "conviction_mult: CCL = 3.0, HCA = 1.0 (√rank decay concentrates priority capital in top-ranked positions)"

The 3× multiplier is not accidental — it is the mechanism by which the system **concentrates capital** in the highest-conviction tier.

### Evidence C: CCL gate design (`trim_intelligence.py`)
The 1.5% weight threshold for CCL is a deliberate quality signal: a holding must already have demonstrated commitment (via accumulated position size) before qualifying for the highest-conviction tier.

### Logical coherence of the design

The system's logic is internally consistent:
1. A holding that already commands 3.60% of the portfolio has proven its strategic importance through operator decisions over time
2. New entrants (like ARW at 0.92%) — however strong their signals — have not yet earned the "concentrated alpha" designation
3. The 3× planner multiplier then delivers disproportionate new capital to reinforce the position that has already been designated as the portfolio's core conviction

**This is the Concentrated Alpha philosophy operating exactly as designed.**

---

## 4. The Design Tension

The analysis reveals a genuine but intentional tension:

| Dimension | VRT | ARW | Winner |
|-----------|-----|-----|--------|
| Signal quality (composite) | 4.5556 | **4.8889** | ARW |
| ESS momentum | VERY_BULLISH | VERY_BULLISH | Tie |
| Replay support | ✓ | ✓ | Tie |
| Trim score (lower = better) | 1.62 | **0.41** | ARW |
| Portfolio weight | **3.60%** | 0.92% | VRT |
| Conviction tier | **CCL (35)** | HCA (28) | VRT |
| Capital recommended | **$8,822** | $2,049 | VRT |

ARW is objectively a higher-quality signal by multiple measures, yet receives 4.31× less capital. This is not a bug — it is the system preferring **concentration in established positions** over **signal-optimized rebalancing toward new entrants**.

An operator who understands this design would accept the outcome. An operator who does not understand it would reasonably question the ranking.

---

## 5. Recommendation

### VERDICT: ADD CONVICTION BREAKDOWN PANEL

**Rationale:** The current behavior is correct and intentional, but it is not explainable from the current UI. The operator trust test fails: an operator cannot answer "Why does VRT get $8,822 vs ARW's $2,049?" without reading source code.

The recommended panel does **not change any scores**. It adds visibility into:

1. **CCL gate explanation** — Which condition(s) separate CCL from HCA for each candidate
2. **Conviction tier label with threshold** — "CCL: all 5 gates passed (weight 3.60% ≥ 1.5%)"  vs "HCA: weight 0.92% < 1.5% CCL threshold"
3. **Planner weight formula** — "Deployment weight = 95.53 × 3.0 / √1 = 286.6 (CCL 3× priority multiplier)"
4. **Dollar allocation derivation** — "26.6% of $33,175 pool = $8,822"

### What the operator should be able to read

**For VRT:**
> *"CCL tier: weight 3.60% exceeds 1.5% threshold. Conviction = 35/35. Planner applies 3× CCL priority multiplier. Deployment weight = 95.53 × 3.0 / √1 = 286.6 (26.6% of pool). Allocation = $8,822."*

**For ARW:**
> *"HCA tier: weight 0.92% below 1.5% CCL threshold (needs +$2,754 to qualify). Conviction = 28/35. Planner applies 1× HCA multiplier. Deployment weight = 94.11 × 1.0 / √2 = 66.6 (6.2% of pool). Allocation = $2,049."*

---

## 6. Specific UI Addition Proposal

### Conviction Breakdown Panel (new panel in deployment queue breakdown row)

Placement: After the existing CW-DAS score breakdown (Signal/Replay/Conviction/Sizing/Momentum chips)

Content:

```
[ CCL TIER — CONCENTRATED ALPHA ]       (or [ HCA TIER ])

Tier gate:
  ✓ Signal = BULLISH                    ✓ Signal = BULLISH
  ✓ Replay supported                    ✓ Replay supported
  ✓ Composite 4.56 ≥ 4.0               ✓ Composite 4.89 ≥ 4.0
  ✓ Weight 3.60% ≥ 1.5% threshold      ✗ Weight 0.92% < 1.5% threshold
  ✓ Trim score 1.62 < 30               ✓ Trim score 0.41 < 30

Capital allocation:
  Score (95.53) × CCL mult (3.0) / √rank (1)  = weight 286.6
  286.6 / 1077.7 pool = 26.6% → $8,822

  Score (94.11) × HCA mult (1.0) / √rank (2)  = weight 66.6
  66.6 / 1077.7 pool = 6.2% → $2,049
```

---

## 7. Implementation Scope

This is a **VISIBILITY-ONLY** addition:
- No changes to `deployment_queue.py` (conviction constants, CW-DAS formula)
- No changes to `deployment_planner.py` (CCL mult, HCA mult, weight formula)
- No changes to `trim_intelligence.py` (CCL gate conditions)
- No changes to ranking or allocation amounts
- UI: `app.js` — add conviction breakdown panel to deployment queue breakdown row
- UI: `index.html` — add CSS for the new panel

Data already available in the breakdown row:
- `ov.narrative_tier` — tier label
- `ov.current_weight_pct` — weight (for CCL gate check)
- `ov.composite_score` — composite (for CCL gate check)
- `ov.trim_score` — trim (for CCL gate check)
- `ov.replay_supported` — replay (for CCL gate check)
- `ov.deployment_score` — CW-DAS score
- `ov.rank` — for planner weight formula

The 1.5% CCL threshold, CCL_MULT (3.0), and HCA_MULT (1.0) are compile-time constants that can be hardcoded in the UI panel or passed through the API.

---

## 8. Success Criteria for Phase 7.5P (if implemented)

After the conviction breakdown panel is added, an operator must be able to answer without external documentation:

- [ ] "Why does VRT receive 35/35 conviction points?" → CCL gate explanation visible
- [ ] "Why does ARW receive 28/35?" → Weight 0.92% < 1.5% threshold visible
- [ ] "How did $8,822 get calculated?" → Planner weight formula visible  
- [ ] "Would ARW get more capital if I added to it?" → CCL threshold and gap visible
- [ ] "Is this system concentrating capital in VRT because of its signal or because of its existing size?" → Both shown; operator can judge

---

## 9. Conclusion

The conviction scoring model is **sound and intentional**. The 4.31× capital advantage for VRT over ARW reflects:
1. VRT's proven position size (3.60% weight → CCL tier)
2. The Concentrated Alpha design philosophy (3× planner multiplier for CCL)
3. Rank 1 priority (no √rank decay)

The model is not rewarding incumbency inappropriately — it is rewarding **demonstrated accumulated conviction** via position size, which is a reasonable proxy for portfolio management intent.

However, **operators cannot currently distinguish between this intentional design and a system bug without reading source code.** The conviction breakdown panel makes the model's logic transparent, preserves all operator authority, and eliminates the trust gap without changing any scoring formula.

**Recommendation: ADD CONVICTION BREAKDOWN PANEL (Phase 7.5P, VISIBILITY-ONLY)**
