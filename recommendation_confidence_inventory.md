# SIH DECISION-CONFIDENCE-01 - Recommendation Confidence Inventory

## Summary

The requested Candidate Confidence model is feasible from existing artifacts only.

The repository already contains:

- per-provider latest files
- per-symbol provider dates
- candidate symbol lists for CW-DAS, UCF, recommendations, and CRA
- an existing transparency endpoint that already computes symbol-level provider freshness

Implementation complexity is primarily UI placement and naming, not data availability.

## Provider Freshness Fields

| Provider | Primary File | Date Field | Presence Fields | Notes |
|---|---|---|---|---|
| ESS | [data/current/signal_snapshot.csv](/Users/scottmmeyer/Projects/security-intelligence-hub/data/current/signal_snapshot.csv) | `snapshot_date` | `signal_coverage_status`, `starmine_ess_text` | Current intake writes June 22 records after ESS processing. |
| Zacks | [data/signals/zacks/latest_zacks.csv](/Users/scottmmeyer/Projects/security-intelligence-hub/data/signals/zacks/latest_zacks.csv) | `sourced_date` | `zacks_rank`, `zacks_score` | Current latest rows include June 22 dates. |
| Danelfin | [data/signals/danelfin/latest_danelfin.csv](/Users/scottmmeyer/Projects/security-intelligence-hub/data/signals/danelfin/latest_danelfin.csv) | `sourced_date` | `danelfin_raw`, `danelfin_score` | Current sample rows are June 18. |
| Yahoo | [data/signals/yahoo/latest_yahoo_supplemental.csv](/Users/scottmmeyer/Projects/security-intelligence-hub/data/signals/yahoo/latest_yahoo_supplemental.csv) | `sourced_date` | `price_target`, `analyst_count`, `current_price` | Current sample rows are June 18. |
| FMP | [data/signals/fmp/latest/latest_fmp_enriched_universe.csv](/Users/scottmmeyer/Projects/security-intelligence-hub/data/signals/fmp/latest/latest_fmp_enriched_universe.csv) | `fmp_sourced_date` | `fmp_coverage_status` | Current sample rows are June 4. |

## Existing Freshness Logic

Current server logic already exposes:

- freshness threshold in [scripts/run_outcome_ui.py](/Users/scottmmeyer/Projects/security-intelligence-hub/scripts/run_outcome_ui.py#L69)
- provider value presence checks and age classification in [scripts/run_outcome_ui.py](/Users/scottmmeyer/Projects/security-intelligence-hub/scripts/run_outcome_ui.py#L500)
- symbol-set and row payload generation in [scripts/run_outcome_ui.py](/Users/scottmmeyer/Projects/security-intelligence-hub/scripts/run_outcome_ui.py#L673)
- JSON endpoint in [scripts/run_outcome_ui.py](/Users/scottmmeyer/Projects/security-intelligence-hub/scripts/run_outcome_ui.py#L1811)

This means Q1, Q2, Q3, Q4, and Q12 are already operationally answerable from current data.

## Candidate Symbol Sources

| Surface | Source Artifact | Symbol Field | Current Access Pattern |
|---|---|---|---|
| CW-DAS deployment queue | [data/portfolio_ingestion/analysis_runs/PAR-20260622-8E719817/deployment_queue.json](/Users/scottmmeyer/Projects/security-intelligence-hub/data/portfolio_ingestion/analysis_runs/PAR-20260622-8E719817/deployment_queue.json) | `queue[].symbol` | Already read by current transparency logic. |
| UCF rankings | [data/portfolio_ingestion/analysis_runs/PAR-20260622-8E719817/ucf_verdicts.json](/Users/scottmmeyer/Projects/security-intelligence-hub/data/portfolio_ingestion/analysis_runs/PAR-20260622-8E719817/ucf_verdicts.json) | `verdicts[].symbol` | Already read by current transparency logic. |
| Recommendations | [data/portfolio_ingestion/analysis_runs/PAR-20260622-8E719817/recommendations.json](/Users/scottmmeyer/Projects/security-intelligence-hub/data/portfolio_ingestion/analysis_runs/PAR-20260622-8E719817/recommendations.json) | `affected_symbols[]` | Existing transparency payload uses both primary and all symbols. |
| CRA deployments | computed from manifest + runs via CRA builder | `deployments[].symbol` | Current logic builds this on demand from manifest. |
| Reduction candidates | derived in UI from recommendations + overlays + queue | symbol from overlays and recommendation membership | Not yet represented as a dedicated backend artifact. |

## Existing UI Surfaces

There is already a refresh-health presentation layer in outcome visualization:

- Candidate Readiness panel in [ui/outcome_visualization/index.html](/Users/scottmmeyer/Projects/security-intelligence-hub/ui/outcome_visualization/index.html#L994)
- Recommendation Freshness table in [ui/outcome_visualization/index.html](/Users/scottmmeyer/Projects/security-intelligence-hub/ui/outcome_visualization/index.html#L1001)
- client rendering in [ui/outcome_visualization/app.js](/Users/scottmmeyer/Projects/security-intelligence-hub/ui/outcome_visualization/app.js#L1563) and [ui/outcome_visualization/app.js](/Users/scottmmeyer/Projects/security-intelligence-hub/ui/outcome_visualization/app.js#L1588)

This is useful evidence that the backend computation problem is already solved.

## Existing Placement Gap

The operator's trust decision happens in portfolio-action surfaces, not in refresh-health surfaces.

Current capital-decision surfaces:

- deployment queue in [ui/portfolio_alignment/app.js](/Users/scottmmeyer/Projects/security-intelligence-hub/ui/portfolio_alignment/app.js#L4487)
- recommendation cards in [ui/portfolio_alignment/app.js](/Users/scottmmeyer/Projects/security-intelligence-hub/ui/portfolio_alignment/app.js#L3230)
- CRA loader in [ui/portfolio_alignment/app.js](/Users/scottmmeyer/Projects/security-intelligence-hub/ui/portfolio_alignment/app.js#L7762)
- portfolio action pipeline and reduction candidates in [ui/portfolio_alignment/app.js](/Users/scottmmeyer/Projects/security-intelligence-hub/ui/portfolio_alignment/app.js#L582)

None of these currently surface the freshness-derived trust label prominently.

## Existing Confidence Semantics That Must Be Preserved

Two unrelated confidence concepts already exist.

| Existing Confidence | Meaning | Must Change? |
|---|---|---|
| Recommendation `confidence` in [src/portfolio/models.py](/Users/scottmmeyer/Projects/security-intelligence-hub/src/portfolio/models.py#L210) | model or action confidence | No |
| Decomposition / predictive confidence elsewhere | structural or calibration confidence | No |

New Candidate Confidence must not overwrite these.

## FMP Inventory Assessment

FMP matters in two different ways.

- Display-only FMP payload in the run result is explicitly read-only in [src/portfolio/runner.py](/Users/scottmmeyer/Projects/security-intelligence-hub/src/portfolio/runner.py#L1418)
- CW-DAS already incorporates an FMP fundamental modifier in [src/portfolio/deployment_queue.py](/Users/scottmmeyer/Projects/security-intelligence-hub/src/portfolio/deployment_queue.py#L1) and [src/portfolio/deployment_queue.py](/Users/scottmmeyer/Projects/security-intelligence-hub/src/portfolio/deployment_queue.py#L146)

Implication:

- FMP freshness is core to deployment trust for CW-DAS, UCF, and CRA deployment surfaces.
- FMP freshness is supporting context for some recommendation and reduction surfaces.

## Complexity Assessment

| Area | Complexity | Reason |
|---|---|---|
| Provider freshness inventory | Low | Already exists today. |
| Candidate symbol inventory | Low | Already exists today. |
| Symbol-level confidence computation | Low | Existing freshness payload already computes the needed provider states. |
| Multi-symbol recommendation card labeling | Medium | Needs a display-only aggregation rule. |
| Queue, UCF, CRA UI placement | Medium | Multiple renderers need the same badge semantics. |
| Governance risk | Low | Can remain entirely post-hoc and display-only. |

## Inventory Verdict

The repository already contains enough provider dates, symbol sets, and freshness semantics to calculate Candidate Confidence without touching scoring or recomputing the analytical universe.