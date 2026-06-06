# CRA Persistence Design — Phase 23.6C

## Storage Model

**File:** `data/operator/cra_draft.json`  
**Format:** JSON (UTF-8)  
**Contents:** Full `RotationProposal.to_dict()` output + operator state extension  
**Lifecycle:** Overwritten on each save; single latest proposal

## Persisted Fields

All fields from `RotationProposal.to_dict()` plus:

```json
{
  "proposal_id": "CRA-20260605-ABCD1234",
  "run_id": "PAR-20260605-F3522BBB",
  "as_of_date": "2026-06-05",
  "cra_version": "1.0",
  "created_at_utc": "2026-06-05T22:00:00Z",
  "saved_at_utc": "2026-06-05T22:05:00Z",
  "proposal_status": "READY",
  "portfolio_mv": 487234.12,
  "total_capital_pool": 38450.00,
  "sources": [...],
  "deployments": [...],
  "impact": {...},
  "review_flags": [],
  "suppressed_sources": [...],
  "operator_include_map": {
    "CVE": true,
    "FIS": false,
    "TSLA": true
  }
}
```

## NOT Persisted

- Raw portfolio CSV
- Account numbers or PII
- API keys, credentials, secrets
- Signal data (references run_id for lineage)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/cra/draft` | Load the saved draft (404 if none) |
| POST | `/api/cra/draft` | Save current proposal as draft |
| DELETE | `/api/cra/draft` | Clear the saved draft |

## Load-on-Startup Behavior

When a portfolio analysis loads:
1. Fetch fresh proposal from `/api/cra/proposal`
2. Separately check `/api/cra/draft`
3. If draft exists AND `draft.run_id === fresh.run_id`: restore operator_include_map to checkboxes
4. If draft is stale (different run_id): show "Stale draft available" banner, do not auto-apply

This ensures operator selections survive page refresh without stale data contaminating a new analysis.
