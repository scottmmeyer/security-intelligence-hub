# PIS-UI-01 Dashboard Design (Phase 1, Read-Only)

## Objective
Deliver a read-only visibility layer for PIS history without changing SIH decisioning or portfolio recommendation logic.

## Navigation
- Added top-level SIH/PIS links:
  - Security Intelligence Hub -> /ui/portfolio_alignment/
  - Portfolio Intelligence System (Beta) -> /ui/pis_dashboard/

## Page
- UI path: /ui/pis_dashboard/index.html
- Script: /ui/pis_dashboard/app.js

## Sections
1. Snapshot inventory
- Source: GET /api/pis/snapshots
- Fields: snapshot_date, snapshot_id, account_number, account_name, positions, market_value, cash_value, source_file, ingestion_timestamp

2. Value timeline table
- Source: GET /api/pis/summary -> timeline
- Fields: snapshot_date, portfolio_value, cash_value, positions, change_vs_prior_snapshot

3. Latest snapshot summary + top 10 holdings
- Source: GET /api/pis/latest
- Fields: snapshot_date, total_value, cash, position_count, largest_holdings

4. Snapshot history health
- Source: GET /api/pis/health
- Fields: first_snapshot_date, latest_snapshot_date, snapshot_count, missing_days, duplicate_uploads_prevented

5. SIH lineage summary
- Source: GET /api/pis/summary -> lineage
- Fields: total_sih_analyses_captured, latest_par, latest_mandate, latest_upload_date

## Empty-State Behavior
- Empty inventory and timeline render explicit no-data messages.
- Latest summary, health, and lineage render default placeholders when data is absent.
- API failures are fail-open to JSON defaults so UI remains visible.

## Non-Goals (Phase 1)
- No write endpoints.
- No attribution engine changes.
- No PAP/CRA/DIL/CW-DAS/allocation model changes.
