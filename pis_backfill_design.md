# PIS-BACKFILL-01 Design

## Goal
Backfill existing SIH analysis runs into PIS snapshot history so PIS APIs and dashboard reflect historical portfolio snapshots.

## Scope
- Add one-time utility: scripts/backfill_pis_snapshots.py
- Reuse canonical registration service:
  - src.pis.service.register_portfolio_snapshot_from_sih
- Source artifacts from:
  - data/portfolio_ingestion/analysis_runs/<PAR>/snapshot.json
  - data/portfolio_ingestion/analysis_runs/<PAR>/holdings.csv

## Canonical Reconstruction Path
For each eligible run:
1. Read snapshot.json into canonical SIH PortfolioSnapshot model.
2. Read holdings.csv into canonical SIH PortfolioHolding rows.
3. Call register_portfolio_snapshot_from_sih(snapshot, holdings, ...).

No alternate PIS parser is introduced.

## Registration Behavior
- Registration writes to:
  - data/history/pis/pis_snapshot_index.csv
  - data/history/pis/snapshot_date=.../account_id=.../snapshot_id=.../
- Duplicate handling is delegated to canonical PIS append-only storage:
  - same snapshot_id -> duplicate suppressed
- Rejected SIH snapshots are skipped.
- Accepted and Partial SIH snapshots are eligible for registration.

## Idempotency
- Running backfill repeatedly is safe.
- Existing snapshot identities are skipped as duplicates.
- No duplicate index rows for same snapshot_id.

## CLI Contract
- --all
- --run-id PAR-...
- --dry-run
- --limit N
- optional path overrides:
  - --runs-root
  - --history-root
  - --index-path

## Reporting
Backfill summary reports:
- eligible_runs
- registered_snapshots
- skipped_duplicates
- skipped_invalid_runs
- failures
- dry_run
- output paths
- per-run records

## Additional Lineage Preservation
PIS snapshot storage now records source_run_id so SIH run lineage is preserved in PIS index rows.
