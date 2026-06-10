# Action Ranking Architecture Assessment

**Date:** 2026-06-09  
**PAR:** PAR-20260609-87134CE1

---

## Q1. Is the current Top 10 actually a "Top 10 Buy" list?

**YES. Definitively.**

The "Recommended Actions — Top 10" is:
1. Populated exclusively from the CW-DAS Capital Deployment Queue
2. The DQ admits only holdings with `signal_direction == BULLISH`, `replay_supported == True`, `strategic_classification == HIGH_CONVICTION_RETAIN`, and `narrative_tier in {CCL, HCA}`
3. The UI hardcodes the action label as `"BUY"` in `_daRenderActionCards()`
4. No code path exists to render TRIM, SELL, REDUCE, or ROTATE actions in the Top 10

This is not an edge case. It is the structural design of the system. The current "Top 10" is a "Top 10 Buys" list in every functional sense.

---

## Q2. Is this intentional architecture or accidental behavior?

**Intentional by component design; potentially accidental at the product level.**

At the component level:
- The CW-DAS was explicitly designed as a "conviction-weighted deployment attractiveness score" — its purpose is capital deployment (buys)
- The eligibility gate `signal_direction == BULLISH` was a deliberate design decision (see `_is_eligible()` docstring and comments)
- The DQ and deployment plan were named "deployment" because deployment = capital allocation = buys

At the product/UI level:
- The label "Recommended Actions — Top 10" implies a comprehensive priority view of all portfolio actions
- No disclaimer or scope note accompanies the Top 10 to indicate it is buy-only
- The PAP, CRA, and ESS surfaces that contain sell/trim actions are presented as separate panels with no unified ranking visible to the operator

**Assessment:** The buy-only DQ was an intentional component decision. The presentation of it as "Recommended Actions" without qualification was a product-level framing decision that creates a trust gap: the operator sees "top actions" and may assume it is comprehensive.

---

## Q3. If a sell action becomes the highest-value portfolio action, can it appear in Top 10 today?

**NO.** Under the current architecture, no sell, trim, or reduction action can appear in the Top 10 under any circumstances, including:
- When a BEARISH position has the highest RPS in the portfolio (TSLA RPS=85)
- When an overweight node is severely misaligned
- When a position is a tax-loss candidate with meaningful proceeds
- When the REDUCE_OVERWEIGHT recommendation is EXECUTABLE (no policy constraint)

The structural gate is the DQ eligibility requirement `signal_direction == BULLISH`. A BEARISH holding is permanently excluded from the DQ and therefore from the Top 10, regardless of how urgent its reduction priority score is.

---

## Q4. If not, should it?

**This is a product design question, not a data question. But the data supports consideration.**

Arguments for including sell actions in Top 10 (or a unified view):
- TSLA at RPS=85 is the highest-urgency single-position action in the portfolio — more urgent than the marginal improvement from adding ARW vs ATLC (both score 96-97)
- The portfolio has a REDUCE_OVERWEIGHT alert on EQUITIES.INTERNATIONAL at +5.9% drift — a material allocation deviation. None of the execution actions for this appear in the Top 10.
- KGC at RPS=42 is a legitimate reduction candidate that is not visible in any prioritized operator surface
- The allocation intelligence section shows overweight alerts, but does not surface them as ranked actions

Arguments against:
- Buy and sell actions are fundamentally different in operator intent, risk, and process
- Mixing buy scores (CW-DAS) and sell scores (RPS) on the same scale requires normalization that doesn't currently exist and could be misleading if poorly calibrated
- Portfolio managers often think in separate "buy list" and "sell list" mental models

**Recommendation:** The operator should be able to access a unified priority view. But this requires explicit design — not just merging the two lists.

---

## Q5. Does the current design overemphasize deployment while underemphasizing rotation?

**YES, structurally.**

**Evidence:**

1. **The most prominent operator-facing action surface (Top 10) is 100% buy actions** regardless of the portfolio's current overweight state or reduction urgency.

2. **All 14 sell-side actions in the current PAR are BLOCKED or DEFERRED:**
   - REDUCE_OVERWEIGHT for EQUITIES.US.MEGA.ULTRA_MEGA: BLOCKED (TSLA DO_NOT_SELL)
   - REDUCE_OVERWEIGHT for EQUITIES.INTERNATIONAL: DEFERRED (DODFX SELL_LAST)
   - Net executable sell-context recs: **0**

3. **The CRA capital pool ($96,633) is only visible in the CRA panel**, which is a separate panel lower on the page, not integrated into the Top 10 or main action priority view.

4. **The portfolio has a 5.9pp overweight in EQUITIES.INTERNATIONAL** — a moderate-severity allocation deviation that triggers a recommendation but generates zero entries in the Top 10.

5. **CW-DAS formula structure:** The formula's positive components (signal + replay + conviction + sizing + momentum + fund_mod) can generate scores up to ~103. The negative components (redundancy_pen + conc_pen) reduce scores for overweight positions but do not flip them to "reduction recommended." A holding in an overweight node gets a 15-point penalty but a VERY_BULLISH CCL can still score 80+.

**Conclusion:** The system is architecturally optimized for deployment discovery. Reduction and rotation are second-class actions — they are computed and surfaced, but not ranked alongside buys in the primary operator view.

---

## Structural Root Cause

The SIH was built with strong, well-designed buy-side scoring (CW-DAS) and a separate, also well-designed sell-side scoring system (RPS). These were developed as components serving different surfaces:
- CW-DAS → Deployment Queue → Top 10
- RPS → REDUCE_OVERWEIGHT drilldowns → PAP

The product surface never combined them. This is not a bug — it is a design boundary. But that boundary means the operator's primary action view is incomplete.

---

## Key Finding: GTX Appears in Both Lists

GTX is an unusual case: it appears at **#20 in the buy queue (CW-DAS 86.11)** AND at **#13 in the reduction list (RPS 2)**. This is because:
- GTX is CCL tier, VERY_BULLISH, replay-supported → legitimate buy candidate
- GTX is also in the REDUCE_OVERWEIGHT rec for EQUITIES.INTERNATIONAL → included in reduction context

The system's multi-symbol recommendation design creates this ambiguity: a strong individual signal (bullish, high conviction) and an allocation-level action (reduce the overweight node) conflict. The system surfaces both but provides no unified resolution.
