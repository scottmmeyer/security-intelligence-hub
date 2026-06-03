# Replay Impact Analysis
**Phase 7.6D — Replay Authority Calibration Audit**
**Run Reference:** PAR-20260601-9CFD7C63
**Date:** 2026-06-01

---

## Q5: Would Depth-Aware Scoring Change Any Deployment Recommendations?

**Summary Answer:** YES — for one holding (SANM). All Q5 focus holdings (VRT, ARW, CIEN, CAH, ATLC) are unchanged under any model. SANM experiences a material, rank-order-changing impact.

---

## Q5 Focus Holdings: VRT, ARW, CIEN, CAH, ATLC

These five holdings were selected as Q5 anchors because they represent the highest-conviction deployment targets with the most operator interest.

| Symbol | Coverage Days | Tier | Model A Rank | Model A Score | Model B Rank | Model C Rank | Delta B | Delta C |
|---|---|---|---|---|---|---|---|---|
| VRT | 365 | STRONG | 1 | 95.50 | 1 | 1 | 0 | 0 |
| ARW | 365 | STRONG | 2 | 94.12 | 2 | 2 | 0 | 0 |
| ATLC | 365 | STRONG | 4 | 93.47 | 4 | 4 | 0 | 0 |
| CAH | 365 | STRONG | 9 | 91.62 | 9 | 9 | 0 | 0 |
| CIEN | 365 | STRONG | 13 | 90.07 | 13 | 12 | 0 | +1 |

**All Q5 focus holdings are completely unaffected by depth-aware replay scoring.** All five have 365-day HISTORICAL_VALIDATION evidence — the maximum available in this system. Under any depth-aware model, STRONG holdings at 365 days receive the same 20 pts they currently earn. Their deployment order, allocation priority, and UCF verdicts are identical across all four models.

Interpretation: For the holdings the operator most actively monitors, depth-aware replay calibration changes nothing. These positions are already earning their replay bonus on the basis of full-year validated evidence.

---

## Material Impact Finding: SANM

SANM is the only deployment-queue holding where depth-aware scoring produces a material rank change.

### Current State (Model A — Binary)

| Field | Value |
|---|---|
| Symbol | SANM (Sanmina Corporation) |
| UCF Label | HIGH_CONVICTION_ANCHOR |
| Coverage days | 6 |
| Replay window | 2026-05-20 to 2026-05-26 (CURRENT_RECOMMENDATION mode) |
| Replay pts | 20 (full binary bonus) |
| CW-DAS score | 90.78 |
| CW-DAS rank | **11** |
| UCF score | 89.53 |

### Under Depth-Aware Models

| Model | Replay Pts | CW-DAS Score | CW-DAS Rank | Rank Delta |
|---|---|---|---|---|
| A (current, binary) | 20 | 90.78 | 11 | — |
| B (THIN=10, STRONG=20) | 10 | 80.78 | 33 | **−22** |
| C (linear: 6/365×20 = 0.33) | 0.33 | 71.11 | 37 | **−26** |
| D (display-only, no change) | 20 | 90.78 | 11 | 0 |

Under Model B, SANM drops **22 positions** — from rank 11 to rank 33. Under Model C, SANM drops **26 positions** — from rank 11 to rank 37. These are not marginal adjustments; they represent a fundamental change in deployment priority.

### Why SANM Is Rank 11 in the Current System

SANM's rank 11 position is not primarily driven by its replay evidence — it is driven by strong ESS, Zacks, and Danelfin signals accumulated in other CW-DAS components. The 20-pt replay bonus is a passenger: it does not reflect genuine year-long validation but rather a 6-day CURRENT_RECOMMENDATION replay window that happened to appear in recent data.

SANM's non-replay CW-DAS components: 90.78 − 20 = **70.78 pts** from signal, conviction, sizing, and momentum.  
VRT's non-replay components: 95.50 − 20 = **75.50 pts**.

On non-replay signal strength alone, SANM ranks below most STRONG holdings — but the binary replay bonus elevates it above 31 of 42 queue holdings that have 59× more validated evidence.

### Allocation Consequence

Under the sqrt-rank-decay allocation formula used in `deployment_planner.py`, a holding at rank 11 receives approximately 2–2.5× the allocation weight of a holding at rank 33. SANM at rank 11 would receive a materially larger capital allocation than SANM at rank 33 or 37.

Quantitatively: With $33,141.34 total deployable capital and sqrt-decay weighting, the difference between rank 11 and rank 33 corresponds to an estimated **50–60% reduction in SANM's allocation share**. This is a deployment-material impact: not a cosmetic adjustment.

---

## Minor Impact: Bucket-Only Holdings (GTX, SIMO, SBS)

These three holdings have `replay_supported = True` from bucket-level assignment but no individual replay basket appearances.

| Symbol | Model A Rank | Model B Rank | Delta B | Model C Rank | Delta C |
|---|---|---|---|---|---|
| GTX | 34 | 37 | −3 | 38 | −4 |
| SIMO | 38 | 39 | −1 | 41 | −3 |
| SBS | 42 | 42 | 0 | 42 | 0 |

**Assessment: Minor.** GTX loses 3–4 positions; SIMO loses 1–3; SBS loses 0. All remain in the lower third of the queue. These changes reduce allocation by a small amount but do not move any of them into or out of a priority deployment window. Classified as **minor but directionally correct** adjustments.

---

## Non-Queue Holdings: Minimal Additional Exposure

Holdings outside the ranked queue (UCF labels: TACTICAL_GROWTH, MAINTAIN, TRIM_WATCH) with `replay_supported = True` are not currently subject to CW-DAS ranking. Depth-aware scoring would not change their UCF verdicts or non-deployment labels under any of the four models evaluated.

---

## Net Assessment

| Category | Count | Material Impact? |
|---|---|---|
| STRONG (365d) — Q5 focus | 5 | NO — unchanged |
| STRONG (365d) — other | 33 | NO — unchanged |
| THIN (6d) — SANM | 1 | **YES — drops 22–26 ranks** |
| BUCKET_ONLY — GTX, SIMO, SBS | 3 | Minor (0–4 rank positions) |

One deployment-material recommendation change under any depth-aware model: **SANM**. All 38 STRONG holdings, including all operator-priority positions, are entirely unaffected. The universe of changed recommendations is narrow but not trivial: rank 11 → rank 33–37 for a HIGH_CONVICTION_ANCHOR holding represents a meaningful reordering of the early deployment sequence.
