# Phase 22D.11 — Generated Artifact Analysis
**Generated:** 2026-06-03  
**Scope:** `data/portfolio_ingestion/analysis_runs/` and `data/exports/archive/`

---

## Executive Summary

The dominant source of dirty files is the `data/portfolio_ingestion/analysis_runs/` directory, containing **175 Portfolio Analysis Runs (PAR)** totaling **1,411 files** and **~91MB** of machine-generated output. These are runtime artifacts — not source code, not documentation, not governance records. **They must not be committed to git.**

---

## 1. Portfolio Analysis Run (PAR) Directory

### Inventory

| Metric | Value |
|---|---|
| Total run directories | 175 |
| Total files | 1,411 |
| Total size | ~91 MB |
| Date range | 2026-05-21 through 2026-06-03 |
| Git status | `??` (untracked — correctly excluded by gitignore) |

### Run ID Taxonomy

PAR IDs follow two patterns:
- `PAR-YYYYMMDD-XXXXXXXX` — date-stamped runs (chronological production runs)
- `PAR-CONCENTRATED_ALPHA-XXXXXXXX` — mandate-tagged runs (CONCENTRATED_ALPHA mandate-specific outputs)

### Date Distribution

| Date Range | Run Count (approx.) |
|---|---|
| 2026-05-21 | ~60 runs |
| 2026-05-22 through 2026-05-30 | ~80 runs |
| 2026-05-31 through 2026-06-02 | ~30 runs |
| 2026-06-03 (session date) | 3 runs |
| CONCENTRATED_ALPHA tag | 2 runs |

### Per-Run File Structure

Each PAR directory contains a consistent set of output files:

| File | Type | Description |
|---|---|---|
| `run_metadata.json` | JSON | Run ID, timestamp, mandate, input checksums |
| `snapshot.json` | JSON | Full portfolio snapshot with all computed fields |
| `holdings.csv` | CSV | Normalized holdings with classification |
| `alignment.csv` | CSV | Security-to-ETF alignment scores |
| `security_overlays.csv` | CSV | Replay evidence, ESS, signal overlays per symbol |
| `concentration.json` | JSON | Concentration analysis output |
| `recommendations.json` | JSON | Full recommendation set |
| `reconciliation.json` | JSON | Portfolio reconciliation state |
| `deployment_queue.json` | JSON | Deployment queue (capital deployment candidates) |
| `deployment_plan.json` | JSON | Generated deployment plan with allocations |
| `ucf_verdicts.json` | JSON | UCF conviction verdicts per symbol |

**Note:** Newer runs (post-Phase 7.7A) contain `deployment_queue.json`, `deployment_plan.json`, and `ucf_verdicts.json` which were not present in earlier runs. Earlier runs contain a subset of 4–8 files.

### File Type Breakdown

| Extension | Count |
|---|---|
| `.json` | 886 |
| `.csv` | 525 |
| `.md` | 0 |
| **Total** | **1,411** |

### Certified Run — PAR-20260603-AC8FD5F0

This is the production-certified run from Phase 22D.10A validation:

| Field | Value |
|---|---|
| Run ID | PAR-20260603-AC8FD5F0 |
| Timestamp | 2026-06-03T01:52:31 UTC |
| Mandate | CONCENTRATED_ALPHA |
| Cash target | 7.0% |
| Total market value | $480,298.55 |
| cash_mv (SPAXX) | $41,279.15 |
| settlement_adjustment | $3,566.55 |
| adjusted_deployable_mv | $4,091.70 |
| Cash after deployment | 7.7426% ≥ 7.0% floor ✅ |

This run is the certification artifact for Phase 22D.10. It is a generated artifact and should NOT be committed. Its key values are preserved in the Phase 22D.10A governance documents (`data/analysis/phase_22d10a/`).

### Gitignore Verification

`data/portfolio_ingestion/analysis_runs/` is shown as `??` (untracked) in git status, confirming gitignore exclusion is active. The `.gitignore` change in this session added `.env` but did not alter run exclusion rules.

**Gitignore status: CONFIRMED EXCLUDED. No action required.**

---

## 2. Export Archive

### Inventory

| Path | Files | Size | Description |
|---|---|---|---|
| `data/exports/archive/` | 3 | ~24KB | Snapshot export archive from 2026-06-01 |

### Files

| File | Description |
|---|---|
| `data/exports/archive/deployment_queue_export_20260601.csv` | Deployment queue CSV export |
| `data/exports/archive/holdings_export_20260601.csv` | Holdings CSV export |
| `data/exports/archive/snapshot_export_20260601.json` | Portfolio snapshot JSON export |

**Classification:** Generated export artifacts. Date-stamped. Small in size. These could be committed as a point-in-time reference snapshot if there is operational value, but they are not required for production correctness. Recommend excluding from commit unless explicitly requested.

---

## 3. Root-Level Analysis Data Files (37 .csv files in root)

37 CSV files at the repository root are classified as ROOT_REPORT in the dirty inventory. These are analysis data files (not run outputs) — they were written during signal/replay/conviction analysis phases and contain computed metrics:

Representative examples:
- `allocation_curve_models.csv` — allocation curve model parameters
- `ess_coverage_tiers.csv` — ESS signal coverage by tier
- `signal_authority_inventory.csv` — signal authority scores
- `conviction_decomposition.csv` — conviction breakdown by symbol

**Classification:** These are small analytical artifacts (not run outputs). Unlike the PAR directory, they have research/governance value and should be committed as ROOT_REPORT artifacts alongside the other root-level reports.

---

## 4. Impact Assessment

### Git Repository Health

If the `analysis_runs/` directory were accidentally committed:
- Repository would grow by **~91MB** in a single commit
- All future clones would download 91MB of stale machine-generated data
- `git log --stat` output would become essentially unreadable
- `git diff` operations across relevant commits would be noise-contaminated

**The gitignore exclusion of `analysis_runs/` is a critical infrastructure control.** It must be preserved in all future `.gitignore` modifications.

### Recommendation Summary

| Path | Commit? | Action |
|---|---|---|
| `data/portfolio_ingestion/analysis_runs/` | **NO** | Remains gitignored; certified run values preserved in governance docs |
| `data/exports/archive/` | Optional | Small; no correctness value; omit unless specifically requested |
| Root-level CSV files | **YES** | Commit as ROOT_REPORT alongside root markdown files |
