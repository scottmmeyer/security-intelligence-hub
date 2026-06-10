# Zacks Lineage Trace

**Date:** 2026-06-10

---

## Complete Data Flow Diagram

```
SOURCE 1: Fidelity ESS CSV (daily)
  incoming/ess/starmine/EquitySummaryScores-{date}.csv
  Column: "Zacks Investment Research"
      ↓
  fidelity_column_mapping.py (maps column → "analyst_rating")
      ↓
  provider_normalizer.py (line 119):
    "ess_zacks_rating": validated_row.get("analyst_rating") or ""
      ↓
  base_universe (ess_zacks_rating column stored but NOT in analytical_universe.csv)
      ↓
  analytical_universe_manager.py FALLBACK ONLY if zacks_rating is empty:
    ess_zacks_raw = float(ess_zacks_rating)
    zacks_score = round(6.0 - ess_zacks_raw, 2)  # inverted scale
      ↓
  analytical_universe.csv ["zacks_rating"] ← label is indistinguishable from direct

SOURCE 2: Direct Zacks Fetch (daily)
  scripts/refresh_signals.py OR UI /api/signal-refresh
      ↓
  src/scoring/fetch_zacks_scores.py
  data/signals/zacks/latest_zacks.csv [symbol, zacks_score, sourced_date]
      ↓
  analytical_universe_manager.py PRIMARY path:
    fetched_zacks_score = zacks_scores_by_symbol.get(symbol)  ← from latest_zacks.csv
    zacks_rating = str(fetched_zacks_score) if available else ""
      ↓
  analytical_universe.csv ["zacks_rating"] ← same field as fallback, no distinction
```

---

## Field Presence at Each Pipeline Stage

| Stage | File/Object | Zacks Field | Source |
|---|---|---|---|
| Fidelity ESS ingestion | `provider_normalizer.py` output | `ess_zacks_rating` | Fidelity embedded |
| Base universe | `data/current/base_equity_universe.csv` | `ess_zacks_rating` | Fidelity embedded |
| Direct Zacks cache | `data/signals/zacks/latest_zacks.csv` | `zacks_score` | Direct Zacks.com |
| Analytical universe | `data/current/analytical_universe.csv` | `zacks_rating` (numeric) | Direct (preferred) or Fidelity fallback — **indistinguishable** |
| Portfolio holding | `PortfolioHolding.zacks_rating` | `zacks_rating` | From analytical_universe |
| Security overlay | `SecurityIntelligenceOverlay.zacks_rating` | `zacks_rating` | From PortfolioHolding |
| recommendations.json | `zacks_rating` in drilldown.holdings | `zacks_rating` | From overlay |
| `fidelity_signals_by_symbol` | runner.py `_build_fidelity_payload()` | None — no direct Zacks field | ESS only |
| `signal_source_metadata` | runner.py `_build_signal_source_metadata()` | `zacks_refresh_date` | Source 1 only (latest_zacks.csv) |
| Freshness badge | `_signal_status()` in run_outcome_ui.py | `badge_state` | Source 1 only (latest_zacks.csv) |
| DIL evidence list | `computeDIL()` in app.js | Shows `zacks` value from overlay | Indistinguishable |
| Deployment Candidate profile | `_daRenderActionCards()` in app.js | Uses overlay's zacks_rating | Indistinguishable |
| Reduction Queue profile | ARCH-05 profile expand | Uses overlay's zacks_rating | Indistinguishable |

---

## Critical Observation: Source Provenance Is Lost at `analytical_universe.csv`

The `analytical_universe.csv` field `zacks_rating` stores a numeric score (e.g., `1.0` = STRONG BUY) with no companion field indicating whether this came from:
- Direct Zacks.com fetch (authoritative, dated)
- Fidelity ESS embedded Zacks (indirect, unknown freshness)

Once a symbol's `zacks_rating` is written to the analytical universe, it is read by the enrichment pipeline, placed on `PortfolioHolding.zacks_rating`, passed to `SecurityIntelligenceOverlay.zacks_rating`, and displayed in all UI surfaces — all without any indication of source.

---

## Which Zacks Source Is Used in Each UI Surface

| UI Surface | Zacks Value Source | Known? |
|---|---|---|
| Security Overlay panel | `zacks_rating` from overlay — may be either source | No provenance |
| Deployment Candidate profile (DQ) | Same | No provenance |
| Reduction Queue profile (ARCH-05) | Same | No provenance |
| DIL evidence list | Same — shows e.g. `Zacks: 1.0 [Zacks, 2026-06-09]` | **Date is from `signal_source_metadata.zacks_refresh_date` which is latest_zacks.csv max date — NOT per-symbol source date** |
| Signal freshness badge (Outcome Viz) | `latest_zacks.csv` sourced_date | Source 1 only — correct |
| `zacks_refresh_date` in portfolio runs | `latest_zacks.csv` sourced_date | Source 1 only — correct |

---

## The DIL Date Labeling Issue

The DIL evidence list currently shows:
```
Zacks: 1.0 [Zacks, 2026-06-09]
```

The date `2026-06-09` comes from `signal_source_metadata.zacks_refresh_date` which is the **max sourced_date in `latest_zacks.csv`**. This is the most recent date any symbol was directly fetched — it is not the sourced date for the specific symbol being displayed.

**Example:** PRIM's `zacks_rating=1.0` has `sourced_date=2026-05-21` in `latest_zacks.csv`. But DIL shows `[Zacks, 2026-06-10]` (the max date across all symbols). This is misleading — the date shown does not correspond to when PRIM's Zacks data was fetched.
