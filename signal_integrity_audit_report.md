# Signal Integrity Audit Report — Phase 7.5H

**Date:** 2026-05-31  
**Reference Run:** PAR-20260529-BAF83F16  
**Audit Type:** Read-only. No code changes. No scoring changes.  
**Scope:** Top 20 deployment candidates

---

## 1. Audit Universe

Reference run PAR-20260529-BAF83F16 contains 42 deployment candidates. The top 20 are audited below.

| Rank | Symbol | CW-DAS Score | UCF Label | Composite |
|:----:|--------|:------------:|-----------|:---------:|
| 1 | VRT | 95.53 | CORE_CONVICTION_LEADER | 4.5556 |
| 2 | ARW | 94.11 | HIGH_CONVICTION_ANCHOR | 4.8889 |
| 3 | SNX | 93.51 | HIGH_CONVICTION_ANCHOR | 4.7778 |
| 4 | ATLC | 93.48 | HIGH_CONVICTION_ANCHOR | 4.7778 |
| 5 | PSX | 93.34 | HIGH_CONVICTION_ANCHOR | 4.7222 |
| 6 | CBOE | 93.04 | HIGH_CONVICTION_ANCHOR | 4.6667 |
| 7 | AVT | 92.10 | HIGH_CONVICTION_ANCHOR | 4.5556 |
| 8 | LRCX | 91.73 | HIGH_CONVICTION_ANCHOR | 4.5000 |
| 9 | CAH | 91.59 | HIGH_CONVICTION_ANCHOR | 4.5000 |
| 10 | DELL | 90.91 | HIGH_CONVICTION_ANCHOR | 4.4444 |
| 11 | SANM | 90.78 | HIGH_CONVICTION_ANCHOR | 4.2778 |
| 12 | PCB | 90.74 | HIGH_CONVICTION_ANCHOR | 4.3333 |
| 13 | CIEN | 90.11 | HIGH_CONVICTION_ANCHOR | 4.2778 |
| 14 | NUE | 89.62 | HIGH_CONVICTION_ANCHOR | 4.1111 |
| 15 | GFF | 88.50 | HIGH_CONVICTION_ANCHOR | 3.8333 |
| 16 | ALNT | 88.46 | HIGH_CONVICTION_ANCHOR | 3.7778 |
| 17 | MTZ | 88.35 | HIGH_CONVICTION_ANCHOR | 3.7778 |
| 18 | CRS | 88.20 | HIGH_CONVICTION_ANCHOR | 3.7222 |
| 19 | CMCO | 87.95 | HIGH_CONVICTION_ANCHOR | 3.6667 |
| 20 | ANGO | 87.88 | HIGH_CONVICTION_ANCHOR | 3.8333 |

---

## 2. Signal Trace — All Candidates

### 2A. ESS (StarMine Equity Summary Score)

**Source:** `EquitySummaryScores-May2026.csv` via FIDELITY provider  
**Snapshot date:** 2026-05-26  
**Age:** 5 days (as of 2026-05-31)  
**Coverage:** 20/20 (100%)

| Symbol | ESS Value | Coverage Domain | ESS Numeric | Source File |
|--------|-----------|:--------------:|:-----------:|-------------|
| VRT | VERY_BULLISH | STARMINE_COVERED | 5.0 | EquitySummaryScores-May2026.csv |
| ARW | VERY_BULLISH | STARMINE_COVERED | 5.0 | EquitySummaryScores-May2026.csv |
| SNX | VERY_BULLISH | STARMINE_COVERED | 5.0 | EquitySummaryScores-May2026.csv |
| ATLC | VERY_BULLISH | STARMINE_COVERED | 5.0 | EquitySummaryScores-May2026.csv |
| PSX | VERY_BULLISH | STARMINE_COVERED | 5.0 | EquitySummaryScores-May2026.csv |
| CBOE | VERY_BULLISH | STARMINE_COVERED | 5.0 | EquitySummaryScores-May2026.csv |
| AVT | VERY_BULLISH | STARMINE_COVERED | 5.0 | EquitySummaryScores-May2026.csv |
| LRCX | VERY_BULLISH | STARMINE_COVERED | 5.0 | EquitySummaryScores-May2026.csv |
| CAH | VERY_BULLISH | STARMINE_COVERED | 5.0 | EquitySummaryScores-May2026.csv |
| DELL | VERY_BULLISH | STARMINE_COVERED | 5.0 | EquitySummaryScores-May2026.csv |
| SANM | BULLISH | STARMINE_COVERED | 4.0 | EquitySummaryScores-May2026.csv |
| PCB | VERY_BULLISH | STARMINE_COVERED | 5.0 | EquitySummaryScores-May2026.csv |
| CIEN | BULLISH | STARMINE_COVERED | 4.0 | EquitySummaryScores-May2026.csv |
| NUE | BULLISH | STARMINE_COVERED | 4.0 | EquitySummaryScores-May2026.csv |
| GFF | BULLISH | STARMINE_COVERED | 4.0 | EquitySummaryScores-May2026.csv |
| ALNT | BULLISH | STARMINE_COVERED | 4.0 | EquitySummaryScores-May2026.csv |
| MTZ | BULLISH | STARMINE_COVERED | 4.0 | EquitySummaryScores-May2026.csv |
| CRS | BULLISH | STARMINE_COVERED | 4.0 | EquitySummaryScores-May2026.csv |
| CMCO | BULLISH | STARMINE_COVERED | 4.0 | EquitySummaryScores-May2026.csv |
| ANGO | BULLISH | STARMINE_COVERED | 4.0 | EquitySummaryScores-May2026.csv |

**Observation:** ESS splits cleanly at rank 10/11: ranks 1–10 are VERY_BULLISH, ranks 11–20 are BULLISH. No NEUTRAL or BEARISH readings in the top 20.

### 2B. Zacks

**Source:** `2026-05-29_zacks.csv`  
**Age:** 2 days  
**Coverage:** 20/20 (100%)

| Symbol | Zacks Score | Signal Pts Contribution |
|--------|:-----------:|:-----------------------:|
| VRT | 4.0 | 27.3 |
| ARW | 5.0 | 29.3 |
| SNX | 5.0 | 28.7 |
| ATLC | 5.0 | 28.7 |
| PSX | 5.0 | 28.3 |
| CBOE | 5.0 | 28.0 |
| AVT | 4.0 | 27.3 |
| LRCX | 4.0 | 27.0 |
| CAH | 4.0 | 27.0 |
| DELL | 4.0 | 26.7 |
| SANM | 5.0 | 25.7 |
| PCB | 3.0 | 26.0 |
| CIEN | 5.0 | 25.7 |
| NUE | 5.0 | 24.7 |
| GFF | 4.0 | 23.0 |
| ALNT | 3.0 | 22.7 |
| MTZ | 3.0 | 22.7 |
| CRS | 3.0 | 22.3 |
| CMCO | 3.0 | 22.0 |
| ANGO | 4.0 | 23.0 |

**Note:** Zacks score scale is 1–5 (1=Strong Buy; 5=Strong Sell for Zacks Rank, but mapped inversely here to signal contribution). All 20 have valid Zacks scores.

### 2C. Danelfin

**Source:** `2026-05-29_danelfin.csv`  
**Age:** 2 days  
**Coverage:** 20/20 (100%)

| Symbol | Danelfin Score | Danelfin Raw |
|--------|:--------------:|:-----------:|
| VRT | 3.5 | 7 |
| ARW | 4.0 | 8 |
| SNX | 3.0 | 6 |
| ATLC | 3.0 | 6 |
| PSX | 2.5 | 5 |
| CBOE | 2.0 | 4 |
| AVT | 3.5 | 7 |
| LRCX | 3.0 | 6 |
| CAH | 3.0 | 6 |
| DELL | 2.5 | 5 |
| SANM | 4.0 | 8 |
| PCB | 4.0 | 8 |
| CIEN | 4.0 | 8 |
| NUE | 2.5 | 5 |
| GFF | 2.5 | 5 |
| ALNT | 4.5 | 9 |
| MTZ | 4.5 | 9 |
| CRS | 4.0 | 8 |
| CMCO | 3.5 | 7 |
| ANGO | 2.5 | 5 |

### 2D. Replay

**Coverage:** replay_supported = True for all 20 (100%)  
**Replay percentile:** MISSING for all 20 (0% percentile coverage)  
**Score impact:** All 20 candidates receive replay_pts = 20.0 (replay-supported, no percentile refinement)

This is the single structural gap in the signal pipeline. `replay_supported=True` is the eligibility gate that allows a symbol into the deployment queue. The replay percentile, when available, would refine the signal component. Its absence is consistent across all 20 candidates and represents a known system limitation, not per-symbol data corruption.

### 2E. UCF and Composite Breakdown

| Symbol | UCF Score | Sig | Rpl | Conv | Sizing | Mom | R_Pen | C_Pen | Total |
|--------|:---------:|:---:|:---:|:----:|:------:|:---:|:-----:|:-----:|:-----:|
| VRT | 91.17 | 27.3 | 20.0 | 35.0 | 3.2 | 10.0 | 0.0 | 0.0 | 95.53 |
| ARW | 92.76 | 29.3 | 20.0 | 28.0 | 6.8 | 10.0 | 0.0 | 0.0 | 94.11 |
| SNX | 92.19 | 28.7 | 20.0 | 28.0 | 6.8 | 10.0 | 0.0 | 0.0 | 93.51 |
| ATLC | 92.14 | 28.7 | 20.0 | 28.0 | 6.8 | 10.0 | 0.0 | 0.0 | 93.48 |
| PSX | 92.05 | 28.3 | 20.0 | 28.0 | 7.0 | 10.0 | 0.0 | 0.0 | 93.34 |
| CBOE | 91.63 | 28.0 | 20.0 | 28.0 | 7.0 | 10.0 | 0.0 | 0.0 | 93.04 |
| AVT | 90.42 | 27.3 | 20.0 | 28.0 | 6.8 | 10.0 | 0.0 | 0.0 | 92.10 |
| LRCX | 90.23 | 27.0 | 20.0 | 28.0 | 6.7 | 10.0 | 0.0 | 0.0 | 91.73 |
| CAH | 90.53 | 27.0 | 20.0 | 28.0 | 6.6 | 10.0 | 0.0 | 0.0 | 91.59 |
| DELL | 89.75 | 26.7 | 20.0 | 28.0 | 6.2 | 10.0 | 0.0 | 0.0 | 90.91 |
| SANM | 88.40 | 25.7 | 20.0 | 28.0 | 7.1 | 10.0 | 0.0 | 0.0 | 90.78 |
| PCB | 88.23 | 26.0 | 20.0 | 28.0 | 6.7 | 10.0 | 0.0 | 0.0 | 90.74 |
| CIEN | 86.68 | 25.7 | 20.0 | 28.0 | 6.4 | 10.0 | 0.0 | 0.0 | 90.11 |
| NUE | 85.62 | 24.7 | 20.0 | 28.0 | 7.0 | 10.0 | 0.0 | 0.0 | 89.62 |
| GFF | 84.11 | 23.0 | 20.0 | 28.0 | 7.5 | 10.0 | 0.0 | 0.0 | 88.50 |
| ALNT | 83.73 | 22.7 | 20.0 | 28.0 | 7.8 | 10.0 | 0.0 | 0.0 | 88.46 |
| MTZ | 83.73 | 22.7 | 20.0 | 28.0 | 7.7 | 10.0 | 0.0 | 0.0 | 88.35 |
| CRS | 83.43 | 22.3 | 20.0 | 28.0 | 7.9 | 10.0 | 0.0 | 0.0 | 88.20 |
| CMCO | 82.99 | 22.0 | 20.0 | 28.0 | 8.0 | 10.0 | 0.0 | 0.0 | 87.95 |
| ANGO | 83.79 | 23.0 | 20.0 | 28.0 | 6.9 | 10.0 | 0.0 | 0.0 | 87.88 |

**Observation:** No candidate carries a redundancy penalty (0.0) or concentration penalty (0.0) in the top 20. Momentum component is uniformly 10.0 for all 20 — maximum. Conviction score is 35.0 for VRT (CCL tier) and 28.0 for all HCA.

---

## 3. Cross-Artifact Reconciliation

All 20 candidates were checked for consistency across:
- `data/current/analytical_universe.csv`
- `holdings.csv` (PAR-20260529-BAF83F16)
- `security_overlays.csv` (PAR-20260529-BAF83F16)
- `ucf_verdicts.json` (PAR-20260529-BAF83F16)
- `deployment_queue.json` (PAR-20260529-BAF83F16)
- `deployment_plan.json` (PAR-20260529-BAF83F16)

**Fields reconciled:** `ess_score_text`, `composite_score`, `narrative_tier`/`ucf_label`

**Result: 0 cross-artifact inconsistencies detected.**

All signal values propagate consistently from `analytical_universe.csv` through holdings → overlays → UCF verdicts → deployment queue. The Phase 7.5G-B fix (coverage-aware dedup) resolved the prior ESS propagation gap.

---

## 4. Signal Health Report

| Metric | Coverage | Status |
|--------|:--------:|--------|
| ESS (StarMine) | 20/20 (100%) | ✅ Full coverage |
| Zacks | 20/20 (100%) | ✅ Full coverage |
| Danelfin | 20/20 (100%) | ✅ Full coverage |
| Replay Supported | 20/20 (100%) | ✅ Full coverage |
| **Replay Percentile** | **0/20 (0%)** | ⚠️ Structural gap |
| Yahoo Price Target | 20/20 (100%) | ✅ Available (not scored) |

**Signal Age (as of 2026-05-31):**
| Signal | Source Date | Age | Status |
|--------|:-----------:|:---:|--------|
| ESS | 2026-05-26 | 5 days | ✅ Fresh |
| Zacks | 2026-05-29 | 2 days | ✅ Fresh |
| Danelfin | 2026-05-29 | 2 days | ✅ Fresh |
| Yahoo | 2026-05-29 | 2 days | ✅ Fresh (not scored) |

**Missing signals:** 0 (all ESS, Zacks, Danelfin present)  
**Stale signals:** 0 (all within 14-day threshold)  
**Conflicting signals:** 0 (no cross-artifact inconsistencies)  
**Structural gaps:** 1 — replay percentile missing for all 20 candidates

---

## 5. Deployment Risk Review

**Risk Classification Logic:**
- `HIGH_RISK`: Missing ESS or 2+ missing signals
- `MEDIUM_RISK`: 1 missing signal OR any stale signal
- `LOW_RISK`: All signals present and fresh

**Result: All 20 candidates are MEDIUM_RISK.**

The singular risk factor is the missing `replay_percentile` for all 20 candidates. This is a system-level structural gap, not a per-symbol data quality issue. All three primary scoring signals (ESS, Zacks, Danelfin) are present and fresh. No candidate carries HIGH_RISK.

| Symbol | Risk | Gap | Notes |
|--------|:----:|-----|-------|
| VRT | MEDIUM_RISK | replay_percentile missing | ESS=VERY_BULLISH, Zacks=4, Danelfin=3.5 |
| ARW | MEDIUM_RISK | replay_percentile missing | Strongest Zacks (5.0) in top 20 |
| SNX | MEDIUM_RISK | replay_percentile missing | — |
| ATLC | MEDIUM_RISK | replay_percentile missing | — |
| PSX | MEDIUM_RISK | replay_percentile missing | — |
| CBOE | MEDIUM_RISK | replay_percentile missing | Yahoo ABR=3.12 (moderate) |
| AVT | MEDIUM_RISK | replay_percentile missing | — |
| LRCX | MEDIUM_RISK | replay_percentile missing | — |
| CAH | MEDIUM_RISK | replay_percentile missing | — |
| DELL | MEDIUM_RISK | replay_percentile missing | — |
| SANM | MEDIUM_RISK | replay_percentile missing | Zacks=5, Danelfin=4.0 |
| PCB | MEDIUM_RISK | replay_percentile missing | Lowest Zacks (3.0) in top 12 |
| CIEN | MEDIUM_RISK | replay_percentile missing | Phase 7.5G-B ESS restored |
| NUE | MEDIUM_RISK | replay_percentile missing | Phase 7.5G-B ESS restored |
| GFF | MEDIUM_RISK | replay_percentile missing | Yahoo upside 35.4% (highest in top 20) |
| ALNT | MEDIUM_RISK | replay_percentile missing | Highest Danelfin (4.5) in top 20 |
| MTZ | MEDIUM_RISK | replay_percentile missing | Danelfin=4.5 |
| CRS | MEDIUM_RISK | replay_percentile missing | — |
| CMCO | MEDIUM_RISK | replay_percentile missing | Yahoo upside 65.3% |
| ANGO | MEDIUM_RISK | replay_percentile missing | Yahoo upside 54.1% |

**Scoring note on replay_pts=20:** All candidates receive `replay_pts=20` (the "replay-supported, no percentile available" tier). If replay percentile became available, top-quartile candidates could score up to `replay_pts=25`, potentially reordering ranks within the cluster. This is documented as a future optimization path, not an active defect.

---

## 6. AEIS Postmortem Validation

See [aeis_postmortem_validation.md](aeis_postmortem_validation.md) for the complete postmortem. Summary:

| Check | Result |
|-------|:------:|
| AEIS `ess_score_text` = BEARISH | ✅ PASS |
| AEIS `composite_score` = 3.055556 | ✅ PASS |
| AEIS UCF = DEPLOYMENT_CANDIDATE | ✅ PASS |
| AEIS absent from deployment queue | ✅ PASS |
| AEIS absent from deployment plan | ✅ PASS |

**Prior artifacts (PAR-20260531-F794D952)** retain the pre-fix blank ESS state. This is expected behavior — historical PAR artifacts are immutable. All runs generated after REBUILD-20260531-FIX reflect the corrected data.

---

## 7. Acceptance Criteria

| # | Criterion | Status |
|---|-----------|:------:|
| 1 | Top 20 deployment candidates fully audited | ✅ |
| 2 | All signal gaps identified | ✅ replay_percentile gap identified for all 20 |
| 3 | All stale signals identified | ✅ No stale signals found |
| 4 | All cross-artifact inconsistencies identified | ✅ 0 inconsistencies found |
| 5 | AEIS remediation validated | ✅ All 5 checks pass |
| 6 | Readiness for Yahoo/Fidelity documented | ✅ See yahoo_fidelity_readiness_matrix.md |
| 7 | No code changes | ✅ Audit only |
| 8 | No ranking changes | ✅ |
| 9 | No scoring changes | ✅ |
