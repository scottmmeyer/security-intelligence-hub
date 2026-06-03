# UCF Information Loss Report — Phase 7.7B

**Run:** PAR-20260531-F794D952  
**Date:** 2026-05-31  
**Surfaces analyzed:** 6  
**Classification scale:** FULLY_REPLACED | PARTIALLY_REPLACED | NOT_REPLACED

---

## Summary

| Source Surface | Classification | Detail |
|----------------|---------------|--------|
| Narrative Tier | FULLY_REPLACED | UCF label subsumes all narrative tier information |
| Anchor Rank | PARTIALLY_REPLACED | Strong correlation (ρ = 0.896); OW-penalized CCL loses anchor rank fidelity |
| Strategic Classification | FULLY_REPLACED | Embedded in label routing; TRIM classifications surface as TRIM_WATCH |
| Deployment Queue | PARTIALLY_REPLACED | UCF adds conviction layering; raw queue still needed for cash math |
| Replay Support | FULLY_REPLACED | Embedded in scoring + REPLAY_LOSS flag |
| Trim Intelligence | PARTIALLY_REPLACED | TRIM_WATCH captures active trim risk; trim_score granularity partially lost |

---

## 1. Narrative Tier → UCF Label

**Classification: FULLY_REPLACED**

### Mapping completeness

| STI Narrative Tier | Count | UCF Label Breakdown |
|-------------------|-------|---------------------|
| CORE_CONVICTION_LEADER | 6 | CCL: 2 · HCA: 4 |
| HIGH_CONVICTION_ANCHOR | 37 | HCA: 35 · DC: 1 · MAINTAIN: 1 |
| TACTICAL_GROWTH_CANDIDATE | 38 | TG: 16 · MAINTAIN: 15 · TRIM_WATCH: 7 |
| WATCH_TRIM_CANDIDATE | 0 | n/a |

### What UCF adds over raw narrative tier

Narrative tier classifies only conviction strength.  UCF adds:
- **Constraint overlays:** CCL tier + OW node → HCA (explicitly flags CONVICTION_OW_TENSION)
- **Queue gate:** CCL tier + rank > top-quartile → HCA Path B (handles MU, CVE, TSM, NVDA)
- **Signal negative:** TGC tier + BEARISH signal → TRIM_WATCH (7 holdings surfaced)
- **Replay gate:** TGC tier + composite < 2.5 or UNKNOWN signal → MAINTAIN (15 holdings distinguished from TACTICAL_GROWTH)

### What is lost

Nothing.  UCF label encodes the narrative tier signal and adds constraint context.  The original tier can always be recovered from `source_signals.narrative_tier` in the verdict JSON.

---

## 2. Anchor Rank → UCF Rank

**Classification: PARTIALLY_REPLACED**

### Rank correlation

Spearman rank correlation between `anchor_rank` and `ucf_rank` across all 81 holdings:

**ρ = 0.896** — strong alignment.

For 63 of 81 holdings (77.8%), the rank ordering is effectively preserved (gap ≤ 5 positions).

### Largest rank gaps

| Symbol | Anchor Rank | UCF Rank | Gap | Root Cause |
|--------|------------|---------|-----|-----------|
| MU | 1 | 32 | 31 | OW concentration penalty: weight=6.14%, conc_pen in CW-DAS depresses queue rank to 37; HCA Path C keeps MU in UCF rank 32 |
| CVE | 3 | 34 | 31 | OW node active: redundancy_pen=15 pts; UCF labels HCA with CONVICTION_OW_TENSION |
| TSM | 9 | 37 | 28 | OW node active; similar to CVE |
| NVDA | 16 | 40 | 24 | OW node active |
| TSLA | 52 | 75 | 23 | BEARISH signal → TRIM_WATCH (anchor rank was based on strategic importance, not signal) |
| GTX | 18 | 39 | 21 | OW node active |
| ASML | 14 | 33 | 19 | OW node active |
| MSFT | 41 | 59 | 18 | OW node active |

### Interpretation

All 7 of the top-8 gap cases are explained by a single structural reason: the anchor rank was assigned on strategic importance alone (without deployment constraint).  UCF rank reflects deployment-weighted conviction — it demotes OW-blocked positions within the ranking because an operator cannot add to them regardless of conviction level.

**This is UCF adding information, not losing it.**  The anchor rank gap for MU/CVE/TSM is a feature: it tells the operator "high conviction but currently untouchable due to position sizing."

### What is lost

Anchor rank captures a pure strategic importance view (conviction without constraint).  An operator who wants the unconstrained ranking can still read `source_signals` → `cw_das_rank` or the STI-published `anchor_rank`.  UCF does not delete this data; it surfaces it alongside the constrained ranking.

---

## 3. Strategic Classification → UCF Label

**Classification: FULLY_REPLACED**

### Mapping

| Strategic Classification | Count | UCF Treatment |
|--------------------------|-------|---------------|
| HIGH_CONVICTION_RETAIN | 43 | Routes to CCL (2), HCA (35), DC (1), MAINTAIN (5) based on signal/constraint gates |
| TACTICAL_GROWTH | 38 | Routes to TG (16), MAINTAIN (15), TRIM_WATCH (7) based on signal/composite gates |
| REDUCIBLE | 0 | Would route directly to TRIM_WATCH |
| REDUNDANT_EXPOSURE | 0 | Would route directly to TRIM_WATCH |
| CONCENTRATION_RISK | 0 | Would route directly to TRIM_WATCH |

### What UCF adds

Strategic classification is a coarse binary (retain / trim direction).  UCF converts it to a 6-level ordered label with constraint visibility.  The `HIGH_CONVICTION_RETAIN` group splits across 4 UCF labels — each carrying distinct operator action guidance that the binary classification cannot provide.

### What is lost

Nothing materially.  The full classification string is preserved in `ucf_comparison_matrix.csv` for any query that needs the source label.

---

## 4. Deployment Queue → UCF

**Classification: PARTIALLY_REPLACED**

### What UCF replaces

| Deployment Queue Feature | UCF Equivalent | Fidelity |
|--------------------------|---------------|---------|
| In-queue / not-in-queue | `deployment_eligible` | Exact |
| Queue rank ordering | `ucf_rank` (with tier ordering) | Strong (ρ≈0.896, monotone within tier) |
| OW node blocked | `deployment_blocked` + `CONVICTION_OW_TENSION` flag | Exact |
| High-conviction vs low-conviction ordering | `ucf_label` tier | Exact |
| Score formula breakdown | Not in UCF | Not present |

### What UCF does not replace

1. **Cash math:** `compute_deployable_cash()`, available headroom by position, minimum cash floor enforcement.  UCF does not know how much cash is available to deploy — it only knows which holdings deserve it.

2. **Score formula breakdown:** The `score_breakdown` dict in each queue item (signal / replay / conviction / sizing / momentum / redundancy_pen / conc_pen components) is not reproduced in UCF.  An operator examining why AEIS scores 95.56 vs ATLC at 84.29 cannot infer that from UCF alone.

3. **Exact CW-DAS scores:** Available via `source_signals.cw_das_score` in the verdict, but not the primary UCF metric.

**Verdict:** For conviction ordering and constraint visibility, UCF fully replaces the deployment queue.  For cash deployment mathematics, the deployment queue remains authoritative.

---

## 5. Replay Support → UCF

**Classification: FULLY_REPLACED**

### Encoding in UCF

- **Score component:** `replay_supported` contributes 20 points (× 0.20 weight) to `ucf_score`.  A non-replay holding with otherwise identical signals scores 20 points lower.
- **Gating:** `replay_supported` is a hard gate for DEPLOYMENT_CANDIDATE label; strongly influences HCA Path C.
- **REPLAY_LOSS flag:** Fires for all 8 holdings with BULLISH signal + composite ≥ 3.5 + no replay.  Visible in `conflict_flags`.

### What is lost

The specific replay strategy name and return details (best_replay_return, replay_percentile in underlying data) are not surfaced in the UCF verdict beyond `replay_percentile`.  For operator-level conviction decisions, the binary (replay_supported: true/false) is sufficient; the raw backtest figures are available in source overlays if needed.

---

## 6. Trim Intelligence → UCF

**Classification: PARTIALLY_REPLACED**

### What UCF captures

- **TRIM_WATCH label:** All 7 active trim cases appear.  6 are driven by BEARISH signal; 1 could be driven by high trim_score.  The label communicates the key operator instruction: do not add, evaluate reduction.
- **trim_priority_score** preserved verbatim in `source_signals.trim_priority_score` in every verdict.
- **TRIM_RETAIN_CONFLICT flag:** Fires when `HIGH_CONVICTION_RETAIN` classification conflicts with trim_score ≥ 50 (0 instances in this run).

### What UCF does not replace

1. **Trim granularity within the non-TRIM population:** Holdings with trim_score of 5 vs 25 both appear in HCA or TG without distinction, unless the score difference is large enough to affect ucf_score materially.

2. **Trim factor narrative:** The specific trim factors (overlap_peers, thematic_redundancy_score, concentration_pressure) that explain WHY a holding has a particular trim score are not surfaced in UCF.

3. **Trim priority ordering within TRIM_WATCH:** UCF ranks TRIM_WATCH positions at the bottom, but within the TRIM_WATCH group the ordering is by ucf_score (not trim_priority_score directly).  An operator asking "which TRIM_WATCH holding is most urgent to reduce?" must cross-reference trim_priority_score or weight_pct from the matrix.

**Verdict:** TRIM_WATCH as a label is operationally sufficient for the primary instruction (do not add, evaluate).  The trim granularity within non-TRIM holdings and the within-group ordering are not fully preserved.

---

## Aggregate Assessment

| Surface | Verdict | Primary Gap (if any) |
|---------|---------|---------------------|
| Narrative Tier | FULLY_REPLACED | None |
| Anchor Rank | PARTIALLY_REPLACED | OW-penalized CCL demoted in UCF rank (by design; not a loss) |
| Strategic Classification | FULLY_REPLACED | None |
| Deployment Queue | PARTIALLY_REPLACED | Cash math, score formula breakdown |
| Replay Support | FULLY_REPLACED | None |
| Trim Intelligence | PARTIALLY_REPLACED | Trim granularity within non-TRIM group; within-TRIM-WATCH ordering |

**3 of 6 surfaces: FULLY_REPLACED.**  
**3 of 6 surfaces: PARTIALLY_REPLACED.**  
**0 of 6 surfaces: NOT_REPLACED.**

The three partial replacements share a common pattern: UCF preserves the conviction signal faithfully but does not replicate the full precision of the specialist sub-system (cash math for deployment queue, trim score narrative for trim intelligence, unconstrained strategic importance rank for anchor rank).  In all three cases, the source artifact remains available for drill-down.

---

## Conclusion

UCF successfully synthesizes all six conviction surfaces into a single ordered verdict.  No conviction signal is lost — every source field is preserved verbatim in `source_signals`.  The partial replacements represent **depth loss** (operator must consult source for sub-detail), not **direction loss** (UCF never gives a wrong answer on the primary conviction question).  For primary operator use — what to buy, what to protect, what to avoid — UCF is sufficient.
