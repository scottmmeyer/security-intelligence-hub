# Dashboard Status Model

## Section States
- `LOADING`: request in progress, placeholder shown.
- `LOADED`: section rendered with returned data or explicit no-data state.
- `SLOW`: request still pending after 5 seconds; placeholder changes to degraded waiting state.
- `FAILED`: request failed or timed out; section renders `Data unavailable` with reason.

## Subsystem Aggregation
Top-level subsystem status is derived from member sections:
- `LOADED` when all member sections are loaded.
- `FAILED` when any member section fails.
- `SLOW` when none failed but at least one is slow.
- `LOADING` otherwise.

## Global Banner Behavior
- Banner appears at startup.
- Banner shows loaded-section count and elapsed time.
- Banner remains visible while any section is still `LOADING` or `SLOW`.
- Banner hides automatically once every section is either `LOADED` or `FAILED`.

## Operator Meaning
- Operators can distinguish healthy startup from degraded startup.
- Operators can see which subsystem is slow.
- Operators can see that partial failures do not invalidate the whole dashboard.