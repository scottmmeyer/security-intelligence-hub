# AI-006C — Explainable Signal Decomposition & Recommendation Transparency

**Status:** COMPLETE  
**Date:** 2026-06-16  
**Scope:** Display-only UI enhancement. No scoring, ranking, or recommendation changes.

---

## Executive Summary

AI-006C adds a **Signal Intelligence panel** to every holding row in the Portfolio Alignment drilldown tables. The panel is collapsed by default and expands on click to show four sections:

1. **Recommendation Driver Summary** — Bullish / Bearish / Neutral evidence drivers
2. **CW-DAS Score Decomposition** — Visual breakdown of the 7 score components
3. **UCF Classification Reasoning** — Why the conviction label was assigned
4. **Signal Conflict Analysis** — Explicit explanation of source disagreement

No backend changes. No new API endpoints. All data sourced from existing analysis artifacts already in memory.

---

## Validation Questions

| Question | Answer |
|----------|--------|
| Q1: Can an operator determine why ESS is bullish or bearish? | **YES** — Driver Summary shows ESS direction + native value; Conflict Analysis shows ESS vs other sources |
| Q2: Can an operator determine why CW-DAS produced its score? | **YES** — CW-DAS Decomposition shows all 7 components with bar visualization |
| Q3: Can an operator determine why Replay produced its percentile? | **YES** — Replay is shown in Driver Summary with percentile and strength; Replay component shown in CW-DAS breakdown |
| Q4: Can an operator determine why UCF assigned its label? | **YES** — UCF section shows label, score, rank, all source signals, deployment status, and conflict flags |
| Q5: Can an operator understand the exact source of signal disagreement? | **YES** — Conflict Analysis shows each provider's direction and names the conflict source |
| Q6: Were any scoring algorithms changed? | **NO** |
| Q7: Were any rankings changed? | **NO** |
| Q8: Were any recommendations changed? | **NO** |
| Q9: Were any governance rules changed? | **NO** |

---

## Architecture

### Data Sources (All Pre-Existing)

| Panel Section | Data Source | Location |
|---------------|-------------|----------|
| CW-DAS Decomposition | `deployment_queue.json` → `queue[*].score_breakdown` | Loaded in `_lastAnalysisData.deployment_queue.queue` |
| UCF Classification | `ucf_verdicts.json` → `ucf_verdicts_by_symbol[symbol]` | Loaded in `_lastAnalysisData.ucf_verdicts_by_symbol` |
| Driver Summary | `security_overlays.csv` fields (ess_score_text, danelfin_score, zacks_rating, composite_score, replay_percentile) | Loaded in `h` (holding row object) |
| Analyst Consensus | `analyst_consensus.json` → by symbol | `_lastAnalysisData.analyst_consensus_by_symbol` |
| Signal Matrix | `fidelity_signals_by_symbol` → `consensus_matrix` | `_lastAnalysisData.fidelity_signals_by_symbol` |
| Conflict Analysis | Derived from above sources | Computed in JS |

### No New API Endpoints Required

All data is already present in the `_lastAnalysisData` object populated by `GET /api/portfolio/runs/{id}`. The `load_analysis_run()` function already loads all required artifacts.

### Implementation Location

**File modified:** `ui/portfolio_alignment/app.js`  
**New function:** `_signalIntelligencePanelHtml(sym, ov, ac, fs)` — ~220 lines  
**Hook location:** `renderHoldingsTable()` — appended to the RPS expand row

**File modified:** `ui/portfolio_alignment/index.html`  
**CSS added:** `.si-panel`, `.si-bd-*`, `.si-driver-*`, `.si-conflict-*`, `.si-badge-*` — ~130 lines  
**Cache version:** v25 → v26

---

## Panel Sections Detail

### Section A: Recommendation Driver Summary

Categorizes all available signals into three columns:

**Bullish Evidence** (green column)
- ESS: BULLISH / VERY_BULLISH signals
- Replay percentile ≥ 60th
- Composite score ≥ 3.5
- Danelfin ≥ 3.5
- Zacks ≤ 2.0 (Buy / Strong Buy)
- Analyst consensus BUY/STRONG_BUY
- Positive fundamental modifier

**Bearish Evidence** (red column)
- ESS: BEARISH / VERY_BEARISH signals
- Composite score ≤ 2.5
- Danelfin ≤ 2.5
- Zacks ≥ 4.0 (Sell)
- Analyst consensus SELL
- Negative fundamental modifier
- Deployment blocked

**Neutral** (gray column)
- Signals in the neutral range
- Holds/neutral consensus

Each driver shows: signal name + native value, STRONG/MODERATE/WEAK strength.

### Section B: CW-DAS Score Decomposition

Visual bar chart showing all 7 score components:

| Component | Max | Description |
|-----------|-----|-------------|
| Signal | /30 | ESS + Danelfin + Zacks weighted direction |
| Replay | /20 | Replay backing strength and percentile |
| Conviction | /35 | UCF tier × multiplier (CCL 1.75×, HCA 1.25×) |
| Sizing | /8 | Headroom to warning threshold |
| Momentum | /10 | ESS momentum direction |
| Fund. Mod | ±5 | Fundamental consistency bonus/penalty |
| Redund. Pen | deduction | Overweight allocation node penalty |
| Conc. Pen | deduction | Concentration penalty |

Also shows: thesis_integrity badge, fundamental_consistency badge, CW-DAS notes string.

### Section C: UCF Classification Reasoning

Shows:
- UCF label with color-coding
- UCF score (0–100) and portfolio rank
- Deployment eligibility / block reason
- Source signals table: composite_score, signal_direction, replay support, CW-DAS score/rank, trim pressure
- Signal summary string
- Conflict flags (advisory badges)

### Section D: Signal Conflict Analysis

Triggered when `consensus_matrix.classification = MAJOR_DIVERGENCE` or `PARTIAL_ALIGNMENT`, or when UCF conflict_flags are present.

Shows:
- Grid of all 4 providers (ESS, Danelfin, Zacks, Yahoo) with native value + direction chip
- Plain-English conflict source explanation

---

## MSFT Example Output

With current data (2026-06-16):

**Driver Summary:**
- Bullish: ESS VERY_BULLISH, Replay 88th percentile (STRONG), Composite 4.06 (MODERATE), Analyst Consensus STRONG_BUY +43.8% (STRONG)
- Bearish: (none — MSFT's ESS is now VERY_BULLISH, not SELL as in the background)
- Neutral: Danelfin 1.5/5, Zacks 3.0 (Hold)

**CW-DAS (77.09 total):**
- Signal: 24.3/30, Replay: 20/20, Conviction: 28/35, Sizing: 6.8/8, Momentum: 10/10, Redundancy: −15 (OW node penalty)

**UCF:** HIGH_CONVICTION_ANCHOR, Score 85.3, Rank #18, Deployment Blocked (OW node)

---

## Success Criteria Verification

An operator opening MSFT, VRT, DELL, LRCX, or SANM can now answer:

| Question | How answered |
|----------|-------------|
| Why is SIH bullish? | Driver Summary — Bullish Evidence column |
| Why is SIH bearish? | Driver Summary — Bearish Evidence column |
| Which signals agree? | Signal Agreement panel (existing) + Driver Summary |
| Which signals disagree? | Conflict Analysis section |
| What evidence is strongest? | STRONG/MODERATE/WEAK labels on each driver |
| What evidence is weakest? | Neutral column + low-strength labels |
| Why did the recommendation engine reach this conclusion? | UCF section + CW-DAS decomposition |

All without reading source code or external reports.
