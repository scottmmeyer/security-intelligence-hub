# SIGNAL-COVERAGE-06: UI Refresh Truthfulness Assessment

## Previous Behavior

The UI displayed "Refresh complete" when `running=false`, regardless of whether providers actually refreshed any symbols.

## Updated Behavior

`ui/outcome_visualization/app.js` now reads `last_report` from `/api/signal-refresh/status` and generates outcome-aware text:

- No submitted targets:
  - "No refresh required; holdings coverage already compliant or no stale/missing applicable holdings targeted."
- Submitted targets:
  - Includes aggregate refreshed/failures/coverage gain and provider-level submitted-refreshed-failed details.

## Truthfulness Improvement

Completion messaging now represents provider activity and coverage effect, not process lifecycle only.

## Residual Limitations

- Message quality depends on report availability and parse success
- Coverage gain is reported by covered_today deltas; this is operationally useful but not a full quality metric

## Acceptance Outcome

This satisfies REFRESH-BEHAVIOR and SIGNAL-COVERAGE-06 truthfulness requirements by coupling UI completion text to concrete provider work results.
