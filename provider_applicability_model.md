# Provider Applicability Model

## Purpose

Mandatory Holdings Coverage must distinguish between:

- holdings that should be refreshed by stock-signal providers
- holdings that are intentionally out of scope for those providers

## Current Model

A holding is `applicable` to Zacks, Danelfin, and Yahoo when all of the following are true:

1. `asset_class = EQUITIES`
2. symbol is present in `data/current/base_equity_universe.csv`
3. `operational_state != ZERO_VALUE_LEGACY_POSITION`
4. `security_type != CONTRA_ENTRY`

Otherwise, the holding is `not applicable` with an explicit reason.

## Explicit Non-Applicable Reasons

- `not_in_base_equity_universe`
- `zero_value_legacy_position`
- `contra_entry`
- `non_equity_asset`
- `missing_symbol`

## Practical Effect

This intentionally classifies the following as not applicable instead of silently stale:

- broad-market ETFs
- mutual-fund-like vehicles represented outside the refreshable research universe
- internal contra entries such as `M26CNT069`
- symbols absent from the refreshable base equity universe such as `VWO`

## Current Live Outcome

- Active holdings baseline: `74`
- Applicable: `58`
- Not applicable: `16`

## Governance Benefit

The system now distinguishes:

- `not applicable` = intentionally out of scope
- `stale` = applicable but older than threshold
- `missing` = applicable but absent from provider cache
- `failed` = attempted/current row exists without usable primary provider data

That removes the prior ambiguity where non-refreshable instruments appeared as stale coverage defects.