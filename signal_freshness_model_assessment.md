# Signal Freshness Model Assessment

## Why “0 Missing” and “38 Stale” Can Both Be True

These statements are computed from different models and denominator sets:

- “0 missing from merged smart refresh set” is a queue-construction assertion: after forced symbols are merged into smart symbols, forced symbols are present in the target list by construction.
- “38 stale” is a holdings-state assertion: for the active portfolio holdings baseline, 38 symbols still have `sourced_date < today` in provider `latest_*` caches.

Additional denominator drift exists:
- Active holdings baseline: 74 symbols (PAR-20260529-33B7DB0B).
- Refresh forced set baseline: 71 symbols (date-sorted PAR selection in refresh helper).
- Drift: 3 symbols present in active holdings but absent from forced set: FIGFX, VEA, VXUS.

## Option Assessment (A/B/C/D)

| Option | Assessment | Rationale |
|---|---|---|
| A) Refresh logic correct, UI measuring wrong thing | Partially true | UI “research universe refresh health” is not a holdings coverage metric. |
| B) UI correct, refresh logic not operating | Partially true | UI metric is internally correct for its own denominator; holdings coverage remains unmet operationally. |
| C) Holdings queued but provider refreshes failing | Not supported as primary cause | Skipped holdings are absent from today execution files, indicating not queued in today run scope. |
| D) Another explanation | Primary explanation | Denominator drift + queue-construction vs holdings-governance mismatch + operational run scope mismatch. |

Primary determination: D (with A/B contributing factors).
