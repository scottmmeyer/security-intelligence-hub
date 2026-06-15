# PIS Read-Only API Contract (PIS-UI-01)

All endpoints are GET and return JSON.

## GET /api/pis/summary
Returns dashboard rollup with health, lineage, and value timeline.

Response shape:
- health: object
- lineage: object
- timeline: array of objects

Example:
```json
{
  "health": {
    "first_snapshot_date": "2026-05-21",
    "latest_snapshot_date": "2026-05-29",
    "snapshot_count": 12,
    "missing_days": 3,
    "duplicate_uploads_prevented": 0
  },
  "lineage": {
    "total_sih_analyses_captured": 234,
    "latest_par": "PAR-20260529-33B7DB0B",
    "latest_mandate": "CONCENTRATED_ALPHA",
    "latest_upload_date": "2026-05-29"
  },
  "timeline": [
    {
      "snapshot_date": "2026-05-29",
      "portfolio_value": 452000.23,
      "cash_value": 13210.44,
      "positions": 78,
      "change_vs_prior_snapshot": 1142.38
    }
  ]
}
```

## GET /api/pis/snapshots
Returns account-level snapshot inventory rows.

Response shape:
- snapshots: array of objects

## GET /api/pis/latest
Returns latest snapshot summary and top holdings.

Response shape:
- snapshot_date: string
- total_value: number
- cash: number
- position_count: integer
- largest_holdings: array[{symbol, market_value}]

## GET /api/pis/health
Returns snapshot history health counters.

Response shape:
- first_snapshot_date: string
- latest_snapshot_date: string
- snapshot_count: integer
- missing_days: integer
- duplicate_uploads_prevented: integer

## Compatibility
- GET /api/pis/status remains available for legacy SIH UI consumers and returns the historical summary payload (`snapshot_count`, `latest_snapshot_date`, `account_count`, `position_count`, etc.).
