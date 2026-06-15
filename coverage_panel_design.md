# Coverage Panel Design

## Objective
Separate holdings-governance coverage from research-universe refresh health so operators can immediately see whether held capital has fresh provider data.

## New Panel: Portfolio Holdings Coverage

Display for each provider (Zacks, Danelfin, Yahoo):
- Covered Today: holdings with `sourced_date == today`.
- Covered Within Threshold: holdings with `today - sourced_date <= threshold_days` (default 2).
- Stale: holdings present but older than threshold.
- Missing: holdings absent from provider cache.

### Proposed API contract
Endpoint: `GET /api/signal-status` (extend existing response) or `GET /api/holdings-coverage` (new endpoint).

```json
{
  "holdings_baseline": {"run_id": "PAR-...", "count": 74},
  "providers": {
    "zacks":    {"covered_today": 34, "covered_within_threshold": 34, "stale": 38, "missing": 2},
    "danelfin": {"covered_today": 34, "covered_within_threshold": 34, "stale": 38, "missing": 2},
    "yahoo":    {"covered_today": 34, "covered_within_threshold": 34, "stale": 38, "missing": 2}
  }
}
```

## Keep Existing Panel: Research Universe Refresh Health

Continue current today-row metrics (attempted_count, with_data_count, field coverage) but relabel clearly as research-universe health.

## Governance Rules
- Any provider with `missing > 0` on holdings => `NON_COMPLIANT`.
- Any provider with `stale > 0` beyond threshold => `DEGRADED`.
- Only all-zero stale/missing qualifies as `COMPLIANT`.
