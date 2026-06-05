# Phase 8.0B.0A — Daily Operations Model

**Date:** 2026-06-04  

---

## Current SIH Morning Sequence (Without FMP)

```
Any time (on demand or scheduled):
  POST /api/signal-refresh → scripts/refresh_signals.py
    - Checks staleness for Zacks, Danelfin, Yahoo
    - Fetches stale providers sequentially
    - Writes to data/signals/{provider}/latest_*.csv
    - Returns refresh status

User action:
  POST /api/portfolio/analyze → Portfolio Alignment Analysis
    - Reads latest_zacks.csv, latest_danelfin.csv, latest_yahoo_supplemental.csv
    - Builds analytical_universe.csv
    - Runs alignment, recommendations, CW-DAS, CRA
    - Writes PAR run to analysis_runs/
```

---

## Proposed Daily Operations Model (With FMP)

### Pre-Market Window: 03:30–05:00

```
03:30 — FMP daily refresh (new — runs before existing signal refresh)
  scripts/refresh_signals.py (extended with --providers fmp)
  
  FMP daily endpoints (4 calls with bulk, or ~689 calls per-symbol):
    /key-metrics-ttm-bulk     → data/signals/fmp/daily/fmp_key_metrics_{date}.csv
    /ratios-ttm-bulk          → data/signals/fmp/daily/fmp_ratios_{date}.csv
    /grades-consensus-bulk    → data/signals/fmp/daily/fmp_grades_{date}.csv
    
  Updates:
    data/signals/fmp/latest/latest_fmp_key_metrics.csv
    data/signals/fmp/latest/latest_fmp_ratios.csv
    data/signals/fmp/latest/latest_fmp_grades_consensus.csv
    
  Duration: < 5 min (bulk) or ~12 min (per-symbol at 240/min)
  Failure: Non-blocking; retain last good data; log warning

03:45 — Existing signal refresh (unchanged)
  Zacks, Danelfin, Yahoo — current behavior preserved exactly
  Duration: ~45–60 min (Danelfin is slowest at 689 symbols)

04:45 — Analytical universe rebuild (triggered by signal freshness)
  Reads all latest_*.csv files (existing + new FMP files)
  Joins FMP columns into analytical_universe.csv
  FMP null values → no change to non-FMP scores
  Duration: < 1 min

05:00 — PAR ready for operator upload
  Operator uploads portfolio CSV via UI
  PAR run reads analytical_universe.csv (now includes FMP data)
  CW-DAS and CRA use FMP-enriched signals
```

---

## Quarterly Refresh (Earnings Season)

```
After each earnings reporting period (Jan, Apr, Jul, Oct):

Phase 1 — Bulk earnings refresh:
  /earnings-surprises-bulk?year=YYYY   → fmp_earnings_surprises_{year}_{q}.csv
  /income-statement-growth-bulk        → fmp_income_growth_{year}_{q}.csv
  Duration: < 5 min (bulk) or ~12 min (per-symbol)

Phase 2 — Event-triggered refresh for recent reporters:
  For symbols that reported this week:
    /earnings?symbol=X&limit=8         → update symbol row in fmp_earnings_surprises
  Duration: ~15 min for 50-100 symbols

Phase 3 — Analytical universe rebuild (same as daily)
```

---

## Dependency Chain

```
FMP refresh
    └─► FMP latest files fresh
        └─► Analytical universe rebuild
            └─► PAR analysis run
                └─► CW-DAS, CRA, STI (all consume from analytical universe)
```

**Key design principle:** FMP is a parallel input to the analytical universe rebuild. It does not create a new pipeline stage — it enriches an existing stage. The analytical universe rebuild already reads from multiple signal files; FMP is one more.

---

## Recovery Path

| Problem | Detection | Recovery |
|---------|-----------|---------|
| FMP refresh failed this morning | run_metadata warnings include "FMP stale" | Re-run `refresh_signals.py --providers fmp` manually; re-run PAR |
| FMP key expired | HTTP 401/402 on all endpoints | Update FMP_API_KEY in .env; restart server; re-run refresh |
| Quarterly earnings batch missed | earnings_surprises sourced_date > 3 months old | Run `refresh_signals.py --providers fmp --mode quarterly` |
| Coverage gap identified | Symbol missing from latest_fmp_key_metrics.csv | Accept gracefully; no action required |

---

## Comparison: Before and After FMP

| Phase | Before FMP | After FMP |
|-------|-----------|----------|
| 03:30 | — | FMP daily refresh (new) |
| 03:45 | Existing signal refresh | Existing signal refresh (unchanged) |
| 04:45 | Analytical universe rebuild | Analytical universe rebuild (extended with FMP join) |
| 05:00 | PAR ready | PAR ready (with FMP-enriched signals) |
| PAR Quality | Signal opinions only | Signal + fundamental context |

**Total additional time:** < 15 minutes for FMP daily refresh. Existing timeline unchanged.
