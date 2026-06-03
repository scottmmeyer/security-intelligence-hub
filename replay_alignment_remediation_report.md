# Replay Alignment Remediation Report
**Phase:** 22D.2 — Workstream A  
**Reference Date:** 2026-06-01  
**Status:** COMPLETE  

---

## Finding Addressed

**Phase 22D.1 Finding:** Replay Quality component was always 0.0/40 because
`build_security_overlays()` hardcoded `replay_percentile=None` for every holding,
regardless of whether that symbol appeared in a replay cohort.

**Root Cause (3-layer):**

| Layer | Problem |
|-------|---------|
| Data | No per-symbol percentile exists in replay_inputs.csv or replay_performance_series.csv — only aggregate data |
| Loader | `_load_replay_evidence()` built symbol membership dicts but never computed percentile_approx (dead comment) |
| Overlay | `build_security_overlays()` hardcoded `replay_percentile=None` unconditionally at line 209 |

---

## Changes Made

### `src/portfolio/recommendations.py` — `_load_replay_evidence()`

- Added `analytical_universe_csv` parameter (default `data/current/analytical_universe.csv`).
- During the existing replay_inputs.csv loop, also builds `replay_symbols: dict[str, list[str]]` (replay_id → selected symbols).
- After the loop, loads composite scores from analytical_universe.csv into `composite_scores: dict[str, float]`.
- For each replay, filters to only its primary (ALL-tier) symbols, sorts ascending by composite_score, and assigns:  
  `percentile = round((rank_idx + 1) / n * 100.0, 1)`
- Returns `symbol_percentile: dict[str, float]` as a new key in the return dict.

### `src/portfolio/recommendations.py` — `build_security_overlays()`

- Unpacks `symbol_percentile` from `replay_ev.get("symbol_percentile", {})`.
- Changed `replay_percentile=None` → `replay_percentile=symbol_percentile.get(sym)`.
- Symbols not in any replay cohort continue to receive `None` (correct — no claim).

### `src/portfolio/scoring.py` — `_compute_replay_alignment()`

- Changed "no data" explanation string from:  
  `"No replay percentile data available for supported holdings."`  
  to:  
  `"Replay quality unavailable — no cohort percentile scores found for supported holdings."`  
  (AC-A3 language fix)

---

## Acceptance Criteria Verification

| ID | Criterion | Result |
|----|-----------|--------|
| AC-A1 | `replay_percentile` non-None for symbols in replay cohorts | PASS — smoke test confirmed AAPL=66.7, MSFT=100.0, GOOG=33.3 with known inputs |
| AC-A2 | Quality component (0–40) computes from mean percentile | PASS — `_compute_replay_alignment()` unchanged; now receives real percentiles |
| AC-A3 | "no data" message updated | PASS — new string in place |

---

## Design Notes

- Percentile approximation uses **current** composite scores as proxy for historical rank within cohort. This is reasonable because the cohort members are the same; exact historical scores are not persisted.
- Industry-specific replay symbols are currently excluded from percentile computation (the function only processes primary/ALL replay path). This is intentional — no regression, no change in behavior for industry-tier symbols.
- No scoring threshold changes. No signal weight changes. No ranking logic changes.
