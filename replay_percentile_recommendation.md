# Replay Percentile Recommendation — Phase 7.5I

**Date:** 2026-05-31  
**Companion Report:** [replay_percentile_lineage_report.md](replay_percentile_lineage_report.md)  
**Recommendation:** Option B — Generate from existing data

---

## Decision Summary

| Option | Verdict | Rationale |
|--------|:-------:|-----------|
| A — Recover existing data | ❌ Not viable | No percentile was ever generated; nothing to recover |
| **B — Generate from current replay outputs** | ✅ **Recommended** | Data exists; low risk; minimal scope; no deployment queue impact |
| C — Retire percentile concept | ⚠️ Acceptable fallback | Valid if scoring team decides the concept adds no value going forward |

---

## 1. Problem Restatement

`replay_percentile` is blank for all deployment candidates because `build_security_overlays()` in `recommendations.py` hardcodes `replay_percentile=None` (line 212). This was a designed stub left for future enrichment.

**Critical constraint:** The deployment queue scorer (`compute_cw_das()`) does **not** use `replay_percentile`. The flat `replay_pts=20.0` for all replay-supported candidates is **correct and by design** — a binary gate. Implementing Option B does not change deployment queue rankings.

---

## 2. Option B — Implementation Design

### 2A. What to compute

For each symbol in a replay's `selected_symbols` list:

$$\text{replay\_percentile} = \frac{N - r + 1}{N} \times 100$$

Where:
- $N$ = `full_universe_symbol_count` from `replay_evidence_summary.json`
- $r$ = position of the symbol in `selected_symbols` (1-indexed)

**Example:**
- ARW: rank #6 in 611-symbol universe → $(611−6+1)/611 × 100 = 99.2$
- MTZ: rank #20 in 80-symbol universe → $(80−20+1)/80 × 100 = 76.2$

### 2B. Data sources

| Input | Source | Already loaded? |
|-------|--------|:---------------:|
| Symbol selection rank | `selected_symbols` field, `replay_inputs.csv` | ✅ Already read by `_load_replay_evidence()` |
| Universe size | `full_universe_symbol_count`, `replay_evidence_summary.json` | ❌ Not currently read |
| Symbol → replay_id | `symbol_replay` dict in `_load_replay_evidence()` | ✅ Already built |

### 2C. Files to change (2 functions only)

**Function 1: `_load_replay_evidence()` in `src/portfolio/recommendations.py`**

Add:
1. Load `full_universe_symbol_count` from each replay's `replay_evidence_summary.json`
2. Build `symbol_percentile: dict[str, float]` alongside `symbol_tier` and `symbol_replay`
3. Return `symbol_percentile` in the result dict

```python
# Pseudocode — not a code change (audit scope)
#
# While iterating replay_inputs.csv rows:
#   1. For each row, locate the replay_evidence_summary.json via replay_matrix.csv or path convention
#   2. Load full_universe_symbol_count from the summary
#   3. For each symbol in selected_symbols at index i:
#        rank = i + 1
#        percentile = (univ_n - rank + 1) / univ_n * 100
#        symbol_percentile[sym] = percentile  (first-seen wins, matching symbol_tier logic)
#
# Return: {"symbol_tier": ..., "symbol_replay": ..., "symbol_percentile": ..., ...}
```

**Function 2: `build_security_overlays()` in `src/portfolio/recommendations.py`**

Change line 212 from:
```python
replay_percentile=None,
```
To:
```python
replay_percentile=replay_ev.get("symbol_percentile", {}).get(sym),
```

**No other files change.** The three consumers of `replay_percentile` — UCF scoring, deployment queue, trim scoring — already handle `None` vs numeric correctly.

### 2D. Risks

| Risk | Likelihood | Mitigation |
|------|:----------:|-----------|
| `selected_symbols` is not rank-ordered | Low | `TOP_N_COMPOSITE_AT_START` implies rank order. Verify against replay selection code before implementing. |
| Evidence summary not found for a replay | Low | Fall back to `replay_percentile=None` (current behavior). |
| Universe size mismatch (partial coverage replay) | Low | Cross-check `full_universe_symbol_count` against `selected_symbols` count. Exclude partial replays from percentile computation if needed. |
| Deployment queue reordering | None | `compute_cw_das()` does not accept `replay_percentile`. Confirmed by code inspection. |

### 2E. Expected Outcome

After implementation:

| Metric | Before | After |
|--------|:------:|:-----:|
| Top-20 replay_percentile coverage | 0/20 (0%) | 20/20 (100%) |
| MEDIUM_RISK candidates (missing replay_pctile) | 20/20 | 0/20 |
| Deployment queue rank changes | — | 0 |
| UCF label changes | — | 0 (all ≥76% pctile) |
| UCF score delta range | — | −0 to −4.76 pts |
| Trim priority score delta | — | −5 pts per candidate (directionally correct) |

---

## 3. Option C — Retire Percentile Concept

If the scoring team determines that `replay_percentile` adds no differentiation value (given that all replay-supported candidates are already top-quintile), Option C is an acceptable alternative.

**What retirement means:**

| Component | Current behavior | Retired behavior |
|-----------|:----------------:|:----------------:|
| UCF `replay_component` | `100.0 if percentile is None` | `100.0 always` (simplify code) |
| Trim `replay_pts` | `5 if percentile is None and replay_ok` | `0 if replay_ok` (simplify) |
| Overlay schema | `replay_percentile: Optional[float]` | Remove field |
| MEDIUM_RISK classification | Triggered by missing pctile | Resolved (no longer a signal gap) |

**Retirement explicitly does NOT change:**
- Deployment queue CW-DAS formula (already binary gate)
- Which symbols enter the queue (replay_supported gate unchanged)
- Any ranking order

**Retirement argument:** All 20 top candidates computed percentiles of 76–100%. In the current dataset, percentile does not differentiate. If future replay batches yield lower percentiles for marginal candidates, the differentiation value would increase — but this has not happened yet.

---

## 4. Comparison Matrix

| Criterion | Option A | Option B | Option C |
|-----------|:--------:|:--------:|:--------:|
| Data exists to implement | ❌ | ✅ | ✅ |
| Code changes required | — | Yes (2 functions) | Yes (schema + consumers) |
| Deployment queue impact | — | None | None |
| Resolves MEDIUM_RISK classification | — | ✅ | ✅ |
| Implementation complexity | — | Low | Medium |
| Introduces new test surface | — | Yes (percentile calc) | No (removal) |
| Future flexibility | — | ✅ Preserved | ❌ Removed |
| Recommended | — | ✅ **YES** | Acceptable fallback |

---

## 5. Decision Checklist for Implementing Option B

Before implementation (out of audit scope):

- [ ] Verify `selected_symbols` ordering is rank-descending by composite score for `TOP_N_COMPOSITE_AT_START` replay mode
- [ ] Verify `replay_evidence_summary.json` path is accessible from `_load_replay_evidence()` via `replay_matrix.csv` `replay_evidence_summary_path` column
- [ ] Confirm `full_universe_symbol_count` is consistently populated in all 257 evidence summaries
- [ ] Write unit test: given mock `replay_inputs.csv` + mock evidence summary, assert `symbol_percentile` computed correctly
- [ ] Run full pipeline with percentile populated; verify 0 deployment queue rank changes
- [ ] Update Phase 7.5H risk classification: expected change from MEDIUM_RISK → LOW_RISK for all 20 candidates

---

## 6. Status

**Phase 7.5I — Audit complete. No implementation performed.**  
Implementation of Option B deferred to a future phase pending the verification checklist above.  
All acceptance criteria met (read-only audit).
