# Signal Capital Alignment Report
**Phase 7.5T — Pure Signal Capital Allocation Audit**
**Run:** PAR-20260601-9CFD7C63 | **Date:** June 1, 2026

---

## Executive Summary

Four allocation models were evaluated by blending CW-DAS deployment scores with Pure Signal Scores (PSS) at 0%, 20%, 40%, and 50% PSS weights. The analysis answers whether deploying capital more directly aligned with signal quality produces better, worse, or equivalent portfolio positioning.

**Core finding:** PSS integration measurably improves signal-quality alignment and replay evidence depth. However, Models C (40%) and D (50%) create a structural tier-bucket mismatch that the current deployment architecture was not designed to handle. Model B (20%) achieves meaningful alignment improvement without disrupting the CCL capital structure.

---

## Does PSS Integration Improve Capital Allocation?

**Answer: Yes — at 20% weight. Ambiguous — at 40%+.**

### Evidence for improvement (all models)

1. **Corr(alloc, PSS) improves at every increment:**
   - Model A: 0.273
   - Model B: 0.316 (+16%)
   - Model C: 0.489 (+79%)
   - Model D: 0.495 (+81%)
   Capital becomes meaningfully better aligned with underlying signal quality as PSS weight increases.

2. **Replay evidence quality improves dramatically:**
   - Model A: 58.9% of top-10 deployed capital backs THIN-evidence signals
   - Model B: 42.6% THIN (improved)
   - Model C/D: ~16% THIN (nearly eliminated)
   PSS rewards 261-day validated signals over 4-day current-recommendation signals.

3. **PCB (highest PSS in universe) moves from rank 12 to rank 3:**
   PCB was the most signal-underserved stock in the entire queue — its $805.66 baseline allocation does not reflect its quality. PSS integration materially corrects this.

4. **Corr(alloc, composite) remains stable:**
   Composite score alignment doesn't degrade — it stays flat at ~0.26 across all models, suggesting PSS integration does not sacrifice composite quality while improving signal depth.

### Evidence against improvement (at 40%+)

1. **ATLC takes rank 1 and receives the CCL allocation ($8,810):**
   ATLC was never evaluated under the CCL gate. It did not need to satisfy:
   - current_weight ≥ 1.5% (ATLC holds only 0.90%, below threshold)
   - high_conviction_designation review
   - CCL narrative validation
   Assigning CCL-level capital ($8,810, 26.6% of pool) to a stock that never cleared the CCL gate is a framework integrity concern, not an improvement.

2. **VRT loses 87.9% of its allocation in one step:**
   The A→C cliff for VRT ($8,811 → $1,169) is not a gradual recalibration. It is an abrupt displacement of the framework's most carefully constructed position. If the CCL designation reflects genuine conviction, this displacement is a cost, not a benefit.

3. **Corr(alloc, cur_weight) sign-flips to negative at 40%+:**
   This is not inherently bad — it could represent healthy rotation toward underweighted signal leaders. But it is a behavioral inversion from the design intent of the CW-DAS framework (which deliberately reinforces high-conviction existing positions). The framework would be operating against its own conviction logic.

---

## Does PSS Integration Introduce Instability?

**Answer: Yes — specifically at the 40% threshold.**

### Stability profile by model

| Model | Top-10 rank changes vs A | Max single rank change | VRT position |
|-------|--------------------------|----------------------|-------------|
| B | 13 symbols shifted | 5 (ATLC +2 net of B) | Stable (rank 1) |
| C | 18 symbols shifted | 14 (SANM -10) | Unstable (rank 1→6) |
| D | 19 symbols shifted | 14 (SANM -11) | Unstable (rank 1→7) |

Model B produces stable adjustments — no symbol shifts more than 5 positions, and the CCL structure remains intact. Model C produces a non-linear instability event: VRT falls 5 positions and ATLC jumps to rank 1 in a single threshold crossing.

The instability is not random — it reflects a meaningful structural tension (CCL vs signal quality). But instability at the rank-1 allocation slot is consequential because the allocation curve is highly concave: the gap between rank 1 ($8,810) and rank 2 ($2,047) is larger than the sum of ranks 15–31 allocation differences combined.

---

## Does PSS Integration Materially Change Rankings?

**Answer: Yes at both 20% and 40%, but in different ways.**

### At 20% (Model B)

Material changes:
- ATLC: +2 (rank 4 → 2)
- AVT: +3 (rank 7 → 4)
- PCB: +5 (rank 12 → 7)
- SNX: -5 (rank 3 → 8)
- PSX: -4 (rank 5 → 9)

These are meaningful reorderings but VRT's top position is preserved. The changes reflect genuine signal-quality differentiation without disrupting the CCL-level capital structure.

### At 40% (Model C)

Material changes:
- ATLC: +3 → rank 1 (CCL-level capital assigned to HCA stock)
- VRT: -5 → rank 6 (CCL stock demoted below CCL allocation threshold)
- PCB: +9 → rank 3
- SANM: -10 → rank 21
- SNX: -5 → rank 8

These are structural ranking inversions. The signal-quality leaders now govern the queue rather than the conviction-tier leaders.

---

## Does PSS Integration Create Unintended Consequences?

**Four unintended consequences identified:**

### 1. Tier-bucket mismatch (Models C, D)
The deployment plan was designed around a two-bucket structure: Tier 1 (CCL, ~$8,810) and Tier 2 (HCA, ~$940–$2,047). In Models C and D, the Tier 1 bucket is populated by ATLC — an HCA stock. This means the capital concentration designed for a CCL position flows to a stock that was never designated CCL, never cleared the CCL gate's position-size requirement, and would be under-concentrated at 0.90% current weight. Deploying $8,810 into ATLC would take it from 0.90% to ~2.77% of portfolio — effectively self-constructing a CCL-like position through signal-driven capital, not through the CCL policy process.

### 2. Replay evidence double-counting risk
PSS includes a replay component (0–20 pts) in the pure signal score. CW-DAS also includes a replay component. Blending PSS with CW-DAS thus partially double-counts replay support — stocks that have replay support get credit in both the CW-DAS signal component and the PSS input. This is a second-order effect, but it means replay evidence is slightly over-weighted in the blend vs. the stated weights.

### 3. CCL logic inversion
The CCL gate requires `current_weight ≥ 1.5%`. This threshold is partially a portfolio construction rule — it ensures CCL-level capital deployment goes into positions where the portfolio already has meaningful conviction exposure. PSS integration bypasses this logic entirely. A stock can receive CCL-level capital without ever having satisfied the size-threshold part of the CCL gate. This undermines the intent of the CCL policy.

### 4. Excessive convergence of Models C and D
The top-5 ranking is identical between Models C and D. The incremental shift from 60/40 to 50/50 produces minimal additional change. This means there is a saturation point at ~40% PSS weight beyond which increasing PSS weight adds no further signal diversity — it only increases instability for the CCL capital bucket without corresponding benefit.

---

## Alignment Assessment Summary

| Assessment Dimension | Model A | Model B | Model C | Model D |
|---------------------|---------|---------|---------|---------|
| Signal quality alignment | Baseline | ✅ Improved | ✅ Strongly improved | ✅ Strongly improved |
| Replay evidence quality | ⚠️ Thin-biased | ✅ Balanced | ✅ Strong-dominant | ✅ Strong-dominant |
| CCL tier integrity | ✅ Intact | ✅ Intact | ❌ Mismatch | ❌ Mismatch |
| Ranking stability | ✅ Stable | ✅ Stable | ⚠️ Non-linear | ⚠️ Non-linear |
| Composite correlation | Baseline | ≈ Equal | ≈ Equal | ≈ Equal |
| Weight-correlation behavior | Reinforcing | Reinforcing | ⚠️ Inverted | ⚠️ Inverted |
| Unintended consequences | None | 1 minor | 3 significant | 3 significant |

**Overall: Model B achieves the best balance.** It captures most of the signal-quality alignment improvement while avoiding the structural tier-bucket mismatch and ranking instability of Models C and D.
