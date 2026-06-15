# PIS Storage Strategy
**Date:** 2026-06-12

## Recommendation

Use an integrated storage tree under the shared platform data root:
- `data/history/pis/`

Avoid a separate `data/pis/` root unless PIS later becomes a physically separate service.

## Why Integrated Storage Is Best

- It matches the existing SIH pattern of immutable historical partitions.
- It preserves proximity to shared run metadata and benchmark history.
- It keeps the PIS storage contract consistent with the rest of the repository.
- It reduces duplication and avoids a second unrelated storage convention.

## Proposed Subtree

```text
data/
  history/
    pis/
      snapshots/
      positions/
      changes/
      lineage/
      reconciliation/
      outcomes/
```

## Storage by Artifact

### Portfolio snapshots
Store in:
- `data/history/pis/snapshots/`

### Position snapshots
Store in:
- `data/history/pis/positions/`

### Change events
Store in:
- `data/history/pis/changes/`

### Decision lineage
Store in:
- `data/history/pis/lineage/`

### Reconciliation queue
Store in:
- `data/history/pis/reconciliation/`

### Outcome summaries
Store in:
- `data/history/pis/outcomes/`

## Storage Pattern

Each artifact should be append-only and partitioned by snapshot date and run id where appropriate.

Recommended pattern:
- `snapshot_date=YYYY-MM-DD/run_id=RUN-.../artifact.csv`

## Alternative Options

### `data/pis/`
- Too disconnected from the platform’s existing historical storage model.
- Acceptable only if PIS becomes an independent runtime with separate lifecycle controls.

### `data/history/pis/`
- Best fit for the current repository and current governance model.

## Recommendation

Choose `data/history/pis/` now.
It preserves lineage, keeps the model consistent with SIH, and leaves room for future extraction.
