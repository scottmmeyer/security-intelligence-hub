# Zacks Source Inventory

**Date:** 2026-06-10

---

## Source 1: Direct Zacks Website Fetch

| Attribute | Value |
|---|---|
| Source Name | Direct Zacks / Zacks.com |
| File Path | `data/signals/zacks/latest_zacks.csv` |
| Partitioned history | `data/signals/zacks/YYYY-MM-DD_zacks.csv` |
| Field Names | `symbol`, `zacks_rank`, `zacks_score`, `abr`, `price_target`, `eps_growth`, `sourced_date` |
| Sourced Date Semantics | Date the row was fetched from Zacks.com via scraper |
| Refresh Cadence | Daily (on-demand via `refresh_signals.py` or UI trigger) |
| Trust Level | **PRIMARY** — direct from authoritative source |
| Primary or Fallback | **PRIMARY** |
| Key inverted convention | `zacks_rank` (1=best) inverted to `zacks_score` (1=Strong Buy: 5.0, 5=Sell: 1.0) |
| Fetch function | `src/scoring/fetch_zacks_scores.py` |
| Persisted by | `scripts/run_outcome_ui.py::_persist_fetched_scores()`, `scripts/refresh_signals.py` |

**Current state (2026-06-10):** 2,647 rows total. 122 rows with today's date (refresh in progress). 583 rows from 2026-06-09. 1,601 rows from 2026-05-26 (oldest bulk fetch). Not all symbols have a recent direct fetch — only ~120 today vs 2,647 total.

---

## Source 2: Fidelity ESS Embedded Zacks Rating

| Attribute | Value |
|---|---|
| Source Name | Fidelity Equity Summary Scores — Zacks Investment Research column |
| File Path (incoming) | `incoming/ess/starmine/EquitySummaryScores-{date}.csv` |
| Column in Fidelity CSV | `"Zacks Investment Research"` (column header in Fidelity export) |
| Internal mapping | `fidelity_column_mapping.py` maps `"Zacks Investment Research"` → `analyst_rating` |
| Normalized field name | `ess_zacks_rating` (set in `provider_normalizer.py` line 119) |
| Sourced Date Semantics | Date of the Fidelity ESS file (not the date Zacks published the rating) |
| Refresh Cadence | Daily (when new Fidelity ESS file is placed in incoming folder) |
| Trust Level | **FALLBACK** — Fidelity provides a value from Zacks but via indirect channel |
| Primary or Fallback | **FALLBACK only** |
| Scale | 1–5 (1=Sell, 5=Buy) — **inverted** vs direct Zacks (1=Strong Buy) |
| Stored in | `src/history/base_universe_manager.py` — `ess_zacks_rating` column in base_universe |
| Used by | `_score_from_inputs()` in `analytical_universe_manager.py` when `zacks_rating` is empty |

**Important:** The `ess_zacks_rating` scale is inverted relative to direct Zacks. Fidelity ESS shows 1=Sell, 5=Buy. Direct Zacks shows rank 1=Strong Buy, rank 5=Sell (inverted to score 5.0=Strong Buy, 1.0=Sell). The conversion at line 166: `zacks_score = round(6.0 - ess_zacks_raw, 2)`.

---

## Source 3: Non-StarMine Zacks (Placeholder)

| Attribute | Value |
|---|---|
| File Path | `incoming/ess/non_starmine_zacks/non_ess.csv` |
| Current state | File does not exist — empty placeholder directory |
| Purpose | For symbols not covered by Fidelity StarMine (non-StarMine universe) |
| Active | No — not currently in use |

---

## Source 4: `analytical_universe.csv` — Composite Zacks Field

| Attribute | Value |
|---|---|
| File Path | `data/current/analytical_universe.csv` |
| Field | `zacks_rating` (numeric score: 1.0–5.0 where 5.0=Strong Buy) |
| How set | By `analytical_universe_manager.py` recalculation — prefers direct Zacks (source 1); falls back to `ess_zacks_rating` (source 2) if direct is absent |
| No source provenance field | The field stores a numeric score only — there is no companion field indicating whether the value came from direct Zacks or Fidelity ESS fallback |

---

## Source 5: `signal_snapshot.csv` — Daily ESS Signal File

| Attribute | Value |
|---|---|
| File Path | `data/current/signal_snapshot.csv` |
| Zacks field | None — signal_snapshot contains only ESS/StarMine fields |
| Zacks role | ESS snapshot does NOT contain direct Zacks data |

---

## Freshness Badge Driver

The Zacks freshness badge is driven by `_signal_status()` in `scripts/run_outcome_ui.py`:
- Reads `data/signals/zacks/latest_zacks.csv` (Source 1 only)
- Uses `_sourced_date()` which returns the **maximum `sourced_date`** found in the file
- If max date == today: badge = FRESH (or FRESH_PARTIAL if coverage < 95%)
- Fidelity ESS Zacks data (Source 2) **does NOT contribute to this badge logic**

The `zacks_refresh_date` in `signal_source_metadata` (runner.py) also reads from `_ZACKS_LATEST` (Source 1 only).
