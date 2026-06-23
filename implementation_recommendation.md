# SIH DECISION-CONFIDENCE-01 - Implementation Recommendation

## Recommendation Summary

This phase is feasible as a pure transparency enhancement.

The backend already computes nearly everything required through the existing refresh-transparency path. The main recommendation is to reuse that computation, rename the semantics clearly, and surface the result directly on capital-decision UI components.

## Recommended Backend Approach

### Preferred Option

Reuse the existing symbol-level freshness computation in [scripts/run_outcome_ui.py](/Users/scottmmeyer/Projects/security-intelligence-hub/scripts/run_outcome_ui.py#L673).

Keep it display-only.

Suggested behavior:

- continue computing provider states from current artifacts only
- add explicit `data_confidence` per symbol and optionally per candidate set
- do not feed the result back into any scoring or ranking stage

### API Placement

Best API placement:

- extend or alias the existing `/api/refresh-transparency` endpoint

Reason:

- it already knows provider freshness
- it already knows candidate sets
- it already computes row-level symbol coverage

Naming recommendation if changed later:

- `/api/candidate-confidence`

But no architectural need exists to create a second computation path.

## Recommended UI Placement

### 1. Portfolio Alignment App

Primary placement target.

Add Data Confidence to:

- deployment queue rows
- recommendation cards
- CRA deployment rows
- CRA source rows
- portfolio action pipeline rows

This is where the operator decides whether to deploy or reduce capital.

### 2. Outcome Visualization App

Retain the current summary surfaces, but reposition them as monitoring and audit views.

Suggested purpose:

- refresh-health dashboard
- confidence summary table
- debugging stale-provider clusters

This should not be the only place the feature lives.

## Card Placement Recommendation

### Deployment Queue

Place Data Confidence beside:

- `deployment_score`, or
- existing status cell

### Recommendation Cards

Place Data Confidence in the card meta row.

Important naming rule:

- keep existing badge as `Action Confidence`
- add new badge as `Data Confidence`

### UCF

Place Data Confidence beside:

- `ucf_label`, or
- `ucf_score`

### CRA

Place Data Confidence beside each symbol row, not only in a side drawer.

## Whether Confidence Belongs Beside Score, Rank, Or Recommendation

Best answer: beside the thing the operator is reading as the decision anchor.

- CW-DAS row: beside score
- UCF row: beside label or rank
- recommendation card: beside recommendation metadata
- CRA row: beside target/source symbol

It should not be isolated in a separate diagnostics panel.

## Recommended Confidence Semantics

Use a single label family across surfaces:

- `HIGH`
- `MEDIUM`
- `LOW`

Interpretation:

- `HIGH`: current enough to trust without immediate refresh concern
- `MEDIUM`: partially stale or missing, review with caution
- `LOW`: stale enough that refresh or manual verification is warranted before acting

## Why Readiness And Confidence Should Both Exist

They answer different operator questions.

- Readiness: should I trust the system posture broadly?
- Confidence: should I trust this specific row or card now?

Removing one in favor of the other would reduce clarity.

## Governance Recommendation

Document this phase explicitly as:

- post-analysis
- display-only
- not persisted into analytical ranking inputs
- not allowed to alter queue ordering, label assignment, recommendation priority, or CRA outputs

That protects the non-negotiable constraints.

## Final Verdict - Q1 to Q12

### Q1. What provider freshness information already exists per symbol?

Answer: per-symbol freshness already exists for ESS, Zacks, Danelfin, Yahoo, and FMP via current latest files and backend freshness classification.

### Q2. Can we compute candidate confidence using existing freshness metadata without introducing any new calculations that affect rankings?

Answer: yes. The freshness-to-confidence mapping can be derived entirely after rankings are already produced.

### Q3. Which existing files already contain ESS, Zacks, Danelfin, Yahoo, and FMP dates?

Answer:

- ESS: [data/current/signal_snapshot.csv](/Users/scottmmeyer/Projects/security-intelligence-hub/data/current/signal_snapshot.csv)
- Zacks: [data/signals/zacks/latest_zacks.csv](/Users/scottmmeyer/Projects/security-intelligence-hub/data/signals/zacks/latest_zacks.csv)
- Danelfin: [data/signals/danelfin/latest_danelfin.csv](/Users/scottmmeyer/Projects/security-intelligence-hub/data/signals/danelfin/latest_danelfin.csv)
- Yahoo: [data/signals/yahoo/latest_yahoo_supplemental.csv](/Users/scottmmeyer/Projects/security-intelligence-hub/data/signals/yahoo/latest_yahoo_supplemental.csv)
- FMP: [data/signals/fmp/latest/latest_fmp_enriched_universe.csv](/Users/scottmmeyer/Projects/security-intelligence-hub/data/signals/fmp/latest/latest_fmp_enriched_universe.csv)

### Q4. Can candidate confidence be computed entirely from existing provider freshness files?

Answer: yes.

### Q5. What candidate sets should receive confidence indicators?

Answer:

- CW-DAS deployment queue
- UCF rankings
- recommendation cards
- CRA deployment candidates
- CRA source candidates
- existing reduction and funding-source candidates

### Q6. What is the simplest operator-facing confidence model?

Answer: `HIGH | MEDIUM | LOW`, using only counts of fresh, stale, and missing providers with surface-specific core-provider sets.

### Q7. Can confidence be computed independently from readiness?

Answer: yes, and it should be.

### Q8. Does any proposed confidence logic alter rankings?

Answer: no, if computed strictly after artifacts are produced.

### Q9. Does any proposed confidence logic alter recommendation generation?

Answer: no.

### Q10. Does any proposed confidence logic alter deployment decisions?

Answer: no. It changes operator visibility only.

### Q11. Is this entirely display-only?

Answer: yes, if implemented as recommended.

### Q12. Can confidence be calculated from existing artifacts without recomputing the analytical universe?

Answer: yes.

## Final Recommendation

Proceed as a UI transparency phase, not a scoring phase.

Reuse the existing freshness computation, rename the semantics clearly, and attach Data Confidence directly to the rows and cards where capital decisions are actually reviewed.