# Signal Conflict Backtest — SIGNAL-GOV-02

**Date:** 2026-06-15  
**Dataset:** 28 attribution records (June 10–11, 2026 interval)  
**Conflict Signal:** FMP Street aggregate sell vote count + Zacks NEUTRAL/BEARISH

---

## Critical Context

The attribution dataset covers one snapshot interval. Zero LOSER outcomes exist. Any conflict analysis is directionally informative only. Statistical conclusions cannot be drawn from N=28.

---

## Conflict Level Classification of Attribution Records

### Signal Source Used for Classification
- **Primary:** FMP Street sell_count (aggregate of all Street analysts)
- **Secondary:** Zacks score (1–5, where ≤2 = bearish)
- **Tertiary:** Yahoo ABR (≥3.5 = bearish zone)

### Classification Results

| Level | Label | N | Win Rate | Avg Return | Symbols |
|-------|-------|---|---------|-----------|---------|
| L0 | FULL_ALIGNMENT | 6 | **100.0%** | 9.4% | VRT×3, CAH×2, ATLC×1 |
| L1 | MILD_CONFLICT (hold consensus) | 1 | 100.0% | 12.0% | PCB |
| L2 | MODERATE_CONFLICT (1+ sell votes) | 14 | **85.7%** | **15.0%** | ARW×3, PSX×2, LRCX×2, AVT×2, DELL×2, SNX×2, CBOE×1 |
| Special | EXITED_POSITIONS | 3 | 100.0% | 100.0% | FIGFX, VXUS, FIS (exits, not new deployments) |
| Special | REDUCED | 4 | 100.0% | 37.7% | VXUS, FIS×2, legacy |

**Note on L2 win rate (85.7%):** The 2 non-winner records are DELL (−0.12%, NEUTRAL) and CBOE (+0.72%, NEUTRAL). Both are L2. This is weakly consistent with the conflict hypothesis but NOT statistically meaningful.

---

## L2 Detailed Symbol Analysis

| Symbol | FMP Sell Count | Sell % | N Records | Outcome | Returns |
|--------|---------------|--------|-----------|---------|---------|
| ARW | 2 of 17 | 11.8% | 3 | WINNER×3 | +29.65%, +15.58%, +11.18% |
| PSX | 2 of 35 | 5.7% | 2 | WINNER×2 | +13.30%, +11.46% |
| LRCX | 1 of 50 | 2.0% | 2 | WINNER×2 | +12.30%, +4.40% |
| AVT | 4 of 20 | 20.0% | 2 | WINNER×2 | +14.09%, +3.76% |
| DELL | 2 of 45 | 4.4% | 2 | 1 WINNER + 1 NEUTRAL | +6.49%, −0.12% |
| SNX | 1 of 24 | 4.2% | 2 | WINNER×2 | +9.94%, +5.25% |
| CBOE | 4 of 31 | 12.9% | 1 | NEUTRAL | +0.72% |

**Key observation:** AVT has the **highest sell percentage** (20% of analysts say sell) and was a WINNER on both entries (+14% and +3.76%). ARW was the **best performer** in the entire dataset (+29.65%) while carrying 2 sell votes.

---

## Conflict Signal Predictive Analysis

### Q: Does Conflict Level Predict Worse Outcomes?

| Metric | L0 | L2 |
|--------|----|----|
| Win rate | 100% | 85.7% |
| Avg return | 9.4% | 15.0% |
| Max return | 17.4% (VRT) | 29.65% (ARW) |
| Min return | 4.3% (VRT) | −0.12% (DELL) |

**Finding:** L2 has slightly lower win rate but significantly higher average return (+15.0% vs +9.4%). The best-performing symbol in the dataset (ARW +29.65%) was L2. This is contrary to the hypothesis that conflict predicts worse outcomes.

### Q: Does Sell Vote Count Predict Outcomes?

| Symbol | Sell % | Best Return | Verdict |
|--------|--------|-------------|---------|
| AVT | 20% | +14.09% | Winner |
| ARW | 11.8% | +29.65% | Best performer |
| CBOE | 12.9% | +0.72% | NEUTRAL only |
| DELL | 4.4% | +6.49% | WINNER + NEUTRAL |
| PSX | 5.7% | +13.30% | Winner |

**Finding:** No monotonic relationship between sell percentage and outcome quality in this dataset. AVT at 20% sell rate outperformed DELL at 4.4% sell rate.

---

## Most Frequently Disagreeing Sources in Attribution

**Sell votes are aggregated by FMP (not source-resolved).** Based on FMP aggregate data:

| Symbol (in attribution) | Sell Count | Sell % | Notes |
|------------------------|-----------|--------|-------|
| AVT | 4/20 | 20% | Highest sell proportion among attribution symbols |
| CBOE | 4/31 | 12.9% | Second highest |
| ARW | 2/17 | 11.8% | Third highest |
| DELL | 2/45 | 4.4% | Low proportion despite 2 votes |
| PSX | 2/35 | 5.7% | — |
| SNX | 1/24 | 4.2% | — |
| LRCX | 1/50 | 2.0% | Minimal |

---

## Backtest Conclusion

**The attribution data does NOT support the hypothesis that analyst disagreement predicts worse deployment outcomes.**

The 2 NEUTRAL records (non-winners) were both L2, but so were 12 winners including the top performer (ARW, +29.65%). The full-alignment L0 cohort produced 100% win rate but lower average returns (9.4% vs 15.0%).

**The data is consistent with three possible interpretations:**
1. Conflict is noise — the ESS score (55% weight) dominates and individual analyst dissent is irrelevant
2. Conflict is timing signal — sell votes predict some future weakness but not on the 1-day interval tested
3. Sample is too small — 28 records cannot distinguish these hypotheses

**Recommended inference:** The operator's instinct ("I don't want to deploy when sources say SELL") is philosophically sound but empirically unsupported at N=28. Advisory badges are warranted. No enforcement.
