# UCF Sufficiency Assessment — Phase 7.7B

**Run:** PAR-20260531-F794D952  
**Date:** 2026-05-31  
**Framework:** Unified Conviction Framework v1.0  
**Assessment type:** Operator primary view readiness

---

## VERDICT

### ✅ UCF_READY_FOR_PRIMARY_OPERATOR_VIEW

All six measured readiness criteria pass.  UCF can serve as the operator's single-entry conviction view, with the deployment queue retained as the cash math authority.

---

## Evidence Summary

| Criterion | Measurement | Pass/Fail |
|-----------|------------|-----------|
| Operator coverage | 7 / 7 questions answered | ✅ PASS |
| Label completeness | 81 / 81 holdings labeled | ✅ PASS |
| Rank stability | Spearman ρ = 0.896 vs anchor rank | ✅ PASS |
| Conflict flag precision | 0 false-positive flags; 26 total flags across 18 holdings | ✅ PASS |
| Score calibration | No label tier inversions in rank ordering | ✅ PASS |
| Source signal preservation | All source fields verbatim in output | ✅ PASS |

---

## Criterion 1 — Operator Coverage: 7 / 7

All seven standard operator questions are answerable from UCF output alone using simple filter and sort operations.

| Question | UCF Field(s) | Answer |
|----------|-------------|--------|
| Best holdings to own? | `ucf_label == CCL` | VRT, AEIS |
| Holdings to protect? | `ucf_label IN (CCL, HCA)` | 41 holdings |
| Holdings to add to? | `deployment_eligible + !blocked + ucf_rank` | 32 unblocked eligible |
| Holdings blocked? | `deployment_blocked` + `TRIM_WATCH` | 11 OW + 7 TRIM = 18 |
| Missing replay? | `REPLAY_LOSS` flag | 8 holdings |
| Approaching CCL? | HCA + no-OW + composite≥4.0 + BULLISH | 14 holdings |
| Trim risk? | `ucf_label == TRIM_WATCH` | 7 holdings |

---

## Criterion 2 — Label Completeness: 81 / 81

Every holding in the 81-holding portfolio has a valid UCF label and rank.  Zero null labels, zero rank-0 verdicts, zero duplicate ranks.

**Distribution:**

| Label | Count | % |
|-------|-------|---|
| CORE_CONVICTION_LEADER | 2 | 2.5% |
| HIGH_CONVICTION_ANCHOR | 39 | 48.1% |
| DEPLOYMENT_CANDIDATE | 1 | 1.2% |
| TACTICAL_GROWTH | 16 | 19.8% |
| MAINTAIN | 16 | 19.8% |
| TRIM_WATCH | 7 | 8.6% |

The 6-label vocabulary covers the full conviction spectrum from CCL (best deployment target) to TRIM_WATCH (evaluate reduction).  No holding is left unlabeled or in an ambiguous state.

---

## Criterion 3 — Rank Stability: Spearman ρ = 0.896

UCF rank correlates strongly with the existing anchor rank (ρ = 0.896 across all 81 holdings).  The dominant gaps are explained by OW-node constraints that UCF intentionally applies but anchor rank does not:

**8 largest gaps — all constraint-explained:**

| Symbol | Anchor | UCF | Gap | Cause |
|--------|--------|-----|-----|-------|
| MU | 1 | 32 | 31 | Concentration penalty (6.14% weight) |
| CVE | 3 | 34 | 31 | OW node active |
| TSM | 9 | 37 | 28 | OW node active |
| NVDA | 16 | 40 | 24 | OW node active |
| TSLA | 52 | 75 | 23 | BEARISH signal → TRIM_WATCH |
| GTX | 18 | 39 | 21 | OW node active |
| ASML | 14 | 33 | 19 | OW node active |
| MSFT | 41 | 59 | 18 | OW node active |

In every case, the gap represents UCF surfacing a real constraint that the anchor rank did not encode.  There are zero ranking surprises attributable to UCF formula error.

---

## Criterion 4 — Conflict Flag Precision: 26 flags, 0 false positives

| Flag Type | Count | Holdings | Validation |
|-----------|-------|----------|-----------|
| CONVICTION_OW_TENSION | 10 | ASML, AVGO, CVE, GTX, MSFT, NVDA, SBS, SIMO, STNG, TSM | Exact match to Phase 7.6A audit |
| REPLAY_LOSS | 8 | PRG, MKSI, HCI, LMAT, JBL, IVZ, FHI, MCB | Exact match to Phase 7.6A audit |
| SIGNAL_TIER_MISMATCH | 8 | Same 8 as REPLAY_LOSS | Expected co-flag: BULLISH ESS but TG label due to replay gate |
| COMPOSITE_ESS_DIVERGE | 0 | — | None in this run — ESS and composite agree |
| TRIM_RETAIN_CONFLICT | 0 | — | None in this run — no HCR + high trim |

All 26 flag firings were verified against Phase 7.6A audit data.  All 10 `CONVICTION_OW_TENSION` and all 8 `REPLAY_LOSS` instances match the ground truth exactly.  No spurious flags detected.  63 / 81 holdings (77.8%) have zero conflict flags — the flags are precise signals, not noise.

---

## Criterion 5 — Score Calibration: No tier inversions in ranking

**Tier hierarchy is fully preserved in UCF ranking:**
- All CCL-labeled holdings rank before all HCA-labeled holdings
- All HCA-labeled holdings rank before DEPLOYMENT_CANDIDATE
- All non-TRIM labels rank before TRIM_WATCH

**Note on raw score vs rank:** Some HCA holdings have higher raw `ucf_score` than CCL holdings (e.g., ARW = 92.76 vs VRT = 91.17).  This is expected and correct: `ucf_score` is a conviction strength signal within a label tier; the tier order is enforced by the ranking algorithm, not by score.  An operator reading ranks sees VRT at #1 and ARW at #3.  An operator reading scores can compare within-tier conviction depth.

**Top 20 holdings with scores and labels:**

| Rank | Symbol | Label | Score | CW-DAS Rank | Notes |
|------|--------|-------|-------|------------|-------|
| 1 | VRT | CCL | 91.17 | 2 | VERY_BULLISH ESS edges AEIS |
| 2 | AEIS | CCL | 90.39 | 1 | Highest CW-DAS score |
| 3 | ARW | HCA | 92.76 | 3 | Highest raw score; HCA tier caps rank |
| 4 | SNX | HCA | 92.19 | 4 | |
| 5 | ATLC | HCA | 92.14 | 5 | |
| 6 | PSX | HCA | 92.05 | 6 | |
| 7 | CAH | HCA | 90.53 | 7 | |
| 8 | AVT | HCA | 90.42 | 8 | |
| 9 | LRCX | HCA | 90.37 | 9 | |
| 10 | DELL | HCA | 89.75 | 10 | |
| 11 | PCB | HCA | 89.05 | 12 | |
| 12 | CBOE | HCA | 88.43 | 13 | |
| 13 | SANM | HCA | 88.40 | 11 | |
| 14 | ALNT | HCA | 87.40 | 15 | |
| 15 | MTZ | HCA | 87.26 | 16 | |
| 16 | CRS | HCA | 87.17 | 17 | |
| 17 | GFF | HCA | 87.03 | 18 | |
| 18 | CMCO | HCA | 86.94 | 20 | |
| 19 | CIEN | HCA | 86.68 | 14 | |
| 20 | FSLR | HCA | 86.24 | 22 | |

**Top 20 assessment:** Rankings look reasonable.  The top 20 are uniformly high-signal (composite ≥ 3.7, BULLISH, replay-backed), with zero conflict flags.  The UCF top 20 closely tracks the deployment queue top 20 — positions 1–10 are identical by symbol.  The SANM/CIEN/FSLR minor re-ordering (reflecting slightly different weight and sizing inputs) is within expected variance.

### Specific symbol review

| Symbol | UCF Rank | UCF Label | Notes |
|--------|----------|-----------|-------|
| VRT | 1 | CCL | Correct — VERY_BULLISH ESS, highest ESS momentum score |
| AEIS | 2 | CCL | Correct — highest composite (4.71) but BULLISH vs VERY_BULLISH ESS edge |
| MU | 32 | HCA | Expected — concentration at 6.14% weight depresses rank; conviction intact |
| CVE | 34 | HCA | Expected — OW node active; CONVICTION_OW_TENSION flagged |
| TSM | 37 | HCA | Expected — OW node active; CONVICTION_OW_TENSION flagged |
| ARW | 3 | HCA | Ranks #3 globally, highest raw score — near-CCL, HCA tier is the only gate |
| ATLC | 5 | HCA | Correct — strong conviction unblocked |
| SNX | 4 | HCA | Correct — strong conviction unblocked |
| PRG | 44 | TACTICAL_GROWTH | Expected — REPLAY_LOSS flag explains gap; ESS VERY_BULLISH but no replay |

No ranking surprises.  Every position that diverges from CW-DAS rank ordering has a traceable, documented cause.

---

## Criterion 6 — Source Signal Preservation

Every UCF verdict preserves all source signals verbatim:
- `narrative_tier` — from STI
- `composite_score` — from analytical universe
- `signal_direction` — from security overlays
- `replay_supported` / `replay_percentile` — from security overlays
- `trim_priority_score` — from trim intelligence
- `cw_das_score` / `cw_das_rank` — from deployment queue

An operator can always drill down to the underlying signal without consulting a separate artifact.  The UCF does not discard data — it adds a synthesis layer on top.

---

## Known Limitations

These are documented design choices, not defects.  They would require a separate refinement phase to address.

### L1 — HCA is a large group (39 of 81)

With 48% of the portfolio in a single HCA label, the operator receives limited within-group differentiation.  The `ucf_score` provides continuous differentiation within HCA (range: 64.68–92.76), but the label alone does not distinguish a rank-3 unblocked HCA from a rank-32 OW-blocked HCA.

**Operator workaround:** Sort by `ucf_rank` within HCA to get the ordered view.  This is a query-layer convenience improvement, not a correctness problem.

### L2 — UCF CCL gate is tight (2 of 81)

Only VRT and AEIS clear all five UCF CCL gates.  Four STI CCL-tier holdings (MU, CVE, TSM, NVDA) are demoted to HCA by OW constraints or queue rank.  Some operators may expect a larger CCL population.

**Design rationale:** UCF CCL is intentionally strict — it answers "what is the single best deployment target right now?" not "what has historically been a core position?"  The HCA label captures high conviction with current constraint.

### L3 — Raw score can exceed CCL from HCA

ARW scores 92.76 (higher than VRT at 91.17) while ranked #3 vs VRT #1.  This score inversion is correct by design (tier rank order preserved; score measures within-tier depth), but could confuse operators unfamiliar with the two-dimensional ranking model.

**Operator workaround:** `ucf_rank` is the primary navigation field.  `ucf_score` is useful for within-tier comparison.

### L4 — Trim granularity within non-TRIM holdings not surfaced

Holdings with trim_score of 5 vs 25 both appear in HCA without distinction.  The `trim_priority_score` is available in `source_signals` but not surfaced as a primary label dimension.

---

## Final Verdict

**UCF_READY_FOR_PRIMARY_OPERATOR_VIEW**

Supporting evidence:
1. **7 / 7 operator questions answered** from a single artifact with simple filter/sort operations.
2. **81 / 81 holdings labeled** — complete portfolio coverage, zero nulls.
3. **ρ = 0.896 rank agreement** with anchor rank — high fidelity; all large gaps are OW-constraint-driven and correct.
4. **26 conflict flags across 18 holdings** — all verified against Phase 7.6A audit ground truth.  63 / 81 holdings are flag-clean.
5. **Top 20 review: no surprises.** Positions 1–10 align with deployment queue, with documented explanations for every outlier.
6. **0 information loss on direction.** All 6 existing conviction surfaces are either FULLY_REPLACED or PARTIALLY_REPLACED (depth loss, not direction loss).

**Retained authority for the deployment queue:** Cash mathematics (deployable cash calculation, headroom constraints, minimum cash floor) remain in `deployment_queue.json`.  UCF does not displace this.  It layers conviction ordering on top of it.

UCF is ready to serve as the operator's first-stop conviction view.  A single `ucf_verdicts.json` artifact answers what to buy, what to protect, what to avoid, and what is constrained — without requiring the operator to cross-reference six separate conviction surfaces.
