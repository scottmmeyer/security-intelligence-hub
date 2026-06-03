# Phase 7.4B — Replay Coverage Expansion Analysis

**Analysis Run:** `PAR-20260530-3A136D4F`  
**Date:** 2026-05-30  
**Gap candidates identified:** 9  
**Current replay coverage:** 21 holdings · $180,132 · 37.9% of portfolio  

> Analysis only. No replay changes. No scoring changes. No portfolio recommendation changes.

---

## Executive Summary

**9 holdings** meet the signal and quality threshold for HIGH_CONVICTION_RETAIN classification but are blocked solely by `replay_supported=False`.

**Root cause:** `_load_replay_evidence()` in `src/portfolio/recommendations.py` contains a filter `filter_industry != 'ALL'` that silently discards all industry-specific replay selections from `replay_inputs.csv`. 8 of 9 gap symbols ARE selected in their industry-specific replays (TECHNOLOGY, HEALTHCARE, FINANCIAL SERVICES, BASIC MATERIALS) but the filter prevents `replay_supported=True` from being assigned to their overlays.

**Impact if resolved:**
- Replay-supported portfolio weight: 37.9% → 45.7% (+7.8pp)
- Replay-supported portfolio value: $180,132 → $217,250 (+$37,118)
- 9 TGC holdings become eligible for HIGH_CONVICTION_ANCHOR reclassification

---

## Step 1 — Replay Gap Holdings

Holdings with `signal=BULLISH`, `composite>=4.0`, `STI=TACTICAL_GROWTH_CANDIDATE`, `replay_supported=False`.

| Symbol | Weight | Composite | ESS | Zacks | STI | Asset Class | MCap | Replay |
|---|---|---|---|---|---|---|---|---|
| `CIEN` | 1.20% | 4.57 | — | 5.0 | TGC | EQUITIES | MID | False |
| `CAH` | 1.04% | 4.56 | VERY_BULLISH | 4.0 | TGC | EQUITIES | MID | False |
| `PCB` | 0.94% | 4.28 | VERY_BULLISH | 3.0 | TGC | EQUITIES | MICRO | False |
| `AVT` | 0.91% | 4.50 | VERY_BULLISH | 4.0 | TGC | EQUITIES | SMALL | False |
| `ATLC` | 0.90% | 4.78 | VERY_BULLISH | 5.0 | TGC | EQUITIES | MICRO | False |
| `NUE` | 0.79% | 4.29 | — | 5.0 | TGC | EQUITIES | MID | False |
| `PRG` | 0.78% | 4.72 | VERY_BULLISH | 5.0 | TGC | EQUITIES | MICRO | False |
| `CBOE` | 0.69% | 4.11 | VERY_BULLISH | 3.0 | TGC | EQUITIES | MID | False |
| `BSVN` | 0.56% | 4.00 | — | 4.0 | TGC | EQUITIES | MICRO | False |

**TGC = TACTICAL_GROWTH_CANDIDATE**  
ESS = Fidelity Equity Summary Score  
All symbols are actively held, non-cash, non-ETF equities.

**Why this matters:** `HIGH_CONVICTION_RETAIN` classification in `_classify_holding()` (src/portfolio/trim_intelligence.py) requires `signal=BULLISH AND replay_ok=True AND thematic_redundancy<35 AND trim_score<30`. All 9 symbols meet the signal and composite criteria but `replay_ok=False` prevents the classification, which in turn prevents HIGH_CONVICTION_ANCHOR assignment in `build_strategic_profiles()`.

---

## Step 2 — Root Cause Analysis

### Root Cause Taxonomy

| Code | Description |
|---|---|
| A | No replay generated for the symbol's category |
| B | Replay exists for category, but symbol was not selected in top-N |
| C | Symbol excluded from replay universe |
| D | Missing/stale signal data at replay time |
| E | Filter mismatch — industry-specific replay ignored by overlay pipeline |
| F | Symbol mapping issue |
| G | Other |

### Per-Symbol Root Cause

| Symbol | MCap | Industry | Code | Explanation |
|---|---|---|---|---|
| `CIEN` | MID | TECHNOLOGY | **E** | Industry-specific replay ignored by `_load_replay_evidence()` filter |
| `CAH` | MID | HEALTHCARE | **E** | Industry-specific replay ignored by `_load_replay_evidence()` filter |
| `PCB` | MICRO | FINANCIAL SERVICES | **E** | Industry-specific replay ignored by `_load_replay_evidence()` filter |
| `AVT` | SMALL | TECHNOLOGY | **E** | Industry-specific replay ignored by `_load_replay_evidence()` filter |
| `ATLC` | MICRO | FINANCIAL SERVICES | **E** | Industry-specific replay ignored by `_load_replay_evidence()` filter |
| `NUE` | MID | BASIC MATERIALS | **E** | Industry-specific replay ignored by `_load_replay_evidence()` filter |
| `PRG` | MICRO | INDUSTRIALS | **B** | Replay exists for category; symbol ranked below top-N |
| `CBOE` | MID | FINANCIAL SERVICES | **E** | Industry-specific replay ignored by `_load_replay_evidence()` filter |
| `BSVN` | MICRO | FINANCIAL SERVICES | **E** | Industry-specific replay ignored by `_load_replay_evidence()` filter |

### Root Cause E — Detailed Explanation (8 symbols)

`_load_replay_evidence()` in `src/portfolio/recommendations.py`, lines 57–73, loads replay selections from `replay_inputs.csv` with this filter:

```python
if row.get('filter_industry', '').upper() != 'ALL':
    continue
```

This means only cross-sector `ALL` replays contribute to the `symbol_tier` dictionary used by `replay_supported=in_replay`. Industry-specific replay selections (TECHNOLOGY, HEALTHCARE, FINANCIAL SERVICES, etc.) are silently discarded.

**Evidence — industry-specific replay selections for gap symbols:**

| Symbol | Category | Replay Selection | Replay ID (truncated) |
|---|---|---|---|
| `CIEN` | US/MID/TECHNOLOGY | Selected (top-N) | `REPLAY-2025-05-14-TO-2026-05-14-US-MID-TECHNOLOGY-TOP20...` |
| `AVT` | US/SMALL/TECHNOLOGY | Selected (top-N) | `REPLAY-2025-05-14-TO-2026-05-14-US-SMALL-TECHNOLOGY-TOP...` |
| `CAH` | US/MID/HEALTHCARE | Selected (top-N) | `REPLAY-2025-05-14-TO-2026-05-14-US-MID-HEALTHCARE-TOP20...` |
| `CBOE` | US/MID/FINANCIAL SERVICES | Selected (top-N) | `REPLAY-2025-05-14-TO-2026-05-14-US-MID-FINANCIAL_SERVIC...` |
| `PCB` | US/MICRO/FINANCIAL SERVICES | Selected (top-N) | `REPLAY-2025-05-14-TO-2026-05-14-US-MICRO-FINANCIAL_SERV...` |
| `ATLC` | US/MICRO/FINANCIAL SERVICES | Selected (top-N) | `REPLAY-2025-05-14-TO-2026-05-14-US-MICRO-FINANCIAL_SERV...` |
| `BSVN` | US/MICRO/FINANCIAL SERVICES | Selected (top-N) | `REPLAY-2025-05-14-TO-2026-05-14-US-MICRO-FINANCIAL_SERV...` |
| `NUE` | US/MID/BASIC MATERIALS | Selected (top-N) | `REPLAY-2025-05-14-TO-2026-05-14-US-MID-BASIC_MATERIALS-...` |

These 8 symbols ARE in `replay_inputs.csv` selections, but the pipeline never reads their rows due to the `filter_industry != 'ALL'` guard.

### Root Cause B — PRG Detailed Explanation

PRG (`MICRO/US/INDUSTRIALS`, composite=4.72) has no industry-specific replay selection. The MICRO/US/INDUSTRIALS replay was generated and is `AVAILABLE`, but PRG did not rank in the top-N composite score at the replay snapshot date.

**MICRO/US/INDUSTRIALS top-20 selections:** `ATRO`, `CMCO`, `GIC`, `KFY`, `PBI`, `PKOH`, `RCMT`, `RLGT`, `VVX`, `ARCB`, `BBSI`, `BRC`, `CECO`, `CIX`, `CMRE`, `CRAI`, `CVLG`, `DLX`, `EBF`, `EML`

PRG is not among these symbols. Its composite score at the replay snapshot date was below the top-N threshold for this category.

**Path to remediation:** PRG needs to rank in the top-N for its category in a future replay run with current composite data.

---

## Step 3 — Replay Coverage Impact Estimate

### Current Replay Metrics

| Metric | Current |
|---|---|
| Replay-supported holdings count | 21 |
| Replay-supported portfolio value | $180,132 |
| Replay-supported weight | 37.89% |
| Total portfolio value | $473,913 |

### Per-Symbol Impact (cumulative, if resolved in composite-descending order)

| Symbol | Weight | MV | Replay MV Gain | Cumulative Replay MV | Cumulative Weight | % of Total |
|---|---|---|---|---|---|---|
| `ATLC` | 0.90% | $4,280 | +$4,280 | $184,412 | 38.79% | 38.9% |
| `PRG` | 0.78% | $3,708 | +$3,708 | $188,121 | 39.57% | 39.7% |
| `CIEN` | 1.20% | $5,703 | +$5,703 | $193,823 | 40.77% | 40.9% |
| `CAH` | 1.04% | $4,922 | +$4,922 | $198,745 | 41.80% | 41.9% |
| `AVT` | 0.91% | $4,340 | +$4,340 | $203,085 | 42.72% | 42.9% |
| `NUE` | 0.79% | $3,758 | +$3,758 | $206,843 | 43.51% | 43.6% |
| `PCB` | 0.94% | $4,451 | +$4,451 | $211,293 | 44.44% | 44.6% |
| `CBOE` | 0.69% | $3,298 | +$3,298 | $214,592 | 45.14% | 45.3% |
| `BSVN` | 0.56% | $2,659 | +$2,659 | $217,250 | 45.70% | 45.8% |

**Projected if all 9 gap symbols resolved:**
- Replay-supported holdings: 21 → 30
- Replay-supported value: $180,132 → $217,250
- Replay-supported weight: 37.9% → 45.7% (+7.8 percentage points)
- Coverage improvement: 38.0% → 45.8%

### HCA Upgrade Potential

If `replay_supported` becomes True for these holdings, they become eligible for `HIGH_CONVICTION_RETAIN` classification, which maps to `HIGH_CONVICTION_ANCHOR` (HCA) in `build_strategic_profiles()`. Additional criteria required:

| Criterion | Threshold | Notes |
|---|---|---|
| signal | BULLISH | ✓ Met by all 9 gap symbols |
| replay_ok | True | ✗ Currently blocking all 9 |
| thematic_redundancy | < 35 | Not validated in this analysis — run-time check |
| trim_score | < 30 | Not validated in this analysis — run-time check |

All 9 symbols have BULLISH signals and composites ≥ 4.0. Whether `thematic_redundancy < 35` and `trim_score < 30` are met depends on portfolio-state calculations at run time.

---

## Step 4 — Replay Readiness Matrix

Ranked by: portfolio value impact · composite quality · remediation ease.

| Rank | Symbol | Weight | MV | Composite | ESS | Zacks | MCap | Industry | Gap Code | Gap Reason | Upgrade Potential | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `CIEN` | 1.20% | $5,703 | 4.57 | — | 5.0 | MID | TECHNOLOGY | **E** | Filter mismatch (industry-specific replay ignored) | HCA candidate | High — filter change |
| 2 | `CAH` | 1.04% | $4,922 | 4.56 | VERY_BULLISH | 4.0 | MID | HEALTHCARE | **E** | Filter mismatch (industry-specific replay ignored) | HCA candidate | High — filter change |
| 3 | `PCB` | 0.94% | $4,451 | 4.28 | VERY_BULLISH | 3.0 | MICRO | FINANCIAL SERVICES | **E** | Filter mismatch (industry-specific replay ignored) | HCA candidate | High — filter change |
| 4 | `AVT` | 0.91% | $4,340 | 4.50 | VERY_BULLISH | 4.0 | SMALL | TECHNOLOGY | **E** | Filter mismatch (industry-specific replay ignored) | HCA candidate | High — filter change |
| 5 | `ATLC` | 0.90% | $4,280 | 4.78 | VERY_BULLISH | 5.0 | MICRO | FINANCIAL SERVICES | **E** | Filter mismatch (industry-specific replay ignored) | HCA candidate | High — filter change |
| 6 | `NUE` | 0.79% | $3,758 | 4.29 | — | 5.0 | MID | BASIC MATERIALS | **E** | Filter mismatch (industry-specific replay ignored) | HCA candidate | High — filter change |
| 7 | `PRG` | 0.78% | $3,708 | 4.72 | VERY_BULLISH | 5.0 | MICRO | INDUSTRIALS | **B** | Replay exists; not selected top-N | HCA candidate | Medium — need selection |
| 8 | `CBOE` | 0.69% | $3,298 | 4.11 | VERY_BULLISH | 3.0 | MID | FINANCIAL SERVICES | **E** | Filter mismatch (industry-specific replay ignored) | HCA candidate | High — filter change |
| 9 | `BSVN` | 0.56% | $2,659 | 4.00 | — | 4.0 | MICRO | FINANCIAL SERVICES | **E** | Filter mismatch (industry-specific replay ignored) | HCA candidate | High — filter change |

---

## Step 5 — Replay Universe Diagnostic

| Symbol | In AU? | AU replay_eligible | Category Replay Generated | Category Status | In ANY replay selection? | In ALL-industry replay? | Blocking Factor |
|---|---|---|---|---|---|---|---|
| `CIEN` | ✓ | True | true | AVAILABLE | ✓ | ✗ | `_load_replay_evidence()` filter_industry='ALL' only |
| `CAH` | ✓ | True | true | AVAILABLE | ✓ | ✗ | `_load_replay_evidence()` filter_industry='ALL' only |
| `PCB` | ✓ | True | true | AVAILABLE | ✓ | ✗ | `_load_replay_evidence()` filter_industry='ALL' only |
| `AVT` | ✓ | True | true | AVAILABLE | ✓ | ✗ | `_load_replay_evidence()` filter_industry='ALL' only |
| `ATLC` | ✓ | True | true | AVAILABLE | ✓ | ✗ | `_load_replay_evidence()` filter_industry='ALL' only |
| `NUE` | ✓ | True | true | AVAILABLE | ✓ | ✗ | `_load_replay_evidence()` filter_industry='ALL' only |
| `PRG` | ✓ | True | true | AVAILABLE | ✗ | ✗ | Not in top-N at composite snapshot date |
| `CBOE` | ✓ | True | true | AVAILABLE | ✓ | ✗ | `_load_replay_evidence()` filter_industry='ALL' only |
| `BSVN` | ✓ | True | true | AVAILABLE | ✓ | ✗ | `_load_replay_evidence()` filter_industry='ALL' only |

**Key:**
- **In AU?** — symbol present in `data/current/analytical_universe.csv`
- **AU replay_eligible** — the `replay_eligible` flag in the AU row
- **Category Replay Generated** — `replay_availability.csv` for symbol's geo/mcap/industry
- **In ANY replay selection?** — appears in any row of `replay_inputs.csv` selected_symbols
- **In ALL-industry replay?** — appears in `replay_inputs.csv` rows where filter_industry='ALL'

---

## Step 6 — Remediation Options

> Analysis only. No changes recommended without explicit authorization.

### Option A — Fix the `_load_replay_evidence()` filter (Highest Impact, Low Risk)

**File:** `src/portfolio/recommendations.py` (~line 57)

**Current:**
```python
if row.get('filter_industry', '').upper() != 'ALL':
    continue
```

**Change would:**
- Remove the filter or change it to also accept industry-specific replays
- Immediately make 8 of 9 gap symbols replay-supported in the next overlay generation
- No replay re-runs needed — the data already exists in `replay_inputs.csv`
- Downstream: these 8 symbols would become eligible for HIGH_CONVICTION_RETAIN → HCA

**Coverage impact:** +7.03pp (8 symbols)

### Option B — Regenerate ALL-industry replays to include gap symbols (Medium Impact)

The current ALL-industry replays (batch 2026-05-20) selected different symbols than the industry-specific replays. Gap symbols like ATLC, CIEN, CAH, AVT have high composites but were outranked in their categories by symbols in the ALL replay.

**Change would:**
- Re-run ALL-industry replays with updated composite scores
- If gap symbols rank in top-N, they get picked up automatically
- Risk: changes which symbols appear in replay — affects scoring for ALL holdings

### Option C — Add industry-specific replay selection for PRG (Narrow Impact)

PRG needs to rank in top-N for MICRO/US/INDUSTRIALS in a replay run using current composite data. PRG's composite is 4.72 — it may qualify with fresh data.

**Change would:**
- Generate a new MICRO/US/INDUSTRIALS replay with 2026-05-30 composite snapshot
- If PRG ranks top-N, it enters replay_inputs.csv
- Still blocked by root cause E if Option A is not also applied

### Option D — Accept current coverage (analysis only, no action)

If the intent is that `replay_supported` should only be granted to symbols in the ALL-industry cross-sector top-N, then the 8 industry-specific symbols are intentionally excluded. This is a portfolio philosophy question: should industry-specific replay evidence count as replay support?

---

*Analysis only. No replay changes. No scoring changes. No portfolio recommendation changes.*
