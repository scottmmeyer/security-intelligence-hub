# Holdings Baseline Unification

## Canonical Baseline

The canonical active holdings baseline is now:

- latest `holdings.csv` by file modification time under `data/portfolio_ingestion/analysis_runs/`
- filtered to `asset_class = EQUITIES`

Current live baseline:

- Run ID: `PAR-20260529-33B7DB0B`
- Active holdings baseline: `74`

## Implementation

Shared source of truth:

- `src/portfolio/holdings_coverage.py`
  - `find_latest_holdings_run()`
  - `load_active_holdings_baseline()`
  - `load_active_holding_symbols()`

Consumers now aligned to that same baseline:

- `scripts/refresh_signals.py`
- `scripts/run_outcome_ui.py`
- holdings coverage reporting via `summarize_holdings_coverage()`

## Result

Denominator drift between mtime-selected UI context and lexicographically selected refresh context has been removed.

Before:

- UI active holdings baseline: 74
- Refresh forced set baseline: 71

After:

- Active holdings baseline source is shared
- Refresh enforcement derives from the same baseline
- Holdings coverage reporting derives from the same baseline

## Acceptance

- UI analysis, refresh enforcement, and holdings coverage reporting now resolve the same active holdings run.
- No separate PAR selection rule remains in the main refresh/status path.