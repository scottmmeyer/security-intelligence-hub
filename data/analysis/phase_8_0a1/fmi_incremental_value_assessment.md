# FMI Incremental Value Assessment
**Phase 8.0A.1 | Does Fundamental Momentum Intelligence Add Measurable Value?**
**Generated:** 2026-06-02

---

## 1. Executive Summary

**Verdict: MODERATE INCREMENTAL VALUE — Justified for Phase 8.0B Implementation**

Fundamental Momentum Intelligence (FMI), operationalized as the FMS scoring system in this study, provides **measurable but uneven incremental value** over SIH signals alone. The value is concentrated in specific high-impact use cases, partially offset by a significant data coverage gap.

**Overall assessment: FMI adds incremental value in approximately 25-30% of the top 100 universe — the cases where that value matters most (divergence detection and recovery validation).**

---

## 2. Value Assessment Framework

For FMI to justify implementation, it must provide value in one or more of these ways:
1. **Divergence Detection**: Catch cases where strong signals mask deteriorating fundamentals
2. **Recovery Confirmation**: Validate that recovery stories have real fundamental support (not just sentiment)
3. **Compounder Identification**: Surface exceptional A_ACCELERATING_COMPOUNDER quality that signals don't adequately distinguish
4. **Future Winner Discovery**: Find high-FMS symbols that signals haven't yet fully surfaced

---

## 3. Value Area Analysis

### Value Area 1: Divergence Detection

**Evidence**: FMI identified 6 HIGH_SIGNAL_LOW_FUNDAMENTAL cases in the top 100:
- PSX (FMS 24): FCF collapsed -98.7%; signals VERY_BULLISH
- LYB (FMS 15): Operating losses; signals BULLISH
- CHRD (FMS 20): EPS negative; signals BULLISH
- DINO (FMS 26): EPS trough $0.91; signals VERY_BULLISH
- VLO (FMS 28): EPS -53% from peak; signals VERY_BULLISH
- MPC (FMS 30): FCF -81% from peak; signals VERY_BULLISH

**Quantified value**: PSX case study shows that following VERY_BULLISH signals without FMI overlay led to a ~-43% drawdown from signal-attractive levels. FMI (FMS 24 = DIVERGENCE flag) would have prompted 50-75% position reduction, saving approximately 20-30% in drawdown.

**Verdict for Value Area 1**: HIGH VALUE — catches real losses on 6/53 multi-signal symbols (~11%)

### Value Area 2: Recovery Confirmation

**Evidence**: FMI validated 11+ B_RECOVERY_STORY symbols with FMS > 50:
- ARW (FMS 64): Fundamental recovery confirmed — revenue near peak, EPS recovering strongly
- STX (FMS 65): Explosive recovery — near prior revenue peak
- MU (FMS 75): Exceptional recovery — revenue +85.5%
- GMED (FMS 62): Post-merger integration recovery confirmed
- BFH (FMS 55): Credit cycle recovery confirmed

**Contrast**: FMI also identified lower-quality recovery stories:
- TREE (FMS 40): Revenue recovering but GAAP losses persist — requires continued monitoring
- MCHP (FMS 48): Early-stage recovery; EPS near-zero — uncertain timeline
- CHRD (FMS 20): Labeled "recovery" by signals but FMS shows near-zero profitability

**Verdict for Value Area 2**: HIGH VALUE — FMI creates a quality spectrum within B_RECOVERY_STORY that signals don't differentiate. ARW/STX/MU are very different quality situations than TREE/MCHP/CHRD, despite all being "recovery" stories.

### Value Area 3: Compounder Identification

**Evidence**: FMI correctly identifies FIX and ATLC as exceptional A_ACCELERATING_COMPOUNDER cases:
- FIX (FMS 85): Rank 62nd by composite, but FMS ranks it #2 in the entire study
- ATLC (FMS 81): Composite 4.778 (rank ~69th), but FMS ranks it #3
- VRT (FMS 89): Not even in top 100 by composite, but #1 by FMS

**Does FMI surface these that signals miss?** Partially:
- Signals DO capture FIX (VERY_BULLISH ESS + Zacks 5.0 + Danelfin 4.0 = composite 4.833)
- Signals DO capture ATLC (VERY_BULLISH + 5.0 + 3.0 = 4.778)
- FMI's incremental contribution: **Distinguishing FIX (FMS 85) from the median VERY_BULLISH symbol (FMS ~52)** — i.e., signals tell you "this is good" but FMI tells you "this is exceptional vs merely good"

**Verdict for Value Area 3**: MODERATE VALUE — signals capture compounders but FMI provides quality ranking within the VERY_BULLISH tier that helps prioritize allocation

### Value Area 4: Future Winner Discovery

**Evidence**: VRT (FMS 89, composite ~4.556) is the primary example of a high-FMS symbol that composite scoring had temporarily depressed.

**Limitation**: Only 1 confirmed case (VRT) in this study. The study was limited to the top 100 by composite — additional future winners may exist in the 101-300 range.

**Assessment**: This is the most intellectually compelling value area but has the least empirical support from this study alone. Phase 8.0B (with FMP API computing FMS for the full universe) would be required to validate this hypothesis at scale.

**Verdict for Value Area 4**: POTENTIAL HIGH VALUE but requires Phase 8.0B to validate

---

## 4. Coverage Gap Analysis

### Critical Limitation: 47% of Top 100 = G_INSUFFICIENT_DATA

| Category | Count | % of Top 100 |
|----------|-------|-------------|
| Multi-signal (3/3) with full FMS data | 28 | 28% |
| Multi-signal with partial data | 25 | 25% |
| G_INSUFFICIENT_DATA (Zacks-only) | 47 | 47% |

**For 47 symbols (ranks 1-47, all composite 5.0), FMI provides NO incremental value.** These are foreign ADRs, micro-caps, and obscure instruments where fundamental data is either unavailable or unreliable.

**Practical implication**: FMI's value is concentrated in the multi-signal tier (ranks 48-100), where it provides incremental intelligence for approximately 25-30 of the 53 symbols. This is meaningful but not universal.

### Data Acquisition Cost-Benefit

| Option | Annual Cost | Symbols Covered | Coverage Rate |
|--------|------------|-----------------|---------------|
| Manual web scraping (current) | $0 | ~30-40 top symbols | ~50% of multi-signal |
| FMP Starter API | ~$228/year | ~5,000+ symbols | ~100% of multi-signal + broader universe |
| Bloomberg Terminal | $24,000/year | Full professional data | 100%+ |

**FMP Starter API at $228/year is the clear optimal choice**: provides coverage for the full multi-signal universe at negligible cost, enables Phase 8.0B hypothesis testing, and automates FMS computation.

---

## 5. Summary Value Matrix

| Use Case | Value Level | Coverage | Implementation Complexity |
|----------|-------------|----------|--------------------------|
| Divergence detection (PSX/LYB pattern) | HIGH | 6 cases = ~11% of multi-signal | Low — FMS threshold rule |
| Recovery quality ranking (ARW vs TREE) | HIGH | ~15-20 cases | Low — FMS spectrum use |
| Compounder prioritization (FIX vs median) | MODERATE | ~5-10 cases | Low — FMS threshold |
| Future winner discovery (VRT pattern) | HIGH POTENTIAL | 1 confirmed case | Requires FMP API (Phase 8.0B) |
| Broad universe scanning | Not yet possible | Limited | Requires FMP API |

---

## 6. Should FMS Be Incorporated into SIH Scoring?

**Verdict: NO — maintain FMS as informational only**

Rationale:
1. **Insufficient validation data**: 28 symbols with FMS computed from one data point in time is not a statistically valid sample for scoring integration
2. **Temporal validation required**: FMS must be shown to predict 3-6 month forward returns before integration into composite scoring
3. **Signal quality is already validated**: SIH ESS + Zacks + Danelfin combination has demonstrated predictive power; adding FMS without validation risks degrading proven performance
4. **Asymmetric information**: FMS is backward-looking (current fundamentals); signals are forward-looking (institutional positioning, estimate revisions). They serve different analytical purposes and should remain separate.
5. **Coverage gap**: With 47% G_INSUFFICIENT_DATA, incorporating FMS into composite would create systematic coverage bias

**Instead**: FMS should appear as a UI overlay/informational badge on the operator dashboard — visible for context but not influencing signal scores.

---

## 7. Overall Incremental Value Verdict

**FMI adds MODERATE incremental value to the SIH system:**

✅ **WHERE IT ADDS VALUE (30% of use cases, 80% of risk mitigation opportunity):**
- Divergence detection: 6 confirmed cases where signals are misleading about fundamental quality
- Recovery story differentiation: distinguishes ARW/STX/MU quality from TREE/MCHP early-stage uncertainty
- Compounder ranking: FIX at FMS 85 vs average VERY_BULLISH at FMS 52

❌ **WHERE IT DOESN'T ADD VALUE (47% of top 100):**
- G_INSUFFICIENT_DATA symbols (ranks 1-47): no data available; FMI silent
- Symbols where signals and fundamentals fully align: FMI just confirms what signals already say
- Forward-looking situations where current fundamentals are weak but catalyst is imminent

**Net verdict: FMI is worth implementing at the Phase 8.0B level (FMP API), maintaining as informational overlay, and monitoring for statistical validation over 6-12 months before considering any scoring integration.**
