# Active Job State Audit

## Observation

The UI can simultaneously show:

- Dropdown selection: Refresh Portfolio Signals.
- Active poll message: Rebuild Research Universe in progress.

Current API confirms active mode is rebuild_research_universe.

## Why This Happens

1. Dropdown state

- The dropdown reflects current control selection (next intent), not authoritative active job state.

2. Active job state

- The backend stores active mode in /api/signal-refresh/status.mode when the job starts.
- Polling uses that field for in-progress text.

3. Most Recent Refresh card

- This card shows the last completed report, which can be from a different mode than the currently running job.

## Is This Expected or a Race?

- This is expected with current state model.
- It behaves like stale control-state presentation, not a backend race condition.

## Operator Risk

- Operator may think selected mode equals running mode.
- Operator may think last completed report metrics belong to the active run.

## Recommended Presentation (No Algorithm Change)

1. Split sections clearly:

- Active Refresh Job: authoritative mode, stage progress, started time, elapsed time.
- Next Refresh Intent: dropdown value for next trigger only.
- Last Completed Refresh: immutable summary from last_report.

2. Add explicit badges:

- Running now: Rebuild Research Universe.
- Next click intent: Refresh Portfolio Signals.

3. Keep dropdown enabled if desired, but visually mark as next run intent while a job is running.
