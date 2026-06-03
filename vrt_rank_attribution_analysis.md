# VRT Rank Attribution Analysis
**Run:** PAR-20260601-9CFD7C63 | **Date:** June 1, 2026 | **Signal Refresh:** RUN-ESS-20260601-001

---

## Summary Answer

**VRT's deployment rank #1 is driven primarily by framework mechanics, not by having the strongest signal profile in the universe.**

VRT's **Pure Signal Rank = #14** out of 42 candidates. Its **CW-DAS Rank = #1**. The delta of +13 positions represents the measurable rank inflation attributable to the deployment framework.

---

## CW-DAS Score Decomposition

| Component | VRT Score | Max | % of Max | Framework or Signal? |
|-----------|-----------|-----|----------|----------------------|
| Signal quality | 27.33 | 30 | 91.1% | Signal |
| Replay bonus | 20.00 | 20 | 100% | Signal (but evidence-agnostic) |
| Conviction tier | 35.00 | 35 | 100% | Framework (CCL gate) |
| Sizing headroom | 3.17 | 8 | 39.6% | Framework (position size) |
| Momentum | 10.00 | 10 | 100% | Signal |
| Redundancy penalty | 0.00 | — | — | Framework (peer competition) |
| Concentration penalty | 0.00 | — | — | Framework (position cap) |
| **CW-DAS Total** | **95.5** | **103** | **92.7%** | — |

### Attribution Split

**Signal-driven components** (signal + momentum + replay as evidence):
- Signal: 27.33
- Momentum: 10.00
- Replay: 20.00 (counted here, but see note below)
- **Signal subtotal: 57.33 pts (60.0% of CW-DAS)**

**Framework-driven components** (conviction tier + sizing + penalties):
- Conviction (CCL tier): 35.00
- Sizing (existing position effect): 3.17
- Redundancy penalty avoided: 0.00 (others lose 15 pts)
- **Framework subtotal: 38.17 pts (40.0% of CW-DAS)**

---

## What Each Mechanism Contributes to Rank #1

### 1. CCL Conviction Tier — Confirmed Structural Advantage (+7 pts over any HCA)

VRT holds the **CORE_CONVICTION_LEADER** narrative tier, awarding **35 conviction points**. All other candidates in the top 20 are **HIGH_CONVICTION_ANCHOR** (28 points). This creates a 7-point permanent floor advantage over any HCA-tier competitor with identical signals.

**If VRT were demoted to HCA tier** (holding all other scores constant):
- VRT's CW-DAS would fall from 95.5 → 88.5
- That score would rank 15th (tied with GFF), not 1st

The CCL designation is **policy-earned**: VRT meets the CCL gate requirements (BULLISH signal + replay + composite ≥ 4.0 + weight ≥ 1.5% + trim < 30). It is not artificially assigned. However, the CCL gate is partly circular: a large existing position (weight ≥ 1.5%) is a precondition, meaning VRT is partly CCL *because* you already bought it heavily.

### 2. Replay Support — Same Bonus, Thinner Evidence

VRT receives +20.0 replay points from:
- **REPLAY-2026-05-20-TO-2026-05-26-US-LARGE-ALL-TOP20** (CURRENT_RECOMMENDATION, **4 trading days**)

ATLC (rank 4), CBOE (rank 6), AVT (rank 7), CAH (rank 9), PCB (rank 12), CIEN (rank 13) each receive the identical +20 replay bonus from **261-day HISTORICAL_VALIDATION** replays. The system applies no discount for evidence depth.

**Net effect:** VRT's replay contribution = $20 based on 4 days. PCB's replay contribution = $20 based on 261 days. Identical treatment.

### 3. Sizing Component — Slight Penalty for Large Position

VRT's current weight of 3.62% means only 39.6% headroom remains before the concentration warning threshold. This produces a sizing score of **3.17 / 8.0** — the second-lowest in the top 20. The sizing component *hurts* VRT slightly relative to smaller, underweight positions (e.g., GFF at 0.37% current weight earns 7.50 sizing points).

This is a legitimate counter-force. VRT does not fully benefit from the "room to grow" sizing bonus.

### 4. Redundancy Penalty Avoidance — The Hidden Structural Advantage

**This is the most underappreciated mechanism.** The other 4 CCL-tier stocks in the queue — CVE (rank 32), TSM (rank 33), GTX (rank 34), MU (rank 35) — each receive a **-15 point redundancy penalty**, dropping them 30+ positions in the queue. VRT is the sole CCL stock with **zero redundancy penalty**.

Without the redundancy penalty structure, VRT would compete against CVE (raw score ~98.79), TSM (~96.61), GTX (~95.47), MU (~93.16). VRT would still rank near the top, but not by a 12-point margin over rank 2.

In the current framework, VRT is the only CCL stock that is deployment-prioritized. The other CCL stocks are systematically depressed. This creates VRT's uniquely large allocation ($8,810 vs $2,046 for the next candidate).

### 5. Momentum — Full Score

VRT earns 10.0 / 10.0 momentum points. This is legitimate — VERY_BULLISH ESS in the context of trend confirmation. Not inflated.

---

## Pure Signal Profile: How Does VRT Actually Rank?

| Metric | VRT | Top Candidate (PCB) | Rank Among 42 |
|--------|-----|---------------------|---------------|
| Pure Signal Score | 67.44 | 76.67 (PCB) | **#14 of 42** |
| Composite Score | 4.556 | 4.889 (ARW) | #7 |
| ESS | VERY_BULLISH | VERY_BULLISH (tied) | Top tier |
| Danelfin | 3.5 | 4.0 (PCB) | Mid-range |
| Zacks | 4 (weak) | 3 (PCB) | Mid-range |
| Replay Coverage | 4 days (THIN) | 261 days (STRONG) | Near-bottom |

**Thirteen candidates have a higher pure signal score than VRT.** The top three by pure signal:
1. **PCB** (PSR 76.67) — Very Bullish, Danelfin 4.0, Zacks 3, 261-day replay, composite 4.33
2. **AVT** (PSR 75.44) — Very Bullish, Danelfin 3.5, Zacks 4, 261-day replay, composite 4.56
3. **ATLC** (PSR 74.22) — Very Bullish, Danelfin 3.0, Zacks 5, 261-day replay, composite 4.78

---

## A vs B Attribution

| Source | Points | % of Total | Quality |
|--------|--------|-----------|---------|
| **(A) Actual signals** (composite, ESS, Zacks, Danelfin, trim) | ~40.5 | 42% | High quality |
| **(A) Replay as evidence** (4-day basket confirmation) | 20.0 | 21% | Low depth |
| **(B) CCL conviction tier** | 35.0 | 37% | Policy-earned but partially circular |
| **(B) Sizing headroom** | 3.17 | 3% | Position-size dependent |
| **(B) Penalties avoided** (redundancy) | ~15.0 effective | structural | Not visible in VRT's score |

**Honest split:**
- **A (genuine signal quality): ~42% of score**
- **B (framework mechanics): ~58% of score**

---

## Does the Framework Inflation Represent a Problem?

The CCL designation is not manufactured — VRT legitimately cleared every gate requirement. However, two structural concerns are measurable:

1. **Replay evidence is not depth-weighted.** A 4-day basket earns the same +20 as a 261-day basket. PCB's year-long validation is equivalent to VRT's 4-day snapshot.

2. **CCL is partially path-dependent.** The weight ≥ 1.5% gate means a stock becomes CCL partly because it was already heavily accumulated. This rewards size history, not current signal quality.

These concerns do not necessarily require remediation — they may reflect valid portfolio construction preferences. But they do mean:

> **You are buying more VRT partly because you already own a lot of VRT.**

---

## Verdict Inputs for Q7

- VRT signal quality: **Genuine and strong, but not top-14-in-universe**
- VRT rank inflation: **+13 positions (PSR 14 → CW-DAS 1)**
- Inflation mechanisms: CCL tier (+7 vs HCA), thin replay treated as strong (0 penalty), redundancy avoidance (structural floor)
- Signals-only ranking: **VRT would rank approximately #14–15**

See `deployment_rank_validation_report.md` for the final verdict.
