# Benchmark Recommendation Attribution Model (01B-B)

## Objective

Join recommendation outcome attribution rows to benchmark return intervals and compute recommendation-level excess return versus SPY.

## Input Tables

- data/history/pis/attribution/attribution_records.csv
- data/history/pis/changes/change_records.csv
- data/history/pis/benchmark_attribution/benchmark_return_series.csv

## Join Keys

1. Derive prior_snapshot_date from change records using:
- snapshot_id
- change_id

2. Join benchmark interval using:
- snapshot_date
- prior_snapshot_date

## Computed Fields

- recommendation_return_pct: directional_return_pct
- benchmark_return_pct: benchmark interval return
- recommendation_excess_return_pct: recommendation_return_pct - benchmark_return_pct

## Persistence

Target:
- data/history/pis/benchmark_attribution/recommendation_benchmark_records.csv

Fields:
- snapshot_date
- prior_snapshot_date
- recommendation_id
- symbol
- recommendation_source
- change_type
- directional_return_pct
- benchmark_symbol
- benchmark_return_pct
- recommendation_excess_return_pct
- lineage_confidence
- data_quality_status

Implementation module:
- src/pis/benchmark_attribution.py
