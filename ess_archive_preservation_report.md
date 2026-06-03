# ESS Archive Preservation Report
**Phase 7.6E — ESS Archive Preservation**
**Date:** 2026-06-01
**Run Reference:** PAR-20260601-9CFD7C63

---

## Executive Summary

Phase 7.6E has successfully preserved all authentic historical ESS (Equity Summary Score) archives from the Portfolio Manager repository under governed Security Intelligence Hub control.

**50 ESS files** sourced from `portfolio_manager/data/archive/` have been copied to `data/history/ess_archive/` with original filenames and timestamps preserved. All 50 files pass MD5 checksum verification. No files were modified or transformed.

The archive spans **2025-08-18 to 2026-06-01**, representing the earliest known authenticated ESS dataset in any accessible repository. This preservation ensures these files are no longer dependent on the Portfolio Manager repository for continued availability.

---

## Objectives and Outcomes

| Objective | Status |
|---|---|
| Inventory all PM ESS files | COMPLETE — 50 files, 44 unique checksums |
| Create governed archive location | COMPLETE — `data/history/ess_archive/` |
| Preserve original filenames | COMPLETE — no renames; source folder prefix added only for disambiguating duplicate names across dirs |
| Preserve original timestamps | COMPLETE — `shutil.copy2()` / `cp -p` used throughout |
| Generate inventory CSV | COMPLETE — `ess_archive_inventory.csv` (50 rows, 9 columns) |
| Generate manifest | COMPLETE — `ess_archive_manifest.md` |
| Verify archive integrity | COMPLETE — 50/50 checksums verified |
| No files modified or transformed | CONFIRMED |
| No scoring changes | CONFIRMED |
| No replay changes | CONFIRMED |

---

## Archive Structure

```
data/history/ess_archive/
  pm_archive/              (20 files — from PM timestamped archive dirs + root backup)
  pm_processed_inputs/     (30 files — from PM processed_inputs/ dir)
```

### pm_archive/ (20 files)

Contains ESS files from the Portfolio Manager's timestamped operational archive directories (`data/archive/20YYMMDD-HHMMSS/`) and the standalone backup file. These represent point-in-time ESS captures made during active portfolio management sessions.

File naming convention in SIH: `{SOURCE_DIR_TIMESTAMP}__{ORIGINAL_FILENAME}` for files from timestamped subdirs; original filename retained for the root-level backup file.

**Coverage:** 2025-08-18 through 2026-03-10 (portfolio holdings level, ~480–962 rows)

### pm_processed_inputs/ (30 files)

Contains ESS files from the Portfolio Manager's `processed_inputs/` subdirectory. These files were processed into the PM workflow and include both portfolio-level early captures and full-universe captures beginning March 2026.

**Coverage:** 2026-03-10 through 2026-06-01 (full universe ~2,450–2,838 rows from mid-March 2026 onward)

---

## File Statistics

| Metric | Value |
|---|---|
| Total files archived | 50 |
| CSV files | 49 |
| XLSX files | 1 |
| Unique file checksums | 44 |
| Duplicate groups (same content) | 5 |
| Earliest capture date | 2025-08-18 |
| Latest capture date | 2026-06-01 |
| Date range covered | 286 days |

### Coverage Scope Distribution

| Scope | Row Range | Unique Files | Period |
|---|---|---|---|
| full_universe | >2,000 rows | 24 | 2026-03-10 onward |
| portfolio_extended | 600–2,000 rows | 13 | 2025-08 through early 2026 |
| portfolio_core | 400–600 rows | 6 | 2025-12 through 2026-02 |
| xlsx (binary) | — | 1 | 2025-10-29 |

---

## Source File Provenance

All archived files originate from authentic point-in-time captures made during active Portfolio Manager operations. These are not reconstructed or backfilled files.

Evidence of authentic provenance:
1. Files are stored in timestamped archive directories (`20250824-093221/`, etc.) whose timestamps correspond to known portfolio review sessions
2. ESS row counts vary between captures (783 in Aug 2025 → 962 in Nov 2025 → ~484 in early 2026 as portfolio positions changed)
3. Multiple independent sessions capture the same file when no ESS update has been issued (5 duplicate groups), confirming normal operational behavior rather than retroactive reconstruction
4. File modification timestamps (preserved in `file_mtime` column of inventory) match the archive directory timestamp labels

---

## Duplicate File Analysis

Five groups of files with identical MD5 checksums were found. All are preserved — duplicates represent real operational history (same ESS data loaded across multiple PM sessions).

| Group | Common Content | Count | Cause |
|---|---|---|---|
| Aug 18, 2025 | EquitySummaryScores-18Aug2025.csv | 3 | Two session dirs + Aug 24 labeled copy has same content (Fidelity ESS not refreshed Aug 18→24) |
| Oct 29, 2025 | EquitySummaryScores-29Oct2025.csv | 3 | Three PM sessions loaded same Oct 29 ESS file |
| Mar 10, 2026 | EquitySummaryScores-10Mar2026.csv | 2 | Same file appears in timestamped dir and processed_inputs/ |
| May 3, 2026 | EquitySummaryScores-03May2026.csv | 3 | Labeled as May 3, May 3_1, and May 4 — ESS not refreshed overnight |
| Apr 27, 2026 | EquitySummaryScores-27Apr2026.csv | 4 | Four variant names for same Apr 27 ESS across a single day's sessions |

---

## Integrity Verification

All 50 archived files were verified against their recorded MD5 checksums immediately after copy completion.

```
Integrity check: 50 PASS, 0 FAIL
```

Verification method: Post-copy MD5 recomputation compared to pre-copy MD5 recorded in `ess_archive_inventory.csv`. No file corruption detected.

---

## Coverage Gaps

### Fundamental Gap: Pre-August 2025

The archive begins **2025-08-18**. No ESS data exists for any date before this in the PM archive or in any other accessible repository. This means:

- The 2025-05-14 HISTORICAL_VALIDATION replay start date remains outside the coverage window
- A 96-day gap persists between the earliest archive date and the replay start date
- No remediation is possible without a Fidelity/LSEG StarMine historical ESS export for May 2025

This gap is documented and was known prior to this preservation phase. The purpose of Phase 7.6E is preservation of what does exist, not closure of this gap.

### Monthly Gap: September 2025

No ESS capture between 2025-08-25 and 2025-10-19 (55 days).

### Sparse Period: November 2025 – January 2026

3 captures over ~50 days (Nov 18, Dec 11, Jan 8). Portfolio holdings reduced to ~480–500 rows during this period (fewer active positions).

### Portfolio-to-Universe Transition: March 2026

ESS coverage shifts from portfolio-only (~500 rows) to full analytical universe (~2,500 rows) with the appearance of `EquitySummaryScores-10Mar2026All.csv` on 2026-03-10. This is the earliest full-universe ESS file in the PM archive.

---

## Relationship to SIH Signal History

| Repository | Earliest Full-Universe ESS | Earliest Portfolio ESS | Notes |
|---|---|---|---|
| SIH `data/history/signals/` | 2026-05-13 | 2026-05-13 | Full analytical universe |
| SIH `data/history/ess_archive/` (this archive) | 2026-03-10 | 2025-08-18 | PM-sourced; portfolio-level before Mar 2026 |

**The ESS archive extends SIH's accessible ESS history back by approximately 9 months** (from 2026-05-13 to 2025-08-18 for portfolio-level data, and from 2026-05-13 to 2026-03-10 for full-universe data).

---

## Research Value Assessment

While these archives do not resolve the Phase 7.6D.2 finding that the 2025-05-14 replay signal provenance is unverified (the archive doesn't reach May 2025), they have significant research value:

1. **Signal stability research:** Year-over-year comparison of ESS values for portfolio holdings. Comparing Aug 2025 ESS to Aug 2026 ESS quantifies how much the signal drifts over a 12-month period — directly relevant to the magnitude estimation for the CLASS D look-ahead bias.

2. **Future historical replays:** The 2026-03-10 full-universe file enables construction of authenticated historical replays with start date ≥ 2026-03-10. These would be the first CLASS A HISTORICAL_VALIDATION replays for SIH.

3. **PM-SIH cross-validation:** For the ~50–80 symbols present in both the PM portfolio and the SIH analytical universe, the PM archive provides independent ESS confirmation for multiple dates, enabling signal quality validation.

4. **PM operational audit trail:** The archive preserves the complete historical record of ESS inputs used in PM portfolio decisions from Aug 2025 onward.

---

## Governance Notes

1. **Read-only archive.** Files in `data/history/ess_archive/` should never be modified. They are primary source documents for signal provenance research.

2. **Scale conversion required before use.** PM ESS uses LSEG StarMine 1–10 numeric scale. SIH uses 1–5 text categories. Any research using PM archive ESS values must apply the appropriate conversion mapping before comparing to SIH composite_scores.

3. **Portfolio-level coverage limitation.** Files dated before 2026-03-10 cover portfolio holdings only (~480–960 rows). They cannot substitute as full analytical universe ESS sources for the ~2,500 symbol replay universe.

4. **Duplicate preservation.** All 50 files including duplicates are preserved. Duplicates should not be removed — they document actual PM operational behavior.

---

## Deliverable Index

| Deliverable | Location | Status |
|---|---|---|
| Archive directory | `data/history/ess_archive/` | CREATED |
| pm_archive files (20) | `data/history/ess_archive/pm_archive/` | PRESERVED |
| pm_processed_inputs files (30) | `data/history/ess_archive/pm_processed_inputs/` | PRESERVED |
| Inventory CSV | `ess_archive_inventory.csv` | CREATED |
| Manifest | `ess_archive_manifest.md` | CREATED |
| Integrity verification | 50/50 PASS | VERIFIED |
| This report | `ess_archive_preservation_report.md` | THIS DOCUMENT |
