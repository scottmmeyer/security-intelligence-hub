# Fund Vehicle Intelligence (FVI) Governance Assessment

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-19 FVI Governance and Controls  
Date: 2026-06-06

## Q4) Data Source Assessment

| Source | Availability | Cost | Reliability | Implementation Complexity | SIH Fit |
|---|---|---|---|---|---|
| Morningstar | Broad fund coverage, category/rank data, manager metadata | Medium-High (licensed) | High | Medium | Strong primary candidate for institutional-grade peer analytics |
| Lipper | Broad categories and peer analytics | Medium-High (licensed) | High | Medium | Strong secondary/backup taxonomy source |
| Yahoo Finance | Public access, uneven depth for fund analytics | Low/Free | Medium-Low to Medium | Low | Useful fallback for basic return/cost fields; insufficient as sole source |
| FMP | Equity/ETF centric; mutual fund depth may be limited | Medium | Medium (for supported fields) | Medium | Supplemental only unless mutual fund coverage improves materially |
| Fidelity/Schwab account views | Strong for held-fund specifics (loads, transaction details) | Low incremental for account users | High for account-specific data | Medium-High integration constraints | Valuable for switching economics on held positions, not full-universe peer analytics |
| Public fund datasets | Variable coverage and freshness | Low | Low-Medium | Medium | Research support only; weak as production primary |

Recommended practical stack for SIH:
1. Primary analytics/taxonomy: Morningstar-class provider
2. Secondary cross-check: Lipper-class taxonomy and rank support
3. Account-specific friction data: brokerage source fields (Fidelity/Schwab)
4. Public/free sources: fallback only

## Q5) Load and Switching Economics Framework

FVI should evaluate replacement on net benefit after switching friction, not on score gap alone.

Required economic components:
1. Upfront load already paid:
- Treat as sunk cost for forward decision quality, but surface in explanation to avoid user distrust.
2. Deferred loads / redemption fees:
- Treat as direct switching friction in decision model.
3. Tax consequences:
- Include estimated realized gain tax drag where taxable account data is available.
4. Transaction costs / spread / operational friction:
- Include explicit and estimated implicit costs.

Decision principle:
- Recommend replacement only when expected forward net benefit exceeds switching friction by a governance margin.

Example policy:
- If Fund A score is 92 and Fund B score is 95, do not recommend replacement by default.
- Require a break-even horizon test showing expected quality advantage can overcome all switching friction within policy horizon.

Minimum governance-safe rule:
- No replacement recommendation if friction-adjusted advantage is below threshold or uncertainty band overlaps zero.

## Q6) Interaction With Existing Systems

### CRA

Recommendation:
- Phase 1: advisory-only overlay
- Phase 2: replacement recommendation policy gate
- No direct CRA score mutation until higher evidence tier

### PAP

Recommendation:
- Use FVI labels to prioritize review queue, not to auto-execute replacement decisions.

### CW-DAS

Recommendation:
- No direct score influence in initial phases.
- Any future score influence requires formal methodology revision and longitudinal evidence.

### PMI

Recommendation:
- Display FVI as implementation-quality context layer, separate from thesis-quality interpretation.

### Allocation Reduction

Recommendation:
- Separate outputs:
  - sleeve action (reduce/hold/increase)
  - vehicle action (retain/watchlist/replace)
- Permit "reduce sleeve, retain best vehicle" outcomes.

## Required Governance Constraints

FVI must:
1. Not assume active management is superior.
2. Not assume passive management is superior.
3. Not recommend replacement without evidence.
4. Provide explainable and auditable rationale for each replacement signal.

## Control Framework

Required controls:
1. Deterministic peer-group assignment logs
2. Immutable evidence snapshot per recommendation
3. Explainability template with factor contributions and friction-adjusted economics
4. Human override with reason capture
5. Periodic false-positive replacement audit

Governance posture recommendation:
- Start advisory-only.
- Promote influence only after demonstrated decision quality improvement and low false-replacement incidence.
