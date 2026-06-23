# PIS-007 — Allocation Drift Trend Visibility: Design Document

**Status:** APPROVED FOR IMPLEMENTATION  
**Date:** 2026-06-15  
**Phase:** PIS-007  
**Scope:** Read-only analytics enhancement — no scoring, recommendation, or optimizer changes

---

## 1. Purpose

The Portfolio Intelligence System currently exposes point-in-time allocation views: what the portfolio looks like today, what the targets are, and what the current drift is. It does not answer whether that drift is improving or worsening, which nodes are converging toward targets over time, or which nodes are persistently misaligned.

PIS-007 adds historical allocation drift intelligence and trend visibility to the PIS dashboard.

---

## 2. Required Questions — Answered

| Question | Answer | Rationale |
|----------|--------|-----------|
| Q1: Can historical allocation drift be reconstructed from existing data? | **YES** | Every PAR run persists `alignment.csv` containing `node_key`, `actual_pct`, `target_pct`, `tactical_target_pct`, `drift_pct`, `direct_actual_pct`, `etf_derived_actual_pct`, `effective_actual_pct`. 19 unique canonical dates exist spanning 2026-05-21 to 2026-06-15. No new data collection needed. |
| Q2: Are any schema changes required? | **NO** | All required fields exist in current `alignment.csv`. The drift engine reads existing artifacts and writes a new derived CSV only. No changes to PIS models, PAR models, or existing storage contracts. |
| Q3: Does the feature alter SIH recommendations? | **NO** | Read-only. No recommendation logic touched. |
| Q4: Does the feature alter allocation scoring? | **NO** | Read-only. Alignment scores unchanged. |
| Q5: Does the feature alter optimizer behavior? | **NO** | Read-only. Optimizer logic untouched. |
| Q6: Does the feature alter CW-DAS? | **NO** | Read-only. CW-DAS rank order untouched. |
| Q7: Does the feature alter benchmark attribution? | **NO** | Read-only. Benchmark attribution untouched. |
| Q8: Does the feature alter lineage? | **NO** | Read-only. Lineage logic untouched. |
| Q9: Does the feature provide meaningful new portfolio intelligence? | **YES** | Drift velocity, trend direction, and improvement/worsening classification are materially new insights not available from any current endpoint. |
| Q10: Is PIS materially more valuable after this enhancement? | **YES** | "Is my portfolio moving toward or away from mandate targets?" is a fundamental question. Point-in-time allocation answers half the question. Trend answers the other half. |

---

## 3. Data Availability Audit

### 3.1 Existing Canonical History

**19 unique canonical dates** spanning 2026-05-21 to 2026-06-15 have valid PAR runs with `alignment.csv` artifacts. Each file contains up to 40 node rows covering all hierarchy levels.

The canonical selection algorithm follows the existing `drift_analyzer.py` pattern: for each snapshot_date, select the PAR run with the latest `created_at_utc` timestamp. This produces one authoritative record per date.

### 3.2 Available Fields per Node per Date

From `alignment.csv`:

| Field | Use in Drift Engine |
|-------|---------------------|
| `node_key` | Primary identifier |
| `node_label` | Display label |
| `dimension_type` | Classification (ASSET_CLASS / GEOGRAPHY / MARKET_CAP / MEGA_SUBTIER) |
| `effective_actual_pct` | Actual allocation (preferred — includes ETF decomposition) |
| `actual_pct` | Fallback if effective_actual_pct absent |
| `target_pct` | Strategic target |
| `tactical_target_pct` | Tactical-adjusted target (preferred comparison baseline) |
| `drift_pct` | Pre-computed drift (actual − tactical_target) |
| `direct_actual_pct` | Direct-only component |
| `etf_derived_actual_pct` | ETF-contributed component |
| `decomposition_confidence_tier` | Data quality indicator |

### 3.3 Gap Analysis

**No gaps.** All required fields exist in existing alignment.csv artifacts across all 19 canonical dates. Historical reconstruction is fully feasible from existing stored artifacts without re-running any analysis.

---

## 4. Architecture

### 4.1 Module

**New file:** `src/pis/allocation_drift.py`

This module:
- Reads existing PAR `alignment.csv` artifacts (read-only)
- Applies canonical date selection (latest PAR per snapshot_date)
- Reconstructs per-node allocation history across all canonical dates
- Computes drift trend metrics (delta, velocity, direction, severity)
- Generates human-readable observations
- Exposes three API functions: `pis_allocation_drift_latest()`, `pis_allocation_drift_history()`, `pis_allocation_drift_summary()`

**No writes to existing files.** The engine optionally writes a cache file to `data/history/pis/allocation_drift_cache.csv` for performance, but this is a derived artifact and fully regeneratable.

### 4.2 New API Endpoints (3)

| Endpoint | Returns |
|----------|---------|
| `GET /api/pis/allocation-drift/latest` | Latest drift snapshot with trend metrics for all nodes |
| `GET /api/pis/allocation-drift/history` | Full time-series per node across all canonical dates |
| `GET /api/pis/allocation-drift/summary` | Summary cards payload: most improved, most deteriorated, counts |

### 4.3 Integration Points

- **Server:** `scripts/run_outcome_ui.py` — add three new elif branches
- **Dashboard JS:** `ui/pis_dashboard/app.js` — new `allocationDrift` subsystem + 4 section keys
- **Dashboard HTML:** `ui/pis_dashboard/index.html` — 4 new section panels

### 4.4 Isolation Guarantee

The feature is entirely additive:
- Zero changes to existing PAR artifact writing
- Zero changes to existing PIS storage contracts
- Zero changes to existing API endpoints
- Zero changes to alignment, scoring, or recommendation logic
- New module reads only; writes only to a new derived cache path

---

## 5. Canonical Date Selection

Mirrors the existing `drift_analyzer._canonical_by_date()` pattern:

1. Enumerate all PAR run directories under `data/portfolio_ingestion/analysis_runs/`
2. For each directory, confirm `run_metadata.json` + `alignment.csv` both exist
3. Parse `snapshot_date` (YYYY-MM-DD) and `created_at_utc` from `run_metadata.json`
4. Skip any `snapshot_date` that is not a valid 10-character ISO date
5. For each date, retain the PAR with the latest `created_at_utc` (same as Portfolio Manager runner behavior)
6. Sort retained dates ascending by `snapshot_date`

This produces an ordered list of (date, alignment_csv_path) pairs — one per canonical date.

---

## 6. Node History Reconstruction

For each canonical date and each node_key in that date's alignment.csv:

```
actual_pct      = effective_actual_pct if numeric, else actual_pct
target_pct      = tactical_target_pct if numeric, else target_pct  
drift_pct       = actual_pct − target_pct (recomputed for consistency)
drift_direction = OVERWEIGHT if drift_pct > 0, UNDERWEIGHT if < 0, ON_TARGET if ≈ 0
```

The result is a matrix:

```
node_key → [ (snapshot_date, actual_pct, target_pct, drift_pct), ... ]
```

Sorted ascending by snapshot_date.

---

## 7. Trend Metric Definitions

Given history entries `[H_0, H_1, ..., H_n]` where `H_n` is the most recent:

### Current Drift
`H_n.drift_pct`

### Prior Drift
`H_{n-1}.drift_pct` if n ≥ 1, else null.

### Drift Delta
`current_drift − prior_drift` (signed; negative = drift magnitude decreased = improving for underweight nodes is context-dependent — see Trend Direction)

### Trend Direction
The semantics of "improving" depend on whether the node is overweight or underweight.

```
if abs(current_drift) < abs(prior_drift):
    direction = IMPROVING   (drift magnitude decreasing toward zero)
elif abs(current_drift) > abs(prior_drift):
    direction = WORSENING   (drift magnitude increasing away from zero)
elif abs(current_drift - prior_drift) < STABLE_THRESHOLD:
    direction = STABLE
else:
    direction = STABLE
```

`STABLE_THRESHOLD = 0.5` percentage points (consistent with `drift_analyzer.py`).

### Trend Severity
Based on `abs(drift_delta)`:

| abs(drift_delta) | Severity |
|------------------|---------|
| < 0.5 pp | NONE |
| 0.5 – 2.0 pp | MINOR |
| 2.0 – 5.0 pp | MODERATE |
| > 5.0 pp | SIGNIFICANT |

### Drift Velocity
Rate of change across the observation window:

```
velocity_pp_per_day = (current_drift - oldest_drift) / days_span
```

Where `days_span` = calendar days between oldest and most recent entry. If only one entry exists, velocity = 0.0.

### Persistence Score
The fraction of historical entries where drift was in the same direction (OVERWEIGHT or UNDERWEIGHT) as current:

```
persistence_score = same_direction_count / total_entry_count
```

A persistence_score of 1.0 means the node has been consistently on the same side of target across all observed dates.

---

## 8. API Contract Definitions

### 8.1 GET /api/pis/allocation-drift/summary

```json
{
  "generated_at": "ISO timestamp",
  "dates_available": 19,
  "current_date": "2026-06-15",
  "prior_date": "2026-06-14",
  "most_improved_node": {
    "node_key": "CASH",
    "node_label": "Cash",
    "current_drift": 1.2,
    "prior_drift": 6.4,
    "drift_delta": -5.2,
    "trend_direction": "IMPROVING"
  },
  "most_deteriorated_node": {
    "node_key": "EQUITIES.US.MID",
    "node_label": "US Mid Cap",
    "current_drift": -8.3,
    "prior_drift": -4.1,
    "drift_delta": -4.2,
    "trend_direction": "WORSENING"
  },
  "improving_count": 6,
  "worsening_count": 4,
  "stable_count": 14,
  "observations": [
    "EQUITIES.US.MID has deteriorated from -4.1pp to -8.3pp since the prior period.",
    "CASH drift improved from +6.4pp to +1.2pp since the prior period."
  ]
}
```

### 8.2 GET /api/pis/allocation-drift/latest

```json
{
  "generated_at": "ISO timestamp",
  "current_date": "2026-06-15",
  "nodes": [
    {
      "node_key": "EQUITIES",
      "node_label": "Equities",
      "dimension_type": "ASSET_CLASS",
      "current_actual_pct": 94.97,
      "current_target_pct": 88.0,
      "current_drift_pct": 6.97,
      "prior_drift_pct": 7.12,
      "drift_delta_pp": -0.15,
      "trend_direction": "IMPROVING",
      "trend_severity": "NONE",
      "drift_velocity_pp_per_day": -0.04,
      "persistence_score": 1.0,
      "observations": "Persistently OVERWEIGHT across all 19 observed dates. Drift magnitude slightly improving."
    }
  ]
}
```

### 8.3 GET /api/pis/allocation-drift/history

```json
{
  "generated_at": "ISO timestamp",
  "dates": ["2026-05-21", "2026-05-22", "..."],
  "nodes": [
    {
      "node_key": "EQUITIES.US.MID",
      "node_label": "US Mid Cap",
      "dimension_type": "MARKET_CAP",
      "entries": [
        {
          "snapshot_date": "2026-05-21",
          "actual_pct": 18.4,
          "target_pct": 20.0,
          "drift_pct": -1.6
        },
        {
          "snapshot_date": "2026-06-15",
          "actual_pct": 13.3,
          "target_pct": 20.0,
          "drift_pct": -6.7
        }
      ]
    }
  ]
}
```

---

## 9. Dashboard Section Design

### 9.1 New Subsystem: "Allocation Drift Trends"

Added to `SUBSYSTEM_DEFINITIONS` in `app.js` with four section keys:

| Section Key | Content |
|-------------|---------|
| `driftSummary` | Summary cards: most improved, most deteriorated, counts, key observations |
| `driftTrendTable` | Full sortable node table with current drift, prior drift, delta, trend, severity |
| `driftWorsening` | Top worsening nodes highlight panel |
| `driftImproving` | Top improving nodes highlight panel |

### 9.2 Summary Cards

```
┌─────────────────────────────────────────────────────────────────────┐
│  ALLOCATION DRIFT TRENDS  (19 canonical dates — 2026-05-21 to today) │
├───────────┬───────────────┬──────────────┬──────────────┬───────────┤
│ Improving │ Worsening     │ Stable       │ Most Improved│ Most Det. │
│     6     │     4         │    14        │ CASH −5.2pp  │ MID +4.2pp│
└───────────┴───────────────┴──────────────┴──────────────┴───────────┘
```

### 9.3 Drift Trend Table Columns

| Column | Sortable | Format |
|--------|----------|--------|
| Node | ✓ | `EQUITIES.US.MID` |
| Label | ✓ | "US Mid Cap" |
| Current Drift | ✓ | `−6.7pp` (colored) |
| Prior Drift | ✓ | `−4.1pp` |
| Drift Delta | ✓ | `−2.6pp` |
| Trend | ✓ | WORSENING badge |
| Severity | ✓ | MODERATE badge |
| Velocity | — | `−0.18pp/day` |

### 9.4 Trend Color Coding

- `IMPROVING` badge: green (`#2e7d32`)
- `WORSENING` badge: red (`#c62828`)
- `STABLE` badge: gray
- Drift positive: orange (overweight)
- Drift negative: blue (underweight)
- Drift ≈ 0: green (on target)

### 9.5 Observations Panel

Below summary cards: human-readable observations generated by the engine:

```
Key Observations:
• EQUITIES.US.MID has deteriorated from -4.1pp to -8.3pp since the prior period.
• CASH drift improved from +6.4pp to +1.2pp since the prior period.
• EQUITIES.INTERNATIONAL remains persistently overweight across all 19 observed dates.
• EQUITIES.US.LARGE has been underweight for 14 of 19 observed dates.
```

---

## 10. Observations Engine

Human-readable observations are generated deterministically from the trend data. Logic:

```python
def _generate_observations(nodes: list[NodeTrendResult]) -> list[str]:
    obs = []
    for node in nodes:
        if node.trend_direction == "WORSENING" and node.trend_severity in ("MODERATE", "SIGNIFICANT"):
            sign = "deteriorated" if trend worsening else "improved"
            obs.append(f"{node.node_label} has {sign} from {prior_drift:+.1f}pp to {current_drift:+.1f}pp since the prior period.")
        if node.persistence_score == 1.0 and node.dates_available >= 5:
            direction = "overweight" if node.current_drift_pct > 0 else "underweight"
            obs.append(f"{node.node_label} remains persistently {direction} across all {dates_available} observed dates.")
    return obs[:8]  # cap at 8 observations
```

---

## 11. Cache Strategy

For performance under the existing single-threaded server, the drift engine caches its computed history to `data/history/pis/allocation_drift_cache.json` on first computation. The cache is invalidated when any PAR run directory is newer than the cache file's mtime. This ensures the API responds quickly on repeat calls while staying current after new PAR runs.

Cache structure matches the `/api/pis/allocation-drift/history` payload. Cache is a derived artifact — it can be deleted and will be regenerated on next request.

---

## 12. Implementation Files

| File | Status | Role |
|------|--------|------|
| `src/pis/allocation_drift.py` | **NEW** | Core drift engine + API functions |
| `scripts/run_outcome_ui.py` | **MODIFIED** | Add 3 new elif branches |
| `ui/pis_dashboard/app.js` | **MODIFIED** | Add subsystem + sections + render functions |
| `ui/pis_dashboard/index.html` | **MODIFIED** | Add 4 new section panels |
| `tests/test_pis_allocation_drift_trends.py` | **NEW** | Validation test suite |

---

## 13. Non-Goals

- No changes to SIH allocation scoring or target computation
- No changes to PAR run artifacts
- No changes to existing PIS API endpoints
- No changes to recommendation engine
- No changes to CW-DAS, UCF, or deployment queue
- No ML, no prediction, no forecasting
- No auto-suggestion to "rebalance" — observations are informational only
