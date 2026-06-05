# Phase 8.0B.1B — Universe Schema Review

## Analytical Universe Current Schema

**File:** `data/current/analytical_universe.csv`  
**Rows:** 2,473  
**Columns (32):** security_id, symbol, security_type, snapshot_date, run_id, market_cap_bucket, geography, country, industry, sector, composite_score, ess_score_text, zacks_rating, yahoo_score, danelfin_score, benchmark_id, investable_vehicle_id, price_at_snapshot, provider_lineage, analytical_market_cap_subtier, classification_policy_id, classification_snapshot_date, replay_eligible, scoring_eligible, allocation_eligible, benchmark_confidence, sector_benchmark_id, classification_method, yahoo_abr_normalized, composite_v2_yahoo, composite_version, score_generation_timestamp

## Security Type Distribution

| Security Type | Count |
|---------------|-------|
| Common Stock | 2,315 |
| Common Stock (REIT) | 113 |
| Depository Receipt | 37 |
| Unit Trust Fund | 8 |

Note: ETFs held in portfolios (e.g., VXUS, VOO, BND) are NOT in the analytical universe — they appear in portfolio holdings but are excluded from the scoring universe. The 8 "Unit Trust Fund" entries are pipeline-limited partnerships (EPD, ET, MPLX, etc.).

## FMP Enrichment Schema (Phase 8.0B.1B)

**New module:** `src/scoring/fmp_universe_enrichment.py`  
**New output:** `data/signals/fmp/latest/latest_fmp_enriched_universe.csv`

The enriched universe is a **standalone join artifact** — it does not modify `analytical_universe.csv`. The enrichment lives in a separate FMP signals path and is loaded independently by consumers.

### Enriched Schema (28 fields)

| Field | Source Dataset | Type | Notes |
|-------|---------------|------|-------|
| symbol | — | str | Symbol key |
| fmp_coverage_status | derived | str | FULL / PARTIAL / ETF_NOT_APPLICABLE / NO_DATA |
| fmp_sourced_date | any dataset | str | Date FMP data was fetched |
| pe_ratio_ttm | key_metrics_ttm | float | **Currently null** — FMP Starter plan does not return this field |
| ev_ebitda_ttm | key_metrics_ttm | float | EV/EBITDA trailing 12 months |
| price_to_fcf_ttm | key_metrics_ttm | float | Price to free cash flow |
| fcf_yield_ttm | key_metrics_ttm | float | FCF yield |
| roe_ttm | key_metrics_ttm | float | Return on equity |
| roic_ttm | key_metrics_ttm | float | Return on invested capital |
| earnings_yield_ttm | key_metrics_ttm | float | Earnings yield |
| strong_buy_count | grades_consensus | int | Analyst strong buy count |
| buy_count | grades_consensus | int | Analyst buy count |
| hold_count | grades_consensus | int | Analyst hold count |
| sell_count | grades_consensus | int | Analyst sell count |
| strong_sell_count | grades_consensus | int | Analyst strong sell count |
| total_analysts | grades_consensus | int | Total analyst coverage count |
| net_buy_score | grades_consensus | float | (buy+strong_buy) − (sell+strong_sell) |
| consensus_label | grades_consensus | str | BUY / HOLD / SELL |
| latest_eps_surprise_pct | earnings_surprises | float | Most recent EPS surprise % |
| beats_last_8q | earnings_surprises | int | Count of beats in last 8 quarters |
| beat_rate_8q | earnings_surprises | float | Beat rate 0.0–1.0 |
| q1–q4_surprise_pct | earnings_surprises | float | Per-quarter EPS surprise |
| revenue_growth_q1_yoy | income_growth | float | YoY revenue growth most recent Q |
| eps_growth_q1_yoy | income_growth | float | YoY EPS growth most recent Q |
| revenue_acceleration | income_growth | float | Q1 growth minus Q4 growth (trend) |

## Governance Constraint

The enriched universe output is **read-only at this phase**. No pipeline stage reads from it yet.
Phase 8.0B.1B.5 (FMP Diagnostic Overlay) will be the first authorized consumption point.
