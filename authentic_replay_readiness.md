# Authentic Replay Readiness Assessment
**Phase 7.6F-R — Deliverable Q6**
**Generated:** 2026-06-01
**Reference Date:** 2026-06-01 (PAR-20260601-9CFD7C63)

---

## 1. Purpose

This document assesses the readiness of the ESS historical archive for use in **authentic replay construction** — replays where signal data originates from the actual capture date rather than a later proxy. Prior assessment (Phase 7.6D.2) concluded that 110 of 120 replay matrix entries used 2026 ESS as a proxy for all historical snapshot dates, earning verdict `B. REPLAY_AUTHORITY_PARTIALLY_CONFIRMED`. This document determines whether the newly constructed ESS archive can improve that verdict.

---

## 2. ESS Archive Timeline (Authentic Dates)

### Phase 1 — Portfolio-Level Coverage (14 dates)

| Date | Symbols | Scope | Notes |
|------|---------|-------|-------|
| 2025-08-18 | 784 | portfolio_extended | **Earliest authentic ESS date** |
| 2025-08-25 | 804 | portfolio_extended | |
| 2025-10-19 | 871 | portfolio_extended | |
| 2025-10-29 | 631 | portfolio_extended | |
| 2025-11-18 | 963 | portfolio_extended | Largest portfolio-level file |
| 2025-12-11 | 492 | portfolio_core | |
| 2026-01-08 | 467 | portfolio_core | |
| 2026-02-13 | 500 | portfolio_core | |
| 2026-02-15 | 498 | portfolio_core | |
| 2026-02-18 | 496 | portfolio_core | |
| 2026-02-25 | 488 | portfolio_core | |
| 2026-03-02 | 492 | portfolio_core | |
| 2026-03-07 | 479 | portfolio_core | |
| 2026-03-09 | 482 | portfolio_core | |

### Phase 2 — Full-Universe Coverage (17+ dates)

| Date | Symbols | Scope | Notes |
|------|---------|-------|-------|
| **2026-03-10** | **2,539** | **full_universe** | **Earliest authentic full-universe date** |
| 2026-04-03 | 500 | portfolio_core | Portfolio-only in Apr |
| 2026-04-04 | 766 | portfolio_extended | |
| 2026-04-07 | 739 | portfolio_extended | |
| 2026-04-09 | 754 | portfolio_extended | |
| 2026-04-13 | 774 | portfolio_extended | |
| 2026-04-15 | 2,476 | full_universe | Full-universe resumes |
| 2026-04-18 | 2,478 | full_universe | |
| 2026-04-21 | 2,494 | full_universe | |
| 2026-04-22 | 2,495 | full_universe | |
| 2026-04-23 | 2,495 | full_universe | |
| 2026-04-24 | 2,495 | full_universe | |
| 2026-04-27 | 2,493 | full_universe | |
| 2026-04-30 | 2,505 | full_universe | |
| 2026-05-03 | 2,509 | full_universe | |
| 2026-05-08 | 2,500 | full_universe | Small file; large May 8 file had no ESS |
| 2026-05-11 | 2,499 | full_universe | |
| 2026-05-14 | 2,456 | full_universe | |
| 2026-05-15 | 2,452 | full_universe | |
| 2026-05-20 | 2,721 | full_universe | |
| 2026-05-26 | 2,481 | full_universe | |
| **2026-06-01** | **2,498** | **full_universe** | **Latest authentic date = today** |

---

## 3. Replay Readiness by Type

### 3.1 Portfolio-Level Authentic Replay (Historical Validation Tier 1)

**First available replay date:** 2025-08-18
**Baseline ESS source:** `EquitySummaryScores-18Aug2025.csv` (784 symbols, portfolio_extended)

A portfolio snapshot replay using Aug 18, 2025 as the signal date can now be constructed using authentic ESS data rather than the 2026-CLASS-D proxy. This resolves the CLASS D finding for all snapshot dates on or after 2025-08-18 **for securities that appear in the portfolio-level files**.

**Constraint:** Portfolio-level files contain only active holdings (500–963 symbols). Securities not held at the snapshot date will have no authentic ESS signal available.

### 3.2 Full-Universe Authentic Replay (Standard Replay)

**First available full-universe replay date:** 2026-03-10
**Baseline ESS source:** `EquitySummaryScores-10Mar2026All.csv` (2,539 symbols, full_universe)

This is a significant extension from the prior SIH production baseline of 2026-05-13 (first SIH-sourced ESS date). The archive pushes the full-universe authentic baseline back **64 days** to March 10, 2026.

**Key capability unlocked:**
- A full-universe snapshot replay for any date **on or after 2026-03-10** can use authentic ESS for securities present in that file.
- For dates between 2025-08-18 and 2026-03-09: authentic ESS is available only for portfolio-level holdings.

### 3.3 Authentic Replay Availability Windows

| Replay Window | Earliest Start | ESS Available | Status |
|---------------|----------------|---------------|--------|
| 30-day full-universe | 2026-03-10 | 2026-03-10 → 2026-04-09 | **AVAILABLE NOW** |
| 60-day full-universe | 2026-03-10 | 2026-03-10 → 2026-05-09 | **AVAILABLE NOW** |
| 90-day full-universe | 2026-03-10 | 2026-03-10 → 2026-06-08 | **~7 days away** |
| 180-day full-universe | 2026-03-10 | 2026-03-10 → 2026-09-06 | Sep 2026 |
| 365-day full-universe | 2026-03-10 | 2026-03-10 → 2027-03-10 | Mar 2027 |
| 365-day portfolio cohort | 2025-08-18 | 2025-08-18 → 2026-08-18 | Aug 2026 (2.5 months) |

---

## 4. Impact on Phase 7.6D.2 Replay Classification

**Prior verdict:** `B. REPLAY_AUTHORITY_PARTIALLY_CONFIRMED`
- 110 of 120 entries: CLASS D (2026 ESS proxy used for all historical dates)
- 10 of 120 entries: CLASS A (2026-05-20 snapshot, authentic ESS)

**Reclassification potential with this archive:**

| Prior Class | Replay Date | ESS Available | New Classification |
|-------------|------------|---------------|--------------------|
| CLASS D | 2026-05-20 and later | Yes (full-universe) | Already CLASS A |
| CLASS D | 2026-03-10 → 2026-05-19 | Yes (full-universe, 2026-03-10 file) | **CLASS A** (for covered securities) |
| CLASS D | 2025-08-18 → 2026-03-09 | Yes (portfolio-level only) | **CLASS B** (partially authentic — holdings subset) |
| CLASS D | Before 2025-08-18 | No authentic data | Remains CLASS D |

**Net reclassification (if full replay matrix were rebuilt):**
- Entries using 2026-03-10 ESS (or later) as of snapshot date → upgradeable to CLASS A
- Entries using 2025-08-18 → 2026-03-09 → upgradeable to CLASS B for portfolio holdings
- Entries before 2025-08-18 → remain CLASS D

**Revised verdict (if reclassification were executed):** Would approach `A. REPLAY_AUTHORITY_CONFIRMED` for all replay dates on or after 2026-03-10, and `B+` for the Aug 2025 portfolio-level cohort.

---

## 5. Key Finding

> **The ESS archive extends authentic full-universe coverage back 64 days from the prior SIH baseline (2026-05-13) to 2026-03-10, and extends portfolio-level authentic coverage back 287 days to 2025-08-18.**

This archive supports:
1. A 30-day or 60-day full-universe effectiveness pilot today
2. A 90-day full-universe study within 7 days
3. A 12-month portfolio-level effectiveness study available in August 2026
4. Reclassification of replay matrix entries to CLASS A/B (authorization required)

---

## 6. Archive Governance Note

All source files are stored as read-only archives in `data/history/ess_archive/`. Per Phase 7.6E governance, these files should not be modified. The `ess_history_master.csv` constructed in Phase 7.6F-R is the authoritative derived research dataset and should be treated as append-only once finalized.
