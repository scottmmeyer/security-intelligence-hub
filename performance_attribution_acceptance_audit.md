# PERFORMANCE-ATTRIBUTION-01B Acceptance Audit

## Scope Check

The delivered PIS implementation does not provide benchmark attribution.

What exists in the PIS path is recommendation outcome attribution over canonical-governed change and lineage data. The benchmark-specific pieces the issue asks for, such as portfolio return vs SPY, benchmark return, excess return, and source alpha ranking, are not implemented in the PIS feature set reviewed here.

There is a separate legacy SPY outcome engine in [src/portfolio/outcome_tracker.py](src/portfolio/outcome_tracker.py), but it is not wired into the PIS dashboard or the PIS attribution APIs reviewed below.

## Answers

### Q1. Is this portfolio performance attribution, recommendation outcome attribution, or both?

Only recommendation outcome attribution is implemented in the PIS codebase reviewed here.

The reviewed PIS feature joins canonical-governed change records to recommendation lineage rows and classifies outcomes. It does not compute benchmark-relative portfolio performance attribution.

### Q2. How is `return_pct` calculated?

No benchmark `return_pct` is calculated in the PIS implementation.

The closest existing return-like field is `directional_return_pct` in [src/pis/performance_attribution.py](src/pis/performance_attribution.py), which is calculated as:

`directional_return_pct = (directional_attribution / baseline) * 100`

Where:
- `directional_attribution = delta_market_value * direction_multiplier`
- `direction_multiplier = 1` for `NEW_POSITION` and `INCREASED`
- `direction_multiplier = -1` for `EXITED_POSITION` and `REDUCED`
- `baseline = abs(old_market_value)` when non-zero, otherwise `abs(new_market_value)`

Source fields used by that existing calculation:
- `old_market_value`
- `new_market_value`
- `delta_market_value`
- `change_type`

That is recommendation outcome math, not benchmark attribution math.

### Q3. What defines `entry_value` and `current_value`?

These fields are not implemented for PIS benchmark attribution.

The reviewed PIS code does not define benchmark entry/current values. The only comparable values in the existing recommendation outcome layer are the market-value fields used for directional attribution:
- baseline uses `abs(old_market_value)` or `abs(new_market_value)`
- the current change impact is derived from `delta_market_value`

### Q4. Are calculations based on canonical daily history, recommendation lineage, current portfolio state, or some other source?

The implemented PIS calculations are based on canonical daily change history plus recommendation lineage.

Specifically:
- [src/pis/change_detection.py](src/pis/change_detection.py)
- [src/pis/recommendation_lineage.py](src/pis/recommendation_lineage.py)
- [src/pis/performance_attribution.py](src/pis/performance_attribution.py)

They are not based on current portfolio state, and they do not reference a benchmark series.

### Q5. Was benchmark attribution implemented?

No.

There is no PIS benchmark source, no benchmark return series, no excess return calculation, and no alpha logic in the reviewed implementation.

The adjacent legacy SPY engine in [src/portfolio/outcome_tracker.py](src/portfolio/outcome_tracker.py) does compute symbol return versus SPY using fetched prices, but that is not the PIS benchmark attribution feature requested here.

### Q6. Does the implementation satisfy the original issue title: "Portfolio Return and Benchmark Attribution" or only a subset?

Only a subset, and not the benchmark part.

The delivered PIS code satisfies recommendation outcome attribution only. It does not satisfy benchmark attribution, so it does not fully satisfy the title as stated.

### Q7. Should the issue be:

Neither fully closed nor renamed as complete.

Recommended disposition for the benchmark issue:
- **KEEP OPEN**

If the work is being split by concern, the clean split would be:
- Recommendation Outcome Attribution
- Benchmark Attribution

But the benchmark portion itself remains unfinished.

### Q8. What additional work would be required for true benchmark attribution?

At minimum:
- define the benchmark data source for SPY in the PIS pipeline
- persist or ingest a benchmark return series aligned to canonical daily dates
- compute portfolio return against SPY for each canonical interval
- compute benchmark return using the same date windows and alignment rules
- compute excess return as portfolio return minus benchmark return
- compute recommendation return and source-level excess return from attribution records
- add deterministic tests for date alignment, excess-return math, and summary aggregation
- wire new benchmark APIs into [scripts/run_outcome_ui.py](scripts/run_outcome_ui.py)
- add dashboard sections for portfolio vs SPY, top alpha recommendations, worst relative recommendations, and source alpha ranking

## Evidence

Relevant files reviewed:
- [src/pis/performance_attribution.py](src/pis/performance_attribution.py)
- [scripts/run_outcome_ui.py](scripts/run_outcome_ui.py)
- [tests/test_pis_performance_attribution_01.py](tests/test_pis_performance_attribution_01.py)
- [performance_attribution_design.md](performance_attribution_design.md)
- [recommendation_outcome_framework.md](recommendation_outcome_framework.md)
- [src/portfolio/outcome_tracker.py](src/portfolio/outcome_tracker.py)
- [docs/issue_12c/issue_12c_benchmark_validation.md](docs/issue_12c/issue_12c_benchmark_validation.md)

## Final Recommendation

**KEEP OPEN**

Justification:
- The PIS implementation reviewed here does not include benchmark attribution.
- The existing SPY outcome engine is adjacent legacy functionality, not the PIS benchmark feature requested by this issue.
- The requested benchmark outputs and dashboard/API surfaces are still missing.
