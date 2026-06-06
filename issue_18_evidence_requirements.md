# ISSUE-18 Evidence Requirements

Repository: security-intelligence-hub  
Date: 2026-06-06

## Q6 — Evidence Thresholds by MCI Maturity Stage

## A) MCI as UI Overlay (Informational-Only)

Required evidence before launch:
1. Deterministic reproducibility: 100% stable labels on replayed identical inputs.
2. Data quality SLO: >= 99% successful ingestion for required context series across 90-day window.
3. Explainability completeness: each label maps to explicit threshold and source fields.
4. Hallucination guard: prohibited causal phrasing tests pass in UI/API text templates.

Go/No-go threshold:
- All four controls PASS for at least 8 consecutive weekly runs.

## B) MCI as Intelligence Signal (still non-scoring)

Required evidence beyond overlay:
1. Operator usefulness validation: >= 70% reviewer agreement that context labels improved interpretation quality in blinded review set.
2. False-attribution rate: <= 10% of reviewed cases where MCI framing contradicted objective market-state evidence.
3. Stability across regimes: context classifier maintains calibration across at least two distinct volatility regimes.

Go/No-go threshold:
- All three criteria pass over >= 2 full quarters of observations.

## C) MCI Influence on CW-DAS

Required evidence (strict):
1. Outcome uplift evidence from shadow-mode simulation:
   - >= +3% median 90-day excess return improvement versus baseline CW-DAS allocation decisions, OR
   - >= 5 percentage point improvement in hit-rate on a comparable decision cohort.
2. No material degradation:
   - max drawdown impact not worse than baseline by > 2 percentage points on evaluation set.
3. Robustness:
   - uplift persists across >= 4 consecutive quarterly cohorts.
4. Governance approvals:
   - formal methodology review
   - formal scoring-governance sign-off

Go/No-go threshold:
- All four pass. If any fail, remain informational-only.

## D) MCI Influence on CRA

Required evidence (strict):
1. Rotation outcome improvement in shadow mode:
   - statistically significant improvement in post-rotation excess returns at 90-day horizon across >= 4 cohorts.
2. Recommendation stability:
   - no increase in contradictory recommendation incidence versus current CRA baseline.
3. Explainability constraint:
   - every CRA action influenced by MCI must include deterministic evidence trace; no narrative-only justifications.
4. Cross-system consistency:
   - PMI, PAP, and CRA interpretations remain non-conflicting under conflict-graph checks.

Go/No-go threshold:
- All four pass; otherwise CRA remains unaffected by MCI.

## Governance Principle

Any scoring or recommendation influence by MCI requires evidence standards equal to or stronger than ISSUE-12 outcome governance. Until then, MCI remains informational.
