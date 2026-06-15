# Benchmark Quality Policy (01B-B)

## Policy Goal

Preserve all recommendation benchmark attribution rows while preventing unreliable benchmark intervals from contaminating headline alpha metrics.

## Rule

A recommendation row contributes to primary alpha metrics only when:
- data_quality_status == OK

## Non-OK Handling

Non-OK rows are:
- preserved in recommendation_benchmark_records.csv
- excluded from source headline averages and alpha win-rate
- counted in quality summaries

## Exposed Quality Metadata

Across recommendation/source/latest payloads:
- included_rows
- excluded_rows
- excluded_reason_counts

## Typical Non-OK Reasons

- MISSING_BENCHMARK_INTERVAL
- MISSING_BENCHMARK_ENTRY
- MISSING_BENCHMARK_EXIT
- INVALID_BENCHMARK_BASE
- INVALID_PORTFOLIO_BASE

## Determinism

No heuristic overrides are used. Inclusion/exclusion is a strict status rule.
