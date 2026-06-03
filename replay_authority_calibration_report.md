# Replay Authority Calibration Report
**Phase 7.6D — Final Report**
**Run Reference:** PAR-20260601-9CFD7C63
**Date:** 2026-06-01

---

## Audit Question

> *"Evaluate whether Replay should remain a binary deployment gate or evolve into an evidence-weighted confidence signal."*

> *Success condition: "If Replay is Tier 1 authority, should 4 days of evidence and 252 days of evidence really be treated the same?"*

---

## Executive Verdict

**C. ADD_DEPTH_AWARE_REPLAY_SCORING**

The binary gate model is structurally inconsistent with the Tier 1 authority designation established in Phase 7.6C. The evidence for reform is not theoretical: a single holding (SANM) demonstrates a measured, deployment-material impact where 6 days of CURRENT_RECOMMENDATION replay evidence earns the same 20-pt bonus as 365 days of HISTORICAL_VALIDATION evidence, placing SANM at rank 11 above 31 holdings with 59× more validated data. Under depth-aware scoring, SANM drops 22–26 positions — a materially different capital allocation outcome.

---

## Seven-Question Synthesis

### Q1: What replay evidence exists in this run?

**Source:** `replay_evidence_inventory.csv` (81 holdings, 60 US AVAILABLE replays evaluated)

- 257 total replay evidence summaries across INTERNATIONAL and US replays
- 60 US AVAILABLE replays in the relevant domestic set
- Two replay window types present:
  - **365-day window** (HISTORICAL_VALIDATION): 2025-05-14 to 2026-05-14 — the primary year-long backtest
  - **6-day window** (CURRENT_RECOMMENDATION): 2026-05-20 to 2026-05-26 — a recent snapshot from live signal outputs
- SANM appears exclusively in the 6-day CURRENT_RECOMMENDATION window
- 38 STRONG holdings appear in the 365-day HISTORICAL_VALIDATION window
- 3 holdings (GTX, SIMO, SBS) have `replay_supported=True` via bucket assignment but zero basket appearances

---

### Q2: How is replay evidence distributed across the deployment queue?

**Source:** `replay_depth_distribution.md`

| Tier | Coverage Days | Count | Avg CW-DAS | Avg Rank |
|---|---|---|---|---|
| STRONG | 365 | 38 | 87.94 | 19.0 |
| MODERATE | 30–179 | 0 | N/A | N/A |
| THIN | 6 | 1 (SANM) | 90.78 | 11 |
| BUCKET_ONLY | 0 (bucket) | 3 (GTX, SIMO, SBS) | 73.88 | 38 |

**Key finding:** The evidence distribution is bimodal — holdings have either 365 days or 6 days. There is no MODERATE tier in this run. Any depth-aware calibration must handle a binary gap rather than a continuous spectrum.

---

### Q3: Does stronger replay evidence currently receive higher priority?

**Source:** `replay_influence_analysis.md`

**No.** The current system assigns 20 pts to all `replay_supported = True` holdings, regardless of depth. Of 42 ranked holdings, all 42 earn 20 pts. Coverage days have zero correlation with CW-DAS score or deployment rank. The replay component functions as a deployment eligibility gate — not as a confidence-weighted signal. It provides a uniform 20-pt floor but no gradient within the ranked universe.

---

### Q4: How would alternative models affect the queue?

**Source:** `replay_depth_model_comparison.csv`

Four models evaluated:

| Model | Description | Key Difference |
|---|---|---|
| A (current) | Binary: replay_supported → 20/0 pts | Baseline |
| B (tiered) | THIN=10, MODERATE=15, STRONG=20; bucket-only=15 | Step-function by tier |
| C (linear) | days/365 × 20; bucket-only=10 | Continuous gradient |
| D (display-only) | No score change; add coverage_days to output | No scoring impact |

**SANM under each model:**

| Model | Replay Pts | CW-DAS Score | Rank | Delta |
|---|---|---|---|---|
| A | 20 | 90.78 | 11 | — |
| B | 10 | 80.78 | 33 | **−22** |
| C | 0.33 | 71.11 | 37 | **−26** |
| D | 20 | 90.78 | 11 | 0 |

**GTX/SIMO/SBS under Models B and C:** Minor rank changes of 0–4 positions. All remain in lower third of queue.

---

### Q5: Would depth-aware scoring materially change deployment recommendations?

**Source:** `replay_impact_analysis.md`

**Yes — for SANM. No — for all other holdings including all Q5 focus positions.**

Q5 focus holdings (VRT, ARW, CIEN, CAH, ATLC) are entirely unaffected. All five have 365-day STRONG evidence. Their ranks are identical across all four models.

SANM at rank 11 → rank 33 (Model B) or rank 37 (Model C) is a **deployment-material** change. Under sqrt-rank-decay allocation, SANM at rank 11 receives approximately 2–2.5× the capital allocation of SANM at rank 33. This represents an estimated 50–60% reduction in SANM's allocation share — not a cosmetic adjustment.

The finding is narrow in scope (1 holding) but materially significant in consequence.

---

### Q6: Is the current model consistent with the Signal Authority Framework?

**Source:** `replay_governance_consistency_review.md`

**INCONSISTENT — Three documented violations:**

1. **Depth parity:** SANM's 6-day THIN evidence earns identical pts to VRT's 365-day STRONG evidence.
2. **Selection level:** GTX, SIMO, SBS earn basket-level pts from bucket-level assignment without individual selection.
3. **Mode equivalence:** CURRENT_RECOMMENDATION replay (recent snapshot) is treated identically to HISTORICAL_VALIDATION (year-long backtest).

The Signal Authority Framework grants Replay Tier 1 status "because it is the only forward-validated signal in the system." That claim rests on evidence quality. The scoring model does not implement evidence quality as a variable. This is a structural contradiction.

---

### Q7: Should Replay remain a binary gate or evolve into a confidence-weighted signal?

**Answer: Evolve — adopt depth-aware scoring (Model B as recommended minimum).**

The binary gate serves a legitimate purpose — preventing holdings with no replay evidence from entering the deployment queue. That gatekeeping function should be preserved. However, within the `replay_supported = True` universe, the binary model provides no differentiation and therefore no information. Upgrading to a tiered model (Model B) restores the information content that Tier 1 authority is supposed to carry.

---

## Success Condition: Direct Answer

> *"If Replay is Tier 1 authority, should 4 days of evidence and 252 days of evidence really be treated the same?"*

**No. They should not be treated the same.**

The SANM case (6 days vs. 365 days for surrounding holdings) is a live instance of exactly this condition. The answer is not theoretical. SANM earns 20 pts — the same as VRT, ARW, ATLC, CAH, and DELL — from a single 6-day window in May 2026 that spans no earnings, no macro cycle, and no sector rotation. The binary model cannot see this difference. A depth-aware model (Model B or C) restores the evidential distinction that Tier 1 authority requires.

---

## Recommendation

### Adopt Model B: Tiered Depth-Aware Replay Scoring

**Tier mapping:**
- STRONG (180+ days): 20 pts — unchanged from current
- MODERATE (30–179 days): 15 pts — no holdings in current run, but needed for future calibration
- THIN (1–29 days): 10 pts — SANM drops from 20 to 10 pts
- BUCKET_ONLY (0 days, basket-unselected): 15 pts — GTX, SIMO, SBS drop from 20 to 15 pts
- NONE (replay_supported=False): 0 pts — unchanged

**Rationale for Model B over Model C:**
- Model C (linear) is analytically elegant but produces extreme compression: SANM earns 0.33 pts — effectively 0 — which may over-penalize recent-window evidence that is still genuinely informative
- Model B preserves a meaningful reward for THIN evidence (10 pts) while clearly distinguishing it from STRONG evidence (20 pts)
- Model B is operationally transparent: operators can reason about the tier assignment without computing a formula

**Rationale against Model D (display-only):**
- Model D avoids the SANM calibration issue without resolving it
- If Replay is Tier 1 authority on the basis of evidence quality, displaying that quality without scoring it is internally inconsistent
- Model D is appropriate as a transition step (add depth display before changing scoring) but not as a permanent state

**Impact scope:** Narrow. Only SANM (rank 11 → 33, −22 positions) experiences a material change. Q5 focus holdings and all STRONG evidence holders are unaffected.

---

## Implementation Note

This report is analysis-only. No code changes are made in Phase 7.6D.

Implementation would require changes to:
1. **`src/portfolio/models.py`**: Add `replay_coverage_days: Optional[int]` and `replay_evidence_tier: Optional[str]` fields to portfolio models
2. **`src/portfolio/deployment_queue.py`**: Replace binary `replay_pts = 20 if replay_supported else 0` with tiered lookup using evidence tier
3. **Data pipeline**: Propagate coverage days from `replay_evidence_summary.json` through to UCF verdict generation

These changes are out of scope for the current phase. The recommendation establishes the design intent for a future implementation phase.

---

## Deliverable Index

| File | Content | Status |
|---|---|---|
| `replay_evidence_inventory.csv` | 81 holdings with replay appearances, depth tier, basket returns | COMPLETE |
| `replay_depth_distribution.md` | Tier distribution, bimodal finding, SANM anomaly at rank 11 | COMPLETE |
| `replay_influence_analysis.md` | Zero correlation between depth and rank; binary gate analysis | COMPLETE |
| `replay_depth_model_comparison.csv` | 42 queue holdings, 4 models, SANM rank impact | COMPLETE |
| `replay_impact_analysis.md` | Q5 focus: no change; SANM: −22/−26 ranks; minor bucket changes | COMPLETE |
| `replay_governance_consistency_review.md` | 3 inconsistencies with Signal Authority Framework | COMPLETE |
| `replay_authority_calibration_report.md` | Final verdict: C. ADD_DEPTH_AWARE_REPLAY_SCORING | COMPLETE |

**Phase 7.6D Status: `FRAMEWORK_CALIBRATED`**
