# SIGNAL-COVERAGE-06: Refresh Status API Design

## Endpoints

- `POST /api/signal-refresh`
  - launches smart refresh with `--report-path data/current/last_signal_refresh_report.json`
  - clears prior in-memory and file report state before launch

- `GET /api/signal-refresh/status`
  - returns:
    - `running`
    - `exit_code`
    - `last_report` (provider activity report when available)

## Report Contract

`last_report` is sourced from `ensure_signals_fresh_with_report` output and includes per-provider activity and coverage before/after snapshots.

## Behavior Notes

- While running, API reports `running: true`
- After process exits, API exposes final `exit_code` and latest `last_report`
- If report file cannot be parsed, `last_report` safely falls back to null

## Purpose

This status payload enables the UI to render truthful completion messages based on actual refresh work and coverage effect instead of a binary process-running flag.
