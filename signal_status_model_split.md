# Signal Status Model Split

## Old Model

One panel combined two different concepts:

- research-universe refresh health
- portfolio holdings governance coverage

That allowed a provider to appear `FRESH` even when held positions remained stale.

## New Model

`/api/signal-status` now exposes two distinct models:

## 1. Research Universe Refresh Health

Existing today-row metrics remain intact:

- `attempted_count`
- `with_data_count`
- `coverage_pct`
- `badge_state`
- degraded/zero-coverage fields

This answers:

> Did the smart research-universe refresh produce healthy today-row results?

## 2. Portfolio Holdings Coverage

New payload:

- `portfolio_holdings_coverage.run_id`
- `portfolio_holdings_coverage.active_holdings_baseline`
- `portfolio_holdings_coverage.threshold_days`
- per-provider:
  - `applicable_holdings`
  - `covered_today`
  - `covered_within_threshold`
  - `stale`
  - `missing`
  - `not_applicable`
  - `failed`
  - `status`

This answers:

> Are the currently held applicable positions actually covered by fresh provider data?

## Governance States

- `COMPLIANT` = no stale/missing/failed applicable holdings
- `DEGRADED` = stale or failed applicable holdings exist, but none missing
- `NON_COMPLIANT` = missing applicable holdings exist

## Truthfulness Guarantee

The UI may still show research-universe `FRESH`.

However, that can no longer imply holdings compliance because:

- the panel is renamed to `Research Universe Refresh Health`
- holdings coverage is shown separately
- research pills display a holdings advisory when holdings status is not compliant