# PA-006 Design — Allocation Drift Trend Visibility

**Date:** 2026-06-15  
**Status:** Design Phase

---

## Objective

Provide historical visibility into portfolio allocation drift across CPV dimensions. Enable operators to determine when drift began, whether it is improving or worsening, and which symbols contributed most. No changes to recommendation logic, CPV rules, scoring, or governance.

---

## Data Architecture Assessment

### Existing Data Sources

| Source | Location | Contains | Historical Depth |
|--------|----------|---------|-----------------|
| PAR `concentration.json` | `data/portfolio_ingestion/analysis_runs/*/concentration.json` | top1%, top3%, top5%, top10%, mega%, us%, intl%, HHI, tier | **250 runs across 20 dates (May 21 – Jun 15)** |
| PAR `compliance.json` | `data/portfolio_ingestion/analysis_runs/*/compliance.json` | CPV-01 through CPV-08 actual%, status per rule | **4 runs: May 21, May 29, Jun 15 × 2** |
| PAR `holdings.csv` | `data/portfolio_ingestion/analysis_runs/*/holdings.csv` | Per-symbol market value, %, asset class, geography, market cap, ESS, Zacks, Danelfin | **250 runs** |
| PAR `run_metadata.json` | `data/portfolio_ingestion/analysis_runs/*/run_metadata.json` | snapshot_date, portfolio_snapshot_id | **250 runs** |
| PIS `position_snapshots.csv` | `data/history/pis/snapshot_date=*/account_id=PORTFOLIO/snapshot_id=*/position_snapshots.csv` | Per-symbol market_value, percent_of_account | **19 snapshot dates** |
| PIS `canonical_daily_snapshots.csv` | `data/history/pis/canonical/canonical_daily_snapshots.csv` | portfolio_value, cash, position_count per governance-approved date | **19 canonical dates** |
| `allocation_policy.yaml` | `config/allocation_policy.yaml` | Policy targets, CPV tolerances | Current (static) |

### Key Finding: Drift is Fully Reconstructible

All 8 CPV dimensions are computable from PAR `holdings.csv`:
- CPV-01 (Micro Cap): sum of rows where `market_cap_bucket == 'MICRO'` / total
- CPV-02 (Mega Cap): sum of rows where `mega_subtier == 'MEGA'` / total
- CPV-03 (Digital): sum of rows where `asset_class == 'DIGITAL'` / total
- CPV-04 (Cash): sum of rows where `asset_class == 'CASH'` / total
- CPV-05 (International): sum of rows where `geography != 'US'` / total
- CPV-06 (Single Asset Class ≤80%): max asset class %
- CPV-07 (Equities ≥40%): equities %
- CPV-08 (Fixed Income ≤40%): fixed income %

**The 250 PAR runs provide a 20-date historical timeline. Only 4 have pre-computed compliance.json files. The other 246 require on-demand computation from holdings.csv, which is straightforward.**

---

## Drift Dimension Definitions

### Tier 1: CPV Rule Dimensions (directly policy-bound)

| Dimension | CPV Rule | Policy Limit | Direction | Data Field |
|-----------|----------|-------------|-----------|-----------|
| Micro Cap % | CPV-01 | ≤5% | ceiling | `market_cap_bucket == 'MICRO'` |
| Mega Cap % | CPV-02 | ≤50% | ceiling | `mega_subtier == 'MEGA'` |
| Digital % | CPV-03 | ≤8% | ceiling | `asset_class == 'DIGITAL'` |
| Cash % | CPV-04 | ≥2% | floor | `asset_class == 'CASH'` |
| International % | CPV-05 | ≥10% | floor | `geography != 'US'` |
| Single Asset Class % | CPV-06 | ≤80% | ceiling | max(asset class %) |
| Equities % | CPV-07 | ≥40% | floor | `asset_class == 'EQUITIES'` |
| Fixed Income % | CPV-08 | ≤40% | ceiling | `asset_class == 'FIXED_INCOME'` |

### Tier 2: Concentration Dimensions (pre-computed in concentration.json)

| Dimension | Policy Bound | Data Field |
|-----------|-------------|-----------|
| Top 1 holding % | — | `top1_pct` |
| Top 5 holdings % | — | `top5_pct` |
| Top 10 holdings % | — | `top10_pct` |
| US % | — | `us_pct` |
| International % | — | `international_pct` |
| HHI index | — | `herfindahl_index` |

### Tier 3: Symbol-Level Contribution (computed from holdings.csv)

Drift contribution per symbol = change in symbol's `percent_of_portfolio` between two snapshot dates.

---

## Design Answers

### Q1: Can drift be reconstructed from existing data?
**Yes, completely.** All allocation dimensions are computable from PAR `holdings.csv` + `concentration.json`. The 250 existing PAR runs provide a 20-date history. No new data collection is required.

### Q2: What dimensions should be tracked?
All 8 CPV rule dimensions (policy-bound) + top1/5/10 concentration + US/intl split.

### Q3: Which dimensions provide highest operator value?
Priority order:
1. **CPV-01 (Micro Cap)** — currently FAIL/WARN, highest urgency
2. **CPV-06 (Equities)** — currently WARN at 86.7% (limit 80%)
3. **Top 5% / Top 10%** — directly visible concentration risk
4. **Cash %** — cash deployment monitoring
5. **International %** — geographic drift

### Q4: Should drift be snapshot-based or recomputed?
**Computed on demand from existing PAR artifacts.** Storing a separate drift time-series would duplicate data that already exists. The API endpoint computes from `holdings.csv` + `concentration.json` across all PAR runs, applying one canonical selection per date (latest passing PAR).

### Q5: What is the simplest useful dashboard implementation?
A new "Drift Trends" panel in the existing PIS dashboard:
1. A sparkline or mini-table showing CPV rule values across the last N dates
2. Trend direction indicator (↑ worsening / ↓ improving / → stable)
3. Top 5 symbol drift contributors between last two canonical dates
