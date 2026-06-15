# Outcome Classification Model

## Objective

Classify matched recommendation outcomes into `WINNER`, `NEUTRAL`, or `LOSER` with deterministic rules.

## Inputs Per Record

- `change_type`
- `old_market_value`
- `new_market_value`
- `delta_market_value`
- lineage confidence and recommendation metadata

## Directional Alignment

Directional alignment converts observed value change into recommendation-consistent impact.

- Buy-side changes (`NEW_POSITION`, `INCREASED`) keep sign.
- Reduce-side changes (`EXITED_POSITION`, `REDUCED`) invert sign.

Formula:
- `directional_attribution = delta_market_value * direction_multiplier`

## Threshold Classification

Given thresholds:
- `winner_min_score`
- `loser_max_score`

Rules:
- `WINNER` if `directional_attribution >= winner_min_score`
- `LOSER` if `directional_attribution <= loser_max_score`
- `NEUTRAL` otherwise

Default thresholds:
- winner: `50.0`
- loser: `-50.0`

## Stability Guarantees

- No randomness
- No time-dependent branches in classification logic
- Sorting and persisted summaries are deterministic by snapshot date and identifiers

## Edge Handling

- Missing baseline values produce `directional_return_pct = 0.0`.
- Unmatched lineage rows (`confidence = NONE`) are excluded from attribution records.
