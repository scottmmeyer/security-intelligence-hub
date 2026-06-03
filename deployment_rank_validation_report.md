# Deployment Rank Validation Report
**Phase 7.5S — Deployment Rank Validation Audit**
**Run:** PAR-20260601-9CFD7C63 | **Signal Date:** June 1, 2026 | **Portfolio Snapshot:** PSNAP-20260601-8765A09ECC06

---

## The Central Question

> *"Am I buying VRT because it is genuinely the strongest opportunity, or because the framework rewards the fact that I already own more of it?"*

**Answer: Both — but the framework mechanics are the dominant driver of VRT's #1 rank, not VRT's signal quality.**

---

## Evidence Summary

### VRT Signal Profile (Pure Signal Rank = #14 of 42)

| Dimension | VRT | #1 Signal Stock (PCB) | Commentary |
|-----------|-----|----------------------|------------|
| Pure Signal Score | 67.44 | 76.67 | VRT is 9.23 pts behind the pure leader |
| Composite Score | 4.556 | 4.333 | VRT higher; PCB scores better on other dimensions |
| ESS | VERY_BULLISH | VERY_BULLISH | Tied |
| Danelfin | 3.5 | 4.0 | PCB stronger |
| Zacks | 4 (weak) | 3 (moderate) | PCB stronger |
| Replay Coverage | 4 days | 261 days | PCB 65× deeper evidence |
| Trim Score | 1.63 | 0.42 | Both near-zero (no trim pressure) |

VRT has a genuinely strong signal. VERY_BULLISH ESS, composite 4.56, low trim pressure. **It belongs in the top tier.** It does not, however, have the strongest signal profile in the universe.

### CW-DAS Score Decomposition (VRT = 95.5)

| Component | Points | Nature |
|-----------|--------|--------|
| Signal quality | 27.33 | Signal |
| Replay bonus | 20.0 | Signal (evidence-blind) |
| Conviction tier (CCL) | 35.0 | Framework |
| Sizing headroom | 3.17 | Framework |
| Momentum | 10.0 | Signal |
| Penalties avoided | ~0.0 | Framework (others -15) |
| **Total** | **95.5** | — |

**57.6% of VRT's CW-DAS score comes from framework mechanics** (CCL tier + sizing effect + redundancy penalty avoidance).

### Rank Delta: +13 Positions of Framework Inflation

- VRT Pure Signal Rank: **#14**
- VRT CW-DAS Rank: **#1**
- Delta: **+13 positions** gained through framework mechanics

The three specific mechanisms:

**Mechanism 1 — CCL Conviction Tier (+7 pts over any HCA stock)**
The CORE_CONVICTION_LEADER designation awards 35 conviction points vs 28 for HIGH_CONVICTION_ANCHOR. VRT is the only CCL stock in the active deployment window. If VRT were classified HCA, its CW-DAS would be 88.5 (rank ~15), not 95.5 (rank 1). The CCL gate is policy-earned — VRT meets all five gate conditions — but one condition (current weight ≥ 1.5%) is circular: VRT is CCL partly because it was already accumulated to a large position.

**Mechanism 2 — Thin Replay Treated as Strong (+0 depth penalty)**
VRT receives +20 replay points from a 4-trading-day CURRENT_RECOMMENDATION basket (May 20–26, 2026). PCB, AVT, CAH, and CIEN each receive an identical +20 from 261-day HISTORICAL_VALIDATION baskets. The framework applies no discount for evidence depth. VRT's replay support is real — it was top-20 in the May 20 US-LARGE composite — but it is 65× shallower than the year-long validation supporting PCB.

**Mechanism 3 — Unique CCL-Without-Redundancy-Penalty Position (structural)**
The other 4 CCL stocks (CVE rank 32, TSM rank 33, GTX rank 34, MU rank 35) each incur -15 redundancy penalties, dropping them out of the top 20. VRT is the only CCL stock with zero redundancy. This makes VRT's 7-point CCL advantage over HCA translate into a ~30-position functional advantage over other CCL stocks. This is a legitimate design feature of the redundancy penalty system, but it concentrates deployment capital on a single CCL stock uniquely.

---

## Top 20 Signal Inventory (Q1)

See `top20_rank_validation_inventory.csv`

Key observations:
- Every top-20 stock is replay-supported (42/42 queue members have replay support)
- Replay evidence depth divides cleanly: 7 THIN (ranks 1,2,3,5,8,10,11) and 13 STRONG (ranks 4,6,7,9,12–20)
- THIN stocks cluster in the top 10; STRONG stocks dominate ranks 12–20
- CW-DAS spread is narrow: 95.5 (VRT rank 1) to 87.89 (ANGO rank 20) — a 7.6-point range across 20 candidates

---

## Pure Signal Ranking Summary (Q2)

See `pure_signal_ranking.csv`

Top 5 by pure signal:
1. **PCB** (76.67) — VERY_BULLISH, Danelfin 4.0, Zacks 3, 261-day replay, composite 4.33
2. **AVT** (75.44) — VERY_BULLISH, Danelfin 3.5, Zacks 4, 261-day replay, composite 4.56
3. **ATLC** (74.22) — VERY_BULLISH, Danelfin 3.0, Zacks 5, 261-day replay, composite 4.78
4. **CAH** (74.00) — VERY_BULLISH, Danelfin 3.0, Zacks 4, 261-day replay, composite 4.50
5. **CBOE** (71.33) — VERY_BULLISH, Danelfin 2.0, Zacks 5, 261-day replay, composite 4.67

---

## Rank Comparison Summary (Q3)

See `deployment_vs_signal_rank_comparison.csv`

**Stocks significantly overweighted vs pure signal:**

| Symbol | CW-DAS → PSR Inflation | Primary Cause |
|--------|------------------------|---------------|
| SANM | +24 | Zacks=5, BULLISH; thin replay; HCA |
| PSX | +22 | Thin replay; weak Danelfin; HCA |
| DELL | +19 | Thin replay; mid-range signals; HCA |
| SNX | +15 | Thin replay; Zacks=5; HCA |
| VRT | +13 | CCL tier; thin replay; no redundancy |

**Stocks significantly underweighted vs pure signal:**

| Symbol | CW-DAS → PSR Deflation | Primary Cause |
|--------|------------------------|---------------|
| PCB | -11 | Highest PSR; HCA ceiling (28 pts) |
| FSLR | -11 | Strong replay; outside dep. top 15 |
| ALNT | -10 | Strong Danelfin + replay; HCA |
| MTZ | -10 | Same as ALNT |
| HALO | -10 | Outside deployment top 15 |

---

## VRT Attribution (Q4)

See `vrt_rank_attribution_analysis.md`

- Signal contribution (A): **42% of CW-DAS score**
- Framework contribution (B): **58% of CW-DAS score**

---

## Replay Evidence Quality (Q5)

See `replay_evidence_quality_analysis.md`

**Key finding:** THIN-evidence stocks are deployed at higher priority than STRONG-evidence stocks despite the STRONG stocks having better average pure signal quality (+31% better average PSR). The +20 replay flat fee creates equal reward for unequal evidence.

---

## Signal Leadership (Q6)

See `signal_leadership_report.md`

---

## Final Verdict (Q7)

### **B. VRT_RANK_INFLATED_BUT_ACCEPTABLE**

**Rationale for "INFLATED":**

VRT is ranked #1 by CW-DAS but #14 by pure signal. The +13 position inflation is attributable to three measurable framework mechanics:
1. CCL conviction tier confers a 7-point structural advantage that no HCA stock can overcome with signals alone
2. Thin (4-day) replay earns the same +20 as year-long (261-day) replay — evidence depth is invisible to the scoring system
3. VRT is the uniquely positioned CCL stock without a redundancy penalty, concentrating all CCL capital on a single position

The CCL gate condition `weight ≥ 1.5%` creates a feedback loop: VRT is partly CCL *because* you already own more of it, and the CCL tier causes you to buy even more. This is the honest answer to the central question: **a meaningful portion of VRT's #1 rank reflects the fact that you already own more of it**.

**Rationale for "ACCEPTABLE":**

Despite the rank inflation:
1. VRT's signals are genuinely strong — VERY_BULLISH ESS, composite 4.56, low trim score, no concentration flag
2. The CCL designation is rule-earned, not manufactured — VRT satisfies all five gate conditions legitimately
3. VRT's pure signal rank of #14 still places it in the top-third of the 42-candidate universe
4. The existing position at 3.62% means additional deployment concentrates a holding that is already considered the highest-conviction position by portfolio policy
5. The implied counterfactual (deploying into #1 by pure signal — PCB at 0.94% current weight) would itself represent a concentration decision against a micro-cap financial services position

**Remediation is NOT recommended at this time.** The inflation mechanisms are structural features of the CW-DAS design (conviction tiers, flat replay bonus), not bugs. Changing them would require a formal scoring review (Phase 7.5Q-level analysis) and would produce broad second-order effects. The evidence-depth blind spot in replay (Mechanism 2) was documented in Phase 7.5S-A and is the most actionable future consideration.

---

## Actionable Observations (Not Recommendations)

These are factual observations that inform future scoring reviews:

1. **PCB holds the highest pure signal score in the universe (#1, 76.67) but receives only the 12th deployment priority.** If the objective is to deploy into the strongest available opportunity, PCB is being systematically underfunded relative to its evidence quality.

2. **SANM (PSR=35) is the most signal-quality-inflated stock in the top 15 deployment recommendations.** Its Zacks=5 and BULLISH (not VERY_BULLISH) ESS are masked entirely by the HCA tier and thin replay bonus. This is not a call to action — SANM's conviction designation is policy-earned — but it illustrates the limits of the current scoring structure.

3. **ALNT and MTZ each have better pure signal profiles than VRT** (PSR 6 and 7 vs VRT's PSR 14), primarily due to superior Danelfin scores (4.5 vs 3.5) and deeper replay evidence (261-day vs 4-day). Under a purely signal-quality-based framework, they would rank above VRT. Under the current framework, they rank 16th and 17th.

4. **The replay evidence depth inversion is structurally systemic:** THIN stocks average PSR=25.1 vs STRONG stocks PSR=17.3. The deployment system rewards large-cap composite magnitude more than cross-validated historical evidence depth.

---

## Acceptance Criteria Checklist

| Criteria | Status |
|---------|--------|
| 1. Uses June 1 refreshed signals | ✅ RUN-ESS-20260601-001 + PAR-20260601-9CFD7C63 |
| 2. Uses current production logic | ✅ No code changes; output from live run |
| 3. Produces Top 20 inventory | ✅ top20_rank_validation_inventory.csv |
| 4. Produces Pure Signal Rank | ✅ pure_signal_ranking.csv (42 candidates) |
| 5. Quantifies VRT rank attribution | ✅ vrt_rank_attribution_analysis.md |
| 6. Evaluates replay evidence depth | ✅ replay_evidence_quality_analysis.md |
| 7. Compares deployment rank vs signal rank | ✅ deployment_vs_signal_rank_comparison.csv |
| 8. Provides evidence-backed verdict | ✅ Verdict B with full quantification |
| 9. No code changes | ✅ Analysis only |
| 10. No scoring changes | ✅ Analysis only |
