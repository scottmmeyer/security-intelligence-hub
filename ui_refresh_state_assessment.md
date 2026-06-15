# REFRESH-BEHAVIOR-01 UI Refresh State Assessment

## Why refresh appears instant

The UI experience is process-state based, not provider-work based.

Current flow:

1. UI posts /api/signal-refresh and gets {"started": true}.
2. UI polls /api/signal-refresh/status.
3. If running=false, UI message becomes "Refresh complete. Signal dates updated."

If refresh_signals exits quickly (for example, all providers considered fresh), UI still shows complete.

## Why holdings stay DEGRADED right after refresh

This run did not fetch provider symbols.

Each provider exited early at file-level freshness checks:

- sourced_date already equals today
- provider fetch loops never executed

So holdings coverage counts did not improve and remained DEGRADED.

## Truthfulness gap identified

The text "Refresh complete. Signal dates updated." can be misleading when no provider data was fetched.

It currently means:

- background process finished

It does not guarantee:

- applicable holdings were submitted
- new provider rows were fetched
- holdings coverage improved

## Suggested message-state behavior

Prefer a three-state completion surface:

1. Refresh started
2. Refresh completed with provider fetch activity
3. Refresh completed with no fetches (already fresh at file-level)

and display per-provider outcome summary:

- submitted, refreshed, skipped, runtime

This would align UI wording with actual execution behavior.