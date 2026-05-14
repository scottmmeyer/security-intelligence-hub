# Historical Replay Validation Philosophy

## Purpose

Historical replay validation exists to ensure replay outputs remain deterministic,
point-in-time aligned, and free from temporal leakage.

## Core Rules

1. Replay windows must be valid calendar ranges where end_date is greater than
   or equal to start_date.
2. Historical replay windows are fail-closed when end_date is in the future
   relative to the execution as-of date.
3. Replay series dates must remain inside the declared replay window.
4. Duplicate date keys for the same benchmark or vehicle contract are invalid.
5. Curves must pass minimum depth requirements for line rendering semantics.

## Data Quality Boundaries

- Adjusted close values are required and must be positive.
- Missing benchmark or investable vehicle history is a blocking validation
  error in WP-05A.
- Insufficient curve depth is a blocking validation error for line-curve
  generation.

## Governance Intent

Validation failures are explicit operator-facing outcomes and are never silently
coerced. Historical truth is preserved through append-only partition contracts
and deterministic replay identifiers.
