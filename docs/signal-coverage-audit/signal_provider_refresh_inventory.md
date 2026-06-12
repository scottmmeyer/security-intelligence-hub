# Signal Provider Refresh Inventory
**Audit Date**: 2026-06-12  
**Scope**: SIGNAL-COVERAGE-01 — Mandatory Holdings Coverage Audit  
**Trigger**: ZACKS-REFRESH-UNIVERSE-01 defect discovery

---

## Overview

This document inventories every signal provider used by SIH and documents the
exact logic that determines which symbols receive a refresh in each run.

---

## 1. Zacks

**File**: `src/scoring/fetch_zacks_scores.py` — `build_smart_refresh_list()`  
**Invocation**: `scripts/refresh_signals.py` → `_refresh_zacks()`  
**Status**: ✅ FIXED (ZACKS-REFRESH-UNIVERSE-01)

### Refresh Universe Construction

Three-priority ordered list:

| Priority | Set | Logic |
|----------|-----|-------|
| 0 — Forced | Portfolio equity holdings | `_load_portfolio_equity_holdings()` from latest PAR `holdings.csv` (EQUITIES only) |
| 1 — Bullish | BULLISH/VERY_BULLISH symbols in `base_equity_universe.csv` | `starmine_ess_text in {"BULLISH", "VERY_BULLISH"}` |
| 2 — Uncached | Non-bullish universe symbols not in `latest_zacks.csv` | `sym not in cached_symbols` |

All other symbols (non-bullish + cached + not a holding) are excluded.

### Staleness Cadence

- Checked daily via `_is_stale(latest_zacks.csv)` — triggers if `sourced_date ≠ today`
- Triggered automatically when stale

### Score Contribution

- Primary input to CW-DAS composite score (weight varies by ESS tier)
- Zacks rating also used as fallback via `ess_zacks_rating` pass-through

---

## 2. Danelfin

**File**: `src/scoring/fetch_danelfin_scores.py` — `fetch_danelfin_scores_for_symbols()`  
**Invocation**: `scripts/refresh_signals.py` → `_refresh_danelfin(smart=...)`  
**Status**: ⚠️ CONDITIONAL DEFECT — depends on invocation path

### Refresh Universe Construction

| Mode | Symbol Set | Logic |
|------|-----------|-------|
| Default (`smart=False`) | Full universe | `_all_universe_symbols()` — all 2,523 symbols in `base_equity_universe.csv` |
| Smart (`smart=True`) | Bullish + near-bullish | `_smart_universe_symbols()` — BULLISH/VERY_BULLISH + NEUTRAL with raw ESS ≥ 6.5 |

### Invocation Paths

| Caller | Mode | Holdings Covered? |
|--------|------|-------------------|
| `ensure_signals_fresh()` (default) | `smart=False` | ✅ Full universe |
| `scripts/diagnostics/build_wp04_foundation.py` | `smart=False` | ✅ Full universe |
| `scripts/diagnostics/build_wp05b_replay_matrix.py` | `smart=False` | ✅ Full universe |
| **UI `/api/signal-refresh` button** | **`smart=True` (always)** | ❌ Excludes bearish/no-ESS holdings |

**Root cause**: `run_outcome_ui.py` line 724 — `subprocess.Popen([..., "refresh_signals.py", "--smart"])` — hardcodes `--smart` with no override mechanism.

### Staleness Cadence

- Checked daily via `_is_stale(latest_danelfin.csv)`
- No forced portfolio holdings parameter exists (unlike Zacks after fix)

### Score Contribution

- CW-DAS composite score component (danelfin_score field)
- Feeds `analytical_universe.csv` via `patch_universe_danelfin()`

---

## 3. Yahoo Supplemental (ABR, Price Target, Analyst Consensus)

**File**: `src/scoring/fetch_yahoo_supplemental.py` — `fetch_yahoo_supplemental_for_symbols()`  
**Invocation**: `scripts/refresh_signals.py` → `_refresh_yahoo(smart=...)`  
**Status**: ⚠️ CONDITIONAL DEFECT — same path as Danelfin

### Refresh Universe Construction

| Mode | Symbol Set | Logic |
|------|-----------|-------|
| Default (`smart=False`) | Full universe | `_all_universe_symbols()` — 2,523 symbols |
| Smart (`smart=True`) | Bullish + near-bullish | `_smart_universe_symbols()` — same as Danelfin smart path |

Identical invocation paths to Danelfin. UI button always uses `--smart`.

### Provides

- `abr` — Analyst Broker Recommendation (1.0=Strong Buy → 5.0=Sell)
- `price_target` — consensus mean analyst price target
- `analyst_count` — number of covering analysts
- `current_price` — Yahoo current quote
- `upside_pct` — `(price_target - current_price) / current_price × 100`
- `eps_growth_5yr` — long-term EPS growth estimate

### Score Contribution

- `abr` / `analyst_count` → `AnalystConsensus` model → DIL consensus panel (informational)
- `price_target` / `upside_pct` → DIL display (informational)
- `composite_v2_yahoo` score column (secondary; not primary CW-DAS driver)
- **Not a primary CW-DAS composite score driver** — lower impact than Danelfin/Zacks/ESS

---

## 4. FMP (Financial Modeling Prep)

**File**: `src/scoring/fetch_fmp_signals.py`  
**Invocation**: `scripts/refresh_signals.py` → `_refresh_fmp()` | `scripts/fmp_bulk_fetch_universe.py`  
**Status**: ✅ NO HOLDINGS GAP

### Refresh Universe Construction

`_refresh_fmp()` always calls `_all_universe_symbols()` — the full 2,523-symbol universe. There is no smart mode. No cached-exclusion logic in the daily or quarterly refresh path.

`fmp_bulk_fetch_universe.py` uses smart-resume (skips already-cached symbols per run), but this is a one-time enrichment pattern, not daily staleness. FMP daily datasets are re-fetched for the full universe on every stale day.

### Datasets

| Dataset | Cadence | Stale if |
|---------|---------|----------|
| `key_metrics_ttm` | Daily | `sourced_date ≠ today` |
| `grades_consensus` | Daily | `sourced_date ≠ today` |
| `earnings_surprises` | Quarterly | > 90 days old |
| `income_growth` | Quarterly | > 90 days old |

### Score Contribution

- FMP signals are informational (DIL display, PAP research context)
- `grades_consensus` → `consensus_label`, `net_buy_score` → DIL supplemental
- Earnings surprises / income growth → research context
- Not primary CW-DAS composite driver

---

## 5. Analyst Consensus

**Source**: Derived from Yahoo supplemental `abr` field  
**Loader**: `src/portfolio/analyst_consensus.py` — `load_analyst_consensus(yahoo_csv_path)`  
**Status**: ⚠️ DEPENDENT ON YAHOO — same conditional defect

Analyst consensus is not independently fetched. It reads `latest_yahoo_supplemental.csv`. 
Coverage and staleness are 100% dependent on the Yahoo provider.

### Contribution

- `AnalystConsensus` model → consensus panel in PAP/DIL
- `compute_conflict_badge()` → ESS vs. ABR conflict alert (informational)
- Not a scoring input

---

## 6. Price Targets

**Source**: Derived from Yahoo supplemental `price_target` and `upside_pct` fields  
**Status**: ⚠️ DEPENDENT ON YAHOO — same conditional defect

Not independently fetched. Same staleness exposure as Yahoo in smart mode.

---

## 7. Earnings Calendar / Next Earnings Date

**Source**: FMP `earnings_surprises` quarterly dataset + `runner.py` price context  
**Status**: ✅ NO HOLDINGS GAP (FMP always full universe)

Next earnings date is computed in `runner.py` from FMP earnings data per symbol. 
FMP quarterly dataset covers the full universe with no smart exclusion.

---

## 8. ESS (EquitySummaryScores — StarMine / Fidelity)

**File**: `src/pipeline/stages/ess_intake_stage.py` — `execute_ess_intake_stage()`  
**Invocation**: `scripts/_run_intake.py` (manual daily)  
**Status**: ⚠️ PASSIVE INGESTION — coverage externally determined

### Refresh Universe Construction

ESS is not actively fetched. The pipeline reads CSV files published by Fidelity/StarMine
placed in `incoming/ess/starmine/`. The universe of covered symbols is determined by
what Fidelity includes in each daily file — SIH has no control over symbol inclusion.

If a holding is not in the Fidelity ESS file:
- ESS fields default to blank / null
- Composite score uses ESS fallback path (`ess_zacks_rating` proxy)
- No alert fires for missing holding coverage

### Governance Risk

If Fidelity drops a holding from ESS coverage (rare but possible), SIH will silently
use stale/null ESS data. There is no mechanism to detect that a previously-covered
holding is now absent from the latest file.

---

## 9. Security Metadata (Yahoo — Sector/Industry/Country)

**File**: `src/scoring/fetch_security_metadata.py`  
**Status**: ✅ INFORMATIONAL ONLY — not a scoring input, not in daily refresh

Smart-refresh is optional (skips cached symbols); full-universe mode available.
Not invoked by `ensure_signals_fresh()`. Classification metadata; not a CW-DAS input.

---

## 10. `refresh_portfolio_signals.py` — Hardcoded Symbol List

**File**: `scripts/refresh_portfolio_signals.py`  
**Status**: ⚠️ GOVERNANCE DEFECT — hardcoded list diverges from actual holdings

`_PORTFOLIO_SYMBOLS` is a static Python list (~80 symbols) committed in code. 
It is not dynamically loaded from the latest PAR `holdings.csv`. As portfolio 
positions change, this list will silently diverge.

This script is used on-demand (not automated), but the hardcoded list is a
maintenance trap. It should be replaced with `_load_portfolio_equity_holdings()`.

---

## Summary Table

| Provider | Refresh Mode | Default Path | UI Smart Path | Gap Risk |
|----------|-------------|-------------|---------------|----------|
| Zacks | Smart + forced holdings | ✅ Holdings forced | ✅ Holdings forced | ✅ NONE (FIXED) |
| Danelfin | Smart or full | ✅ Full universe | ❌ Bullish only | ⚠️ BEARISH HOLDINGS |
| Yahoo | Smart or full | ✅ Full universe | ❌ Bullish only | ⚠️ BEARISH HOLDINGS |
| FMP | Full universe always | ✅ Full universe | ✅ Full universe | ✅ NONE |
| Analyst Consensus | Via Yahoo | ⚠️ Yahoo-dependent | ⚠️ Yahoo-dependent | ⚠️ BEARISH HOLDINGS |
| Price Targets | Via Yahoo | ⚠️ Yahoo-dependent | ⚠️ Yahoo-dependent | ⚠️ BEARISH HOLDINGS |
| Earnings Calendar | Via FMP | ✅ Full universe | ✅ Full universe | ✅ NONE |
| ESS | Passive ingestion | ⚠️ Externally determined | ⚠️ Externally determined | ⚠️ PASSIVE RISK |
| Security Metadata | On-demand | ✅ Full universe | N/A | ✅ NONE (informational) |
