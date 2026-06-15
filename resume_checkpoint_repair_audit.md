# SIGNAL-COVERAGE-07: Resume Checkpoint Repair Audit

## Problem Verified

Coverage-repair mode in phase 6 correctly selected targets but could finish almost instantly with unchanged degraded coverage.

Root cause was resume checkpoint semantics in provider fetchers:

- Same-day rows were treated as completed solely by presence in the dated file.
- Failed/empty same-day rows were skipped instead of retried.

## Affected Modules

- `src/scoring/fetch_zacks_scores.py`
- `src/scoring/fetch_danelfin_scores.py`
- `src/scoring/fetch_yahoo_supplemental.py`

## Fix Applied

Each fetcher now supports coverage-repair retry controls:

- `force_retry_symbols`: symbols eligible for retry despite same-day checkpoints
- `collect_stats`: returns checkpoint/retry accounting

New behavior for symbols present in today archive:

- if not in `force_retry_symbols`: skip (original resume behavior)
- if in `force_retry_symbols` and already successful today: skip as covered
- if in `force_retry_symbols` and failed/empty/stale: retry

## Provider Success Rules

- Zacks success: `zacks_rank` OR `zacks_score` present and sourced today
- Danelfin success: `danelfin_score` OR `danelfin_raw` present and sourced today
- Yahoo success: one of `current_price`, `abr`, `price_target`, `analyst_count` present and sourced today

## Live Validation Evidence

Live run command:

```bash
PYTHONPATH=. .venv/bin/python scripts/refresh_signals.py --smart --providers danelfin yahoo --report-path data/current/last_signal_refresh_report.json
```

Observed runtime logs:

- Yahoo repair retried 19 symbols with `[1/19]` ... `[19/19]` fetch loop entries
- Danelfin repair retried 2 symbols with `[1/2]` ... `[2/2]` entries

Report evidence in `data/current/last_signal_refresh_report.json`:

- Yahoo: `retried_failed_checkpoint=19`, `refreshed=19`, `failed=0`, status `DEGRADED -> COMPLIANT`
- Danelfin: `retried_failed_checkpoint=2`, `refreshed=2`, `failed=0`, status `DEGRADED -> COMPLIANT`

This confirms failed same-day checkpoints are now retried and repaired.
