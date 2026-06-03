# Pure Signal Integration Recommendation
**Phase 7.5T — Pure Signal Capital Allocation Audit**
**Run:** PAR-20260601-9CFD7C63 | **Date:** June 1, 2026

---

## Recommendation

### **B. ADD_MINOR_SIGNAL_WEIGHT**

Introduce a 20% Pure Signal Score component into the deployment allocation blended score, reducing CW-DAS weight from 100% to 80%.

**This is not a code change recommendation.** This is an analytical recommendation to inform any future scoring review. No code modifications are made in this phase.

---

## Evidence Summary

### The Case for Adding Signal Weight (vs. Model A)

1. **Corr(allocation, PSS) improves +16% at 20% weight.** Capital becomes meaningfully better aligned with the cross-validated signal quality of each position. The improvement is measurable, not marginal.

2. **Replay evidence depth improves in the top-5 deployed pool.** Model A deploys 58.9% of top-10 capital into THIN (4-day) replay signals. Model B reduces this to 42.6%. The rebalancing is gradual and does not disrupt the ranking structure.

3. **Three meaningful rank corrections occur without structural disruption:**
   - ATLC: rank 4 → 2 (+$609 more capital)
   - AVT: rank 7 → 4 (+$366 more capital)
   - PCB: rank 12 → 7 (+$265 more capital)
   All three are stocks that Phase 7.5S identified as underserved relative to their signal quality. PSS integration partially corrects each without requiring code changes.

4. **Composite score alignment is preserved.** Corr(alloc, composite) remains flat (0.255 → 0.245) — the improvement in signal alignment does not sacrifice composite quality tracking.

5. **The CCL capital structure is fully intact.** VRT retains rank 1 and the $8,810.94 CCL-level allocation in Model B. The CCL gate logic, tier-bucket structure, and position-size reinforcement behavior are undisturbed. PSS at 20% is a minor calibration adjustment, not a structural override.

---

### Why Not Model C (40%) or Model D (50%)

1. **ATLC receives CCL-level capital without clearing the CCL gate.** At 40%+ PSS weight, ATLC jumps to rank 1 with $8,810 — a capital assignment designed for CCL-designated stocks. ATLC holds 0.90% current weight, below the CCL gate threshold of 1.5%. Deploying the CCL allocation bucket to an HCA stock bypasses the portfolio construction logic embedded in the CCL policy.

2. **VRT loses 87.9% of its allocation in a single threshold crossing.** The rank-1 allocation gap ($8,810 vs $2,047 at rank 2) means VRT either holds its full CCL capital or loses $7,740 in a single step. This is not a smooth recalibration — it is a disruptive displacement of the portfolio's designated highest-conviction position.

3. **Corr(alloc, current_weight) inverts.** At 40%+, the framework begins systematically allocating more capital to positions held in smaller amounts. While this could reflect healthy rotation, it directly contradicts the design intent of the CW-DAS sizing component, which deliberately rewards positions with headroom from smaller starting sizes. The framework would be working against its own conviction-size reinforcement logic.

4. **Models C and D are effectively identical.** The top-5 is unchanged between 40% and 50% PSS weight. There is no marginal gain from D over C — only additional instability in edge positions. The saturation point is reached at ~40%.

---

### Why Not Model D (50%) — Additional Concern

Model D creates the most extreme allocation reshaping while providing the least marginal improvement over Model C. All four unintended consequences identified in the signal_capital_alignment_report.md are present in their maximum form:
- Tier-bucket mismatch (ATLC at CCL-level capital)
- CCL logic inversion (size-threshold precondition bypassed)
- Replay double-counting (amplified at 50%)
- Convergence saturation (no gain over C)

Model D would represent a de facto policy decision to abandon the CCL structure in favor of pure signal ranking. That is a legitimate portfolio construction choice, but it is not a minor scoring adjustment — it is a full conviction framework redesign.

---

### Why Not Model A (Keep CW-DAS Only)

The findings of Phase 7.5S and 7.5T both indicate that the current framework produces measurable alignment gaps:
- PCB (PSR #1) is funded at rank 12
- SANM (PSR #35) is funded at rank 11
- THIN-evidence stocks receive the same replay bonus as STRONG-evidence stocks

These gaps are structural, not random. They arise from deliberate design choices (CCL conviction multiplier, flat replay bonus, current-weight CCL gate) that over-reward position size history and under-reward signal quality depth. Remaining at Model A means accepting these gaps indefinitely. Model B addresses them partially without requiring a framework redesign.

---

## Implementation Guidance (for Future Scoring Review)

If Model B is adopted in a future scoring review:

### Blended Score Formula
$$\text{blend} = 0.80 \cdot \text{norm\_cwdas} + 0.20 \cdot \text{norm\_pss}$$

Where:
- `norm_cwdas` = (CW-DAS − cwdas_min) / cwdas_range × 100
- `norm_pss` = (PSS − pss_min) / pss_range × 100

### Normalization anchors (recalibrate each cycle)
These should be recalculated per run to reflect the actual queue distribution:
- `cwdas_min/max`: min and max CW-DAS score in the current 42-candidate queue
- `pss_min/max`: min and max PSS score in the current 42-candidate queue

### What this changes
- Deployment ranking sequence (re-sorted by blend, not raw CW-DAS)
- Capital allocation per symbol (follows new rank sequence)
- CCL tier designation is **not changed** (VRT retains CCL, rank 1 at ~20% PSS)

### What this does NOT change
- CW-DAS formula components (signal, replay, conviction, sizing, momentum, penalties)
- CCL gate conditions
- PSS calculation methodology
- Any code in the scoring pipeline

---

## Sensitivity Note: The 28–32% Threshold

Model B (20%) is clearly safe. Model C (40%) clearly crosses the instability threshold. The exact point at which ATLC overtakes VRT for rank 1 is approximately 28–32% PSS weight. Any future consideration of weights in the 25–35% range should be tested carefully — the transition is non-linear and a small change in PSS weight produces a large change in the rank-1 allocation assignment.

---

## Decision Table

| Question | Answer |
|---------|--------|
| Does PSS integration improve capital allocation? | Yes, at 20% weight |
| Does it introduce instability? | Not at 20%; yes at 40%+ |
| Does it materially change rankings? | Meaningfully at 20%, structurally at 40%+ |
| Does it create unintended consequences? | One minor at 20% (replay double-count); three significant at 40%+ |
| Does ATLC or PCB deserve more capital? | Yes — both are underserved in Model A |
| Does VRT deserve less capital? | Partially — but not via CCL-structure displacement |
| Should code changes be made now? | No — analysis phase only |

---

## Final Verdict

**B. ADD_MINOR_SIGNAL_WEIGHT**

A 20% Pure Signal Score blend achieves the goal of better aligning deployment capital with signal quality while preserving the conviction framework architecture. It is the only model that:

1. Improves corr(alloc, PSS) materially (+16%)
2. Improves top-10 replay evidence depth (THIN share drops from 58.9% to 42.6%)
3. Partially corrects the three most signal-underserved positions (ATLC, AVT, PCB)
4. Preserves VRT rank 1 and the CCL capital structure
5. Avoids tier-bucket mismatch
6. Avoids correlation sign-flip
7. Keeps all 4 unintended consequences at "minor" level

This recommendation does not require action in the current deployment cycle. It should be documented as a scoring review candidate for the next framework calibration session.
