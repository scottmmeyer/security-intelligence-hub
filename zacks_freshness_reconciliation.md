# REFRESH-HEALTH-02A Part E - Zacks Freshness Reconciliation

Date: 2026-06-17
Scope: Top-card stale vs holdings-coverage compliant contradiction

## Evidence

1. Top-card source logic (scripts/run_outcome_ui.py):
- zacks sourced_date uses _sourced_date(data/signals/zacks/latest_zacks.csv).
- _sourced_date returns first sourced_date encountered in file, not max.
- Top-card stale flag is (sourced_date != today).

2. Current zacks file observations:
- Head rows have sourced_date=2026-06-16.
- File distribution includes multiple sourced_date values (older and newer cohorts), but no 2026-06-17 rows.
- latest_zacks.csv mtime: 2026-06-16 16:34:09 local.

3. Coverage panel source logic:
- Uses src/portfolio/holdings_coverage.py summarize_holdings_coverage with threshold_days=2.
- For each applicable holding, classification is:
  - COVERED_TODAY if sourced_date == today and primary fields present
  - COVERED_WITHIN_THRESHOLD if age_days <= 2 and primary fields present
- Status COMPLIANT if missing==0 and stale==0 and failed==0.

4. Current coverage report values:
- Applicable holdings: 24
- Covered today: 0
- Covered within threshold: 24
- Stale: 0
- Missing: 0
- Status: COMPLIANT

5. Refresh report confirmation:
- data/current/last_signal_refresh_report.json shows zacks provider state RESEARCH_FRESH_COMPLIANT logic path where refresh was not triggered because holdings remained within threshold.

## Why the Contradiction Appears

No real contradiction in current model:
- Top card answers: "Was provider feed sourced today?"
- Coverage panel answers: "Are portfolio-applicable holdings within allowed freshness window (2 days)?"

So zacks can be:
- stale at provider-level date (2026-06-16 != 2026-06-17), and
- compliant for holdings coverage (all applicable holdings age_days=1).

## Timestamp Source Map

| Surface | Timestamp Source | Current Value |
|---|---|---|
| Top card Zacks date | first sourced_date in data/signals/zacks/latest_zacks.csv | 2026-06-16 |
| Coverage panel Zacks freshness | per-holding sourced_date in latest_zacks.csv with threshold_days=2 | all applicable <=1 day old |
| Provider health/report | data/current/last_signal_refresh_report.json | run at 2026-06-17 06:39 local equivalent |
| Dashboard display payload | scripts/run_outcome_ui.py _signal_status() | combines both views |
| Overlay timestamp | PAR-20260617-001280E0/security_overlays.csv mtime | 2026-06-17 06:30:39 local |

## Authority Assessment

Authoritative freshness depends on purpose:
- Research-provider freshness authority: top card sourced_date (day-level provider recency).
- Portfolio-risk freshness authority: holdings_coverage status (threshold-window compliance for applicable holdings).

Both are valid, but semantically different.

## Part E Conclusion

Zacks still displays stale because provider-level sourced_date is 2026-06-16. Coverage panel shows compliant because holdings are within the 2-day threshold. This is expected under current dual-metric design, not necessarily a defect.