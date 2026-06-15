# SIGNAL-COVERAGE-06: Coverage-Aware Refresh Design

## Objective
Ensure refresh eligibility is determined by two independent conditions:

1. Research freshness (provider latest file sourced today or not)
2. Holdings coverage status for provider-applicable active holdings

A provider must refresh when either condition indicates risk.

## Design Summary

- Canonical holdings baseline and provider applicability are reused from `src/portfolio/holdings_coverage.py`.
- `scripts/refresh_signals.py` computes provider coverage from latest provider cache and classifies holdings status.
- Provider refresh chooses one of three paths:
  - `skip_compliant`: research fresh and no stale/missing/failed applicable holdings
  - `coverage_repair`: research fresh but applicable holdings degraded
  - `research_refresh`: provider cache stale (existing behavior preserved)
- Refresh execution now emits provider metrics (`submitted`, `refreshed`, `failed`, coverage before/after, runtime).

## Contract

A provider is considered compliant only when all applicable holdings are covered today or within threshold and no stale/missing/failed applicable holdings remain.

If any applicable holding is stale/missing/failed, refresh must run even when provider file sourced_date is today.

## Evidence in Code

- Eligibility/targeting primitives in `scripts/refresh_signals.py`
- Coverage summary model in `src/portfolio/holdings_coverage.py`
- Report emission through `ensure_signals_fresh_with_report` in `scripts/refresh_signals.py`

## Expected Operator Outcome

The refresh button remains a process trigger, but completion messaging is tied to actual provider activity and holdings coverage effect, not only process exit.
