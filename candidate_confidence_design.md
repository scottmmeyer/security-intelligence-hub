# SIH DECISION-CONFIDENCE-01 - Candidate Confidence Design

## Purpose

Candidate Confidence answers a narrower question than Decision Readiness.

- Decision Readiness: can the operator trust the system's current research universe and portfolio-review posture overall?
- Candidate Confidence: can the operator trust this specific symbol-level recommendation or ranking enough to review or deploy capital now?

This is a display-only transparency layer.

## Non-Goals

- No scoring changes
- No ranking changes
- No CW-DAS formula changes
- No UCF label logic changes
- No recommendation generation changes
- No CRA source/deployment logic changes
- No allocation or sizing changes

## Existing Baseline

The repo already computes provider freshness from existing artifacts.

- Provider freshness threshold: `2` days in [scripts/run_outcome_ui.py](/Users/scottmmeyer/Projects/security-intelligence-hub/scripts/run_outcome_ui.py#L69)
- Per-provider symbol classification: `fresh | stale | missing` in [scripts/run_outcome_ui.py](/Users/scottmmeyer/Projects/security-intelligence-hub/scripts/run_outcome_ui.py#L500)
- Existing symbol-level transparency payload: `/api/refresh-transparency` in [scripts/run_outcome_ui.py](/Users/scottmmeyer/Projects/security-intelligence-hub/scripts/run_outcome_ui.py#L673) and [scripts/run_outcome_ui.py](/Users/scottmmeyer/Projects/security-intelligence-hub/scripts/run_outcome_ui.py#L1811)

The missing piece is placement. The current transparency is in refresh health UI, not attached to the actual deployment and recommendation surfaces.

## Important Semantic Distinction

The system already has a separate recommendation `confidence` field in [src/portfolio/models.py](/Users/scottmmeyer/Projects/security-intelligence-hub/src/portfolio/models.py#L210).

That existing field means action-model confidence inside the recommendation engine, not data-freshness trust confidence.

New Candidate Confidence should therefore be labeled distinctly:

- `Action Confidence`: existing recommendation field
- `Data Confidence`: new freshness-trust transparency label

Without this distinction, operators will confuse model confidence with input freshness confidence.

## Proposed Confidence Inputs

Use only existing artifacts and current freshness semantics.

Per symbol, evaluate:

- ESS freshness from `data/current/signal_snapshot.csv`
- Zacks freshness from `data/signals/zacks/latest_zacks.csv`
- Danelfin freshness from `data/signals/danelfin/latest_danelfin.csv`
- Yahoo freshness from `data/signals/yahoo/latest_yahoo_supplemental.csv`
- FMP freshness from `data/signals/fmp/latest/latest_fmp_enriched_universe.csv`

Each provider already reduces to:

- `fresh`
- `stale`
- `missing`

No new analytical inputs are required.

## Surface-Specific Confidence Model

The cleanest model is surface-specific but still simple.

### 1. Deployment Ranking Surfaces

Applies to:

- CW-DAS queue
- UCF rankings
- CRA deployment candidates

Core providers:

- ESS
- Zacks
- Danelfin
- Yahoo
- FMP

Reason:

- ESS, Zacks, Danelfin, and Yahoo directly influence signal interpretation and overlays.
- FMP is already baked into CW-DAS via the Fundamental Modifier in [src/portfolio/deployment_queue.py](/Users/scottmmeyer/Projects/security-intelligence-hub/src/portfolio/deployment_queue.py#L1) and [src/portfolio/deployment_queue.py](/Users/scottmmeyer/Projects/security-intelligence-hub/src/portfolio/deployment_queue.py#L146).

Proposed label logic:

- `HIGH`: all core providers are `fresh`
- `MEDIUM`: exactly 1 core provider is `stale` or `missing`
- `LOW`: 2 or more core providers are `stale` or `missing`

### 2. Recommendation And Reduction Surfaces

Applies to:

- Recommendation cards
- Portfolio reduction candidates
- Allocation reduction candidates
- Funding-source candidates

Core providers:

- ESS
- Zacks
- Danelfin
- Yahoo

Supporting provider:

- FMP

Reason:

- Many recommendation cards are driven primarily by signal posture, replay, and allocation drift.
- FMP still matters, but not every recommendation is equally dependent on it.

Proposed label logic:

- `HIGH`: all 4 core providers are `fresh`
- `MEDIUM`: all 4 core providers are not `LOW`, but either 1 core provider is `stale/missing` or FMP is `stale/missing`
- `LOW`: 2 or more core providers are `stale/missing`

## Multi-Symbol Recommendation Cards

Some recommendation cards target multiple affected symbols.

Simplest conservative rule:

- compute per-symbol Data Confidence first
- assign card-level Data Confidence from the lowest confidence among directly affected symbols
- include a short note listing which affected symbols caused the downgrade

Example:

- `Data Confidence: MEDIUM`
- `Freshness Issue: MU FMP stale; TSLA Danelfin stale`

This remains display-only and avoids introducing any new ranking behavior.

## Why This Model Is Preferable

- Uses existing provider ages only
- Reuses current freshness threshold
- Requires no analytical recomputation
- Makes deployment trust explicit where decisions happen
- Cleanly separates overall readiness from candidate-level trust

## Recommended Display Behavior

### CW-DAS Queue Row

Show beside the existing CW-DAS score or status cell.

- `CW-DAS: 102.9`
- `Data Confidence: HIGH`

Hover or expand detail:

- ESS: today
- Zacks: today
- Danelfin: 4d stale
- Yahoo: 4d stale
- FMP: 18d stale

### UCF Row

Show beside `ucf_label` or `ucf_score`.

- `CORE_CONVICTION_LEADER`
- `Data Confidence: MEDIUM`

### Recommendation Card

Keep the current recommendation confidence badge, but relabel it.

- `Action Confidence: HIGH`
- `Data Confidence: MEDIUM`

### CRA

Show on:

- deployment rows
- source rows when source symbols are shown

This is especially useful when a source is being sold or trimmed using stale signal inputs.

## Threshold Summary

The current system already defines stale as age greater than `2` days.

No new freshness thresholds are needed for this phase.

## Examples

### Example A - Deployment Candidate

- Symbol: ARW
- ESS fresh
- Zacks fresh
- Danelfin fresh
- Yahoo fresh
- FMP stale

Result:

- CW-DAS / UCF / CRA deployment: `MEDIUM`
- Recommendation/reduction surfaces: `MEDIUM`

Reason: ranking surfaces depend on FMP today; recommendation surfaces should still surface the stale FMP but not silently ignore it.

### Example B - Recommendation Candidate

- Symbol: XYZ
- ESS fresh
- Zacks fresh
- Danelfin stale
- Yahoo fresh
- FMP stale

Result:

- `MEDIUM`

Reason: one core provider stale plus one supporting provider stale.

### Example C - Low Trust

- Symbol: SIMO
- ESS stale
- Danelfin missing
- Yahoo stale

Result:

- `LOW`

Reason: multiple core providers stale or absent.

## Readiness vs Confidence

Both should coexist.

- Readiness is set-level and operational.
- Confidence is candidate-level and decision-facing.

Recommended operator interpretation:

- `Readiness HIGH` + `Candidate Confidence LOW`: system is broadly healthy, but this symbol should be refreshed before capital deployment.
- `Readiness MEDIUM` + `Candidate Confidence HIGH`: the overall environment has some stale pockets, but this candidate is currently well-supported.

That distinction is useful and should not be collapsed into one badge.