# Replay Percentile Lineage Report — Phase 7.5I

**Date:** 2026-05-31  
**Reference Run:** PAR-20260529-BAF83F16  
**Audit Type:** Read-only. No code changes. No scoring changes.  
**Finding Status:** Root cause confirmed.

---

## Executive Summary

`replay_percentile` is **blank for all 20 top deployment candidates** because it was **never implemented**. The field is hardcoded to `None` in `build_security_overlays()`. No replay percentile data has ever been generated anywhere in the pipeline. The underlying data required to compute it does exist.

**Critical finding:** The deployment queue CW-DAS scoring does NOT use `replay_percentile` at any point — it uses a binary `replay_supported` gate only. **Deployment queue rankings are unaffected by this gap.** The flat `replay_pts=20.0` for all candidates is correct and by design.

---

## Step 1 — Replay Percentile Lineage Trace

### 1A. Where replay_percentile should originate

The `replay_percentile` field (type `Optional[float]`) is defined in `SecurityIntelligenceOverlay` and is documented as: *"From build_security_overlays (None if not available)."*

**Intended semantics:**  
A symbol's percentile rank within its replay selection universe — e.g., if a symbol was selected as rank #6 from a 611-symbol universe, its percentile is `(611−6+1)/611 × 100 = 99.2`.

### 1B. Lineage trace — stage by stage

| Stage | Artifact | Has percentile? | Notes |
|-------|----------|:---------------:|-------|
| Replay selection | `data/current/replay_inputs.csv` | ❌ No column | Contains `selected_symbols` (ordered pipe-list) + `top_n`. Selection rank is inferrable. |
| Replay performance | `data/current/replay_performance_series.csv` | ❌ No column | Aggregate cumulative return series. No per-symbol percentiles. |
| Replay evidence | `replay_evidence_summary.json` (257 files) | ❌ No column | Contains `full_universe_symbol_count` and aggregate strategy/benchmark returns. No symbol-level data. |
| Replay availability | `data/current/replay_availability.csv` | ❌ No column | Status index only. |
| Replay matrix | `data/current/replay_matrix.csv` | ❌ No column | Path index only. |
| Overlay builder | `build_security_overlays()` in `recommendations.py:212` | ❌ Hardcoded `None` | `replay_percentile=None` — comment: *"enriched if needed in future"* |
| Security overlays CSV | `PAR-20260529-BAF83F16/security_overlays.csv` | ❌ Blank | Column exists; all values empty |
| Deployment queue | `compute_cw_das()` in `deployment_queue.py:142` | ❌ Not a parameter | `replay_c = 20.0 if replay_supported else 0.0` — binary gate |
| UCF scoring | `unified_conviction.py:405–410` | ❌ Never populated | Code handles it: `if replay_percentile is not None → use it; else → 100.0` |
| Trim/retention scoring | `runner.py:193–198` | ❌ Never populated | Code handles it: `if pctile is None → replay_pts=5` |

**Conclusion:** `replay_percentile` traverses the full pipeline correctly and is consumed at three points — but it is set to `None` before entering any of them. The field was designed in Phase D/E and left as a future enrichment stub.

### 1C. Code Location of Hardcode

**File:** `src/portfolio/recommendations.py`  
**Function:** `build_security_overlays()`  
**Line 212:**
```python
overlays.append(SecurityIntelligenceOverlay(
    ...
    best_replay_return=None,    # enriched if needed in future
    replay_percentile=None,     # ← HARDCODED — never populated
    replay_supported=in_replay,
    ...
))
```

The `_load_replay_evidence()` function reads `replay_inputs.csv` to populate `symbol_tier` and `symbol_replay` (for the `replay_supported` flag), but does not compute any percentile value. There is no downstream function that enriches the overlay with a computed percentile.

---

## Step 2 — Data Existence Determination

| Hypothesis | Verdict |
|------------|:-------:|
| Percentile exists and is being dropped | ❌ False — not computed anywhere |
| Percentile never generated | ✅ True — never part of any pipeline artifact |
| Percentile generated but not persisted | ❌ False — not generated at all |
| Percentile persisted but not loaded | ❌ False — not persisted anywhere |

**Finding: Percentile never generated.** The stub was placed in `build_security_overlays()` and no follow-up implementation was done.

### 2A. Data available to compute it

Although `replay_percentile` was never generated, the underlying data exists to compute it:

| Data needed | Source | Available? |
|-------------|--------|:----------:|
| Symbol selection rank within top-N | Position index in `selected_symbols` field in `replay_inputs.csv` | ✅ Yes |
| Full universe size for the replay | `full_universe_symbol_count` in `replay_evidence_summary.json` | ✅ Yes (257 summary files) |
| Symbol → replay_id mapping | `replay_inputs.csv` (already read by `_load_replay_evidence()`) | ✅ Yes |

**Percentile formula:** `(universe_N − selection_rank + 1) / universe_N × 100`

---

## Step 3 — Top 20 Replay Lineage

All 20 top deployment candidates appear in at least one replay. `_load_replay_evidence()` confirms each symbol as `replay_supported=True` before entering the deployment queue.

### 3A. Top 20 replay source mapping

| Rank | Symbol | Replay ID | Geo | Cap | Industry | Selection Rank | Universe N | Computed Pctile | Tier |
|:----:|--------|-----------|:---:|:---:|:--------:|:--------------:|:----------:|:---------------:|:----:|
| 1 | VRT | REPLAY-2026-05-20…US-LARGE-ALL-TOP20 | US | LARGE | ALL | 12 | 120 | 90.8% | TOP_QUINTILE |
| 2 | ARW | REPLAY-2026-05-20…US-SMALL-ALL-TOP20 | US | SMALL | ALL | 6 | 611 | 99.2% | TOP_QUINTILE |
| 3 | SNX | REPLAY-2026-05-20…US-MID-ALL-TOP20 | US | MID | ALL | 12 | 380 | 97.1% | TOP_QUINTILE |
| 4 | ATLC | REPLAY-2025-05-14…US-MICRO-FINANCIAL | US | MICRO | FINANCIAL SERVICES | 1 | 182 | 100.0% | TOP_QUINTILE |
| 5 | PSX | REPLAY-2026-05-20…US-MID-ALL-TOP20 | US | MID | ALL | 14 | 380 | 96.6% | TOP_QUINTILE |
| 6 | CBOE | REPLAY-2025-05-14…US-MID-FINANCIAL | US | MID | FINANCIAL SERVICES | 2 | 66 | 98.5% | TOP_QUINTILE |
| 7 | AVT | REPLAY-2025-05-14…US-SMALL-TECHNOLOGY | US | SMALL | TECHNOLOGY | 2 | 94 | 98.9% | TOP_QUINTILE |
| 8 | LRCX | REPLAY-2026-05-20…US-LARGE-ALL-TOP20 | US | LARGE | ALL | 14 | 120 | 89.2% | TOP_QUINTILE |
| 9 | CAH | REPLAY-2025-05-14…US-MID-HEALTHCARE | US | MID | HEALTHCARE | 1 | 45 | 100.0% | TOP_QUINTILE |
| 10 | DELL | REPLAY-2026-05-20…US-LARGE-ALL-TOP20 | US | LARGE | ALL | 13 | 120 | 90.0% | TOP_QUINTILE |
| 11 | SANM | REPLAY-2026-05-20…US-SMALL-ALL-TOP20 | US | SMALL | ALL | 14 | 611 | 97.9% | TOP_QUINTILE |
| 12 | PCB | REPLAY-2025-05-14…US-MICRO-FINANCIAL | US | MICRO | FINANCIAL SERVICES | 12 | 182 | 94.0% | TOP_QUINTILE |
| 13 | CIEN | REPLAY-2025-05-14…US-MID-TECHNOLOGY | US | MID | TECHNOLOGY | 1 | 77 | 100.0% | TOP_QUINTILE |
| 14 | NUE | REPLAY-2025-05-14…US-MID-BASIC_MATERIALS | US | MID | BASIC MATERIALS | 8 | 31 | 77.4% | TOP_2Q |
| 15 | GFF | REPLAY-2025-05-14…US-SMALL-INDUSTRIALS | US | SMALL | INDUSTRIALS | 15 | 110 | 87.3% | TOP_QUINTILE |
| 16 | ALNT | REPLAY-2025-05-14…US-MICRO-TECHNOLOGY | US | MICRO | TECHNOLOGY | 1 | 166 | 100.0% | TOP_QUINTILE |
| 17 | MTZ | REPLAY-2025-05-14…US-MID-INDUSTRIALS | US | MID | INDUSTRIALS | 20 | 80 | 76.2% | TOP_2Q |
| 18 | CRS | REPLAY-2025-05-14…US-MID-INDUSTRIALS | US | MID | INDUSTRIALS | 9 | 80 | 90.0% | TOP_QUINTILE |
| 19 | CMCO | REPLAY-2025-05-14…US-MICRO-INDUSTRIALS | US | MICRO | INDUSTRIALS | 2 | 158 | 99.4% | TOP_QUINTILE |
| 20 | ANGO | REPLAY-2025-05-14…US-MICRO-HEALTHCARE | US | MICRO | HEALTHCARE | 12 | 239 | 95.4% | TOP_QUINTILE |

**Coverage summary:**
- 18/20 candidates: TOP_QUINTILE (≥80th percentile)
- 2/20 candidates: TOP_2Q (60–79th percentile): NUE (77.4%), MTZ (76.2%)
- 4 candidates at rank #1 (100th percentile): ATLC, CAH, CIEN, ALNT
- 0 candidates below 75th percentile

### 3B. Why replay_supported=True but replay_percentile=(blank)

`_load_replay_evidence()` correctly identifies all 20 as replay-supported by reading the `selected_symbols` field in `replay_inputs.csv`. This sets `symbol_tier[sym]` and `symbol_replay[sym]`. The function returns this data to `build_security_overlays()`.

`build_security_overlays()` uses this to set `replay_supported=True` — but then hardcodes `replay_percentile=None`. It does not call any function to compute a rank or percentile from the selection position. The enrichment step was never built.

---

## Step 4 — Impact Model

### 4A. Deployment Queue (CW-DAS) — ZERO IMPACT

`compute_cw_das()` signature:
```python
def compute_cw_das(
    symbol, composite, pct, tier, replay_supported, ess_text, signal_direction, in_ow_node
) -> tuple[float, CwDasBreakdown]:
```

**`replay_percentile` is not a parameter.** The deployment queue replay component is a pure binary gate:

```python
# deployment_queue.py:142
replay_c = 20.0 if replay_supported else 0.0
```

All 20 candidates have `replay_supported=True` → `replay_c=20.0`. This is a fixed value regardless of any percentile. The flat `replay_pts=20.0` observed in the audit is **correct by design** — not a defect.

**Deployment queue rank changes from percentile: 0 candidates affected.**

### 4B. UCF Scoring — Marginal Impact

The UCF formula uses `replay_percentile` as the replay component:

```python
# unified_conviction.py:404–410
if replay_supported:
    if replay_percentile is not None and not math.isnan(replay_percentile):
        replay_component = float(replay_percentile)
    else:
        replay_component = 100.0   # ← current fallback for all 20
```

**Current state:** `replay_component = 100.0` for all 20 (maximum possible).  
**With percentile populated:** `replay_component = actual_percentile` (76.2–100.0 range).

UCF delta = `(100.0 − percentile) × 0.20`:

| Symbol | Current UCF | Percentile | UCF Delta | UCF With Pctile |
|--------|:-----------:|:----------:|:---------:|:---------------:|
| MTZ | 87.26 | 76.2% | −4.76 | 82.50 |
| NUE | 88.32 | 77.4% | −4.52 | 83.80 |
| GFF | 87.36 | 87.3% | −2.54 | 84.82 |
| LRCX | 90.37 | 89.2% | −2.16 | 88.21 |
| DELL | 89.41 | 90.0% | −2.00 | 87.41 |
| CRS | 87.17 | 90.0% | −2.00 | 85.17 |
| VRT | 91.17 | 90.8% | −1.84 | 89.33 |
| PCB | 89.38 | 94.0% | −1.20 | 88.18 |
| ANGO | 86.57 | 95.4% | −0.92 | 85.65 |
| SNX | 92.19 | 97.1% | −0.58 | 91.61 |
| PSX | 92.05 | 96.6% | −0.68 | 91.37 |
| CBOE | 91.76 | 98.5% | −0.30 | 91.46 |
| SANM | 89.53 | 97.9% | −0.42 | 89.11 |
| AVT | 90.75 | 98.9% | −0.22 | 90.53 |
| ARW | 92.76 | 99.2% | −0.16 | 92.60 |
| CMCO | 86.94 | 99.4% | −0.12 | 86.82 |
| ATLC | 92.14 | 100.0% | 0.00 | 92.14 |
| CAH | 90.19 | 100.0% | 0.00 | 90.19 |
| CIEN | 88.67 | 100.0% | 0.00 | 88.67 |
| ALNT | 87.40 | 100.0% | 0.00 | 87.40 |

**UCF label change risk:** All candidates would remain within HIGH_CONVICTION_ANCHOR or CORE_CONVICTION_LEADER range. The largest drop (MTZ: −4.76 pts) still leaves UCF at 82.50 — well within the HCA band.

### 4C. Trim Priority Score — Minimal Impact

`runner.py` uses `replay_percentile` in retention priority scoring (trim intelligence):

```python
if replay_ok and replay_pctile is not None and replay_pctile >= 75:
    replay_pts = 0   # ← ALL 20 would land here (all ≥76.2%)
else (replay_ok, no pctile):
    replay_pts = 5   # ← current state
```

**Current:** `replay_pts = 5` for all 20 (replay-supported, no percentile)  
**With percentile:** `replay_pts = 0` for all 20 (all ≥76.2nd pctile → `pctile >= 75`)

Delta of −5 trim pressure points per candidate. This modestly reduces trim pressure for all 20, which is directionally correct (top-quality replay candidates should have low trim pressure). No candidate would be reclassified for trimming.

### 4D. Ranking Impact Summary

| Context | Current State | With Percentile | Rankings Change |
|---------|:-------------:|:---------------:|:---------------:|
| Deployment queue (CW-DAS) | replay_c=20.0 (binary) | replay_c=20.0 (unchanged) | **NONE** |
| UCF score | replay_component=100.0 | 76.2–100.0 | **NONE** (labels unchanged) |
| Trim priority score | replay_pts=5 | replay_pts=0 | **NONE** (direction correct) |

**No ranking changes in any context.** The computed percentiles for all 20 candidates are sufficiently high (76–100%) that neither deployment queue nor UCF label changes would occur.

---

## Step 5 — Design Options

### Option A: Recover Existing Percentile Data

**Verdict: NOT VIABLE.**

No `replay_percentile` data was ever generated in any artifact. The field was designed but left as a stub. There is nothing to recover.

### Option B: Generate Percentile from Current Replay Outputs

**Verdict: VIABLE. Low complexity.**

The data required exists today:
1. `replay_inputs.csv` — `selected_symbols` field is an ordered list; position index = selection rank
2. `replay_evidence_summary.json` — `full_universe_symbol_count` = universe size

**Computation:** `percentile = (universe_N − selection_rank + 1) / universe_N × 100`

**Implementation scope (code change, out of audit scope):**
- Modify `_load_replay_evidence()` to also return `symbol_percentile: dict[str, float]`
- Modify `build_security_overlays()` to populate `replay_percentile=symbol_percentile.get(sym)`
- **No changes** to `compute_cw_das()`, UCF formula, or scoring constants

**Impact if implemented:**
- All 20 candidates would have correct percentiles (76.2–100.0%)
- MEDIUM_RISK classification resolved (no missing signals)
- Deployment queue ranks: unchanged
- UCF scores: −0 to −4.76 pts (all within same label tier)
- Trim pressure: −5 pts per candidate (directionally correct)

### Option C: Retire the Percentile Concept

**Verdict: VALID. Cleanest option.**

The deployment queue — the primary ranking mechanism — does not use `replay_percentile`. The UCF scoring currently maxes the replay component at 100.0 (correct behavior given 76–100% actual percentiles). Populating percentile would reduce UCF scores for candidates that legitimately earned top-quartile replay selection.

Retiring would:
- Remove `replay_percentile` from `SecurityIntelligenceOverlay` schema
- Remove `replay_percentile` from UCF `compute_ucf_score()` parameter list  
- Simplify UCF formula: `replay_component = 100.0 if replay_supported else 0.0` (current fallback becomes the formula)
- Simplify trim scoring: remove percentile branches from `runner.py`
- Eliminate misleading MEDIUM_RISK risk classification for all replay-supported holdings

---

## Recommendation: Option B (Generate)

**Rationale:**

1. The data exists. The computation is trivial (one expression per symbol).
2. Deployment queue rankings are unaffected — there is no risk.
3. Option C (Retire) would permanently remove a designed enrichment point that, while currently trivial, could become meaningful if the current batch has more variability in future pipeline runs (e.g., symbols near the top-N cutoff line with percentiles in the 40–70% range).
4. The MEDIUM_RISK classification for all 20 candidates is technically correct (missing signal) but misleading. Populating percentile resolves it without requiring any schema changes.
5. Trim scoring improvement is minimal but directionally correct.

**Prerequisite:** Verify the interpretation of `selected_symbols` ordering in `replay_inputs.csv` is rank-ordered by composite score (highest first). This was the assumed semantics for `TOP_N_COMPOSITE_AT_START` selection method. If the ordering is not guaranteed, percentile computation would require reading from the performance series.

**See [replay_percentile_recommendation.md](replay_percentile_recommendation.md) for implementation design.**

---

## Acceptance Criteria Status

| # | Criterion | Status |
|---|-----------|:------:|
| 1 | Root cause identified | ✅ `replay_percentile=None` hardcoded in `build_security_overlays()` line 212 |
| 2 | Data existence confirmed | ✅ Never generated; computable from existing `replay_inputs.csv` + evidence summaries |
| 3 | Top-20 replay lineage documented | ✅ All 20 traced to specific replay_ids with selection rank and universe size |
| 4 | Ranking impact estimated | ✅ ZERO impact on deployment queue; UCF label changes: none |
| 5 | Recommended path documented | ✅ Option B (Generate) |
| 6 | No code changes | ✅ Audit only |
| 7 | No scoring changes | ✅ |
