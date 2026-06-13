# Change Detection Algorithm

## Inputs

- `pis_snapshot_index.csv` rows grouped by `snapshot_date`
- each row's `positions_path` file

## Step-by-step

1. Group index rows by `snapshot_date`.
2. Sort snapshot dates ascending.
3. For each consecutive pair `(prior_date, current_date)`:
   - load and aggregate all positions for `prior_date`
   - load and aggregate all positions for `current_date`
4. Build symbol universe as union of prior and current symbols.
5. For each symbol:
   - if only in current: `NEW_POSITION`
   - if only in prior: `EXITED_POSITION`
   - else compare `delta_quantity`:
     - `> 0`: `INCREASED`
     - `< 0`: `REDUCED`
     - `== 0`: `UNCHANGED`
6. Emit change record row with old/new quantity and market value, plus deltas.
7. Compute summary metrics:
   - `portfolio_value_change = sum(current portfolio_value) - sum(prior portfolio_value)`
   - `cash_change = current cash-equivalent total - prior cash-equivalent total`
   - `position_count_change = current position rows - prior position rows`
   - counts by change class
8. Persist all pairwise outputs to:
   - `change_records.csv`
   - `change_summary.csv`

## Snapshot identity model

For date-level comparisons with multiple accounts, snapshot IDs are normalized as:

- `snapshot_id = "|".join(sorted(snapshot_ids_for_date))`

If a date has no snapshot IDs, fallback key is `PIS-DATE-{snapshot_date}`.

## Empty-state behavior

When there are fewer than two snapshot dates:

- `change_records.csv` and `change_summary.csv` are still written with headers only.
- API readers return empty payloads without raising errors.

## Complexity

Let:

- $D$ = number of snapshot dates
- $P$ = total positions across all dates

Runtime is approximately $O(P + U)$ per consecutive date pair, where $U$ is union symbol count per pair. This is acceptable for current local history scale.
