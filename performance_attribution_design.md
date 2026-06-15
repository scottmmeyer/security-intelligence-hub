# PERFORMANCE-ATTRIBUTION-01 Design

## Scope

This feature attributes recommendation outcomes using canonical-governed PIS data only.

Inputs:
- `data/history/pis/changes/change_records.csv`
- `data/history/pis/changes/change_summary.csv`
- `data/history/pis/lineage/lineage_records.csv`
- `data/history/pis/lineage/lineage_summary.csv`

Outputs:
- `data/history/pis/attribution/attribution_records.csv`
- `data/history/pis/attribution/attribution_summary.csv`

## Non-goals

- No SPY benchmarking
- No alpha/risk decomposition
- No factor analytics

## Deterministic Model

For each lineage match with confidence != `NONE`:
1. Join to change record by `(snapshot_id, change_id)`.
2. Compute directional multiplier by change type:
   - `NEW_POSITION`, `INCREASED` => `+1`
   - `EXITED_POSITION`, `REDUCED` => `-1`
3. Compute directional attribution:
   - `directional_attribution = delta_market_value * multiplier`
4. Compute directional return percent:
   - baseline = `abs(old_market_value)` else `abs(new_market_value)`
   - `directional_return_pct = directional_attribution / baseline * 100`
5. Classify outcome with thresholds:
   - winner if score >= `winner_min_score`
   - loser if score <= `loser_max_score`
   - otherwise neutral

Default thresholds:
- `winner_min_score = 50.0`
- `loser_max_score = -50.0`

## APIs

Added endpoints:
- `/api/pis/attribution/latest`
- `/api/pis/attribution/history`
- `/api/pis/attribution-summary`

## Dashboard Sections

Added sections:
- Recommendation Outcome Summary
- Top Winning Recommendations
- Top Losing Recommendations
- Recommendation Source Performance

## Implementation Notes

- Attribution refresh is lock-protected and persisted as CSV read-model artifacts.
- Existing lineage artifacts are reused when present to avoid unnecessary recompute.
- Endpoint behavior is fail-open with explicit empty payloads on errors.
