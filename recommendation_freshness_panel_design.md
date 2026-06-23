# Recommendation Freshness Panel Design

## Panel Objective

Show candidate-level freshness for recommendation symbols without changing any scoring or ranking logic.

## Proposed Table

Columns:

- Symbol
- Zacks (date + state)
- Danelfin (date + state)
- Yahoo (date + state)
- ESS (date + state)
- FMP (date + state)
- Freshness Summary

## Data Sources

1. Candidate symbols

- recommendations.json affected_symbols
- deployment_queue.json queue symbols
- ucf_verdicts.json verdict symbols
- /api/cra/proposal deployments symbols

2. Freshness join files

- data/signals/zacks/latest_zacks.csv (sourced_date)
- data/signals/danelfin/latest_danelfin.csv (sourced_date)
- data/signals/yahoo/latest_yahoo_supplemental.csv (sourced_date)
- data/current/signal_snapshot.csv (snapshot_date, signal_coverage_status)
- data/signals/fmp/latest/latest_fmp_enriched_universe.csv (fmp_sourced_date)

## Existing API Sufficiency

- Existing APIs are sufficient to build this panel, but not from one endpoint.
- A UI-side or lightweight API join is needed to merge candidate symbols with provider freshness files.

## Suggested Freshness Summary Labels

- CORE_FRESH: Zacks + Danelfin + Yahoo all fresh.
- CORE_PARTIAL: at least one core provider stale or missing.
- FULL_FRESH: core providers fresh and ESS and FMP fresh.

## UX Behaviors (Display Only)

- Sort by worst freshness first.
- Add quick chips: stale, missing, fresh.
- Add filter toggles for CW-DAS, UCF, Recommendations, CRA.
