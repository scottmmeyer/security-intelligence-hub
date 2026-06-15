# Benchmark Dashboard Design (01B-C)

## Dashboard Sections Added

Six new sections in ui/pis_dashboard/:

| Section | ID | API |
|---|---|---|
| Benchmark Performance Summary | benchmarkSummary | /api/pis/benchmark-attribution/latest |
| Portfolio vs Benchmark Trend | benchmarkTrend | /api/pis/benchmark-attribution/returns |
| Top Alpha Recommendations | benchmarkTopAlpha | /api/pis/benchmark-attribution/latest |
| Lowest Alpha Recommendations | benchmarkLowestAlpha | /api/pis/benchmark-attribution/latest |
| Source Alpha Rankings | benchmarkSourceAlpha | /api/pis/benchmark-attribution/sources |
| Benchmark Quality Summary | benchmarkQuality | /api/pis/benchmark-attribution/latest |

## Subsystem Registration

`benchmarkAttribution` subsystem registered in SUBSYSTEM_DEFINITIONS with all six section keys.

## Quality Badge

`benchmarkQualityBadge(included, excluded)` returns:
- HEALTHY when included >= 80% of total
- DEGRADED when included < 80%
- NO DATA when total == 0

## Progressive Loading

All six benchmark sections follow the same runSectionTask/beginSection/completeSection/failSection pattern as existing sections. Dashboard does not block on benchmark API calls.

## Executive Card

benchmarkSummaryCard added to executive cards grid showing benchmark symbol, latest returns, and quality badge.

## Constraints Respected

- No benchmark calculation changes
- No governance/canonical/change/lineage changes
- No explainability changes
- No Signal Coverage/PRA-IMPL-02 changes
