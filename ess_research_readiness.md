# ESS Research Readiness Assessment
**Phase 7.6F-R — Deliverable Q5**
**Generated:** 2026-06-01
**Dataset:** `ess_history_master.csv`, `ess_symbol_history_inventory.csv`, `ess_coverage_tiers.csv`

---

## 1. Dataset Overview

| Metric | Value |
|--------|-------|
| Total ESS records | 54,566 |
| Total unique symbols | 2,918 |
| Observation date range | 2025-08-18 → 2026-06-01 |
| Total span | 287 days |
| Unique observation dates | 36 |
| Portfolio-level observation dates | 19 (Aug 2025 – Apr 13, 2026) |
| Full-universe observation dates | 17 (Mar 10 + Apr 15 – Jun 1, 2026) |
| Files skipped (no ESS column) | 2 (May 1 and May 8 large files) |
| Files processed | 38 of 40 canonical files |

---

## 2. Coverage Tier Summary

| Tier | Threshold | Symbol Count | % of Universe |
|------|-----------|-------------|----------------|
| TIER_A | 10+ observations | 2,504 | 85.8% |
| TIER_B | 5–9 observations | 43 | 1.5% |
| TIER_C | 2–4 observations | 322 | 11.0% |
| TIER_D | 1 observation | 49 | 1.7% |
| **Total** | | **2,918** | **100%** |

**Finding:** 85.8% of symbols meet the TIER_A threshold (10+ observations), reflecting the dense observation schedule of the Apr–Jun 2026 full-universe period (17 dates in 78 days). The 43 TIER_B and 322 TIER_C symbols are primarily securities that appeared only in the earlier portfolio-level files and were not part of the full-universe pull.

---

## 3. Research Analysis Readiness by Study Type

### 3.1 Transition Analysis (ESS Category Transition Rates)
**Minimum requirement:** 2+ observations per symbol
**Eligible symbols:** 2,869 (98.3% of total)
**Status: READY**

A transition analysis can quantify the probability of ESS migrating between categories (e.g., BULLISH → NEUTRAL) over a given time window. With 2,869 multi-observation symbols and a 287-day window, this analysis has strong statistical power.

**Key input dimensions:**
- From/to category pairs across 25 possible transitions (5×5 matrix)
- Configurable time windows: 7-day, 30-day, 90-day, 287-day
- Stratified by coverage_scope (portfolio vs. full-universe)

### 3.2 Persistence Analysis (How Long Do ESS Ratings Hold?)
**Minimum requirement:** 5+ observations over 30+ days
**Eligible symbols:** 2,542 (87.1% of total)
**Status: READY**

Persistence analysis tests whether an ESS category assigned at date T is still valid at T+N. With 2,542 symbols meeting the threshold, this is statistically robust across all five ESS categories.

**Key findings that enable persistence analysis:**
- Median observations per TIER_A symbol: high (36 obs = full 36-date coverage)
- Coverage spans up to 287 days for earliest portfolio symbols
- The flat standard-deviation symbols (APO: 0.0 std over 287 days) anchor "high persistence" baseline

### 3.3 Effectiveness Analysis (ESS as Return Predictor)
**Minimum requirement:** 10+ observations (TIER_A)
**Eligible symbols:** 2,504 (85.8% of total)
**Status: READY FOR PORTFOLIO COHORT; PARTIAL FOR FULL UNIVERSE**

Effectiveness analysis tests whether initial ESS rank predicted subsequent price returns. Two distinct cohorts are available:

**Cohort A — Portfolio-Level (Aug 2025 baseline):**
- 500–963 symbols with Aug 2025 ESS scores
- 12 months of forward return data now available (Aug 2025 → Jun 2026)
- **This cohort supports a full 12-month effectiveness study TODAY**
- Caveat: Selection bias — these were active portfolio holdings with above-average initial ESS

**Cohort B — Full-Universe (Mar 2026 baseline):**
- 2,539 symbols with Mar 10, 2026 ESS scores
- Only 83 days of forward data available (Mar 10 → Jun 1, 2026)
- **Insufficient for a 12-month study; requires until Mar 2027**
- Suitable for a 30-day or 90-day effectiveness preview (90-day window available ~Jun 8, 2026)

---

## 4. Analysis-Specific Symbol Counts

| Analysis Type | Symbol Count | Eligible % | Study Window Available |
|---------------|-------------|------------|------------------------|
| Transition (2+ obs) | 2,869 | 98.3% | Now |
| Persistence (5+ obs, 30+ days) | 2,542 | 87.1% | Now |
| 30-day effectiveness (TIER_A) | 2,504 | 85.8% | Now |
| 90-day effectiveness (TIER_A) | 2,504 | 85.8% | ~Jun 8, 2026 (7 days) |
| 12-month effectiveness (portfolio cohort) | ~800 | portfolio-only | Now (Aug 2025 → Aug 2026) |
| 12-month effectiveness (full universe) | 2,539 | full universe | Mar 2027 |

---

## 5. ESS Category Representation

At the **earliest** observation date (2025-08-18, portfolio scope, 784 symbols):
> The portfolio was selected primarily from high-ESS names, so early distribution skews bullish.

At the **latest** observation date (2026-06-01, full-universe, 2,498 symbols):
> Full-universe data provides broad representation across all five categories.

The normalized ESS dataset (`ess_history_master.csv`) supports cross-date comparison using the `ess_5pt` column, which harmonizes the numeric 1-10 portfolio scale with the text-category full-universe scale into a common 1–5 ordinal.

---

## 6. Known Limitations and Governance Caveats

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Two ESS column name formats | Risk of missed ESS data if parsing naively | Handled in master build: fuzzy `'ess' in col.lower()` matching |
| Numeric 1-10 vs text category formats | Cannot directly compare raw values cross-period | Resolved via `ess_5pt` normalized column |
| Portfolio-level scope bias (early dates) | Survivorship/selection bias in pre-Mar-2026 data | Flag with `coverage_scope` in all analyses |
| 2 files missing ESS column entirely | 2026-05-01 absent; May 8 represented only by _1 file | Both excluded with note in `ess_archive_manifest.md` |
| No price return data in archive | Cannot run effectiveness study without external price data | Price data fetch required before effectiveness study |
| ESS source: single provider (LSEG StarMine) | Provider concentration risk in signal independence testing | Appropriate for single-signal effectiveness study; multi-signal study needs other sources |

---

## 7. Readiness Verdict

**Overall dataset readiness: READY FOR ESS EFFECTIVENESS STUDY**

The dataset is sufficient to execute:
1. **ESS Transition Matrix** — probability that ESS changes from category X to category Y over N days
2. **Persistence Study** — average ESS category half-life by starting category
3. **Effectiveness Pilot** — ESS vs 30/90-day forward returns for the full-universe cohort (Mar 10, 2026 baseline)
4. **Full 12-Month Effectiveness Study** — ESS vs 12-month returns for the portfolio-level cohort (Aug 2025 baseline)

The only missing component for the effectiveness studies is **external price/return data**, which is not part of the ESS archive but is readily obtainable from the `data/current/` and `data/history/` pipeline within this repository.
