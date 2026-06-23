# PA-006A Implementation — Allocation Drift Trend Visibility

**Date:** 2026-06-15  
**Status:** COMPLETE

---

## Scope Delivered (Phase 1 MVP — Exact as Approved)

| Item | Status |
|------|--------|
| `src/portfolio/drift_analyzer.py` | ✅ Created |
| `compute_drift_summary()` | ✅ Implemented |
| `compute_drift_timeline(rule_id)` | ✅ Implemented |
| `GET /api/drift/summary` | ✅ Live |
| `GET /api/drift/timeline` | ✅ Live |
| HTML section `section-drift-trends` | ✅ Added |
| View 1: CPV Trend Table | ✅ Implemented |
| View 4: Drift Summary Banner | ✅ Implemented |
| No holdings.csv parsing | ✅ Confirmed (compliance.json only) |
| No contributor analysis | ✅ Not implemented (Phase 2) |
| No sparklines / charts | ✅ Not implemented (Phase 2) |
| 23 regression tests | ✅ All passing |

---

## Files Changed

### New
- `src/portfolio/drift_analyzer.py` — core drift computation module
- `tests/test_pa_006a_drift_analyzer.py` — 23 regression tests

### Modified
- `scripts/run_outcome_ui.py` — added `GET /api/drift/summary` and `GET /api/drift/timeline` routes
- `ui/allocation_intelligence/index.html` — added `section-drift-trends` panel after CPV compliance
- `ui/allocation_intelligence/app.js` — added `renderDriftTrends()` function, called from render pipeline

### Unchanged
- No changes to: `compliance_validator.py`, any attribution files, any PIS files, any recommendation logic, any scoring logic, `allocation_policy.yaml`

---

## Module Design: `drift_analyzer.py`

### `compute_drift_summary(repo_root)`

**Input:** Repository root path  
**Algorithm:**
1. Scan all PAR run directories for `run_metadata.json` + `compliance.json` pairs
2. Group by `snapshot_date`, select latest `created_at_utc` per date (canonical selection)
3. For current date: extract per-rule actual_pct values
4. Compute 7d and 30d reference points (nearest available date at or before target)
5. Compute `_cpv_status()` for current and prior values
6. Compute `_trend_direction()` from 7d delta (falls back to prior delta if 7d unavailable)

**Output:** JSON dict with `cpv_trend` array (one entry per CPV rule), `current_date`, `prior_date`, `dates_available`, overall compliance status/score.

### `compute_drift_timeline(rule_id, repo_root)`

**Input:** CPV rule ID (e.g. "CPV-01"), repository root  
**Algorithm:**
1. Load all compliance records (same as above)
2. Pick canonical record per date
3. For each date where the rule has data: emit `{date, actual_pct, status, breach_pp}`

**Output:** JSON dict with `timeline` array, `policy_limit_pct`, threshold boundaries.

### `_cpv_status(rule_id, actual_pct)` → `(status, breach_pp)`

Deterministic: mirrors `compliance_validator.py` tolerance logic. Reads from in-module `_CPV_POLICY` constants — does **not** read `allocation_policy.yaml` at runtime (avoids I/O overhead; constants kept in sync with yaml).

### `_trend_direction(rule_id, delta_pp)` → `str`

- For **ceiling** rules: positive delta = `WORSENING`, negative = `IMPROVING`
- For **floor** rules: negative delta = `WORSENING`, positive = `IMPROVING`
- `|delta| < 0.5pp` = `STABLE`
- `None` delta = `UNKNOWN`

---

## API Endpoint Specification

### GET `/api/drift/summary`

```json
{
  "generated_at": "2026-06-15T14:30:00",
  "current_date": "2026-06-15",
  "prior_date": "2026-05-29",
  "dates_available": 3,
  "current_overall_status": "WARN",
  "current_compliance_score": 80,
  "cpv_trend": [
    {
      "rule_id": "CPV-01",
      "name": "Combined Micro Cap",
      "rule_type": "ceiling",
      "policy_limit_pct": 5.0,
      "current_pct": 8.89,
      "prior_pct": 8.5277,
      "delta_7d_pp": 0.3623,
      "delta_30d_pp": null,
      "current_status": "WARN",
      "prior_status": "WARN",
      "trend_direction": "STABLE",
      "breach_pp": 3.89
    }
  ]
}
```

### GET `/api/drift/timeline?rule_id=CPV-01`

```json
{
  "rule_id": "CPV-01",
  "name": "Combined Micro Cap",
  "rule_type": "ceiling",
  "policy_limit_pct": 5.0,
  "advisory_threshold_pct": 7.0,
  "warn_threshold_pct": 9.0,
  "timeline": [
    {"date": "2026-05-21", "actual_pct": 9.5151, "status": "FAIL", "breach_pp": 4.5151, "par_id": "PAR-20260521-074B9F92"},
    {"date": "2026-05-29", "actual_pct": 8.5277, "status": "WARN", "breach_pp": 3.5277, "par_id": "PAR-20260529-0326C559"},
    {"date": "2026-06-15", "actual_pct": 8.89,   "status": "WARN", "breach_pp": 3.89,   "par_id": "PAR-20260615-1716B213"}
  ]
}
```

---

## Dashboard Section

### HTML (added after `section-portfolio-compliance`)

Panel ID: `section-drift-trends`  
Card body ID: `drift-trends-body`  
Sub-elements: `drift-summary-banner`, `drift-trend-table-wrap`, `drift-empty`

### JS (`renderDriftTrends()`)

- Fetches `/api/drift/summary`
- Renders drift summary banner (View 4) with violation count, severity, improving/worsening counts
- Renders CPV trend table (View 1) with all 8 rules, policy limits, current/prior values, deltas, trend arrows
- Uses existing `badge-fail`, `badge-warn`, `badge-ok` CSS classes
- Hides section if no data available
- Called from main render pipeline after `renderPortfolioCompliance()`

---

## Live API Verification (2026-06-15)

```
GET /api/drift/summary
  current_date: 2026-06-15
  dates_available: 3 (May-21, May-29, Jun-15)
  overall: WARN  score: 80
  CPV-01: 8.89% WARN  trend=STABLE   delta7d=+0.36pp
  CPV-05: 17.52% OK   trend=WORSENING delta7d=-1.80pp
  CPV-06: 86.72% WARN trend=IMPROVING delta7d=-2.07pp

GET /api/drift/timeline?rule_id=CPV-01
  2026-05-21: 9.52% FAIL  breach=4.52pp
  2026-05-29: 8.53% WARN  breach=3.53pp
  2026-06-15: 8.89% WARN  breach=3.89pp
```
