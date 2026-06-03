# Replay Governance Consistency Review
**Phase 7.6D — Replay Authority Calibration Audit**
**Run Reference:** PAR-20260601-9CFD7C63
**Date:** 2026-06-01

---

## Q6: Is the Current Replay Scoring Model Consistent with the Signal Authority Framework?

**Verdict: INCONSISTENT**

The current binary replay scoring model contradicts the stated basis for Replay's Tier 1 authority designation in the Signal Authority Framework (Phase 7.6C) in three specific and measurable ways.

---

## Background: Replay's Tier 1 Authority Claim

The Signal Authority Framework (Phase 7.6C) classified Replay as **Tier 1 authority**, co-equal with ESS, on the following stated basis:

> *"Replay is the only forward-validated signal in the system. It is the only component that has actually observed price behavior following a signal recommendation. That observation is what earns Tier 1 status."*

The framework further stated that Tier 1 authority means:
- Replay evidence is weighted at the highest confidence level
- Disagreements between Replay and lower-tier signals favor Replay
- Replay absence is treated as a disqualifying condition (deployment gate)

The basis for Tier 1 status is explicitly **evidence quality**: the depth, scope, and validity of the forward-performance observation. This makes the following three inconsistencies directly relevant to Tier 1 authority.

---

## Inconsistency 1: Depth Parity Between THIN and STRONG Evidence

**What the framework implies:** Tier 1 authority rests on forward-validated evidence. Deeper, longer-duration evidence justifies higher confidence than shorter, shallower evidence.

**What the scoring model does:** Awards identical 20 pts to SANM (6 days of evidence, 2026-05-20 to 2026-05-26) and VRT (365 days of evidence, 2025-05-14 to 2026-05-14).

**Specific comparison:**

| Holding | Evidence Window | Coverage Days | Mode | Replay Pts (Model A) | Rank |
|---|---|---|---|---|---|
| VRT | 2025-05-14 to 2026-05-14 | 365 | HISTORICAL_VALIDATION | 20 | 1 |
| SANM | 2026-05-20 to 2026-05-26 | 6 | CURRENT_RECOMMENDATION | 20 | 11 |

SANM's 6-day window spans a single week in May 2026. It covers no earnings cycle, no macro event, no seasonal pattern, and no multi-quarter business cycle. VRT's 365-day window spans a full year, capturing at minimum four earnings reports, two Fed cycles, and twelve months of sector rotation.

Under any coherent interpretation of "evidence quality," these represent fundamentally different confidence levels. The binary scoring model cannot represent this difference. As a result, SANM appears at rank 11 — above 31 holdings with 59× more validated evidence — purely because the 6-day replay window was sufficient to trigger `replay_supported = True`.

**Inconsistency verdict:** The scoring model grants Tier 1-equivalent confidence to evidence that does not support Tier 1-quality conclusions.

---

## Inconsistency 2: Bucket-Level Attribution Inflates Individual Confidence

**What the framework implies:** Tier 1 authority is earned by the signal's direct observation of a specific security's behavior following a recommendation.

**What the scoring model does:** Awards the full 20-pt Tier 1 bonus to GTX, SIMO, and SBS despite their never appearing in any replay basket's `selected_symbols` list.

**Specific cases:**

| Symbol | Basket Appearances | Replay Source | Replay Pts | Basis for replay_supported=True |
|---|---|---|---|---|
| GTX | 0 | Bucket assignment | 20 | Sector/cap-bucket qualified |
| SIMO | 0 | Bucket assignment | 20 | Sector/cap-bucket qualified |
| SBS | 0 | Bucket assignment | 20 | Sector/cap-bucket qualified |

These symbols earn the replay bonus because the bucket they belong to passed replay validation — not because they themselves were ever selected as a top-N position in a validated basket. Bucket-level attribution is a reasonable approximation for sector-level exposure, but it is not the same as individual-symbol forward validation.

Tier 1 authority on the basis of "direct observation of price behavior following a recommendation" cannot be honestly applied to symbols that were never selected in the baskets being observed. The current model cannot distinguish individual-validation confidence from bucket-approximation confidence.

**Inconsistency verdict:** The scoring model conflates bucket-level and basket-level evidence under a single 20-pt award that claims Tier 1 authority for both.

---

## Inconsistency 3: Replay Mode Equivalence

**What the framework implies:** HISTORICAL_VALIDATION replays — which explicitly represent backtested performance over a validated historical window — are the evidential foundation for Replay's Tier 1 designation.

**What the scoring model does:** Awards identical pts to CURRENT_RECOMMENDATION replays (recent short windows generated from live recommendations) and HISTORICAL_VALIDATION replays (full-year backtested windows).

**Replay mode definitions present in the data:**
- `HISTORICAL_VALIDATION`: Long-horizon replay constructed from historical price series (e.g., 2025-05-14 to 2026-05-14, 365 days). Provides multi-cycle forward validation.
- `CURRENT_RECOMMENDATION`: Recent-window replay generated from current signal outputs (e.g., 2026-05-20 to 2026-05-26, 6 days). Confirms a holding is currently in the live recommendation set, but does not represent historical forward validation.

SANM's replay evidence is entirely CURRENT_RECOMMENDATION mode — a 6-day recent snapshot. VRT, ARW, ATLC, CAH, CIEN, and 33 other STRONG holdings hold 365-day HISTORICAL_VALIDATION evidence. The scoring model makes no distinction between these two fundamentally different validation contexts.

**Inconsistency verdict:** The scoring model grants the same authority weight to a recent-window snapshot as to a year-long validated backtest.

---

## Governance Framework Violations

Cross-referencing against the Signal Authority Framework decision rules:

| Rule | Framework Statement | Current Behavior | Compliant? |
|---|---|---|---|
| SA-RULE-1 | Weight signals by evidence quality | Binary gate; no evidence quality gradient | NO |
| SA-RULE-3 | Replay depth affects deployment confidence | Depth is not tracked in scoring | NO |
| SA-RULE-4 | Distinguish signal recency from signal validity | Current_recommendation and historical_validation treated identically | NO |
| SA-RULE-5 | Bucket-level evidence is lower confidence than basket-level | Both earn identical 20 pts | NO |

---

## What Would Consistency Require?

A governance-consistent replay scoring model would need to satisfy three minimum conditions:

1. **Depth gradient:** STRONG evidence (180+ days) earns more pts than THIN evidence (<30 days). The maximum pts are reserved for the highest-quality evidence tier.

2. **Mode distinction:** HISTORICAL_VALIDATION replays carry more weight than CURRENT_RECOMMENDATION replays of equivalent duration, because historical validation involves a completed forward period rather than an ongoing snapshot.

3. **Selection level distinction:** Basket-selected symbols earn more pts than bucket-only symbols. Individual selection provides direct observational evidence; bucket qualification provides sector-level approximation.

The current model satisfies none of these three requirements.

---

## Scope Note

This review evaluates governance consistency for PAR-20260601-9CFD7C63 as of 2026-06-01. The inconsistencies identified are structural — they derive from the binary `replay_supported: bool` field design in `src/portfolio/models.py`, which does not support coverage days, evidence mode, or selection level as attributes. Resolving these inconsistencies requires schema and scoring logic changes, not configuration adjustments.

---

## Summary

**Verdict: INCONSISTENT — Three specific violations of the Signal Authority Framework**

1. SANM's 6-day THIN evidence earns identical Tier 1-equivalent pts as VRT's 365-day STRONG evidence.
2. GTX, SIMO, and SBS earn basket-level pts from bucket-level assignment without individual selection.
3. CURRENT_RECOMMENDATION replay evidence (recent snapshot) is treated identically to HISTORICAL_VALIDATION evidence (year-long backtest).

The Signal Authority Framework elevates Replay to Tier 1 on the basis of evidence quality. The scoring model does not implement evidence quality as a variable. These are not edge cases — they are the core operating conditions for 4 of 42 deployment-queue holdings (9.5% of the queue).
