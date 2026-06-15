# Snapshot Comparison Model

## Comparison unit

PIS-002 compares date-level portfolio states, not individual ingestion events. Each state is the aggregate of all accounts ingested for that `snapshot_date`.

## Canonical entities

- Snapshot date group:
  - `snapshot_date`
  - set of raw `snapshot_id`s
  - rows from `pis_snapshot_index.csv`
- Aggregated symbol state:
  - `symbol`
  - `quantity`
  - `market_value`
- Summary state:
  - date-level portfolio totals and counts

## Record schema

### Change record

From `change_records.csv`:

- `change_id`
- `snapshot_id`
- `prior_snapshot_id`
- `snapshot_date`
- `prior_snapshot_date`
- `change_type`
- `symbol`
- `old_quantity`
- `new_quantity`
- `old_market_value`
- `new_market_value`
- `delta_quantity`
- `delta_market_value`
- `created_at`

### Change summary

From `change_summary.csv`:

- `snapshot_id`
- `prior_snapshot_id`
- `snapshot_date`
- `prior_snapshot_date`
- `portfolio_value_change`
- `cash_change`
- `position_count_change`
- `new_holdings_count`
- `exited_holdings_count`
- `increased_holdings_count`
- `reduced_holdings_count`
- `unchanged_holdings_count`
- `created_at`

## API read model

- `/api/pis/changes/latest` returns latest summary plus categorized detail arrays.
- `/api/pis/changes/{snapshot_id}` returns one summary row plus categorized details.
- `/api/pis/change-summary` returns all summary rows (descending by date).

## Classification semantics

- Position existence drives `NEW_POSITION` and `EXITED_POSITION`.
- Quantity delta drives `INCREASED`, `REDUCED`, and `UNCHANGED`.
- Market value deltas are still preserved for all classes.

This keeps classification deterministic even when prices move without share count changes.
