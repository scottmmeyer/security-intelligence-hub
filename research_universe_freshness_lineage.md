# Research Universe Freshness Lineage

## Exact Computation Path

Source implementation: `scripts/run_outcome_ui.py`.

The current Research Universe Core Freshness metric is computed in `_compute_candidate_transparency_payload()` by:

1. Loading research-universe symbols from `data/current/analytical_universe.csv`.
2. Loading latest provider caches for Zacks, Danelfin, and Yahoo.
3. Classifying each provider row as `fresh`, `stale`, or `missing` using a 2-day threshold.
4. Marking a symbol `core_fresh` only when Zacks, Danelfin, and Yahoo are all fresh.
5. Computing `core_fresh_pct = core_fresh / total_symbols`.

## Source Files

- `data/current/analytical_universe.csv`
- `data/signals/zacks/latest_zacks.csv`
- `data/signals/danelfin/latest_danelfin.csv`
- `data/signals/yahoo/latest_yahoo_supplemental.csv`

## Freshness Rule

- provider row is `fresh` when its provider date is within 2 days of the current date
- otherwise `stale`
- missing row or missing primary value means `missing`

## Inclusion Criteria

- every unique symbol in `data/current/analytical_universe.csv`

## Exclusion Criteria

- none at the metric layer
- non-covered instruments and structurally weak coverage names remain in the denominator

## Current Live Value

- `53 / 2473`
- `2.1%`

## Important Clarification

This metric does not require ESS freshness and does not require FMP freshness.
It is a three-provider freshness intersection metric over the full analytical-universe denominator.
