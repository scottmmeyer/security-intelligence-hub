# Replay Authority Reassessment
**Phase 7.6D.2 — Replay Historical Signal Integrity Audit**
**Date:** 2026-06-01

---

## Q6: Should Tier 1 Authority Remain?

**Background:** Phase 7.6C elevated Replay to Tier 1 Authority based on the presence of 200 HISTORICAL_VALIDATION 365-day replays demonstrating that the composite_score ranking system successfully identified high-performing baskets. These replays covered 2025-05-14 to 2026-05-14.

**This audit's finding:** The 200 HISTORICAL_VALIDATION replays that justified Tier 1 promotion are classified as CLASS D — the basket selection rankings were computed using ESS data from May 2026, not May 2025.

---

## The Circular Authority Problem

The 365-day HISTORICAL_VALIDATION replays use:
- **Start date:** 2025-05-14
- **End date:** 2026-05-14
- **Composite scores used for basket selection:** Derived from `EquitySummarScores_May-15-2026.csv`
- **Return measurement:** 2025-05-14 to 2026-05-14 (authentic market prices)

**The problem:** The ESS file dated May 2026 reflects analyst consensus opinion AFTER the May 2025 to May 2026 return period had elapsed. If a basket of high-ESS stocks performs well from 2025 to 2026, one reason could be that analysts in 2026 are rating those stocks highly BECAUSE they performed well over that exact period. The signal and the return are not independent.

This is not standard backtesting look-ahead bias (predicting returns with future price data). It is **signal-return circularity**: the selection signal was produced after the performance period it is supposed to predict.

---

## Is This Disqualifying?

The severity depends on one key empirical question: **How much does ESS change in response to past price performance?**

**Arguments that Tier 1 should be reduced:**

1. **The circular structure cannot be controlled for.** Without May 2025 ESS data, it is impossible to know whether the basket would have been selected the same way with contemporaneous signals.

2. **The +104.6% SMALL-ALL basket return is suspicious without authentic signals.** Baskets selected in hindsight (using signals from after the return period) would be expected to show elevated returns vs. baskets selected in real-time. The actual +67.2% outperformance vs. benchmark may partially or substantially reflect this effect.

3. **The framework's own lookahead validator does not detect this gap.** The validator passes these replays, creating a false sense of validation. Signal-level lookahead is not being audited at the code level.

4. **ESS does incorporate recent price performance.** Analyst recommendations (which ESS aggregates) respond to price momentum. A stock that rises 50% may receive analyst upgrades. The May 2026 ESS for a stock that rose 50% from May 2025 to 2026 is likely more bullish than the May 2025 ESS would have been. This effect is measurable and expected.

**Arguments that Tier 1 may remain partially justified:**

1. **ESS is fundamentally forward-looking.** ESS reflects analyst 12-month price targets and earnings estimates — these are independent of recent returns to a degree. A analyst who raised a stock from NEUTRAL to BULLISH in 2026 may have done so based on improving earnings, not just past price gains.

2. **The composite_score formula was consistent across current and historical runs.** Relative rankings within a basket are less affected by look-ahead if ESS scores for most stocks moved in parallel. Cross-sectional signal ordering may be partially preserved even with 12-month-old data substituted.

3. **CURRENT_RECOMMENDATION 6-day replays (CLASS A) do confirm current-cycle applicability.** The framework's current outputs are derived from authentic signals. The CURRENT_RECOMMENDATION evidence, while thin (6 days), is uncontaminated.

4. **Price return measurement is authentic.** The replay validation is measuring real market performance. The results (basket return vs. benchmark) are real — the only question is whether the basket was selected by a predictive signal or a retrospective one.

---

## Authority Assessment

### Framework's Tier 1 Claim

Phase 7.6C promoted Replay to Tier 1 on the basis of:
> "200 HISTORICAL_VALIDATION replays demonstrating systematic basket performance above benchmark"

The evidence:
- US-SMALL-ALL basket: +104.6% vs +37.4% benchmark (+67.2% alpha)
- Multiple industry-specific baskets showing similar patterns
- Consistent performance across geography and cap bucket variants

### Audit Finding

The 200 HISTORICAL_VALIDATION replays that support this claim are CLASS D. Their basket selection was determined by 2026 ESS data, creating an unknown degree of circularity with the return period being measured.

### Adjusted Assessment

| Component | Phase 7.6C Assumption | Audit Finding | Revision |
|---|---|---|---|
| Signal authenticity | "Historical validation confirmed in 2025 signals" | 2026 signals used for 2025 start date | UNSUPPORTED |
| Return measurement | Authentic market prices 2025→2026 | CONFIRMED authentic | CONFIRMED |
| Lookahead protection | Validator confirmed no lookahead | Validator only checks date field, not signal provenance | INADEQUATE |
| Cross-sectional validity | Strong ranking correlation to future returns | Cannot be separated from circular ESS effect | UNVERIFIABLE |
| CURRENT_RECOMMENDATION evidence | "Recent signal confirmation" | 6-day authentic replays (CLASS A) | CONFIRMED |

---

## Recommended Authority Adjustment

**Verdict: `B. REPLAY_AUTHORITY_PARTIALLY_CONFIRMED`**

Replay authority is partially confirmed under the following conditions:

1. **The return measurement component of replay evidence is authentic** (actual market prices). Replay's role as a performance measurement system is sound.

2. **The basket selection component for HISTORICAL_VALIDATION replays is unverifiable** due to CLASS D signal provenance. The remarkable outperformance figures (+67% alpha for SMALL-ALL) cannot be attributed to predictive signal quality without authentic 2025 ESS data.

3. **Tier 1 status should be conditionally maintained** with explicit disclosure that the HISTORICAL_VALIDATION evidence basis is subject to a signal provenance gap. The authority should not be downgraded to Tier 2 because the outperformance could still be genuine even with imperfect signal provenance — but neither can full confidence be claimed.

4. **CURRENT_RECOMMENDATION evidence (CLASS A) supports ongoing Tier 1 use** for present-day routing decisions.

5. **The lookahead validator should be enhanced** to record ESS source file generation dates alongside composite_score_snapshot_date to enable future audits.

---

## Practical Implication for Current Run

The current PAR-20260601-9CFD7C63 uses replay evidence for ~38 holdings via HISTORICAL_VALIDATION 365-day replays. These routing decisions are based on basket membership from CLASS D snapshots. The current signal (ESS, Zacks, Danelfin from May 2026) is authentic and the current composite_score rankings are legitimate. The question is whether the historical replay validation was predictive — and that question cannot be conclusively answered with available data.

**The replay bonus (20 pts in CW-DAS) represents real basket membership evidence.** The stocks that made the 2025-05-14 baskets did perform well from 2025 to 2026. The concern is whether the baskets would have been the same if constructed with authentic 2025 signals. For stable-signal stocks (large-cap, established ESS ratings), the difference is likely minimal. For momentum-driven selections, the difference could be material.
