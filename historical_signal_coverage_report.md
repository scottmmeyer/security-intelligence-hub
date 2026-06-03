# Historical Signal Coverage Report
**Phase 7.6D.2 — Replay Historical Signal Integrity Audit**
**Run Reference:** PAR-20260601-9CFD7C63
**Date:** 2026-06-01

---

## Q3: Earliest Date of Authentic Signal Coverage

### Definition

An **authentic** signal is one that was captured contemporaneously — stored in its original file form at the time it was produced, not reconstructed, backfilled, or sourced from a later-dated export.

**Inferred** signals (ESS scores approximated from related data), **reconstructed** signals (current-date file used to populate a historical date field), and **missing** signals (no data available for that date) do not qualify.

---

## Signal Coverage by Source and Earliest Authentic Date

### Fidelity ESS (StarMine Equity Summary Score)

| Repository | Earliest Authentic ESS File | Date |
|---|---|---|
| security-intelligence-hub | `data/history/signals/snapshot_date=2026-05-13/` | **2026-05-13** |
| portfolio_manager archive | `data/archive/20250824-093221/EquitySummaryScores-18Aug2025.csv` | **2025-08-18** |

**SIH ESS coverage begins:** 2026-05-13

The signal history directory (`data/history/signals/`) contains ESS captures starting on 2026-05-13. No ESS archives for any date before 2026-05-13 exist in SIH.

The Portfolio Manager's `data/archive/` directory contains `EquitySummaryScores-18Aug2025.csv` as its earliest authentic capture. However, PM ESS archives cover portfolio holdings only (~784 rows vs ~2,502 rows in SIH's full analytical universe). The PM ESS data is not a full-universe substitute.

**No authentic ESS data exists for May 2025 in any accessible repository.** The gap between the earliest replay start date (2025-05-14) and the earliest authentic ESS archive (2025-08-18, portfolio-level only) is approximately **96 days**. To the full analytical universe, the gap is approximately **12 months** (earliest SIH ESS: 2026-05-13).

---

### Zacks Investment Research

| Repository | Earliest Authentic Zacks File | Date |
|---|---|---|
| security-intelligence-hub | `data/signals/zacks/2026-05-14_zacks.csv` | **2026-05-14** |
| portfolio_manager | `data/starmine/2026-03-10_scores.csv` (includes Zacks column) | **2026-03-10** |

**SIH Zacks coverage begins:** 2026-05-14

The `data/signals/zacks/` directory contains files from 2026-05-14 onward. The PM StarMine file dated 2026-03-10 includes a Zacks column but covers portfolio holdings only.

**No Zacks data for any 2025 date exists in any accessible repository.** The analytical_universe for `snapshot_date=2025-05-14` shows 1 Zacks-populated row (likely a watchlist entry), not a meaningful coverage level.

---

### Danelfin

| Repository | Earliest Authentic Danelfin File | Date |
|---|---|---|
| security-intelligence-hub | `data/signals/danelfin/2026-05-14_danelfin.csv` | **2026-05-14** |
| portfolio_manager | Not found | N/A |

**SIH Danelfin coverage begins:** 2026-05-14

Danelfin AI scores appear in SIH signal snapshots starting 2026-05-14. Coverage in the analytical_universe only begins substantially at `snapshot_date=2026-05-20` (800 rows) and remains partial through current date. No Danelfin data for 2025 exists.

---

### Yahoo Analyst Consensus (ABR)

| Repository | Earliest Authentic Yahoo File | Date |
|---|---|---|
| security-intelligence-hub | `data/signals/yahoo/2026-05-14_yahoo_supplemental.csv` | **2026-05-14** |
| portfolio_manager | `data/raw/analyst_scores/2026-04-20_yahoo_fetch_diagnostics.json` | **2026-04-20** |

**SIH Yahoo coverage begins:** 2026-05-14 (supplemental signal files only)

**Important caveat:** Yahoo signal data is NOT loaded into the analytical_universe. The v1 composite_score formula marks Yahoo as "unused" (`Yahoo=0.10 (unused)`). Even though Yahoo files exist in `data/signals/yahoo/`, they have zero rows in the analytical_universe `yahoo_score` column across all snapshot dates. Yahoo is effectively absent from all replay composite scores.

---

### Fidelity ESS (Whole-Universe Coverage Summary)

| Snapshot Date | ESS File Used | File Generation Date | Authentic? | Rows |
|---|---|---|---|---|
| 2025-05-14 | EquitySummarScores_May-15-2026.csv | 2026-05-15 | **NO** | 2,560 |
| 2025-05-13 | SecurityExtract_ESS_2026May13.csv | 2026-05-13 | **NO** | 2,502 |
| 2026-05-13 | SecurityExtract_ESS_2026May13.csv | 2026-05-13 | YES | 2,502 |
| 2026-05-14 | ESS_2026May14.csv | 2026-05-14 | YES | 2,559 |
| 2026-05-15 | EquitySummarScores_May-15-2026.csv | 2026-05-15 | YES | 2,560 |
| 2026-05-20 | ESS1.csv | 2026-05-20 | YES | 2,802 |
| 2026-05-22 | EquitySummaryScores-May2026.csv | 2026-05-22 | YES | 2,586 |
| 2026-05-31 | EquitySummaryScores-May2026.csv | 2026-05-31 | YES | 2,586 |

---

## Earliest True Signal Date (All Sources Authentic Simultaneously)

| Signal | Earliest Authentic Full-Universe Date |
|---|---|
| ESS (Fidelity StarMine) | 2026-05-13 |
| Zacks | 2026-05-14 (sparse) → 2026-05-31 (full coverage) |
| Danelfin | 2026-05-14 (sparse) → 2026-05-20 (substantial) |
| Yahoo | Never loaded into analytical_universe |
| Fidelity (provider) | 2026-05-13 |

**Earliest date with authentic ESS + Zacks (sparse) + Danelfin (sparse):** `2026-05-14`

**Earliest date with authentic ESS + Zacks (full) + Danelfin (partial):** `2026-05-31`

**Yahoo** is a perpetual gap — it is not integrated into the composite_score formula for any snapshot date.

---

## Implication for Replay Validation

The 365-day HISTORICAL_VALIDATION replays in the replay matrix have a start date of **2025-05-14**. No authentic signals exist for that date. The signals used to construct those replays (ESS from May 2026) are temporally displaced by approximately **12 months**.

A replay claiming authentic 2025-05-14 composite scores cannot be verified as accurate because:
1. The ESS signal file is dated 2026-05-15 (12 months forward of the claimed snapshot date)
2. No May 2025 ESS archive exists in any accessible repository
3. No Zacks, Danelfin, or Yahoo data for May 2025 exists in any accessible repository

The authentic signal window for which full-universe replays could be constructed without look-ahead bias is **2026-05-13 onward**.
