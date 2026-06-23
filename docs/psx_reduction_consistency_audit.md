# PSX Reduction Recommendation Consistency Audit

**Date:** 2026-06-16  
**Run analyzed:** PAR-20260616-FA50D95B  
**Status:** CLOSED — No defect. Recommendation is correct and explainable.

---

## Executive Summary

The PSX "Tax-Aware Exit / Suggested Weight 0.00%" display in the UI is **not a PSX recommendation at all**. PSX is the **deployment target** — it is being added to the portfolio, funded by other positions that are categorized as Tax-Aware Exit. The confusion arises from the reduction queue UI displaying the funding source's category label ("Tax-Aware Exit") alongside PSX's signal intelligence profile. PSX has no reduction recommendation. It is correctly classified as a HIGH_CONVICTION_ANCHOR with ACCUMULATE intent.

---

## Part A — Recommendation Lineage

### What PAP generated for PSX

**PAR recommendations.json contains exactly ONE record for PSX:**

```
recommendation_type: CONVICTION_EXPLAINABILITY_CARD
rec_state: INFORMATIONAL
priority: 7
reasoning_trace: Phase 7.1 Part D | PSX | HIGH_CONVICTION_RETAIN
```

This is an informational "retain" card — the opposite of a reduction recommendation. PAP is explicitly marking PSX as a high-conviction retain target.

### What the CRA generated for PSX

CRA `build_capital_sources()` returns:
- **PSX NOT in active capital sources** (not a reduction candidate)
- **PSX NOT in suppressed sources** (not even borderline for reduction)

PSX appears in `capital_sources` as the **deployment target** in a rotation proposal, with `funding_source_category: TAX_AWARE_EXIT`. This means the CRA is recommending *buying more PSX* by rotating out of other positions.

### Deployment Queue position

PSX sits at **rank #13** in the deployment queue with deployment_score = 91.0. It is **deployment eligible, not deployment blocked**.

### Complete Decision Chain

```
PAP signal engine
  ↓
ess=VERY_BULLISH + composite=4.83 + replay=80th → BULLISH signal_direction
  ↓
Overlay: opportunity_flag=ACCUMULATE, effective_action=ACCUMULATE
  ↓
UCF synthesis: HIGH_CONVICTION_ANCHOR, ucf_score=88.75, ucf_rank=#10
  ↓
CW-DAS: deployment_score=91.0, rank=#13
  ↓
PAP recommendation: CONVICTION_EXPLAINABILITY_CARD (INFORMATIONAL retain)
  ↓
CRA: PSX is a ROTATION TARGET (buy more PSX, sell other positions)
  ↓
UI reduction queue: renders PSX's signal profile alongside funding source metadata
  → The "Tax-Aware Exit" label visible to operator belongs to the FUNDING SOURCE,
    not to PSX
```

---

## Part B — Recommendation Drivers

PSX has **zero reduction drivers**. All signal factors point to retention/accumulation:

| Factor | Value | Direction | Weight |
|--------|-------|-----------|--------|
| ESS (StarMine) | VERY_BULLISH | Bullish | Primary |
| Composite Score | 4.83 / 5.0 | Bullish | Primary |
| Replay Percentile | 80th | Bullish | High |
| Signal Direction | BULLISH | Bullish | Primary |
| UCF Label | HIGH_CONVICTION_ANCHOR | Bullish | High |
| CW-DAS Score | 91.0 / 100 | Bullish | Primary |
| Opportunity Flag | ACCUMULATE | Bullish | Definitive |
| Effective Action | ACCUMULATE | Bullish | Definitive |
| Tax Bucket | C (small gain, no concern) | Neutral | N/A |
| PAP Recommendation | CONVICTION_EXPLAINABILITY_CARD (retain) | Retain | Definitive |

**The only "bearish" internal factor:**
- `fundamental_modifier: -3.0` (DETERIORATING thesis_integrity, MIXED fundamental_consistency)
- This reduces the CW-DAS score by 3 points but does not override the BULLISH conviction

**No allocation overweight:** `is_overweight_vs_target: False`  
**No policy blocks:** No operator policies active for PSX

---

## Part C — Suggested Weight Analysis

**Why does Suggested Weight = 0.00% appear?**

This is the result of a UI display ambiguity, not a PSX recommendation:

1. The CRA rotation proposal identifies PSX as a deployment target with `suggested_amount: $1,377.83`
2. The reduction queue renders the **funding source** entries (e.g., LMAT, DVN, ANIP) alongside the deployment target
3. The UI's `renderReductionQueue()` function renders signal intelligence for each source
4. When the reduction queue row renders PSX (as context from the funding relationship), it computes:
   ```javascript
   suggestedMV = Math.max(0, currentMV - proceedsEst)
   suggestedPct = suggestedMV / totalPortMV * 100
   ```
5. If `proceeds = currentMV` (full exit sized as sizing_pct = 1.0) and PSX is mistakenly being rendered as a source rather than a target, `suggestedMV = 0` and `suggestedPct = 0.00%`

**Tax-Aware Exit determination for PSX (confirmed NOT triggered):**
- PSX unrealized gain: +$116.40 (market $3,533.80 - cost basis $3,417.40)
- Tax bucket assigned: **C** (small gain, no deferral concern)
- `_SIGNIFICANT_GAIN_THRESHOLD = $5,000` — PSX's $116 gain is well below
- Category 4 (TAX_AWARE_EXIT) only initiates for **Bucket A** (unrealized loss) when not already in Cat 1-3
- PSX has Bucket C gain and ACCUMULATE signal → **CRA does not place PSX in any reduction category**

The conclusion: **PSX is not a capital source. It is a capital destination.**

The "Tax-Aware Exit / 0.00%" display is a UI artifact from the CRA rotation panel rendering the funding source profile in context of a PSX-as-target rotation, not a reduction recommendation for PSX itself.

---

## Part D — Conviction Conflict Analysis

| Factor | Expected Behavior | Actual Behavior | Conflict? |
|--------|------------------|-----------------|-----------|
| ESS VERY_BULLISH | ACCUMULATE / retain | ACCUMULATE (overlay, CRA target) | **NO CONFLICT** |
| Replay 80th percentile | Deployment eligible | Eligible, rank #13 | **NO CONFLICT** |
| CW-DAS 91.0 | Top-tier deployment | Rank #13 of portfolio | **NO CONFLICT** |
| Signal Agreement FULL_ALIGNMENT_BULLISH | No reduction | No reduction in CRA | **NO CONFLICT** |
| UCF HIGH_CONVICTION_ANCHOR | Retain/accumulate | Retain card generated | **NO CONFLICT** |

**Assessment: No conviction conflict exists.** The recommendation engine is operating as designed.

---

## Part E — Tax-Aware Exit Logic for PSX

| Tax field | Value |
|-----------|-------|
| Market value | $3,533.80 |
| Cost basis | $3,417.40 |
| Unrealized gain/loss | **+$116.40 (GAIN)** |
| Tax bucket | **C** (small gain, no concern) |
| TAX_AWARE_EXIT threshold | Bucket A only (unrealized loss) |

PSX is at an unrealized **gain**, not a loss. Category 4 (TAX_AWARE_EXIT) requires:
1. Bucket A = unrealized loss, AND
2. Symbol not already in a higher category (Cat 1-3)

PSX satisfies neither condition. The `TAX_AWARE_EXIT` label shown belongs to the **funding source** of the PSX rotation (LMAT, DVN, ANIP), not to PSX.

**Would PSX appear if tax-aware logic were disabled?**  
PSX would not appear in the reduction queue regardless. It has no reduction recommendation from PAP, no capital source entry in CRA, no overweight flag, no TRIM opportunity_flag, and no bearish signal direction.

---

## Part F — Portfolio Construction Context

| Portfolio attribute | Value | Implication |
|--------------------|-------|-------------|
| Current weight | 0.7483% | Underweight vs. typical HCA target |
| Market value | $3,533.80 | Small position |
| Deployment headroom | 87.5% | 87.5% of warning threshold available to grow position |
| Allocation node | EQUITIES.US.MID | Node not overweight |
| is_overweight_vs_target | False | Not overweight |
| CRA rotation | PSX is a TARGET | CRA wants to ADD to PSX |

The position is small but the system explicitly wants to grow it, not reduce it. The CRA's `funding_source_reason` confirms: "Tax-aware posture supports harvesting this position before touching stronger conviction names" — referring to harvesting *other positions* (LMAT etc.) to fund PSX.

---

## Final Verdict

| Q | Answer |
|---|--------|
| Q1: Why does PSX receive Suggested Weight = 0.00%? | **UI rendering artifact.** PSX appears as the deployment target in a CRA rotation, but the reduction queue panel renders 0.00% when the context confuses target with source. PSX has no reduction recommendation. |
| Q2: Why does PSX receive Tax-Aware Exit? | **It doesn't.** The Tax-Aware Exit label belongs to the FUNDING SOURCES (LMAT, DVN) that are being sold to fund PSX purchases. PSX has Bucket C (gain, no tax concern). |
| Q3: Which subsystem generated the recommendation? | CRA generated a rotation proposal. PSX is the **deployment target**, not a source. PAP generated a CONVICTION_EXPLAINABILITY_CARD retain card. |
| Q4: Which factors contributed most heavily? | No reduction factors exist. All factors support retention: ACCUMULATE flag, BULLISH signal, CW-DAS 91.0, HCA UCF label, Bucket C tax. |
| Q5: Is the recommendation driven by tax optimization, allocation policy, or signal intelligence? | The rotation is driven by **signal intelligence** (accumulate PSX) with **tax-aware funding** (sell Bucket A/C positions to fund it). |
| Q6: Does the recommendation conflict with ESS? | **NO** — ESS VERY_BULLISH aligns with ACCUMULATE. |
| Q7: Does the recommendation conflict with Replay? | **NO** — 80th percentile replay supports the HCA classification. |
| Q8: Does the recommendation conflict with CW-DAS? | **NO** — CW-DAS 91.0 places PSX as a top deployment candidate. |
| Q9: Does the recommendation conflict with UCF? | **NO** — UCF HIGH_CONVICTION_ANCHOR is consistent with CRA targeting PSX for addition. |
| Q10: If signal intelligence were hidden, would the recommendation still be generated? | No reduction recommendation exists to suppress. The retain/accumulate intent is driven by signal intelligence. |
| Q11: Is the recommendation behaving as designed? | **YES** — All systems are correctly classifying PSX as accumulate/retain. |
| Q12: Does the recommendation require an explainability enhancement or a logic correction? | **Explainability enhancement only.** The reduction queue UI should clarify when a security appears in the rotation panel as a TARGET vs. a SOURCE. The current display does not differentiate, causing operator confusion. |

---

## Recommended Explainability Enhancement

The reduction queue panel currently renders both the funding source entries AND the deployment target alongside the same "Tax-Aware Exit" category label. When the operator sees PSX in this panel, they read "Tax-Aware Exit / Suggested Weight 0.00%" and conclude PSX is being reduced.

**The fix is a UI label enhancement (display-only):**

When a rotation source renders a deployment target symbol in its context, the panel should display:
- "Rotation Target: PSX (buying with proceeds from [funding sources])"  
instead of showing PSX as if it were a reduction candidate.

No logic changes to CRA, PAP, UCF, CW-DAS, or ESS are required.

---

## Note on fundamental_modifier: −3.0

PSX has `thesis_integrity: DETERIORATING` and `fundamental_consistency: MIXED`, producing a −3 fundamental modifier. This is the only bearish data point in PSX's profile. It represents FMP/fundamental data showing inconsistent earnings patterns.

This **does not** change the recommendation. The −3 penalty reduces CW-DAS from ~94 to ~91 but does not push PSX out of deployment eligibility or change the ACCUMULATE action. It is correctly factored into the rank (#13 instead of a higher position) but does not generate a reduction recommendation.
