# SIGNAL-COVERAGE-07: Provider Retry Semantics

## Zacks

Primary success fields:

- `zacks_rank`
- `zacks_score`

Rule:

- same-day row with either field populated => covered, skip under force-retry
- same-day row empty OR non-today row => retry under force-retry

## Danelfin

Primary success fields:

- `danelfin_score`
- `danelfin_raw`

Rule:

- same-day row with either field populated => covered, skip under force-retry
- same-day row empty OR non-today row => retry under force-retry

## Yahoo

Primary success fields:

- `current_price`
- `abr`
- `price_target`
- `analyst_count`

Rule:

- same-day row with any primary field populated => covered, skip under force-retry
- same-day row empty OR non-today row => retry under force-retry

## Research Refresh Compatibility

When `force_retry_symbols` is not provided:

- resume semantics are unchanged
- any symbol present in same-day checkpoint remains skipped

## Coverage Repair Compatibility

When `force_retry_symbols` is provided:

- only targeted symbols are eligible for forced retry logic
- successful same-day targeted rows still skip
- failed/empty/stale targeted rows retry

This preserves normal resume performance while making coverage-repair operationally effective.
