# Portfolio Intelligence System (Beta) - Phase 1 Read-Only Dashboard

This page provides read-only visibility into PIS historical snapshots and SIH lineage.

## Location
- /ui/pis_dashboard/index.html
- /ui/pis_dashboard/app.js

## API Contract
- GET /api/pis/summary
- GET /api/pis/snapshots
- GET /api/pis/latest
- GET /api/pis/health

## Rendered Sections
1. Snapshot inventory
2. Value timeline with change vs prior snapshot
3. Latest snapshot summary with top 10 holdings
4. Snapshot history health
5. SIH lineage summary

## Notes
- Empty states are rendered gracefully when no snapshots exist.
- This dashboard is display-only and does not alter SIH/PIS data.
