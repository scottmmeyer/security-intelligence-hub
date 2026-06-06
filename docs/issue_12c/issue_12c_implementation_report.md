# ISSUE-12C — Implementation Report
## Dislocation Outcome Computation Engine

**Date:** June 5, 2026  
**Status:** COMPLETE  
**Scope:** ISSUE-12B (detection persistence) + ISSUE-12C (outcome computation). No scoring changes.

---

## 1. Summary

Implemented the full dislocation outcome tracking pipeline in two integrated phases:

- **ISSUE-12B** (detection persistence): appends dislocation detection snapshots to `data/derived/dislocation_detections.csv` at every PAR run
- **ISSUE-12C** (outcome engine): computes realized returns vs. SPY benchmark from mature detections, produces `dislocation_outcomes.csv` and `dislocation_outcome_summary.json`

---

## 2. Files Created / Modified

| File | Change |
|------|--------|
| `src/portfolio/outcome_tracker.py` | New module — `persist_dislocation_detections()`, `compute_outcomes()`, `build_outcome_summary()`, helpers |
| `src/portfolio/runner.py` | Import `persist_dislocation_detections`; call it after `dislocation_by_symbol` is built (wrapped in try/except — tracking never breaks the analysis run) |
| `tests/test_issue_12bc_outcome_tracker.py` | 30 unit tests |

**No UI changes. No scoring changes. No CW-DAS changes. No CRA changes.**

---

## 3. ISSUE-12B: Detection Persistence

### `persist_dislocation_detections()`

Called from `runner.py` after `dislocation_by_symbol` is computed:

```python
persist_dislocation_detections(
    detection_date=snapshot_date,
    run_id=run_id,
    dislocation_payload=_disloc_payload,
    overlays=overlays,
    dq_payload=dq_payload,
    yahoo_prices=_yahoo_prices,
)
```

**Output:** `data/derived/dislocation_detections.csv` — append-only.

**De-duplication:** Skips `(detection_date, symbol, tier)` tuples already in the file. A persistent dislocation across consecutive run dates is not re-logged.

**NONE tier exclusion:** Only non-NONE detections are recorded.

**Schema:**
```
detection_date, run_id, symbol, tier, dislocation_class, active_classes,
ess_at_detection, danelfin_at_detection, replay_percentile_at_detection,
replay_supported_at_detection, composite_score_at_detection,
cw_das_score_at_detection, thesis_integrity_at_detection,
fundamental_modifier_at_detection, dislocation_version, price_at_detection
```

### Governance

The call is wrapped in `try/except Exception: pass`. A failure in the tracking
write (permissions, disk full, etc.) never propagates to the analysis run.
Tracking is additive and non-blocking.

---

## 4. ISSUE-12C: Outcome Computation Engine

### `compute_outcomes(holding_period_days, ...)`

Batch function. Reads `dislocation_detections.csv`, fetches price history via
yfinance, computes per-detection returns, writes `dislocation_outcomes.csv`.

**Maturity filter:** Only processes detections where
`detection_date + holding_period_days <= today`.

**Price sourcing:**
- `price_at_detection`: stored at run time in detections CSV (no retroactive fetch needed)
- `price_at_outcome`: fetched via yfinance `auto_adjust=True` for the outcome date
- `SPY` benchmark prices: fetched in same yfinance call, covering all detection/outcome date pairs

**Nearest-price logic:** If outcome_date falls on a weekend/holiday, falls back
to the nearest prior trading day (up to 5 days back). If no price is found,
the row is excluded rather than imputed.

**Injectable fetch function:** The `_fetch_fn` parameter accepts any callable
matching `(symbol, start, end) -> {date: price}`. Used in tests to avoid live
network calls.

### `build_outcome_summary(holding_period_days, ...)`

Aggregates outcome rows into `dislocation_outcome_summary.json`:

```json
{
  "holding_period_days": 90,
  "total_outcomes": N,
  "computed_at": "YYYY-MM-DD",
  "by_tier": {
    "HIGH_CONVICTION": { "detection_count": N, "hit_rate": %, "median_excess_return": %, "mean_excess_return": % },
    "MODERATE": { ... },
    "WATCH": { ... }
  },
  "by_class": {
    "A1_FUNDAMENTAL_BEAT_DIVERGENCE": { ... },
    "D1_REPLAY_SIGNAL_LAG": { ... },
    "B2_ANALYST_AI_DIVERGENCE": { ... },
    "MULTI_CLASS": { ... }
  }
}
```

Multi-class rows are counted in each of their contributing classes AND in the
`MULTI_CLASS` bucket — allowing independent class evaluation as specified in
ISSUE-12 assessment.

---

## 5. No Outcomes Yet (Expected)

**Detection start: June 5, 2026.** No detections are mature for any holding period.
The engine returns an empty list today, which is the correct behavior.

**First 30-day outcomes:** July 5, 2026  
**First 90-day outcomes:** September 3, 2026  
**First meaningful statistical analysis:** September–October 2026
