# Refresh Batch Reconciliation

## What `1/1` Means

The top-card `1/1 rows` text is a provider cache row metric.

It means:

- `attempted_count = 1`
- `with_data_count = 1`

This is the row count in the latest provider file for that provider, not the portfolio coverage universe.

## Why It Differed From Coverage

The coverage block uses the portfolio applicability universe:

- Applicable: 56
- Within threshold: 56
- Covered today: 1

That is a different metric family.

## Reconciliation

### Provider File / Batch Metric

- Zacks: `1/1 rows`
- Danelfin: `1/1 rows`
- Yahoo: `1/1 rows`

### Coverage Metric

- Applicable holdings: 56
- Covered today: 1
- Within threshold: 56

## Interpretation

The UI is showing a provider refresh batch row count in the top cards and a portfolio coverage count in the coverage block.

That is technically coherent, but operationally misleading when the refresh intent is `Refresh Portfolio Signals`, because the operator expects the top refresh summary to reflect the 56-symbol applicable universe.

After the completed Portfolio Signals refresh, the provider batch summary now reports `56/56 rows` for each provider, which aligns the top cards with the applicable universe.

## Reconciliation Conclusion

- `1/1` was expected behavior for a provider cache row metric before the refresh completed.
- It was not sufficient as the primary operator-facing refresh summary.
- The operator should see `Submitted / Succeeded / Failed` alongside `Applicable / Current / Missing / Stale` so the batch and coverage universes cannot be confused.