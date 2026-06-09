# Freshness Badge Logic Update

Repository: security-intelligence-hub  
Issue: SI-REFRESH-02  
Date: 2026-06-09

## Before (Original Logic)

`_signal_status()` in `scripts/run_outcome_ui.py`:

```python
def _signal_status() -> dict:
    today = date.today().isoformat()
    result = {}
    for name, path in _SIGNAL_FILES.items():
        sd = _sourced_date(path)
        result[name] = {
            "sourced_date": sd,
            "stale": sd != today,
            "exists": path.exists(),
        }
    return result
```

The UI rendered:
- `stale=False` → "(fresh)" green dot
- `stale=True` → "(stale)" red dot

**Critical gap:** `sourced_date=today` with 0% data coverage showed "(fresh)".

## After (SI-REFRESH-02 Logic)

`_signal_status()` now computes per-provider coverage metrics and emits `badge_state`:

New API fields:
- `attempted_count` — rows with sourced_date=today
- `with_data_count` — rows with at least one primary field non-empty
- `coverage_pct` — percentage
- `primary_field_coverage` — per primary field coverage
- `degraded_fields` — primary fields with 0% coverage today
- `zero_coverage_fields` — all score fields with 0% today
- `badge_state` — FRESH | FRESH_PARTIAL | STALE

## Badge State Rendering

`_renderSignalPills()` in `ui/outcome_visualization/app.js` now:
- Shows dot color: green (FRESH), orange (FRESH_PARTIAL), red (STALE), blue-pulse (REFRESHING)
- Shows coverage detail: "671/702 rows · 95.6%"
- Shows degraded field warnings: "⚠ 0% coverage: eps_growth_5yr"
- Shows advisory for non-primary zero fields

## Backwards Compatibility

All new fields are additive. `stale` boolean is preserved unchanged for any consumers that rely on it. `badge_state` is a new field that can be ignored by older consumers.
