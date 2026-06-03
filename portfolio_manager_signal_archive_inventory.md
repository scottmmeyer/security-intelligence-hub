# Portfolio Manager Signal Archive Inventory
**Phase 7.6D.2 — Replay Historical Signal Integrity Audit**
**Date:** 2026-06-01

---

## Q4: Portfolio Manager Repository Signal Archive Assessment

**Repository:** `/Users/scottmmeyer/Projects/portfolio_manager`

---

## Archive Overview

The Portfolio Manager (PM) repository contains a structured archive of input files collected during active portfolio management operations. These represent authentic contemporaneous data captures, not retroactive reconstructions.

### Archive Directory Structure

```
portfolio_manager/
  data/
    archive/          (35 timestamped subfolders, 2025-08-24 → 2026-03-10)
    archive/processed_inputs/  (additional ESS + position files)
    snapshots/        (portfolio_snapshots.csv)
    starmine/         (one StarMine file: 2026-03-10_scores.csv)
    raw/
      analyst_estimates/  (3 files: 2026-05-04 → 2026-05-26)
      analyst_scores/     (Yahoo consensus, 2026-04-20 → 2026-06-01)
    signals/          (not present; signals handled via archive)
```

---

## ESS (Equity Summary Score) Archives

### Available Files

| Date | File | Rows (approx) | Notes |
|---|---|---|---|
| 2025-08-18 | EquitySummaryScores-18Aug2025.csv | ~784 | Earliest authentic ESS capture |
| 2025-08-24 | EquitySummaryScores-24Aug2025.csv | ~784 | |
| 2025-08-25 | EquitySummaryScores-25Aug2025.csv | ~784 | |
| 2025-10-19 | EquitySummaryScores-19Oct2025.csv | ~784 | |
| 2025-10-29 | EquitySummaryScores-29Oct2025.csv | ~784 | Also in xlsx format |
| 2025-11-18 | EquitySummaryScores-18NOV2025.csv | ~784 | |
| 2025-12-11 | EquitySummaryScores_backup_20251211_171503.csv | ~784 | Backup file |
| 2026-01-08 | EquitySummaryScores-08JAN2026.csv | ~784 | |
| 2026-02-13 | EquitySummaryScores-13FEB2026.csv | ~784 | |
| 2026-02-15 | EquitySummaryScores-15FEB2026.csv | ~784 | |
| 2026-02-18 | EquitySummaryScores-18Feb2026.csv | ~784 | |
| 2026-02-25 | EquitySummaryScores-25Feb2026.csv | ~784 | |
| 2026-03-02 | EquitySummaryScores-02Mar2026.csv | ~784 | |
| 2026-03-07 | EquitySummaryScores-07Mar2026.csv | ~784 | |
| 2026-03-09 | EquitySummaryScores-09Mar2026.csv | ~784 | |
| 2026-03-10 | EquitySummaryScores-10Mar2026.csv | ~784 | |
| 2026-03-10 | EquitySummaryScores-10Mar2026All.csv | ~784 | "All" variant |
| 2026-04-03 through 2026-06-01 | Multiple files in processed_inputs/ | ~784 each | Continuous near-daily coverage Apr–Jun 2026 |

**Earliest ESS archive date:** `2025-08-18` (EquitySummaryScores-18Aug2025.csv)

**ESS archive schema:**
```
Symbol, Company Name, Security Type, Security Price, ESS from LSEG StarMine,
Fwd EPS LTG (3-5 Yrs), Zacks Investment Research, Jefferson Research, McLean Capital Management
```

**Scale difference:** PM ESS uses a 1–10 numeric scale (LSEG StarMine raw). SIH ESS uses a 1–5 text scale (VERY_BULLISH/BULLISH/NEUTRAL/BEARISH/VERY_BEARISH). A conversion mapping exists (`8.0–10.0 → VERY_BULLISH`, etc.) but would need validation.

---

## StarMine Archives

**File:** `data/starmine/2026-03-10_scores.csv`

Contains: Symbol, Company Name, analyst_score, Forward EPS LTG, Market Cap, Jefferson Research, **Zacks Investment Research**, McLean Capital Management

This is a single-date capture (2026-03-10) that includes multi-provider data. No additional StarMine files beyond this single date exist in PM.

---

## Yahoo Analyst Consensus Archives

**Location:** `data/raw/analyst_scores/`

| Date | File |
|---|---|
| 2026-04-20 | 2026-04-20_yahoo_fetch_diagnostics.json |
| 2026-04-24 | 2026-04-24_yahoo_fetch_diagnostics.json |
| 2026-04-28 | 2026-04-28_yahoo_fetch_diagnostics.json |
| 2026-04-30 | 2026-04-30_yahoo_fetch_diagnostics.json |
| 2026-05-04 | 2026-05-04_yahoo_consensus.csv |
| 2026-05-09 | 2026-05-09_yahoo_consensus.csv |
| 2026-05-12 | 2026-05-12_yahoo_consensus.csv |
| 2026-05-14 | 2026-05-14_yahoo_consensus.csv |
| 2026-05-15 | 2026-05-15_yahoo_consensus.csv |
| 2026-05-20 | 2026-05-20_yahoo_consensus.csv |
| 2026-05-26 | 2026-05-26_yahoo_consensus.csv |
| 2026-06-01 | 2026-06-01_yahoo_consensus.csv |

**Earliest Yahoo:** 2026-04-20 (diagnostics only). First CSV: 2026-05-04. No 2025 Yahoo data.

---

## Portfolio Snapshots

**File:** `data/snapshots/portfolio_snapshots.csv`

Schema: `run_date, symbol, category, asset_type, quantity, market_value, current_weight, portfolio_value`

This file contains position-level data but not signal scores. Not directly usable for replay signal reconstruction.

---

## Analyst Estimates

**Location:** `data/raw/analyst_estimates/`

| Date | File |
|---|---|
| 2026-05-04 | 2026-05-04_estimates.csv |
| 2026-05-12 | 2026-05-12_estimates.csv |
| 2026-05-26 | 2026-05-26_estimates.csv |

No pre-May 2026 analyst estimates archived.

---

## Recoverability Assessment

### Can PM Archives Upgrade Replay Signal Fidelity?

| Upgrade Scenario | Assessment |
|---|---|
| Replace 2026 ESS with Aug 2025 ESS for 2025-05-14 replay | **PARTIAL** — PM ESS starts 2025-08-18, not 2025-05-14. Gap of 96 days remains. Coverage is portfolio-level only (~784 rows, not 2,502-row full universe) |
| Replace 2026 ESS with 2026-03-10 ESS for 2025-05-14 replay | **WORSE** — 2026-03-10 is 300 days after start date; more look-ahead than current 2026-05-15 |
| Backfill Zacks from PM StarMine (2026-03-10) | **NOT USEFUL** — Single date, still forward-looking, portfolio-level only |
| Use PM archive for a new mid-2025 replay start date | **LIMITED** — Earliest PM ESS is 2025-08-18. Could support an Aug 2025 replay start date but still covers portfolio holdings only, not the full analytical universe |

### Key Constraint

All PM ESS archives are sourced from the **Fidelity brokerage account's portfolio view** — they show ESS scores only for securities held or recently analyzed in the portfolio (typically 600–900 rows). The SIH full analytical universe contains 2,502–2,802 symbols. PM archives cannot substitute as a full-universe signal source.

---

## Replay Upgrade Opportunity via PM

**Verdict: LIMITED OPPORTUNITY**

The PM archive provides authentic ESS data back to 2025-08-18 for portfolio holdings. This enables:

1. **Partial signal validation:** For the ~50–80 symbols in the current portfolio that also appeared in PM archives from Aug 2025 onward, the PM ESS captures provide a ground-truth comparison point. If the 2025-05-14 replay's ESS ranking for a portfolio holding was significantly different from what PM recorded in Aug 2025, this indicates look-ahead bias affected that specific selection.

2. **No full-universe backfill possible:** The PM archive cannot replace the SIH full analytical universe for the 2025-05-14 replay. There is no source of authentic May 2025 ESS data for the ~2,500 symbol full-universe scope required by the replay construction.

3. **Gap not closable without vendor export:** Retrieving authentic May 2025 ESS data would require a Fidelity/LSEG StarMine historical extract for that specific date. No such export was captured at the time.
