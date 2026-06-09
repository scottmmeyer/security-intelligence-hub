# Refresh Coverage Model

Repository: security-intelligence-hub  
Issue: SI-REFRESH-02  
Date: 2026-06-09

## Primary Fields Per Provider

Primary fields are the score fields that constitute the core data value of each provider. Zero coverage on a primary field is treated as a silent partial failure regardless of row count.

| Provider | Primary Fields | Rationale |
|---|---|---|
| Zacks | zacks_rank, zacks_score | These are the values consumed by composite scoring; empty = no Zacks signal |
| Danelfin | danelfin_raw, danelfin_score | Both are required; raw is the input, score is the normalized output |
| Yahoo | price_target, analyst_count, current_price | Core analyst consensus fields; eps_growth_5yr and abr are supplemental |

## All Score Fields Per Provider

| Provider | All Score Fields |
|---|---|
| Zacks | zacks_rank, zacks_score, abr, price_target, eps_growth |
| Danelfin | danelfin_raw, danelfin_score |
| Yahoo | price_target, abr, analyst_count, current_price, upside_pct, eps_growth_5yr |

## Coverage Metrics Computed

| Metric | Definition |
|---|---|
| attempted_count | Rows in latest file with sourced_date = today |
| with_data_count | Rows where at least one primary field is non-empty |
| coverage_pct | (with_data_count / attempted_count) × 100 |
| primary_field_coverage | Per-field: (rows with field non-empty / attempted_count) × 100 |
| degraded_fields | Primary fields with 0% coverage today |
| zero_coverage_fields | All score fields with 0% coverage today (including supplemental) |

## Badge State Logic

| Condition | Badge State |
|---|---|
| sourced_date = today AND coverage_pct >= 95% AND degraded_fields = [] | FRESH |
| sourced_date = today AND (coverage_pct < 95% OR degraded_fields != []) | FRESH_PARTIAL |
| max sourced_date in file ≠ today | STALE |
| Active refresh process detected | REFRESHING |
| File missing | STALE |

## Threshold Rationale

95% coverage threshold: accounts for expected null returns from illiquid or recently-delisted symbols (the Zacks 31/702 case). These are known-expected; systematically present in every run. A hard 100% threshold would produce spurious FRESH_PARTIAL badges daily.

Primary field 0% check: a separate gate catches systematic field failures (e.g., Yahoo `eps_growth_5yr`) regardless of row count coverage.

## Today's State (2026-06-09)

| Provider | Attempted | With Data | Coverage | Primary Fields | Badge |
|---|---|---|---|---|---|
| Zacks | 702 | 671 | 95.6% | zacks_rank/score: 95.6% | FRESH |
| Danelfin | 497 | 497 | 100% | all: 100% | FRESH |
| Yahoo | 697 | 696 | 99.9% | price_target: 98.1%, analyst_count: 98.1% | FRESH_PARTIAL (eps_growth_5yr: 0%) |
