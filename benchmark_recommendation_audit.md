# PERFORMANCE-ATTRIBUTION-01B-D Phase 2 Audit

## Scope

Inspected:
- data/history/pis/benchmark_attribution/recommendation_benchmark_records.csv

## Answers

Q6. How many recommendation benchmark rows exist?
- 28 data rows.

Q7. How many rows are included?
- 0 rows (data_quality_status = OK).

Q8. How many rows are excluded?
- 28 rows.

Q9. Show exclusion counts by reason.

| exclusion_reason | row_count |
|---|---:|
| MISSING_BENCHMARK_ENTRY | 28 |

Q10. Are any recommendation rows eligible for alpha calculations?
- No. Eligibility is 0 because no recommendation row has data_quality_status = OK.

## Evidence Notes

- benchmark_return_pct is 0.0 on all recommendation rows.
- recommendation_excess_return_pct currently mirrors directional_return_pct because benchmark contribution is zeroed under exclusion status.
