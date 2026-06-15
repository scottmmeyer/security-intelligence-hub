# PIS Snapshot Registration Design

## Goal
Register a PIS snapshot automatically whenever SIH successfully processes a portfolio upload.

## Shared Contract
PIS consumes the canonical SIH parsed portfolio object:
- `src/portfolio/models.py::PortfolioSnapshot`
- `src/portfolio/models.py::PortfolioHolding`

## Registration Rules
- Register only after SIH parsing succeeds.
- Register only when SIH ingestion is fully accepted.
- Do not register snapshots for malformed files or rejected uploads.
- Do not re-open, re-parse, or re-validate the upload in PIS.

## Implementation Shape
- `run_analysis(...)` calls a best-effort helper in [src/portfolio/runner.py](../../src/portfolio/runner.py).
- The helper converts the SIH snapshot and holdings into PIS history rows.
- PIS writes to append-only history storage in [src/pis/storage.py](../../src/pis/storage.py).

## Visibility
The UI exposes a lightweight administrative summary:
- Snapshots Stored
- Latest Snapshot
- Latest Snapshot Date
- Accounts
- Positions
