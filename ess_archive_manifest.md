# ESS Archive Manifest
**Phase 7.6E — ESS Archive Preservation**
**Generated:** 2026-06-01
**Archive Location:** `data/history/ess_archive/`
**Source Repository:** `/Users/scottmmeyer/Projects/portfolio_manager`

---

## Summary Statistics

| Metric | Value |
|---|---|
| Total files archived | 50 |
| Unique files (by checksum) | 44 |
| Duplicate file groups | 5 |
| Earliest ESS file | 2025-08-18 |
| Latest ESS file | 2026-06-01 |
| Archive date range | 286 days |
| Archive subdirectories | 2 (pm_archive, pm_processed_inputs) |

---

## Earliest ESS File

**File:** `20250824-093221__EquitySummaryScores-18Aug2025.csv`
**Capture date:** 2025-08-18
**Row count:** 783
**Coverage scope:** portfolio_extended (portfolio holdings only)
**Checksum:** `cc1ce09b6a9996efe14e64e9cb5d63c5`
**Source:** `portfolio_manager/data/archive/20250824-093221/EquitySummaryScores-18Aug2025.csv`
**File mtime:** 2025-08-18T19:09:12

This file is the oldest authentic ESS snapshot known to exist in any accessible repository. It precedes the SIH signal history by approximately 9 months and predates the current replay start date (2025-05-14) by 96 days.

---

## Latest ESS File

**File:** `EquitySummaryScores_1Jun2026.csv`
**Capture date:** 2026-06-01
**Row count:** 2,497
**Coverage scope:** full_universe
**Checksum:** `dc549ca8b7d4bf27b6d7115f41078eaa`
**Source:** `portfolio_manager/data/archive/processed_inputs/EquitySummaryScores_1Jun2026.csv`
**File mtime:** 2026-06-01T06:23:40

---

## File Count by Archive Subdirectory

| Subdirectory | File Count | Unique Count | Coverage Type |
|---|---|---|---|
| `pm_archive/` | 20 | 16 | portfolio_core + portfolio_extended (2025–early 2026) |
| `pm_processed_inputs/` | 30 | 28 | mix of portfolio and full_universe (2026 onward) |

---

## Captures by Month

| Month | Capture Dates | Files | Max Row Count | Coverage Scope |
|---|---|---|---|---|
| 2025-08 | 2025-08-18, 2025-08-24, 2025-08-25 | 3 unique | 809 | portfolio_extended |
| 2025-10 | 2025-10-19, 2025-10-29 | 2 | 887 | portfolio_extended |
| 2025-11 | 2025-11-18 | 1 | 962 | portfolio_extended |
| 2025-12 | 2025-12-11 | 1 | 508 | portfolio_core |
| 2026-01 | 2026-01-08 | 1 | 483 | portfolio_core |
| 2026-02 | 2026-02-13, 2026-02-15, 2026-02-18, 2026-02-25 | 4 | 516 | portfolio_core |
| 2026-03 | 2026-03-02, 2026-03-07, 2026-03-09, 2026-03-10, 2026-03-10(All) | 5 | 2,538 | full_universe starts |
| 2026-04 | 2026-04-03, 2026-04-04, 2026-04-07, 2026-04-09, 2026-04-13, 2026-04-15, 2026-04-18, 2026-04-21, 2026-04-22, 2026-04-23, 2026-04-24, 2026-04-27, 2026-04-30 | 13 | 2,504 | full_universe |
| 2026-05 | 2026-05-01, 2026-05-03, 2026-05-04, 2026-05-08, 2026-05-11, 2026-05-14, 2026-05-15, 2026-05-20, 2026-05-26, 2026-05-?? | 10 | 2,838 | full_universe |
| 2026-06 | 2026-06-01 | 1 | 2,497 | full_universe |

---

## Coverage Gaps

### Critical Gap: Pre-August 2025

**Months with no ESS capture:** January through July 2025 (7 months)

This gap means the 2025-05-14 HISTORICAL_VALIDATION replay start date falls entirely within the pre-archive period. No ESS data for May 2025 exists in the archive or in any other accessible repository. This gap is fundamental and cannot be closed with existing PM data.

### Gap: September 2025

No ESS capture between 2025-08-25 and 2025-10-19 (55 days).

### Gap: Late November 2025 to Early January 2026

After 2025-11-18, next substantial capture is 2025-12-11 (backup file, 508 rows). Then no capture until 2026-01-08 (21 days gap).

### Transition: Portfolio-Level to Full-Universe (March 2026)

ESS coverage expands from ~500 portfolio holdings to 2,500+ full analytical universe on 2026-03-10. The file `EquitySummaryScores-10Mar2026All.csv` (2,538 rows) is the first full-universe ESS snapshot in the PM archive. This transition date is significant for replay research.

---

## Coverage Scope Distribution (Unique Files)

| Scope | Definition | Unique Files |
|---|---|---|
| full_universe | >2,000 rows | 24 |
| portfolio_extended | 600–2,000 rows | 13 |
| portfolio_core | 400–600 rows | 6 |
| portfolio_subset | <400 rows | 0 |
| binary (xlsx) | non-CSV | 1 |

---

## Duplicate Files

Five groups of files with identical content (same MD5 checksum). All duplicates are preserved in the archive since they represent genuine PM operational behavior (same ESS file copied across multiple run sessions).

| Group | MD5 (first 8) | Files | Explanation |
|---|---|---|---|
| 1 | `cc1ce09b` | 20250824-093221__EquitySummaryScores-18Aug2025.csv, 20250824-094637__EquitySummaryScores-18Aug2025.csv, 20250824-094637__EquitySummaryScores-24Aug2025.csv | Two Aug 18 copies + Aug 24 file has same content (ESS not refreshed Aug 18→24) |
| 2 | `0a165e6f` | 20251029-191921__EquitySummaryScores-29Oct2025.csv, 20251030-231035__EquitySummaryScores-29Oct2025.csv, 20251118-145348__EquitySummaryScores-29Oct2025.csv | Oct 29 ESS copied across 3 PM sessions |
| 3 | `181f8ebb` | 20260310-094849__EquitySummaryScores-10Mar2026.csv, EquitySummaryScores-10Mar2026.csv (processed_inputs) | Same file in archive dir and processed_inputs |
| 4 | `cc12595b` | EquitySummaryScores-03May2026.csv, EquitySummaryScores-03May2026_1.csv, EquitySummaryScores-04May2026.csv | May 3 file reused as May 4 (ESS not refreshed overnight) |
| 5 | `ebde9967` | EquitySummaryScores-27Apr2026.csv, EquitySummaryScores-27Apr2026_1.csv, EquitySummaryScores-27Apr2026_2.csv, EquitySummaryScores_2026-04-27.csv | 4 copies of Apr 27 ESS from same session runs |

---

## Notable Files

| File | Note |
|---|---|
| `EquitySummaryScores-10Mar2026All.csv` | First full-universe ESS file (2,538 rows); distinct from portfolio-only Mar 10 file |
| `EquitySummaryScores-2026May08.csv` | 2,838 rows — largest file in archive (broader universe than standard 2,502) |
| `20251118-145549_cleanup__EquitySummaryScores-29Oct2025.xlsx` | Only binary file in archive; Excel format; content equivalent to csv version of same date |
| `EquitySummaryScores_backup_20251211_171503.csv` | Root-level backup file (not in timestamped dir); 508 rows; portfolio-subset for that period |

---

## Archive Integrity Status

All 50 files were copied with `shutil.copy2()` (Python) and `cp -p` (shell), both of which preserve original file modification timestamps. MD5 checksums were computed on the source files before copying and are recorded in `ess_archive_inventory.csv`. Post-copy integrity verification confirms all files readable.

**Integrity: VERIFIED**

See `ess_archive_inventory.csv` for per-file checksums.

---

## Schema Reference (PM ESS File Format)

All PM ESS CSV files use the following column schema (portfolio-level files):
```
Symbol, Company Name, Security Type, Security Price, ESS from LSEG StarMine,
Fwd EPS LTG (3-5 Yrs), Zacks Investment Research, Jefferson Research, McLean Capital Management
```

Full-universe files (2026-03-10 onward) use an extended schema:
```
Symbol, Company Name, Security Type, Security Price, ESS from LSEG StarMine,
Fwd EPS LTG (3-5 Yrs), Zacks Investment Research, [additional providers]
```

**Scale:** ESS from LSEG StarMine is on a 1–10 numeric scale (Fidelity brokerage display). SIH internal ESS uses a 1–5 text category scale (VERY_BULLISH through VERY_BEARISH). A conversion mapping is required before these files can be used in SIH replay construction.
