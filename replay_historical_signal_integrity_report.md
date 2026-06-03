# Replay Historical Signal Integrity Report
**Phase 7.6D.2 — Final Report**
**Run Reference:** PAR-20260601-9CFD7C63
**Date:** 2026-06-01
**Analyst:** Security Intelligence Hub — Automated Phase Execution

---

## Executive Summary

**Verdict: `B. REPLAY_AUTHORITY_PARTIALLY_CONFIRMED`**

The 365-day HISTORICAL_VALIDATION replays underpinning Tier 1 Replay Authority were constructed with ESS signals sourced from files dated approximately 12 months after the claimed replay start date. These replays are classified as **CLASS D (current signals applied retrospectively)**. They represent 91.7% of all entries in `replay_matrix.csv` and 100% of the HISTORICAL_VALIDATION evidence base.

The basket return measurements (actual market prices, 2025-05-14 through 2026-05-14) are authentic. The basket selections (which securities were ranked in the top-N) are not — they were made using ESS data from May 2026, after the return period had elapsed. The framework's built-in lookahead validator does not detect this form of bias.

Tier 1 Replay Authority is conditionally maintained. The outperformance figures are real. The predictive validity of the signals that produced the basket selections is unknown and unverifiable without May 2025 ESS data, which does not exist in any accessible repository. The evidence is partially confirmed but cannot be fully validated.

---

## 1. Background and Scope

**Phase 7.6C** promoted Replay to Tier 1 Authority after the WP05D batch established 200 HISTORICAL_VALIDATION replays for snapshot_date=2025-05-14. These 365-day replays covering the period 2025-05-14 to 2026-05-14 showed systematic basket outperformance, with the SMALL-ALL basket achieving +104.6% return vs. a +37.4% benchmark.

**Phase 7.6D.2** was commissioned to answer: "Are replay results based on authentic historical signals, and if not, how much of replay authority is actually justified?"

**Audit scope:**
- `data/current/replay_matrix.csv` (120 entries)
- `data/history/analytical_universe/` (9 snapshot dates)
- `data/history/signals/` (6 authentic signal captures)
- `data/history/replays/` (4 replay dates, ~247 total replays)
- `/Users/scottmmeyer/Projects/portfolio_manager/` (PM archive, 35 ESS captures)

---

## 2. Signal Provenance Findings

### 2.1 The Look-Ahead Signal Mechanism

When the WP05D historical validation batch was executed (on or around 2026-05-15), the function `build_analytical_universe_rows_from_current()` read `data/current/signal_snapshot.csv`. At that time, this file pointed to `EquitySummarScores_May-15-2026.csv` — a Fidelity LSEG StarMine ESS export dated 2026-05-15.

The function was called with `snapshot_date="2025-05-14"` (the historical start date). This parameter populated the metadata field `composite_score_snapshot_date` but had no effect on which ESS file was loaded. The result: every analytical universe row with `snapshot_date=2025-05-14` has ESS values sourced from a file 366 days in the future relative to the claimed snapshot date.

The ESS provider_lineage column in `data/history/analytical_universe/snapshot_date=2025-05-14/` confirms this for every row in those files.

### 2.2 ESS Source File Summary

| Snapshot Date | ESS Source File | File Date | Authentic? | Look-Ahead Gap |
|---|---|---|---|---|
| 2025-05-13 | SecurityExtract_ESS_2026May13.csv | 2026-05-13 | NO | 365 days |
| 2025-05-14 | EquitySummarScores_May-15-2026.csv | 2026-05-15 | NO | 366 days |
| 2026-05-13 | SecurityExtract_ESS_2026May13.csv | 2026-05-13 | YES | 0 days |
| 2026-05-14 | ESS_2026May14.csv | 2026-05-14 | YES | 0 days |
| 2026-05-15 | EquitySummarScores_May-15-2026.csv | 2026-05-15 | YES | 0 days |
| 2026-05-20 | ESS1.csv | 2026-05-20 | YES | 0 days |
| 2026-05-22 | EquitySummaryScores-May2026.csv | 2026-05-22 | YES | 0 days |
| 2026-05-31 | EquitySummaryScores-May2026.csv | 2026-05-31 | YES | 0 days |

### 2.3 Composite Score Formula Contribution

For the CLASS D 2025-05-14 snapshot, the v1 production formula:
```
composite_score = (ESS × 0.55) + (Zacks × 0.25, fallback from ESS file) + (Danelfin × 0.10)
```
- ESS: 2,560 rows from 2026-05-15 file (~55% of composite_score weight)
- Zacks: 1 row (near-zero universe coverage; ~99% of universe uses ESS fallback for Zacks component)
- Danelfin: 1 row (near-zero coverage; Danelfin component effectively absent)
- Yahoo: 0 rows (not integrated; excluded from formula)

**~100% of the composite_score signal for 2025-05-14 analytical universe rows originates from a single May 2026 ESS file.**

---

## 3. Validator Gap

`src/validation/replay_validator.py` — `validate_replay_no_lookahead()` (line 155):

```python
if composite_score_snapshot_date != start_date:
    # FAIL: lookahead detected
```

This check compares the `composite_score_snapshot_date` metadata field to the replay's `start_date`. Both fields are set to `"2025-05-14"` for the HISTORICAL_VALIDATION replays (the snapshot_date parameter is passed explicitly). The check passes.

**The validator does not inspect:**
- Which ESS file was used to populate the analytical universe rows
- The generation date of the ESS source file
- Whether secondary signals (Zacks, Danelfin) match the snapshot date

**The validator passes all 200 HISTORICAL_VALIDATION replays** despite the 12-month ESS look-ahead. This is a genuine validator blindspot, not a logic error in the comparators. The metadata is internally consistent; the provenance error is upstream in the data construction pipeline.

---

## 4. Portfolio Manager Archive Findings

**Repository:** `/Users/scottmmeyer/Projects/portfolio_manager/data/archive/`

The Portfolio Manager contains 35+ timestamped ESS captures representing authentic point-in-time observations:
- **Earliest:** 2025-08-18 (`EquitySummaryScores-18Aug2025.csv`, ~784 rows)
- **Latest:** 2026-06-01 (dense near-daily coverage)

**Why PM cannot close the signal gap:**

| Constraint | Detail |
|---|---|
| No May 2025 ESS | Earliest PM archive is 96 days after replay start date of 2025-05-14 |
| Portfolio-level only | ~784 rows vs ~2,502 SIH full analytical universe |
| Scale mismatch | PM uses 1–10 scale; SIH uses 1–5 text categories |
| No full-universe Zacks | PM Zacks column is portfolio-level |
| No historical Yahoo | PM Yahoo data starts April 2026 |

**PM archives confirm ESS signal stability** (SANM: BULLISH/VERY_BULLISH in Aug 2025 PM archive ≈ BULLISH in May 2026 SIH). Signal direction is preserved but magnitude cannot be assumed identical. Different ESS values would change composite_scores and relative rankings, potentially altering basket membership for near-threshold stocks.

---

## 5. Classification Distribution

### replay_matrix.csv (120 entries)

| Class | Definition | Count | % |
|---|---|---|---|
| CLASS A — Authentic | ESS file date matches snapshot date; Zacks/Danelfin partially authentic | 10 | 8.3% |
| CLASS D — Retrospective | ESS file is 12+ months forward of snapshot date | 110 | 91.7% |

The 10 CLASS A replays are the 2026-05-20 CURRENT_RECOMMENDATION ALL-industry short-window entries.
The 110 CLASS D replays are the 2025-05-14 HISTORICAL_VALIDATION 365-day industry-specific entries.

### All Replays on Disk (~247 total)

| Class | Count | % |
|---|---|---|
| CLASS A | ~27 | 10.9% |
| CLASS D | ~220 | 89.1% |

---

## 6. Authority Reassessment

### What Is Confirmed

| Component | Status |
|---|---|
| Basket return measurement (2025-2026 prices) | AUTHENTIC — actual market prices used |
| CURRENT_RECOMMENDATION signal fidelity | AUTHENTIC — 2026-05-20 signals are contemporaneous |
| 2026 composite_score validity | AUTHENTIC — current analytical universe uses authentic ESS |
| Systematic basket outperformance (result) | REAL — +67.2% alpha vs benchmark for SMALL-ALL is actual market data |

### What Is Not Confirmed

| Component | Status |
|---|---|
| Basket selection predictive validity | UNVERIFIABLE — selection used 2026 signals for 2025 start date |
| ESS values at replay start date | UNKNOWN — no authentic May 2025 ESS exists anywhere |
| Whether the same baskets would have been selected with authentic signals | UNKNOWN |
| Magnitude of outperformance attributable to predictive signal quality | UNKNOWN |

### Bias Risk

The primary risk is **retrospective selection bias**: stocks rated highly by analysts in May 2026 may have earned those ratings partly because they performed well from May 2025 to May 2026. Selecting those stocks "as of May 2025" using 2026 signals is partially equivalent to selecting stocks that happened to do well over the period being measured.

This bias is structural and cannot be detected in the output data without a counterfactual (authentic 2025 signal basket). It is not possible to determine, from available data, how much of the +67.2% alpha is genuine predictive signal and how much is retrospective selection.

### Recommended Authority Level

**Tier 1 — Conditionally Maintained**

Replay retains Tier 1 because:
1. The return evidence is real (authentic prices)
2. ESS is relatively stable consensus data; full circularity is unlikely
3. The magnitude of outperformance (+67% alpha) is large enough that signal noise would need to be extreme to explain it away entirely
4. CURRENT_RECOMMENDATION (CLASS A) replays confirm ongoing applicability
5. No alternative evidence base exists that would support a different authority level

Governance caveat (mandatory): **All HISTORICAL_VALIDATION 365-day replay evidence from snapshot_date=2025-05-14 is classified as CLASS D (current signals applied retrospectively). The outperformance figures are real but the basket selection provenance is unverified. Confidence in replay predictive validity is PARTIAL.**

---

## 7. Historical ESS Opportunity Summary

| Scenario | Feasibility | Closes Gap? |
|---|---|---|
| Retroactive fix with PM Aug 2025 ESS | LOW | Partial only (31% coverage, 96-day gap remains) |
| New replay with Aug 2025 start | PARTIAL | Portfolio holdings only; still CLASS B at best |
| Prospective replay from May 2026 | HIGH | Yes — first authentic 365-day replay available May 2027 |
| Vendor request for May 2025 historical ESS from Fidelity/LSEG | POSSIBLE | Would fully close the gap if obtainable |

**Practical recommendation:** Accept the current CLASS D evidence with governance caveat. Ensure continuous signal capture continues from May 2026 onward. Plan for the first authentic 365-day HISTORICAL_VALIDATION replay to be executed in May 2027 against the 2026-05-13 signal baseline.

---

## 8. Recommendations

### R1 — Add Signal Provenance to Lookahead Validator

**Priority: HIGH**

Enhance `src/validation/replay_validator.py` to record the ESS source file generation date alongside `composite_score_snapshot_date`. Flag as `WARN` when the ESS file is dated more than 7 days after the snapshot date. This would have caught the CLASS D condition automatically.

### R2 — Add CLASS D Provenance Caveat to Replay Matrix

**Priority: MEDIUM**

Add a `signal_integrity_class` column to `replay_matrix.csv` with values CLASS_A through CLASS_D for each entry. This makes the provenance searchable and reportable in downstream analyses.

### R3 — Document Governance Caveat Permanently

**Priority: HIGH**

Add a section to `docs/ARCHITECTURE_CONSISTENCY_CHECKLIST.md` or equivalent noting that the 2025-05-14 HISTORICAL_VALIDATION replays are CLASS D and that Tier 1 Replay Authority is conditionally maintained on this basis.

### R4 — Begin 2026-05-13 Signal Archive Timestamping

**Priority: MEDIUM**

Confirm that all future ESS captures include the file generation date in their filename or metadata. The current naming convention (`SecurityExtract_ESS_2026May13.csv`, `ESS_2026May14.csv`, `ESS1.csv`) is inconsistent. Standardize to ISO date prefix (e.g., `2026-05-20_ess.csv`) for all future captures.

### R5 — Evaluate Fidelity ESS Historical Export

**Priority: LOW (optional)**

Investigate whether LSEG StarMine / Fidelity Active Trader Pro offers a historical export capability for ESS scores as of a specific past date. If a May 2025 ESS extract were obtainable, the CLASS D replays could be retroactively upgraded to CLASS A, fully resolving the authority gap.

---

## Appendix: Phase 7.6D.2 Deliverable Index

| # | File | Status |
|---|---|---|
| Q1 | `replay_snapshot_inventory.csv` | COMPLETE |
| Q2 | `replay_signal_provenance_matrix.csv` | COMPLETE |
| Q3 | `historical_signal_coverage_report.md` | COMPLETE |
| Q4 | `portfolio_manager_signal_archive_inventory.md` | COMPLETE |
| Q5 | `replay_integrity_classification.md` | COMPLETE |
| Q6 | `replay_authority_reassessment.md` | COMPLETE |
| Q7 | `historical_ess_opportunity_assessment.md` | COMPLETE |
| Q8 | `replay_historical_signal_integrity_report.md` | **THIS DOCUMENT** |
