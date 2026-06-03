# Replay Alignment Gap Analysis
**Phase 22D.1 — Audit Objective #1**  
**Reference Date:** 2026-06-01  
**Status:** FULLY DIAGNOSED — 3-layer pipeline gap

---

## Observed Symptom

The Portfolio Quality dashboard shows **Replay Alignment KPI = 31.7/100** with a sub-component breakdown of:
- Coverage component: **31.7/60** (correct and functional)
- Quality component: **0.0/40** (silently zeroed)
- UI tooltip: *"Replay percentile data is not present"*

---

## Root Cause: 3-Layer Pipeline Gap

### Layer 1 — Data Layer: No Per-Symbol Percentile Exists Anywhere

The replay data pipeline produces only aggregate performance data. Specifically:

| File | Schema | Contains Percentile? |
|------|--------|----------------------|
| `data/current/replay_inputs.csv` | `replay_id, start_date, end_date, filter_*, selected_symbols, ...` | ❌ No |
| `data/current/replay_performance_series.csv` | `series_id, replay_id, series_type, date, value, cumulative_return, source, coverage_status` | ❌ No |
| `data/history/replays/*/replay_evidence_summary.json` | `benchmark_return, vehicle_return, top_n_final_return, strategy_vs_benchmark_delta` | ❌ No |
| `data/current/replay_matrix.csv` | `replay_id, ..., replay_evidence_summary_path` | ❌ No |

No file anywhere in the repository contains a per-symbol percentile rank within its replay cohort. The concept of "how did this symbol rank among all symbols in replay R" is **entirely uncomputed and unsaved**.

The comment in `src/portfolio/recommendations.py` line 49 describes the `symbol_replay` dict as containing `"replay_id, return, replay_id, **percentile_approx**"` — this is a **dead comment referencing an unimplemented field**. No `percentile_approx` value is ever loaded or stored.

---

### Layer 2 — Loader Layer: `_load_replay_evidence()` Only Reads Membership

**File:** `src/portfolio/recommendations.py`, lines 49–112

`_load_replay_evidence()` reads `replay_inputs.csv` to identify which symbols appear in each replay (`selected_symbols` column). It builds:
- `symbol_tier` dict: symbol → allocation tier
- `symbol_replay` dict: symbol → `{replay_id, tier}` (only membership, no percentile)

It **does not** read `replay_performance_series.csv`. It **does not** compute any ranking or percentile within the replay cohort. There is no fallback logic that approximates percentile from composite score rank.

---

### Layer 3 — Overlay Layer: `replay_percentile=None` Is Hardcoded

**File:** `src/portfolio/recommendations.py`, line 212

```python
replay_percentile=None,   # hardcoded — never populated
```

`build_security_overlays()` correctly sets `replay_supported=in_replay` based on the loader output, but `replay_percentile` is unconditionally `None` for every overlay regardless of whether the symbol is in a replay or not.

---

## Scoring Engine Consequence

**File:** `src/portfolio/scoring.py`, lines 312–383  
**Function:** `_compute_replay_alignment()`

```python
percentiles = [
    _to_float(_fld(o, "replay_percentile"))
    for o in supported
    if _fld(o, "replay_percentile") is not None
]
# When all replay_percentile=None: percentiles = []
qual_score = mean_percentile / 100.0 * 40.0  # → 0.0
expl = "No replay percentile data available for supported holdings."
```

- **Coverage component** (0–60): Works correctly. Computes `replay_pct / total_pct * 60.0`. For this portfolio: ~52.8% replay-supported → 31.7/60.
- **Quality component** (0–40): Always zeros because `percentiles=[]`. The "0.0" score is **not a data quality issue with individual securities** — it is a structural gap in the pipeline that silently discards 40% of the KPI.

---

## Impact Assessment

| Dimension | Impact |
|-----------|--------|
| KPI accuracy | Quality component is permanently 0.0/40; KPI ceiling is 60/100 regardless of actual replay performance |
| Operator trust | Score appears explanatory but silently caps without any visible indicator beyond the tooltip text |
| Downstream scoring | Portfolio Quality Score includes Replay Alignment; the zero bias suppresses overall PQS for all replays |
| Severity | **HIGH** — affects every portfolio run, not just edge cases |

---

## Required Fix (Not in Scope — Audit Only)

To fix properly, the pipeline needs:
1. **Data**: After a replay completes, compute per-symbol rank within the replay cohort (by composite_score at replay snapshot date). Store as `percentile_approx` in `replay_inputs.csv` or a new `replay_symbol_performance.csv`.
2. **Loader**: Update `_load_replay_evidence()` to load `percentile_approx` from that file and store in `symbol_replay`.
3. **Overlay**: Update `build_security_overlays()` line 212 to assign `replay_percentile` from `symbol_replay[symbol].get("percentile_approx")` instead of hardcoding `None`.

---

## Classification

**Severity: HIGH**  
- Permanently zeros 40% of the Replay Alignment KPI for every run
- Silent failure — no error raised, no warning surfaced in logs
- Dead code comment in `recommendations.py` suggests this was intended but never implemented
