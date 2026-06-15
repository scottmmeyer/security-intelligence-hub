# Failure Isolation Assessment

## Requirement
PIS failure must never block SIH analysis.

## Current Behavior
The SIH runner wraps PIS registration in a best-effort helper. If PIS registration raises an exception:
- SIH analysis still completes.
- The response includes `PIS_SNAPSHOT_REGISTRATION_FAILED` in warnings.
- The registration status is reported as failed in the analysis payload.

## Operational Meaning
PIS is an auxiliary consumer of the portfolio event, not a gatekeeper for SIH analysis.
