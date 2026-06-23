# Signal Conflict Validation — SIGNAL-GOV-02

**Date:** 2026-06-15  
**Validation Type:** Evidence-based qualitative analysis + backtest review

---

## Q1: How many historical recommendations contained bearish signals?

**14 of 28** attribution records (50%) involved symbols with at least one explicit sell vote from Street analysts (FMP data). 0 records involved symbols with bearish Zacks or Danelfin scores at the time of attribution.

---

## Q2: Did those recommendations outperform or underperform?

**They slightly outperformed.** L2 (conflict) symbols averaged **15.0% return** vs L0 (full alignment) symbols at **9.4% return**.

This is a counterintuitive finding. The top performer in the entire dataset — ARW at +29.65% — had 2 explicit sell votes (11.8% sell rate). AVT with the highest sell proportion (20%) was a WINNER on both entries.

**Conclusion:** There is NO evidence in the current dataset that bearish signals from Street analysts predict worse outcomes. If anything, the point estimate slightly favors conflicted symbols — but the difference is not statistically distinguishable at N=28.

---

## Q3: Which sources most frequently disagreed?

Based on FMP aggregate (individual source names not resolvable from current SIH data):

| Symbol | Sell Count | Sell% | Outcome |
|--------|-----------|--------|---------|
| CBOE | 4/31 | 12.9% | NEUTRAL (in attribution) |
| AVT | 4/20 | 20.0% | WINNER×2 |
| ARW | 2/17 | 11.8% | WINNER×3 |
| DELL | 2/45 | 4.4% | WINNER + NEUTRAL |
| PSX | 2/35 | 5.7% | WINNER×2 |

Individual source names (Refinitiv/Verus, Trading Central, Argus, etc.) are **not resolvable** from the FMP aggregate. The individual source is available only in the ESS export data (limited to Jefferson Research, Zacks, McLean Capital Management columns).

---

## Q4: Does analyst disagreement predict weaker outcomes?

**No, not in the current dataset.** 

Win rate was lower for L2 (85.7% vs 100% for L0), but this difference is driven by 2 NEUTRAL records that are also L2. The average return was *higher* for L2 (+15.0% vs +9.4%). No LOSER records exist.

This may reflect:
1. **ESS dominance:** The StarMine ESS (55% weight) is a consensus-aware signal that already incorporates the sell-side views. So explicit sell votes may already be discounted in the ESS score.
2. **Period effect:** June 10–11, 2026 was a uniformly positive period. Sell vote symbols may underperform in different market conditions.
3. **Sample size:** N=28 is too small to draw conclusions.

---

## Q5: Does analyst disagreement predict stronger outcomes?

**Not meaningfully.** While L2 had a higher average return, this is driven by ARW's exceptional +29.65% return. Removing ARW, L2 avg falls to ~11% — close to L0.

---

## Q6: Should conflict levels be surfaced in the UI?

**Yes, strongly.** The operator's preference to be informed about analyst disagreement is operationally sound regardless of whether it predicts outcomes. 

Specific benefits:
- Operator can distinguish between "100% conviction buy" signals and "mixed market view" signals
- Supports deeper due diligence for L3 symbols (TSLA, AVT, GTX)
- Enables NUE-style named source annotation for L4 cases
- Creates an audit trail for deployment decisions under conflict

---

## Q7: Should conflict levels affect ranking?

**Not at this data maturity.** No empirical evidence supports ranking penalties. L2 symbols outperformed L0 in this dataset. A penalty would have suppressed ARW, the best performer.

Future condition for ranking penalty: if a dataset with LOSER records shows correlation between conflict level and loss probability, a penalty is warranted. Currently unwarranted.

---

## Q8: Should conflict levels affect deployment eligibility?

**No for L1 and L2.** Advisory only.  
**Operator review for L3 is reasonable** — not a block, but a required acknowledgement.  
**No hard block at any level** — empirical basis is insufficient.

---

## Q9: Is NUE appropriately ranked despite analyst disagreement?

**Yes, #10 ranking is appropriate.** Full analysis:

| Source | Signal | Interpretation |
|--------|--------|---------------|
| ESS (StarMine) | BULLISH | Primary signal, 55% weight. Reflects majority analyst opinion including sub-providers. |
| Zacks | Score=5.0, Rank=1 | STRONG BUY — the single most bullish Zacks reading in the deployment queue. |
| Danelfin | Raw=7.0 (3.5 normalized) | Moderately bullish AI momentum score. |
| Yahoo ABR | 1.76 | Strongly bullish (1.0=Strong Buy, 2.0=Buy range). |
| FMP Street | 18B/11H/3S (n=32) | 56.3% buy, 9.4% sell — BUY consensus. |
| Trading Central (per operator) | Buy (score 98) | High-confidence buy from quant source. |
| Refinitiv/Verus (per operator) | Sell (score 86) | High-confidence sell from one source. |

**Conflict classification:** The operator-identified Trading Central vs Refinitiv/Verus disagreement would qualify NUE for **L4 (Severe Conflict)** if operator-annotated. The FMP aggregate shows **L2 (Moderate)** — 3 sell votes among 32.

**Ranking verdict:** NUE holds the strongest Zacks signal in the queue (5.0 STRONG BUY) and passes all composite signal thresholds. The 3 sell votes represent 9.4% of analysts. The #10 ranking is justified. The named source disagreement warrants an advisory annotation, not exclusion.

**Appropriate action:** Flag NUE as `HIGH_ANALYST_DISAGREEMENT` with annotation noting the Refinitiv/Verus dissent. Allow deployment with operator awareness.

---

## Q10: Which governance option is recommended?

**Option B (Conflict Warning Badges) for all conflict levels, with Option C (Review Required) for Level 3 holdings.**

Implementation:
- `FULL_ALIGNMENT` — no badge (VRT, ATLC, MTZ)
- `HOLD_CONSENSUS` — yellow badge (PCB)
- `CONFLICTING_SIGNAL` — yellow badge with sell count (DELL, LRCX, SANM, CRS, NUE, SANM, ARW, PSX etc.)
- `SIGNIFICANT_CONFLICT` — orange badge (TSLA, AVT, GTX)
- `HIGH_ANALYST_DISAGREEMENT` — red badge (operator-annotated NUE-style cases)

---

## Q11: Is implementation recommended?

**Yes — Option B advisory badges.** High information value, low risk, directly serves stated operator preference.

Specific items:
1. Add `conflict_level` and `conflict_badge` fields to deployment queue rendering in `app.js`
2. Source FMP sell counts from `latest_fmp_grades_consensus.csv` 
3. Define thresholds in `allocation_policy.yaml:signal_conflict`
4. Display badge alongside symbol name in deployment queue UI

**Not recommended now:**
- Ranking penalties (no evidence)
- Hard deployment blocks (no evidence)
- Level 3 acknowledgement gate (reasonable future item, not urgent)

---

## Special Investigation: CAH, SANM, MTZ, PCB

| Symbol | FMP | Sell% | Zacks | Dan | Yahoo ABR | Conflict | Assessment |
|--------|-----|-------|-------|-----|-----------|---------|------------|
| CAH | 18B/15H/0S (n=33) | 0% | 4.0 | 5.0 | 1.47 | L1 (HIGH_HOLD) | No explicit sells; 45.5% hold ratio is a caution. ESS VERY_BULLISH overrides. Appropriate at #6. |
| SANM | 5B/10H/2S (n=17) | 11.8% | 4.0 | 8.0 | 2.50 | L2 | Buy minority (29.4%). 2 sell votes. Danelfin=8 is a strong counterweight. Advisory badge warranted. Appropriate at #7 with badge. |
| MTZ | 32B/4H/0S (n=36) | 0% | 3.0 | 9.0 | 1.25 | L0 | STRONGEST buy consensus in the queue — 88.9% buy rate. Only Zacks is NEUTRAL (3.0). Fully aligned otherwise. Appropriate at #8. |
| PCB | 1B/4H/0S (n=5) | 0% | 3.0 | 7.0 | no data | L1 | HOLD consensus. 80% hold rate from small coverage. No explicit sells. Danelfin=7 and ESS VERY_BULLISH sustain it. Advisory badge warranted. Appropriate at #5 with badge. |
