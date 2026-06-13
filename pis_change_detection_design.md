# PIS Change Detection Design (PIS-002)

## Objective

Provide deterministic, read-only portfolio change detection between consecutive PIS snapshot dates to answer "what changed" without altering SIH decision engines.

## Scope

- Compare snapshot date N against N-1 using data already persisted in PIS history.
- Detect and classify holding changes into:
  - `NEW_POSITION`
  - `EXITED_POSITION`
  - `INCREASED`
  - `REDUCED`
  - `UNCHANGED`
- Compute account-level delta metrics:
  - portfolio value change
  - cash change
  - position count change
- Persist change artifacts under `data/history/pis/changes/`.
- Expose read-only APIs and dashboard sections for operators.

## Architecture

### Source of truth

- Snapshot index: `data/history/pis/pis_snapshot_index.csv`
- Position partitions referenced by each index row via `positions_path`

### Processing module

- Implementation: `src/pis/change_detection.py`
- Entry point: `compute_all_snapshot_changes(...)`

### Persisted outputs

- Change records: `data/history/pis/changes/change_records.csv`
- Change summary: `data/history/pis/changes/change_summary.csv`

### API surface

- `GET /api/pis/changes/latest`
- `GET /api/pis/changes/{snapshot_id}`
- `GET /api/pis/change-summary`

Routes are implemented in `scripts/run_outcome_ui.py` and call `src.pis.change_detection` helpers.

### UI surface

- `ui/pis_dashboard/index.html` adds six sections for PIS-002.
- `ui/pis_dashboard/app.js` loads and renders:
  - latest change KPI summary
  - new / exited / increased / reduced tables
  - historical change summary table

## Non-goals

- No recommendation logic changes.
- No mutation of SIH/PAP/CRA/DIL/CW-DAS workflows.
- No write-back to portfolio source artifacts.

## Operational behavior

- If fewer than two snapshot dates exist, APIs return explicit empty-state payloads.
- Change outputs are recomputed on demand when change CSVs are missing.
- Aggregation spans all accounts present on each snapshot date.
