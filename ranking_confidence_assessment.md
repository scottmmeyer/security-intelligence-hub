# SIH DECISION-CONFIDENCE-01 - Ranking Confidence Assessment

## Assessment Frame

This phase should not change any ranking or recommendation outcome. The only valid question is where confidence belongs and what it means on each existing surface.

## Current State

The system already computes candidate freshness at the backend, but it is surfaced as refresh transparency rather than ranking trust.

That means the gap is interpretive and presentational, not computational.

## Surface 1 - CW-DAS Deployment Queue

Source: [data/portfolio_ingestion/analysis_runs/PAR-20260622-8E719817/deployment_queue.json](/Users/scottmmeyer/Projects/security-intelligence-hub/data/portfolio_ingestion/analysis_runs/PAR-20260622-8E719817/deployment_queue.json)

### What confidence means here

Confidence means trust in the freshness of the inputs that shaped the current deployment rank.

That includes:

- signal posture inputs
- analyst inputs
- FMP fundamental modifier inputs

### What confidence does not mean here

- probability of outperformance
- certainty that the top-ranked symbol is the best investment
- any revision to `deployment_score`

### Where it should appear

- directly in the deployment queue row
- optionally in the queue summary strip as distribution counts

### Assessment

This is the highest-value placement because the operator is making capital deployment decisions here.

## Surface 2 - Recommendations

Source: [data/portfolio_ingestion/analysis_runs/PAR-20260622-8E719817/recommendations.json](/Users/scottmmeyer/Projects/security-intelligence-hub/data/portfolio_ingestion/analysis_runs/PAR-20260622-8E719817/recommendations.json)

### What confidence means here

Confidence means trust in the freshness of the underlying symbol data referenced by the recommendation.

For single-symbol cards, that is straightforward.

For multi-symbol cards, confidence means the freshness quality of the affected-symbol set.

### Existing ambiguity

Recommendation cards already show `Confidence: HIGH|MEDIUM|LOW` in the UI, but that is the model-side recommendation confidence from the portfolio engine, not freshness trust.

Current location: [ui/portfolio_alignment/app.js](/Users/scottmmeyer/Projects/security-intelligence-hub/ui/portfolio_alignment/app.js#L3405)

### Assessment

This surface needs the strongest naming discipline.

Recommended labels:

- `Action Confidence` for the existing field
- `Data Confidence` for freshness trust

Without this split, the operator will misread the current badge.

## Surface 3 - UCF Rankings

Source: [data/portfolio_ingestion/analysis_runs/PAR-20260622-8E719817/ucf_verdicts.json](/Users/scottmmeyer/Projects/security-intelligence-hub/data/portfolio_ingestion/analysis_runs/PAR-20260622-8E719817/ucf_verdicts.json)

### What confidence means here

Confidence means trust in the freshness of the data that supports the current UCF label and rank.

Because UCF already references CW-DAS inputs in `source_signals`, this confidence should be interpreted as support-quality, not label-quality.

### Assessment

It belongs beside the UCF label or score, not hidden inside a separate detail drawer.

Suggested rendering:

- `CORE_CONVICTION_LEADER`
- `Data Confidence: HIGH`

## Surface 4 - CRA Deployment Candidates

Source: CRA proposal built from manifest and latest run in [ui/portfolio_alignment/app.js](/Users/scottmmeyer/Projects/security-intelligence-hub/ui/portfolio_alignment/app.js#L7762)

### What confidence means here

For deployment targets:

- trust in the freshness of the target symbol's ranking inputs

For capital sources:

- trust in the freshness of the source symbol's reduction or trim context

### Assessment

CRA should show confidence in both columns, not only on deployment targets.

Reason:

- operator trust matters when selling capital sources as much as when choosing buys

## Surface 5 - Existing Portfolio Reduction Candidates

Current source is UI-derived from overlays, recommendations, and queue state in [ui/portfolio_alignment/app.js](/Users/scottmmeyer/Projects/security-intelligence-hub/ui/portfolio_alignment/app.js#L582)

### What confidence means here

Confidence means trust in the signal and supporting data behind the suggestion to reduce, watch, or fund from a holding.

### Assessment

This surface should receive the same per-symbol Data Confidence badge as deployment candidates.

That keeps operator semantics consistent across buy-side and sell-side actions.

## Simplest Consistent Meaning

Across all surfaces, confidence should mean one thing only:

`How fresh and complete are the currently loaded provider inputs for this candidate or candidate set?`

It should not mean:

- conviction strength
- probability of success
- recommendation urgency
- policy executability

## Relationship To Decision Readiness

Readiness and confidence should coexist.

### Readiness

- set-level
- operational
- answers whether the system is broadly current

### Confidence

- candidate-level
- decision-facing
- answers whether this row or card is being interpreted from fresh enough inputs

## Final Assessment

- CW-DAS: confidence belongs on every candidate row
- Recommendations: confidence belongs on every card, but must be renamed to avoid colliding with the existing `confidence` field
- UCF: confidence belongs beside label or score
- CRA: confidence belongs on both deployment and source candidates
- Reduction candidates: confidence belongs anywhere a symbol is being suggested as an action target or funding source

The meaning is stable across all of them: freshness trust, not analytical strength.