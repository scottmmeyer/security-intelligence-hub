# Provider Status API Update

Repository: security-intelligence-hub  
Issue: SI-REFRESH-02  
Date: 2026-06-09

## Endpoint

`GET /api/signal-status`

## Response Schema (After SI-REFRESH-02)

```json
{
  "zacks": {
    "sourced_date": "2026-06-09",
    "stale": false,
    "exists": true,
    "attempted_count": 702,
    "with_data_count": 671,
    "coverage_pct": 95.6,
    "primary_field_coverage": {
      "zacks_rank": 95.6,
      "zacks_score": 95.6
    },
    "degraded_fields": [],
    "zero_coverage_fields": ["abr", "price_target", "eps_growth"],
    "badge_state": "FRESH"
  },
  "danelfin": {
    "sourced_date": "2026-06-09",
    "stale": false,
    "exists": true,
    "attempted_count": 497,
    "with_data_count": 497,
    "coverage_pct": 100.0,
    "primary_field_coverage": {
      "danelfin_raw": 100.0,
      "danelfin_score": 100.0
    },
    "degraded_fields": [],
    "zero_coverage_fields": [],
    "badge_state": "FRESH"
  },
  "yahoo": {
    "sourced_date": "2026-06-09",
    "stale": false,
    "exists": true,
    "attempted_count": 697,
    "with_data_count": 696,
    "coverage_pct": 99.9,
    "primary_field_coverage": {
      "price_target": 98.1,
      "analyst_count": 98.1,
      "current_price": 99.9
    },
    "degraded_fields": [],
    "zero_coverage_fields": ["eps_growth_5yr"],
    "badge_state": "FRESH"
  },
  "_running": false
}
```

## Breaking Changes

None. `sourced_date`, `stale`, `exists` are preserved. New fields are additive.

## Notes

- `degraded_fields` is empty for Yahoo despite `eps_growth_5yr` being 0%, because `eps_growth_5yr` is not a primary field. It appears in `zero_coverage_fields` as an advisory.
- Yahoo `badge_state = FRESH`. `eps_growth_5yr` is a supplemental (non-primary) field; 0% coverage does not trigger FRESH_PARTIAL. It surfaces as a yellow advisory tag ("0% today: eps_growth_5yr") in the UI pill detail row.
- FRESH_PARTIAL is only triggered by: primary field at 0% coverage, OR row coverage < 95%.
