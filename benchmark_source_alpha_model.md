# Benchmark Source Alpha Model (01B-B)

## Objective

Aggregate recommendation-level benchmark attribution by recommendation_source.

## Source Aggregation Outputs

Persisted target:
- data/history/pis/benchmark_attribution/source_benchmark_summary.csv

Fields:
- recommendation_source
- matched_recommendations
- avg_directional_return_pct
- avg_benchmark_return_pct
- avg_excess_return_pct
- positive_alpha_count
- negative_alpha_count
- alpha_win_rate
- total_directional_attribution
- included_rows
- excluded_rows
- excluded_reason_counts

## Inclusion Rule

Primary alpha metrics only include rows where:
- data_quality_status == OK

Rows with non-OK benchmark status are preserved and counted as excluded for audit visibility.

## Classification

For included rows:
- positive alpha: recommendation_excess_return_pct > 0
- negative alpha: recommendation_excess_return_pct < 0

## API Exposure

- /api/pis/benchmark-attribution/sources
- /api/pis/benchmark-attribution/latest (source_alpha_ranking)

Implementation module:
- src/pis/benchmark_attribution.py
