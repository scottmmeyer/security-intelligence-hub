# Benchmark Alignment Policy (01B-A)

## Policy Name

- `NEAREST_PRIOR_TRADING_DAY`

## Rule

For each canonical date target:
1. Use same-day benchmark price if present.
2. If not present, use the nearest prior available benchmark date.
3. If no prior benchmark date exists, mark benchmark side as missing (`data_quality_status`).

## Deterministic Guarantees

- Date resolution is purely data-driven and stable for identical input files.
- No randomization and no heuristic tie-breaking.
- The latest prior date is selected using lexical max on ISO date strings.

## Canonical Pairing

- Entry benchmark target date = `prior_snapshot_date`
- Exit benchmark target date = `snapshot_date`

Resolved dates may differ from canonical targets when canonical dates are non-trading days (weekends/holidays).

## No-Data Behavior

If benchmark data is unavailable for required alignment points:
- benchmark return defaults to `0.0` for row continuity
- row status is set to a non-OK `data_quality_status`
- portfolio and excess return are still computed deterministically
