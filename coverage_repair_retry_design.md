# SIGNAL-COVERAGE-07: Coverage Repair Retry Design

## Objective

Allow coverage-repair mode to retry degraded holdings even when same-day checkpoint rows already exist.

## Design Constraints

- Keep resume optimization for normal research refresh mode
- Avoid deleting daily files
- Avoid full-universe refetch
- Retry only targeted coverage-repair symbols

## Design

### 1. Fetcher API Extension

All three fetchers now accept:

- `force_retry_symbols: set[str] | None`
- `collect_stats: bool`

When `collect_stats=True`, fetcher returns `(output_path, stats)` with:

- `requested`
- `attempted`
- `skipped_checkpoint`
- `skipped_already_covered`
- `retried_failed_checkpoint`

### 2. Retry Decision Rule

For each symbol in requested set:

1. Missing checkpoint row -> attempt fetch
2. Existing row and symbol not forced -> skip checkpoint
3. Existing row and forced:
   - if successful today -> skip as already covered
   - else -> retry failed checkpoint

### 3. Refresh Orchestrator Integration

In `scripts/refresh_signals.py`:

- coverage-repair passes `force_retry_symbols=set(targets)` to fetchers
- research-refresh passes no force set (legacy resume behavior)
- metrics include `skipped_already_covered` and `retried_failed_checkpoint`

## Reporting Contract

Provider report now includes:

- `submitted`
- `skipped_already_covered`
- `retried_failed_checkpoint`
- `refreshed`
- `failed`
- `coverage_before`
- `coverage_after`

## Expected Outcome

Coverage-repair no longer silently short-circuits failed same-day rows.

If providers succeed, degraded holdings move to compliant. If providers still fail, report explicitly shows retries attempted with remaining failures.
