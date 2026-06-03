# Replay Influence Analysis
**Phase 7.6D — Replay Authority Calibration Audit**
**Run Reference:** PAR-20260601-9CFD7C63
**Date:** 2026-06-01

---

## Q3: Does Stronger Replay Evidence Currently Receive Higher Deployment Priority?

**Answer: NO.**

Under the current binary scoring model, stronger replay evidence does **not** receive higher deployment priority. Holdings with 365 days of validated evidence are scored identically to holdings with 6 days of evidence. The replay component of CW-DAS provides no discrimination based on evidence quality, recency, or depth.

---

## Mechanism Analysis

### How Replay Currently Influences CW-DAS

The replay component of CW-DAS is implemented as a binary gate in `src/portfolio/deployment_queue.py`:

```
replay_pts = 20 if replay_supported == True else 0
CW-DAS = signal_pts + replay_pts + conviction_pts + sizing_pts + momentum_pts
```

The system evaluates `replay_supported: bool` only — set at the bucket level in `src/portfolio/models.py`. No field tracks coverage days, evidence depth, recency, or basket-level selection. The field `replay_percentile` exists in the model schema but is null for all 81 holdings in PAR-20260601-9CFD7C63.

### Replay Point Distribution in the Deployment Queue (Model A)

Of 42 CW-DAS ranked holdings:

| Replay Pts Earned | Count | Holdings |
|---|---|---|
| 20 pts | 42 | ALL ranked holdings |
| 0 pts | 0 | None |

**Every single ranked holding earns the maximum replay bonus.** There is zero variance in the replay component across the entire deployment queue. Replay pts contribute 20 of the theoretical 103-pt maximum for every holding without exception.

### Correlation: Coverage Days vs. Deployment Priority

| Correlation Metric | Value | Interpretation |
|---|---|---|
| r(coverage_days, CW-DAS_score) | ≈ 0.00 | No linear relationship |
| r(coverage_days, deployment_rank) | ≈ 0.00 | Coverage depth has no effect on rank |

The correlation is structurally zero for the ranked queue: the replay scoring function does not accept coverage days as an input. The only coverage-days variance in the queue comes from SANM (6 days) vs. the STRONG holdings (365 days), yet SANM earns identical replay pts (20) to VRT (365 days, rank 1). The difference in rank between SANM (11) and VRT (1) is entirely explained by other CW-DAS components — not by replay.

---

## Evidence of Depth-Blindness

### Case 1: SANM at Rank 11 with 6 Days of Evidence

| Holding | Coverage Days | Replay Tier | Replay Pts (Model A) | CW-DAS | Rank |
|---|---|---|---|---|---|
| VRT | 365 | STRONG | 20 | 95.50 | 1 |
| ARW | 365 | STRONG | 20 | 94.12 | 2 |
| ATLC | 365 | STRONG | 20 | 93.47 | 4 |
| CAH | 365 | STRONG | 20 | 91.62 | 9 |
| DELL | 365 | STRONG | 20 | 90.91 | 10 |
| **SANM** | **6** | **THIN** | **20** | **90.78** | **11** |
| PCB | 365 | STRONG | 20 | 90.75 | 12 |
| CIEN | 365 | STRONG | 20 | 90.07 | 13 |

SANM ranks 11th, above CIEN, NUE, ALNT, MTZ, CRS, CMCO, and 30+ other holdings — all of which have 59× more replay evidence than SANM. The system does not see this disparity.

### Case 2: Bucket-Only Holdings Earn Full Basket-Level Points

GTX, SIMO, and SBS earn 20 pts each despite never appearing in any replay basket's `selected_symbols` list. Their `replay_supported = True` derives from sector/cap-bucket assignment. The system cannot distinguish between:
- A symbol individually selected and validated in a basket (VRT, ARW, SANM)
- A symbol that qualifies because its bucket passed (GTX, SIMO, SBS)

Both receive identical 20-pt bonuses.

---

## Why This Matters (Deployment Priority Consequences)

The replay component was elevated to **Tier 1 authority** in the Signal Authority Framework (Phase 7.6C) because Replay is "the only forward-validated signal in the system." The justification for that elevated status rests on the quality and depth of the evidence it represents.

Yet in practice:
- **6 days of CURRENT_RECOMMENDATION replay** (SANM) = 20 pts
- **365 days of HISTORICAL_VALIDATION replay** (VRT) = 20 pts
- **0 days of individual selection, bucket-only** (GTX, SIMO, SBS) = 20 pts

All three fundamentally different evidence categories produce the same deployment score contribution. The replay component has been effectively neutralized as a differentiating signal within the deployment queue: it adds a uniform 20-pt floor across the ranked universe but provides no gradient.

---

## Current Replay Component: Function vs. Stated Purpose

| Stated Purpose | Actual Function |
|---|---|
| Signal that a holding has validated forward performance | Enables queue entry (gatekeeping) |
| Provide higher confidence when evidence is deeper | Does not differentiate depth |
| Distinguish historically-validated from recently-sampled | Treats all as identical |
| Support Tier 1 authority based on evidence quality | Contributes a flat bonus only |

The current replay component functions as a **deployment eligibility gate** — not as a **confidence-weighted signal**. Every holding that clears the gate receives the same 20 pts regardless of whether the gate was cleared by 365 days of validated data or 6 days of a recent snapshot.

---

## Summary

Replay evidence depth has zero influence on current deployment priority. The binary scoring model treats all `replay_supported = True` holdings identically, producing a flat 20-pt reward that does not distinguish STRONG evidence from THIN evidence or basket-level selection from bucket-level assignment. The correlation between replay depth and deployment rank is structurally zero: the scoring function does not accept depth as an input.
