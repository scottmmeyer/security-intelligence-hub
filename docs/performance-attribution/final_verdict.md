# PERFORMANCE ATTRIBUTION — FINAL VERDICT
**Date:** 2026-06-12
**Issue:** #50 PERFORMANCE-ATTRIBUTION-01
**Governance:** Display-only — no impact on scoring, recommendations, or execution logic

---

## Q1: Should Fidelity remain the source of truth for portfolio returns?

**YES. Fidelity should remain the source of truth for 3M, YTD, 1Y, 3Y, 5Y, and since-inception returns.**

**Rationale:**
- Fidelity's time-weighted return calculations correctly handle cash flows, dividends, and corporate actions
- The Fidelity Performance tab already provides 1Y, 3Y, 5Y, YTD figures
- Computing these independently would require daily snapshots SIH has not yet accumulated (21-day PAR history is insufficient for anything beyond 1M)
- Replacing Fidelity return figures is unnecessary — the operator already has them; SIH's job is to *explain* them, not replicate them

**For 1D, 5D, 1M:** SIH can compute adequate approximations from existing holdings weights and price context.

**Hybrid approach:**
- 1D/5D/1M: SIH-computed (automated, already feasible)
- 3M/YTD/1Y+: Fidelity-reported (operator entry or CSV import)

---

## Q2: Can SIH perform attribution without replacing Fidelity calculations?

**YES.**

**Rationale:**
- The attribution question is not "what was the return?" — Fidelity answers that
- The attribution question is "why was the return what it was?" — only SIH can answer that using conviction data, CW-DAS scores, and recommendation history
- Brinson-style contribution analysis (Weight × Return) answers the "why" using data SIH already has
- SIH adds unique value that Fidelity cannot provide: connecting returns to *conviction decisions*, *ESS signals*, and *SIH recommendations*

**Unique SIH attribution advantage:**
```
"VRT contributed +0.42% to 1M return.
SIH deployed capital into VRT at PAR-20260601 (rank #1, CCL tier, CW-DAS 8.74).
Return since SIH deployment: +32.2%."
```

This attribution narrative is not available anywhere else.

---

## Q3: What benchmark architecture is recommended?

**Phase 1:** S&P 500 (SPY) as primary, US Total Market (VTI) as secondary, ACWI as international reference.

**Rationale:**
- All three are free via yfinance (no new infrastructure required)
- S&P 500 matches operator mental model and Fidelity's default benchmark
- VTI better captures mid-cap exposure that Concentrated Alpha intentionally holds
- ACWI provides context for international allocation decisions

**Phase 2:** Custom Concentrated Alpha benchmark blending SPY + Russell Mid + ACWX at mandate target weights. Defer until mandate is formally quantified.

**Not recommended:** Blended dynamic benchmark (creates moving target, undermines operator intuition development).

---

## Q4: How should Concentrated Alpha performance be measured?

Measure it in layers:
- holding contribution = weight × security return
- decision lineage = whether the position came from SIH recommendation, PAP deployment, or reduction retention
- benchmark-relative alpha = portfolio return minus benchmark return
- conviction quality = whether higher-conviction tiers systematically contribute more than they detract

The key question is whether high-conviction capital deployment produces persistent positive contribution relative to the chosen benchmark.

## Q5: Is PERFORMANCE-ATTRIBUTION-01 justified as the next major SIH initiative?

**YES — justified and well-scoped.**

**Evidence supporting justification:**
1. Live portfolio data confirms the need: Portfolio 1M -1.46% vs S&P -1.65% → +0.19% alpha. SIH cannot currently explain *why*.
2. Cost basis is present in every PAR — trade attribution is feasible with current data
3. `price_context_by_symbol` already fetches 1D/5D/1M returns for all holdings — contribution analysis requires only weight multiplication
4. yfinance benchmark fetch requires adding 3 ticker symbols — trivial extension
5. The implementation leverages exclusively existing infrastructure — no new data providers, no new ingestion pipelines for Phase 1

**Phase 1 is low-effort, high-impact.** The entire computation relies on data SIH already collects.

---

## Q6: Recommended Implementation Sequence

### Next 3 Implementation Sessions

**1. PRA-IMPL-02 — Funding Source Surface**
- Highest trade execution ROI
- Backend already done; UI surface is ~2-3 hours
- Directly impacts every future deployment decision

**2. AI-003 — Allocation Philosophy Explainability**
- ~30-60 minutes of UI work (move existing HTML up one level in card hierarchy)
- Eliminates the most common operator confusion pattern

**3. PERFORMANCE-ATTRIBUTION-01 Phase 1**
- ~14 hours total
- Answers: "Why did my portfolio perform this way?"
- Creates a compounding feedback loop: every future SIH recommendation can be attributed

### Beyond Session 3

| Priority | Issue | Rationale |
|----------|-------|-----------|
| 4 | PERFORMANCE-ATTRIBUTION-01 Phase 2 | Transaction-level and Brinson-Fachler enhancements |
| 5 | PERFORMANCE-ATTRIBUTION-01 Phase 3 | Outcome validation against recommendation history |
| 6 | #32 AI-004 | Policy version diff — governance infrastructure |
| 7 | #40 AI-001-OPTION-B | Compliance validator — grows with portfolio complexity |
| 8 | #17 ISSUE-12D | Dislocation outcome review panel |

---

## Final Summary

| Question | Answer |
|----------|--------|
| Fidelity source of truth for returns? | YES — for 3M+ windows and audited return views. |
| SIH can do attribution without replacing Fidelity? | YES — SIH explains *why*, not just *what* |
| Recommended benchmark architecture | SPY primary, VTI secondary, ACWI international reference |
| How should Concentrated Alpha be measured? | Contribution, lineage, alpha, and conviction-tier outcome tracking |
| Is PERFORMANCE-ATTRIBUTION-01 justified? | YES — it is the next major SIH initiative after current roadmap items |
| Implementation sequence | PRA-IMPL-02 → AI-003 → PERFORMANCE-ATTRIBUTION-01 |

**PERFORMANCE-ATTRIBUTION-01 should be implemented after PRA-IMPL-02 and AI-003. It is feasible, well-scoped, and creates compounding value by connecting every future SIH recommendation to measurable outcomes.**

---

## 01B-A Status Update

PERFORMANCE-ATTRIBUTION-01B-A (Benchmark Source and Return-Series Foundation) is now implemented.

Delivered in this phase:
- SPY benchmark source abstraction
- canonical-date-aligned benchmark return series
- canonical portfolio return series
- excess return calculation
- deterministic nearest-prior-trading-day alignment
- benchmark return-series persistence CSV
- read APIs for returns/latest/summary
- deterministic validation tests

Deferred intentionally:
- source-level alpha ranking
- recommendation-level benchmark excess attribution
- full benchmark dashboard rendering
