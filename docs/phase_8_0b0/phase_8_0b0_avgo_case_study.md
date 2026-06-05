# Phase 8.0B.0 — AVGO Case Study

**Date:** 2026-06-04  
**Scenario:** AVGO falls 15% after earnings  
**Purpose:** Demonstrate what SIH can and cannot explain today, and what FMP would add

---

## Current AVGO State in SIH

From the latest analytical universe snapshot:

| Field | Value |
|-------|-------|
| `composite_score` | 3.72 |
| `ess_score_text` | BULLISH |
| `zacks_rating` | 3.0 (normalized) |
| `danelfin_score` | 4.0 |
| `yahoo_abr_normalized` | (included in composite) |
| `replay_supported` | False (not in portfolio long enough for replay) |
| Price Target (Yahoo) | Not available for AVGO in this snapshot |

---

## Scenario: AVGO Falls 15% After Earnings

### What SIH Can Explain Today

**Almost nothing.**

After a 15% post-earnings decline, here is what SIH would show:

1. **ESS response (lagged):** StarMine/Zacks update their models after earnings. If growth deteriorated, ESS may shift from BULLISH → NEUTRAL or BEARISH within 1–2 weeks. SIH would then show `signal_direction=BEARISH` and eventually flag AVGO as SIGNAL_DETERIORATION.

2. **Danelfin response:** Danelfin AI re-scores daily. It would likely reflect the price decline and sentiment shift fairly quickly.

3. **Price target update:** Yahoo ABR would update as analysts revise. The upside_pct would recalculate.

**What SIH cannot say on day 1 after a 15% move:**
- Did revenue miss? By how much?
- Did EPS miss? Beat?
- What happened to guidance?
- Was the growth rate decelerating before this?
- Did estimates get cut? By how much?
- Is the valuation now attractive at the new price?
- Is this a buying opportunity or the beginning of a multi-quarter thesis break?

### What FMP Would Tell SIH on Day 1

**From `/earnings?symbol=AVGO` (earnings report):**
- Actual EPS vs estimate → surprise %
- Actual revenue vs estimate → revenue surprise %
- Whether this was a beat-and-guide-lower, miss-and-guide-lower, or beat-and-raise

**From `/analyst-estimates?symbol=AVGO` (post-earnings):**
- New forward revenue estimates (before vs after)
- New forward EPS estimates
- Estimate cut % (e.g., "analysts cut FY27 EPS by 8%")

**From `/grades?symbol=AVGO` (post-earnings):**
- Downgrades: how many firms moved from Buy → Hold or Sell
- Maintained Buy ratings: how many firms held conviction
- Ratio of upgrades to downgrades in the week following

**From `/key-metrics-ttm?symbol=AVGO` (at new price):**
- Forward P/E at the new price: is it now 15x vs the previous 25x?
- EV/EBITDA compression: did the selloff create a valuation opportunity?
- FCF yield: did it jump to 5%+ (historically attractive)?

**From `/income-statement-growth?symbol=AVGO` (prior quarters):**
- Was revenue growth already decelerating from 20%+ to 12% before this quarter?
- Is this the third consecutive deceleration (thesis break) or the first miss in 8 quarters?

---

## Case Study: The Two Scenarios FMP Distinguishes

### Scenario A — Thesis Break (FMP confirms avoidance)

FMP shows:
- Revenue growth: Q1 28% → Q2 19% → Q3 12% → Q4 6% (three-quarter deceleration)
- EPS miss: −8% vs estimate
- Guidance cut: Revenue guidance down 10%
- Analyst upgrades/downgrades: 6 downgrades, 0 upgrades in the week following
- Forward P/E at new price: 22x (still above semiconductor peers at 18x)
- Earnings surprise history: First miss in 6 quarters, but with significant guidance cut

**SIH response with FMP:** `signal_direction` likely stays BULLISH for a few days, but CRA would surface AVGO as a potential exit candidate with:
- Revenue acceleration score: NEGATIVE (three-quarter deceleration confirmed)
- Earnings momentum: NEGATIVE (guidance cut, analyst downgrades)
- Valuation: NOT COMPELLING (22x still above peer group at new price)

**Correct action:** WATCH → potential SIGNAL_DETERIORATION within 1 quarter

### Scenario B — Buying Opportunity (FMP enables dislocation identification)

FMP shows:
- Revenue growth: Q1 22% → Q2 25% → Q3 29% → Q4 31% (three-quarter acceleration)
- EPS beat: +12% vs estimate
- Miss was on reported margin (one-time acquisition cost), not on organic growth
- Guidance: Maintained or slightly raised
- Analyst upgrades/downgrades: 0 downgrades, 3 upgrades in the week following
- Forward P/E at new price: 14x (below semiconductor peer group at 18x)
- Earnings surprise history: Beat in 7 of last 8 quarters

**SIH response with FMP:** This is a "stock on sale" moment — thesis is intact, growth is accelerating, valuation just compressed. CRA should flag this as a deployment opportunity, not a sell candidate.

**Correct action:** CW-DAS rank preserved or elevated; potential CCL promotion if conditions persist

---

## What SIH Got Wrong Today (Without FMP)

For Scenario B, current SIH would:
1. See the 15% price decline → Danelfin score drops (price momentum negative)
2. See any ESS downgrade (if issued) → potentially flag BEARISH
3. Place AVGO in SIGNAL_DETERIORATION if WATCH flag fires
4. CRA would suggest selling AVGO

**This is exactly backwards.** SIH would recommend selling a high-quality growing business at a valuation compression low.

FMP would prevent this error by surfacing:
- Revenue acceleration despite the price drop
- Earnings beat history
- Valuation now below peers

---

## Summary

| Question | Today (No FMP) | With FMP |
|----------|---------------|---------|
| Did revenue miss? | ❌ Unknown | ✅ Exact %, vs estimate |
| Did growth deteriorate? | ❌ Unknown | ✅ Multi-quarter trend |
| Did estimates get cut? | ❌ Unknown | ✅ Analyst revision direction |
| Is valuation now attractive? | ❌ Unknown | ✅ P/E, EV/EBITDA vs history/peers |
| Is this a buy or avoid? | ❌ Cannot determine | ✅ Framework to classify |
| Should CRA recommend a sell? | Potentially WRONG | ✅ Would prevent false sell signal |
