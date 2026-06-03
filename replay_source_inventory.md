# Replay Source File Inventory — Phase 7.5S-A
**Date:** 2026-06-01  
**Purpose:** Catalog every source file involved in replay evidence, from raw storage to UI output.

---

## Tier 1 — Sole Determinant of `replay_supported`

### `data/current/replay_inputs.csv`
**Role:** Single source of truth for `replay_supported`. If a symbol appears in this file's `selected_symbols` column, it can receive replay support. No other file governs the boolean.

| Field | Description |
|-------|-------------|
| `replay_id` | Unique replay identifier (encodes geo, cap, industry, date range) |
| `start_date` | Start of the replay observation window |
| `end_date` | End of the replay observation window |
| `filter_geography` | US or INTERNATIONAL |
| `filter_market_cap_bucket` | MEGA, LARGE, MID, SMALL, MICRO |
| `filter_industry` | Specific industry (e.g., TECHNOLOGY) or ALL |
| `selection_method` | TOP_N_COMPOSITE_AT_START |
| `top_n` | Number of symbols selected (typically 20) |
| `selected_symbols` | Pipe-delimited list of symbols (e.g., `VRT|ARW|MSFT|...`) |
| `composite_score_snapshot_date` | Date the composite scores were frozen for selection |
| `replay_mode` | HISTORICAL_VALIDATION or CURRENT_RECOMMENDATION |

**Row count:** 120  
**Contains target symbols:** VRT (2 rows), ARW (2 rows), CIEN (1 row), CAH (1 row), ATLC (1 row); PRG: 0 rows

---

## Tier 2 — Performance Context (Not Used for Support Boolean)

### `data/current/replay_performance_series.csv`
**Role:** Tracks daily basket performance for each replay. Contains four series types: BENCHMARK, FULL_UNIVERSE, TOP_N_STRATEGY, INVESTABLE_VEHICLE. Used for UI performance visualization. **Does NOT affect `replay_supported`.**

| Field | Description |
|-------|-------------|
| `series_id` | Replay ID (same as replay_id — one series per replay, not per symbol) |
| `replay_id` | Replay identifier |
| `series_type` | BENCHMARK / FULL_UNIVERSE / TOP_N_STRATEGY / INVESTABLE_VEHICLE |
| `date` | Trading day |
| `value` | Daily price/index level |
| `cumulative_return` | Cumulative return since start_date |
| `source` | Data provider |
| `coverage_status` | AVAILABLE / PARTIAL / UNAVAILABLE |

**Row count:** 80,526  
**Series types:** The series tracks basket-level performance (the combined top-N portfolio), not individual symbol returns. Symbol-level return tracking is not present in this file.

---

## Tier 3 — Replay Registry and Availability

### `data/current/replay_availability.csv`
**Role:** Per-tier matrix indicating which combinations of (geography, market_cap_bucket, industry) have generated replays. Controls what is shown as available in the UI.

| Field | Description |
|-------|-------------|
| `geography` | US or INTERNATIONAL |
| `market_cap_bucket` | MEGA through MICRO |
| `industry` | Specific or ALL |
| `benchmark_available` | Whether a benchmark series exists |
| `vehicle_available` | Whether an investable vehicle series exists |
| `stock_replay_available` | Whether individual stock data is available |
| `top_n_available` | Whether a top-N basket selection was generated |
| `replay_generated` | Whether this tier produced a replay in replay_inputs |
| `replay_status` | AVAILABLE / UNAVAILABLE / PARTIAL |

**Row count:** 120 (one per geo × cap × industry combination)

### `data/history/replay_snapshot_registry.csv`
**Role:** Immutable append-only historical registry of all replays ever generated, with their metadata. Serves as the audit trail for replay generation history.

| Field | Description |
|-------|-------------|
| `replay_id` | Unique replay identifier |
| `snapshot_date` | Date scores were frozen |
| `start_date` | Replay window start |
| `end_date` | Replay window end |
| `geography`, `market_cap_bucket`, `industry` | Filter dimensions |
| `replay_mode` | HISTORICAL_VALIDATION or CURRENT_RECOMMENDATION |
| `generated_at_utc` | When this replay was materialized |

**Row count:** 1,211 entries

### `data/history/replays/`
**Role:** Directory of 46 individual replay partition directories, each storing point-in-time replay snapshots by run ID. Preserves historical replay state for audit and reprocessing.

---

## Tier 4 — Classification Data (Used in Tier-Compatibility Check)

### `data/current/analytical_universe.csv`
**Role:** Provides the holding's canonical classification (`geography`, `market_cap_bucket`, `industry`) used in the tier-compatibility check for industry-specific replays. Without a matching classification, a symbol in `industry_replay_evidence` would NOT receive `replay_supported=True`.

**Fields consulted per symbol:**
- `geography` → must match `replay.filter_geography`
- `market_cap_bucket` → must match `replay.filter_market_cap_bucket`
- `industry` → must match `replay.filter_industry` (exact string, case-insensitive)
- `composite_score` → used for top-N selection at snapshot date
- `ess_score_text` → used for signal direction (separate from replay support)

---

## Tier 5 — Code That Reads the Files

| File | Function | Role |
|------|----------|------|
| `src/portfolio/recommendations.py` | `_load_replay_evidence()` | Reads `replay_inputs.csv`, builds `symbol_tier` and `industry_replay_evidence` dicts |
| `src/portfolio/recommendations.py` | `build_security_overlays()` | Applies tier-compatibility check, sets `overlay.replay_supported` |
| `src/portfolio/runner.py` | `run_analysis()` | Calls `build_security_overlays()`, persists overlays to run output |
| `src/portfolio/deployment_queue.py` | `compute_cw_das_score()` | Reads `overlay.replay_supported`; adds 20 pts to CW-DAS if True |
| `src/portfolio/trim_intelligence.py` | `_tier_for()` | Reads `overlay.replay_supported`; required for CCL promotion |
| `src/portfolio/scoring.py` | `build_concentration_score()` | Reads `overlay.replay_supported` for concentration calculation |
| `src/portfolio/phase_e_synthesis.py` | Various | Reads `overlay.replay_supported` for deployment recommendation logic |
| `src/portfolio/unified_conviction.py` | `build_unified_conviction_profile()` | Reads `overlay.replay_supported`; drives conviction narrative and tier |

---

## Tier 6 — Output Files (Downstream Consumers)

### `data/portfolio_ingestion/analysis_runs/{run_id}/security_overlays.csv`
Contains `replay_supported` column — one row per holding. This is what the UI reads.

### `data/portfolio_ingestion/analysis_runs/{run_id}/deployment_queue.json`
Contains `replay_supported` per deployment candidate, alongside CW-DAS score and `replay_component` (0 or 20 points).

### `data/portfolio_ingestion/analysis_runs/{run_id}/run_metadata.json`
Does not include per-symbol replay flags but includes overall run status.

---

## Source Dependency Graph

```
data/current/replay_inputs.csv          ← ONLY source for replay_supported
        ↓
_load_replay_evidence()
        ↓ symbol_tier (ALL replays)
        ↓ industry_replay_evidence (industry-specific replays)
        ↓
build_security_overlays() + analytical_universe.csv (tier check)
        ↓
SecurityIntelligenceOverlay.replay_supported  (True / False)
        ↓
┌─────────────────────────────────────────────────────┐
│  deployment_queue.py  →  CW-DAS +20 pts             │
│  trim_intelligence.py →  CCL gate requirement        │
│  scoring.py           →  concentration calculation   │
│  unified_conviction.py→  conviction narrative        │
│  phase_e_synthesis.py →  deployment recommendation   │
└─────────────────────────────────────────────────────┘
        ↓
security_overlays.csv / deployment_queue.json  (persisted)
        ↓
UI display
```

---

## Key Structural Observations

1. **Single-file dependency:** `replay_inputs.csv` alone determines `replay_supported`. Removing or modifying this file directly and immediately changes the boolean for all symbols.

2. **No price data involved:** `replay_supported` is not based on return performance. It is based only on whether the symbol was selected in a composite-score-based top-N basket at a prior snapshot date.

3. **Classification dependency for industry-specific replays:** For CIEN, CAH, ATLC — if their `industry` field in `analytical_universe.csv` were changed (e.g., CIEN reclassified from TECHNOLOGY to COMMUNICATIONS), the tier-compatibility check would fail and `replay_supported` would become False, even though CIEN's replay_inputs row still exists.

4. **ALL replays bypass classification:** For VRT and ARW, `replay_supported` is unconditional. No classification change can remove their support as long as they remain in the ALL replay's `selected_symbols`.

5. **`replay_performance_series.csv` is cosmetic for support purposes.** It drives visualization of basket returns in the UI but has zero effect on the `replay_supported` boolean.
