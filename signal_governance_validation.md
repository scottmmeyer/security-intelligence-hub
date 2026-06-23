# Signal Governance Validation — SIGNAL-GOV-01

**Date:** 2026-06-15  
**Validation Type:** Evidence-based qualitative + limited quantitative

---

## Q1: Which policy produces highest historical alpha?

**D2 (Danelfin≥7)** produces the highest average return at **35.42%** for the 10 included records (vs. 20.93% baseline). All 10 are winners.

However: this is driven by selection — the 10 symbols with Danelfin≥7 happened to be the strongest performers in the single available snapshot interval. D2's apparent alpha cannot be separated from luck/period effects at N=10.

**Practical answer:** Under current data, D2 shows highest raw return but is not statistically distinguished from the baseline.

---

## Q2: Which policy produces highest win rate?

**D2 (Dan≥7), C1 (Z≥4 AND D≥7), C3 (Z≥5 AND D≥7)** all achieve **100% win rate**.

The baseline (Z0) has 92.6% win rate (2 NEUTRAL records). Note: "100% win rate" here means the 2 NEUTRAL records are excluded by these policies — both NUETRALs were low-Danelfin symbols (DELL, CBOE with Dan=5).

**Practical answer:** D2 and C1 eliminate the 2 non-winner records. Whether this reflects genuine predictive value or sample coincidence cannot be determined from N=27.

---

## Q3: Which policy removes most losers?

**All policies remove zero losers.** There are no LOSER records in the current attribution dataset. This question cannot be answered empirically — the 28-record dataset contains only WINNERs and NUTRALs.

**Practical answer:** Cannot determine. Requires a larger attribution dataset with genuine loser outcomes.

---

## Q4: Which policy removes most winners?

**Z3 (Zacks≥5)** excludes 17 winners from the 27-record Zacks universe.  
**C4 (Z≥4 AND D≥8)** excludes all 27 records (0 pass) — vacuously worst.  
**D3 (Dan≥8)** excludes 24 winners — extremely restrictive.

In the current queue, **Z3 removes 8/10 symbols** — it is too restrictive for deployment use.

---

## Q5: Does Zacks provide more predictive value than Danelfin?

**No evidence that Zacks is more predictive.** Key findings:

1. Tightening Zacks (Z2, Z3) **reduces** win rate and average return by excluding confirmed winners (PCB: +12%, CAH: +10.93%)
2. Zacks=3.0 symbols are WINNERS in the backtest — Zacks NEUTRAL did not predict poor outcomes
3. PCB (Zacks=3.0, Dan=7.0) is the #5 deployment position with a strong historical record

**Verdict:** In the current dataset, Zacks thresholds do not demonstrate positive predictive value.

---

## Q6: Does Danelfin provide more predictive value than Zacks?

**Mild evidence that Danelfin≥7 correlates with higher returns.**

Danelfin≥7 symbols in the attribution dataset: ARW (3 entries, 11–30% returns), VRT (3 entries, 5–17% returns), PCB (12%), MTZ (no historical record).

Low-Danelfin symbols (Dan=5): DELL (6.49% + NEUTRAL), CBOE (NEUTRAL), CAH (modest returns).

**The pattern is consistent:** higher Danelfin scores correlate with higher returns in this dataset, though the sample is too small to conclude statistical significance.

**Verdict:** Danelfin shows *directionally* more predictive value than Zacks in the current dataset. This aligns with Danelfin's design (ML-based score trained on short-term price outcomes).

---

## Q7: Is Zacks≥4 justified as a hard gate?

**Not justified based on current evidence.** 

Arguments against Z2 hard gate:
- PCB (Zacks=3) was a +12% winner
- CAH (Zacks=3) had two winning entries at +10.93% and +4.26%
- Z2 reduces total attribution from $42,158 to $15,626 by excluding confirmed winners

Arguments for Z2 soft gate:
- Zacks=3 means "NEUTRAL" — it is a mild concern signal
- As a tie-breaker or advisory flag, Zacks=3 is worth surfacing to the operator

**Verdict:** Z2 is NOT justified as a hard exclusion gate. It is reasonable as an advisory flag.

---

## Q8: Is Danelfin≥7 justified?

**Weakly justified as a soft gate based on current evidence.**

Arguments for D2 advisory:
- D2 symbols averaged 35.42% vs 20.93% baseline
- D2 eliminates both NEUTRAL records (DELL, CBOE), both of which had Dan=5
- Pattern is consistent: low Danelfin → lower-quality outcomes in this window

Arguments against D2 hard gate:
- The 4 symbols excluded (ATLC, DELL, LRCX, CAH) are all currently active positions with solid ESS
- Small sample — cannot confirm statistical significance
- ATLC returned +18.49% (Danelfin=6) — would have been excluded

**Verdict:** D2 is reasonable as an **advisory flag** (yellow banner). Hard gate is premature. Suggest re-evaluate at 100+ attribution records.

---

## Q9: Is a combined gate (C1 or C2) justified?

**C2 (Z≥4 OR D≥7) is the most defensible candidate.**

C2 results:
- N=21, win rate=90.5%, avg return=21.44% (slightly above baseline)
- Excludes only 6 records — modest restriction
- In current queue: **excludes zero symbols** (every queue symbol passes at least one of Z≥4, D≥7)
- Provides a floor: a symbol must have at least one confirming signal

C1 (AND) is too restrictive — excludes 6 of 10 current queue symbols including ATLC, DELL, LRCX.

**Verdict:** C2 (OR gate) is the most operationally sensible combined policy. It acts as a "neither signal is strongly positive" filter while preserving deployment flexibility.

---

## Q10: Hard exclusions or ranking penalties?

**Ranking penalties preferred over hard exclusions at this data maturity level.**

Rationale:
- N=28 is insufficient to justify overriding ESS (the primary 55% signal)
- Hard gates may block legitimate ESS-confirmed names (PCB, MTZ both VERY_BULLISH)
- A −5 score penalty for Zacks=3 moves the symbol down the queue without eliminating it
- Annotating symbols with advisory flags (ZACKS_NEUTRAL, DANELFIN_WATCH) preserves operator authority

**Decision: Advisory flag + optional soft ranking penalty. No hard exclusion gate in Phase 1.**

---

## Q11: Configurable by mandate?

**Yes, governance gates should be mandate-configurable.**

The CONCENTRATED_ALPHA mandate operates under different principles than a diversified mandate:
- Higher conviction thresholds appropriate
- Fewer positions → each must clear higher quality bar
- Configurability prevents one-size-fits-all governance

Proposed configuration key: `allocation_policy.yaml:signal_governance`
```yaml
signal_governance:
  zacks_min_advisory: 3       # flag below this
  zacks_min_gate: null        # hard gate (null = disabled)
  danelfin_min_advisory: 6    # flag below this
  danelfin_min_gate: null     # hard gate (null = disabled)
  combined_policy: "C2"       # Z>=4 OR D>=7 advisory
  enforcement: "advisory"     # advisory | soft_penalty | hard_gate
```

---

## Q12: What policy is recommended for CONCENTRATED_ALPHA?

**Recommended: C2-ADVISORY with Z2/D2 soft annotations**

For the CONCENTRATED_ALPHA mandate:
- Apply C2 (Z≥4 OR D≥7) as an advisory check
- Flag but do not exclude symbols failing both signals
- Surface ZACKS_NEUTRAL and DANELFIN_WATCH annotations in the deployment queue UI
- Review gate outcomes at 100+ attribution records before considering hard enforcement
- If promoting to hard gate: use C1 (Z≥4 AND D≥7) not Z2 alone — combined confirmation is stronger signal

**Current queue action items under C2-ADVISORY:**
| Symbol | Status | Note |
|--------|--------|------|
| PCB | Advisory | Zacks=3 flagged; Danelfin=7 offsets — C2 passes |
| MTZ | Advisory | Zacks=3 flagged; Danelfin=9 strong offset — C2 passes |
| All others | Clean | Pass C2 |
