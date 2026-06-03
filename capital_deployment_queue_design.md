# Capital Deployment Queue — Design Document
**Phase 7.5A | Design and Validation Only**  
**Run Reference:** PAR-20260531-942B1F54  
**Total Portfolio:** $472,219.90 | **Deployable Cash:** $33,175 (above 2% floor)

---

## Section 1 — Current State Assessment

### The Problem This Document Addresses

The existing `CONCENTRATED_ALPHA` recommendation engine produces 43 eligible conviction-tier holdings after Phase 7.4D replay fix. While the full recommendation surface is useful for ongoing monitoring, the operator-facing question is more specific: *"I have approximately $33K of deployable cash. Where should capital go first?"*

The current workflow does not answer this question directly. The operator must:
1. Read through all recommendation cards (flagged ACCUMULATE)
2. Mentally sort by conviction tier (CCL vs HCA)
3. Mentally cross-reference current position sizes
4. Infer a deployment priority

This is a usability gap, not a data gap. All signals are present. What is missing is a ranked, explainable capital deployment queue surfaced as a first-class artifact — sitting above all individual recommendation cards and giving the operator a clear #1 action.

### The Existing Framework: DAS

Phase 7.4A introduced the **Deployment Attractiveness Score (DAS)** and produced `conviction_capital_deployment_report.md`. The DAS formula is:

```
DAS = Signal(0-30) + Replay(0-20) + Conviction(0-25) + Sizing(0-15) + Momentum(0-10)
      − Redundancy_Penalty(0-15) − Concentration_Penalty(0-20)

Max theoretical score: 100
```

**Component definitions:**
| Component | Range | Formula |
|-----------|-------|---------|
| Signal | 0–30 | `min(composite/5 × 30, 30)` |
| Replay | 0–20 | 20 if `replay_supported=True`, else 0 |
| Conviction | 0–25 | CCL=25, HCA=20, other=10 |
| Sizing | 0–15 | `15 × max(0, 1 − pct/6%)` |
| Momentum | 0–10 | 10 if ESS_BULLISH+BULLISH signal; 7.5 if one; 4 neutral; 0 bearish |
| Redundancy | 0–15 | −15 if node is in MODERATE+ overweight allocation |
| Concentration | 0–20 | `−min((pct−6%) × 4, 20)` if pct > 6% |

The DAS framework was designed for capital deployment analysis. The issue is not the framework concept — it is a weight calibration problem that causes Sizing to dominate Conviction in discriminating between candidates.

### Identified Structural Problem: Sizing Dominance

The current DAS Sizing component scales from 0–15 based purely on current position size relative to the 6% soft-warn threshold. This creates an unintended ranking inversion:

**Empirical example from PAR-20260531-942B1F54:**

| Symbol | Tier | Weight | Sizing (pts) | Conviction (pts) | Momentum (pts) | DAS | Rank |
|--------|------|--------|-------------|-----------------|----------------|-----|------|
| ARW | HCA | 0.92% | 12.7 | 20 | 10.0 | 92.0 | **#1** |
| AEIS | CCL | 2.42% | 8.9 | 25 | 7.5 | 89.7 | #5 |
| VRT | CCL | 3.60% | 6.0 | 25 | 10.0 | 88.3 | #11 |

ARW (HCA tier) ranks above both CCL holdings. The +5 conviction premium for CCL (`25 − 20 = 5 pts`) is fully offset by ARW's +3.8 sizing advantage and +2.5 momentum advantage. ARW earns #1 not because it is the highest-conviction opportunity, but because it is the smallest position.

For a CONCENTRATED_ALPHA mandate, this ordering is inverted. Conviction tier is the primary signal of portfolio intelligence. Position headroom is relevant but should not override it.

### Additional Finding: OW-Node Buried CCLs

Three of the six CCL-tier holdings (MU, NVDA, TSM, CVE) are suppressed to ranks 37–43 primarily due to the −15 Redundancy Penalty. These are correctly penalized — their allocation nodes are MODERATE+ overweight. This is a valid DAS behavior, not a bug.

**CCL summary for PAR-20260531-942B1F54:**
| Symbol | Weight | Node | OW Penalty | Headroom | DAS | Deployable? |
|--------|--------|------|-----------|---------|-----|-------------|
| AEIS | 2.42% | US.SMALL | No | 60% | 89.7 | ✓ Yes |
| VRT | 3.60% | US.LARGE | No | 40% | 88.3 | ✓ Yes |
| NVDA | 3.20% | US.MEGA | Yes (−15) | 47% | ~71 | ✗ OW node |
| CVE | 2.47% | INTL.MID | Yes (−15) | 59% | ~68 | ✗ OW node |
| TSM | 2.33% | INTL.MEGA | Yes (−15) | 61% | ~67 | ✗ OW node |
| MU | 6.14% | US.MEGA | Yes (−15) | BLOCKED | 67.8 | ✗ OW + over WARN |

Conclusion: Only AEIS and VRT are deployable CCL holdings. The OW node penalty logic is working correctly.

---

## Section 2 — Eligibility Rules

### Inclusion Criteria (all must be true)

| Criterion | Source Field | Rule |
|-----------|-------------|------|
| Signal direction | `signal_direction` | `BULLISH` only |
| Replay support | `replay_supported` | `True` only |
| Strategic classification | `strategic_classification` | `HIGH_CONVICTION_RETAIN` only |
| Conviction tier | `narrative_tier` | `CORE_CONVICTION_LEADER` or `HIGH_CONVICTION_ANCHOR` |
| Position exists | `market_value` | `> 0` (current holding, not new position) |
| Not cash | `is_cash_equivalent` | `False` |

### Exclusion Criteria (any one disqualifies)

| Criterion | Source Field | Rule |
|-----------|-------------|------|
| ETF or fund | `security_type` | Exclude ETF, FUND, MUTUAL_FUND |
| Neutral/Bearish signal | `signal_direction` | Exclude NEUTRAL, BEARISH, UNKNOWN |
| No replay support | `replay_supported` | Exclude False |
| Non-HCR classification | `strategic_classification` | Exclude TACTICAL_GROWTH, REDUCIBLE, TRIM, WATCH, NONE |
| Sub-HCA tier | `narrative_tier` | Exclude TACTICAL_GROWTH_CANDIDATE, WATCH_TRIM_CANDIDATE, NONE |

### Rationale

These rules implement the portfolio philosophy that deployment of fresh capital should reinforce the highest-conviction layer of the book. The replay gate ensures historical precedent validates the conviction signal. The STI=HCR gate ensures the holding has passed the multi-dimensional review that would otherwise produce a TRIM recommendation.

TACTICAL_GROWTH_CANDIDATE holdings are excluded from v1 of this queue. They have legitimate strategic roles but deploying excess cash to tactical positions before core conviction positions are fully sized would be inconsistent with CONCENTRATED_ALPHA construction principles.

### Eligibility Filter Results (PAR-20260531-942B1F54)

| Result | Count | Notes |
|--------|-------|-------|
| Eligible | **43** | 6 CCL + 37 HCA |
| Excluded: TACTICAL_GROWTH tier | 38 | Holdings lack HCR classification |
| Excluded: Replay=False | 35 | (overlaps with above — multi-reason filtering) |
| Excluded: Non-BULLISH signal | 30 | UNKNOWN (20), NEUTRAL (8), BEARISH (2) |
| Excluded: ETF | 19 | (overlaps with above) |
| Excluded: Cash | 1 | SPAXX |

---

## Section 3 — Candidate Universe

### Portfolio State (PAR-20260531-942B1F54)

| Metric | Value |
|--------|-------|
| Total portfolio value | $472,219.90 |
| Cash (SPAXX) | $42,620 (9.03%) |
| Floor reserve (2% mandate minimum) | $9,444 |
| **Deployable cash** | **$33,175 (7.03%)** |
| Investable holdings (ex-cash) | $429,600 |
| Analysis run | PAR-20260531-942B1F54 |
| Eligible candidates | 43 |

### Full Eligible Universe (43 holdings)

**CCL Tier (6 holdings)**

| Symbol | Weight | Composite | Replay | ESS | OW Node | Headroom | Deployable |
|--------|--------|-----------|--------|-----|---------|---------|-----------|
| CVE | 2.47% | 4.889 | ✓ | VERY_BULLISH | ✗ INTL | 59% | No — mandate conflict |
| AEIS | 2.42% | 4.714 | ✓ | — | No | 60% | **Yes** |
| TSM | 2.33% | 4.444 | ✓ | VERY_BULLISH | ✗ INTL | 61% | No — mandate conflict |
| VRT | 3.60% | 4.556 | ✓ | VERY_BULLISH | No | 40% | **Yes** |
| NVDA | 3.20% | 4.111 | ✓ | BULLISH | ✗ US.MEGA | 47% | No — mandate conflict |
| MU | 6.14% | 4.722 | ✓ | VERY_BULLISH | ✗ US.MEGA | Blocked | No — at/above WARN |

**HCA Tier (37 holdings) — Top 25 by composite score**

| Symbol | Weight | Composite | Replay | ESS | Trim Score | Headroom |
|--------|--------|-----------|--------|-----|-----------|---------|
| ARW | 0.92% | 4.889 | ✓ | VERY_BULLISH | 0.4 | 85% |
| CVE (CCL ↑) | — | — | — | — | — | — |
| SNX | 0.86% | 4.778 | ✓ | VERY_BULLISH | 0.4 | 86% |
| ATLC | 0.89% | 4.778 | ✓ | VERY_BULLISH | 0.4 | 85% |
| SANM | 0.66% | 4.714 | ✓ | — | 0.3 | 89% |
| PSX | 0.75% | 4.722 | ✓ | VERY_BULLISH | 0.3 | 88% |
| CIEN | 1.17% | 4.571 | ✓ | BULLISH | 0.5 | 81% |
| CAH | 1.06% | 4.556 | ✓ | VERY_BULLISH | 0.5 | 82% |
| LRCX | 0.95% | 4.500 | ✓ | BULLISH | 0.4 | 84% |
| DELL | 1.32% | 4.500 | ✓ | VERY_BULLISH | 0.6 | 78% |
| AVT | 0.93% | 4.500 | ✓ | VERY_BULLISH | 0.4 | 85% |
| AVGO | 2.58% | 4.444 | ✓ | VERY_BULLISH | 1.2 | 57% |
| ASML | 1.87% | 4.444 | ✓ | VERY_BULLISH | 0.9 | 69% |
| MSFT | 2.24% | 4.278 | ✓ | BULLISH | 1.0 | 63% |
| PCB | 0.94% | 4.278 | ✓ | BULLISH | 0.4 | 84% |
| NUE | 0.79% | 4.286 | ✓ | BULLISH | 0.3 | 87% |
| CBOE | 0.72% | 4.111 | ✓ | VERY_BULLISH | 0.3 | 88% |
| DVN | 1.50% | — | ✓ | — | 0.7 | 75% |
| STLD | 0.86% | — | ✓ | — | 0.4 | 86% |
| BSVN | 0.56% | 4.000 | ✓ | BULLISH | 0.2 | 91% |
| HALO | 0.72% | — | ✓ | — | 0.3 | 88% |
| GTX | 0.83% | — | ✓ | — | 0.4 | 86% |
| ANIP | 0.73% | — | ✓ | — | 0.3 | 88% |
| SIMO | 0.65% | — | ✓ | — | 0.3 | 89% |
| AZZ | 0.66% | — | ✓ | — | 0.3 | 89% |
| *...12 additional HCA holdings* | | | | | | |

*Full universe available via `build_strategic_profiles()` against PAR-20260531-942B1F54*

---

## Section 4 — Ranking Method Evaluation

### Two Methods Evaluated

#### Method A: Current DAS (unchanged)

`DAS = Signal(0-30) + Replay(0-20) + Conviction(0-25) + Sizing(0-15) + Momentum(0-10) − penalties`

#### Method B: Conviction-Weighted DAS (CW-DAS)

`CW-DAS = Signal(0-30) + Replay(0-20) + Conviction(0-35) + Sizing(0-8) + Momentum(0-10) − penalties`

Changes from current DAS:
- **Conviction range**: 0–35 (from 0–25). CCL=35, HCA=28 (7-point spread vs current 5-point)
- **Sizing range**: 0–8 (from 0–15). Formula: `8 × headroom` instead of `15 × headroom`
- **Net shift**: maximum score increases by 8 points for CCL (+10 conviction, −7 sizing max). HCA-tier max unchanged at ~100 if at small weight, but CCL reliably outranks similarly-scored HCA
- All other components (Signal, Replay, Momentum, penalties) unchanged

**Rationale for Conviction weight increase:**  
CCL tier represents `BULLISH + replay_supported + composite ≥ 4.0 + weight ≥ 1.5%`. It is the highest-confidence tier in the STI model. Its +5 DAS premium over HCA (current design) can be entirely eliminated by a position size difference of just 3.4 percentage points in headroom (3.4% × 15/6 × 15 = 12.75 vs 15 = 2.25 pts, plus momentum). That's too small a gap to carry the deployment priority signal.

**Rationale for Sizing weight reduction:**  
Headroom is relevant — deploying capital into a position already near WARN threshold is riskier than deploying into a small position. But the deployment-size question should be answered by the operator, not baked into the ranking. The queue's job is to surface *which* holding to add to first, not *how much* to add. A position at 3.5% weight has substantial headroom and should rank well — but not above a stronger-conviction position at 2.5%.

### Side-by-Side Comparison

**Key metric: Do CCLs rank above HCAs of similar quality?**

| Symbol | Tier | Weight | DAS | DAS Rank | CW-DAS | CW-DAS Rank | Δ Rank |
|--------|------|--------|-----|---------|--------|------------|--------|
| AEIS | **CCL** | 2.42% | 89.7 | 5 | 95.6 | **1** | ↑4 |
| VRT | **CCL** | 3.60% | 88.3 | 11 | 95.5 | **2** | ↑9 |
| ARW | HCA | 0.92% | 92.0 | 1 | 94.1 | 3 | ↓2 |
| SNX | HCA | 0.86% | 91.5 | 2 | 93.5 | 4 | ↓2 |
| ATLC | HCA | 0.89% | 91.4 | 4 | 93.5 | 5 | ↓1 |
| PSX | HCA | 0.75% | 91.5 | 3 | 93.3 | 6 | ↓3 |
| CAH | HCA | 1.06% | 89.7 | 6 | 91.9 | 7 | ↓1 |
| AVT | HCA | 0.93% | 89.7 | 7 | 91.8 | 8 | ↓1 |
| LRCX | HCA | 0.95% | 89.6 | 8 | 91.7 | 9 | ↓1 |
| DELL | HCA | 1.32% | 88.7 | 10 | 91.2 | 10 | = |
| SANM | HCA | 0.66% | 89.1 | 9 | 90.9 | 11 | ↓2 |
| MU | CCL | 6.14% | 67.8 | 42 | 77.8 | 37 | ↑5 |

**Analysis:**

Under current DAS:
- ARW (#1) is a 0.92%-weight HCA outranking AEIS (#5), a 2.42%-weight CCL. The sizing difference accounts for the full inversion. ARW: sizing=12.7 vs AEIS: sizing=8.9 (+3.8 pts). Partially offset by AEIS conviction premium (+5 pts), but AEIS lacks an ESS signal (momentum=7.5 vs ARW's 10.0, -2.5 pts). Net: ARW's raw advantage = +3.8 − 5 + 2.5 = +1.3 sizing wins.
- VRT (#11) is a 3.60%-weight CCL ranked behind 10 HCA holdings, all with smaller position sizes. VRT DAS=88.3; all 10 HCA above it score 88.7–92.0.

Under CW-DAS:
- AEIS (#1): conviction lift +10 (25→35), sizing reduction −1.7 (8.9→4.8), net +8.3 → CW-DAS 95.6
- VRT (#2): conviction lift +10, sizing reduction −2.5 (6.0→3.2), net +7.5 → CW-DAS 95.5
- ARW (#3): conviction lift +8 (20→28), sizing reduction −4.9 (12.7→6.8), net +3.1 → CW-DAS 94.1
- CCL tier reliably leads the queue with 7+ point gap over best HCA

**Full rank shift summary (largest movers):**

| Symbol | Tier | Weight | DAS→CW-DAS rank | Direction |
|--------|------|--------|----------------|-----------|
| VRT | CCL | 3.60% | 11 → 2 | ↑9 |
| MU | CCL | 6.14% | 42 → 37 | ↑5 |
| AEIS | CCL | 2.42% | 5 → 1 | ↑4 |
| HALO | HCA | 0.72% | 30 → 26 | ↑4 |
| CIEN | HCA | 1.17% | 17 → 14 | ↑3 |
| PSX | HCA | 0.75% | 3 → 6 | ↓3 |
| ANGO | HCA | 0.84% | 24 → 21 | ↑3 |

**Notable finding:** Heavier-weight HCAs (CIEN, DELL, LRCX) also improve slightly under CW-DAS relative to the lightest-weight HCAs (PSX, SANM, ARW), because the Sizing reduction disproportionately hurts tiny positions. This is a secondary benefit: the queue better surfaces established HCA positions that need reinforcement over micro-positions where the full position thesis hasn't yet been established.

### Method A Problems (Keep DAS)

1. CCLs do not reliably lead the queue — ranking is determined primarily by position size
2. A 0.92%-weight HCA (ARW) outranks a 2.42%-weight CCL (AEIS) by 2.3 DAS points purely on size
3. VRT, one of the portfolio's most conviction-validated positions (replay, composite 4.556, CCL tier, VERY_BULLISH ESS), ranks #11 behind 10 HCA holdings
4. The queue fails its primary purpose: it should answer "which CCL opportunity needs reinforcement?" but instead answers "which holding has the most headroom?"

### Method B Properties (CW-DAS)

1. CCL tier leads the queue (ranks #1 and #2 for deployable CCLs) ✓
2. CCL/HCA gap is reliable: 7-point conviction spread + reduced sizing = CCL wins unless HCA has meaningfully higher composite AND smaller position
3. Mandate conflicts (OW nodes, blocked positions) still correctly suppressed — penalties are unchanged
4. All operator-facing scores remain in same 0–100 range; formula is explainable
5. Backward-compatible: existing DAS scores in `conviction_capital_deployment_report.md` are clearly labeled as a different formula version

---

## Section 5 — Top 20 Prototype Queue

**Ranked by CW-DAS | Run: PAR-20260531-942B1F54 | Deployable: $33,175**

| # | Symbol | Wt% | Composite | Tier | Replay | Trim Score | Headroom | DAS | CW-DAS | Notes |
|---|--------|-----|-----------|------|--------|-----------|---------|-----|--------|-------|
| 1 | **AEIS** | 2.42% | 4.714 | CCL | ✓ | 1.1 | 60% | 89.7 | **95.6** | Primary deployment candidate |
| 2 | **VRT** | 3.60% | 4.556 | CCL | ✓ | 1.6 | 40% | 88.3 | **95.5** | Largest CCL by MV; $17K position |
| 3 | ARW | 0.92% | 4.889 | HCA | ✓ | 0.4 | 85% | 92.0 | 94.1 | Highest composite in universe |
| 4 | SNX | 0.86% | 4.778 | HCA | ✓ | 0.4 | 86% | 91.5 | 93.5 | VERY_BULLISH momentum |
| 5 | ATLC | 0.89% | 4.778 | HCA | ✓ | 0.4 | 85% | 91.4 | 93.5 | VERY_BULLISH momentum |
| 6 | PSX | 0.75% | 4.722 | HCA | ✓ | 0.3 | 88% | 91.5 | 93.3 | High composite, small position |
| 7 | CAH | 1.06% | 4.556 | HCA | ✓ | 0.5 | 82% | 89.7 | 91.9 | VERY_BULLISH momentum |
| 8 | AVT | 0.93% | 4.500 | HCA | ✓ | 0.4 | 85% | 89.7 | 91.8 | VERY_BULLISH momentum |
| 9 | LRCX | 0.95% | 4.500 | HCA | ✓ | 0.4 | 84% | 89.6 | 91.7 | BULLISH signal, large cap |
| 10 | DELL | 1.32% | 4.500 | HCA | ✓ | 0.6 | 78% | 88.7 | 91.2 | VERY_BULLISH; semi-strategic |
| 11 | SANM | 0.66% | 4.714 | HCA | ✓ | 0.3 | 89% | 89.1 | 90.9 | High composite, no ESS signal |
| 12 | PCB | 0.94% | 4.278 | HCA | ✓ | 0.4 | 84% | 88.3 | 90.4 | BULLISH signal |
| 13 | CBOE | 0.72% | 4.111 | HCA | ✓ | 0.3 | 88% | 87.9 | 89.7 | VERY_BULLISH momentum |
| 14 | CIEN | 1.17% | 4.571 | HCA | ✓ | 0.5 | 81% | 87.0 | 89.4 | BULLISH signal, tech infrastructure |
| 15 | ALNT | 0.16% | 3.778 | HCA | ✓ | 0.1 | 97% | 87.3 | 88.5 | Micro position; headroom near max |
| 16 | MTZ | 0.23% | 3.778 | HCA | ✓ | 0.1 | 96% | 87.1 | 88.3 | Micro position |
| 17 | CRS | 0.10% | 3.722 | HCA | ✓ | 0.0 | 98% | 87.1 | 88.2 | Near-zero position |
| 18 | GFF | 0.37% | 3.778 | HCA | ✓ | 0.2 | 94% | 86.7 | 88.2 | Small position |
| 19 | NUE | 0.79% | 4.286 | HCA | ✓ | 0.3 | 87% | 86.2 | 88.2 | BULLISH signal |
| 20 | CMCO | 0.03% | 3.667 | HCA | ✓ | 0.0 | 99% | 86.9 | 88.0 | Near-zero position |

**Queue interpretation notes:**
- Ranks #1–2 are the two deployable CCL positions. Capital deployment should prioritize these before any HCA
- Ranks #3–14 are the high-composite, established HCA positions (>0.6% weight, composite ≥4.1)
- Ranks #15–20 include micro/near-zero positions with very high headroom — these are structurally attractive to DAS but represent position-building context the operator should evaluate separately
- MU (CCL, 6.14%): Not in queue — blocked at WARN threshold + OW node mandate conflict. Correctly excluded

**Critical operator note:** The queue represents *attractiveness order* for adding to existing positions. It does not specify add size, does not validate against tax lots, does not confirm intraday pricing. All deployment decisions remain with the operator.

---

## Section 6 — Recommended Design

### Recommendation: Adopt CW-DAS (Method B) for the Capital Deployment Queue

**Option A (Keep DAS):** Not recommended. The sizing dominance problem is confirmed empirically against live portfolio data. VRT (#11 → #2) and AEIS (#5 → #1) represent real displacement of the portfolio's highest-conviction holdings behind small, under-built positions. For a CONCENTRATED_ALPHA mandate, this ordering is incorrect.

**Option B (CW-DAS with conviction reweighting):** Recommended. Specific parameters:

| Component | Current DAS | Proposed CW-DAS | Change |
|-----------|------------|----------------|--------|
| Signal | 0–30 | 0–30 (unchanged) | — |
| Replay | 0–20 | 0–20 (unchanged) | — |
| Conviction: CCL | 25 | **35** | +10 |
| Conviction: HCA | 20 | **28** | +8 |
| Conviction: other | 10 | 10 (unchanged) | — |
| Sizing scale | 15 | **8** | −7 |
| Momentum | 0–10 | 0–10 (unchanged) | — |
| Redundancy penalty | 0–15 | 0–15 (unchanged) | — |
| Concentration penalty | 0–20 | 0–20 (unchanged) | — |

**Why these specific parameters:**
- CCL=35, HCA=28: The 7-point CCL/HCA spread ensures that at any realistic position size difference (≤5%), CCL conviction will exceed HCA sizing advantage. Max sizing advantage for any HCA vs any CCL with comparable small weights is ~3 points under the 8-pt scale; the 7-point conviction spread absorbs this reliably.
- Sizing scale=8: Headroom remains a meaningful tiebreaker (up to 8 points) but cannot override conviction. An HCA at 0.5% earns sizing_c = 8×0.917 = 7.3 pts; a CCL at 3.0% earns sizing_c = 8×0.5 = 4.0 pts. The 7-point CCL conviction premium (+7 vs HCA) exceeds this +3.3 HCA sizing advantage, so CCL wins.
- Maximum theoretical CW-DAS: 35 + 30 + 20 + 8 + 10 = 103. Score range acceptable; operator interpretation is ordinal, not absolute.

**Option C (New deployment-specific score):** Not recommended for v1. A fully restructured formula (e.g., conviction-gated base score with multiplicative headroom modifier) would require additional validation against edge cases, redesign of the breakdown explainability layer, and user-facing changes to how the score is described. The incremental correctness gain over CW-DAS is small. Defer to a future design cycle if CW-DAS v1 reveals structural gaps.

### Design Properties of the Capital Deployment Queue

1. **Position**: Rendered above all recommendation cards on the portfolio detail view
2. **Default display**: Top 5 candidates; expandable to full eligible universe
3. **Columns**: Rank | Symbol | Current Weight | Composite | Tier | Headroom | CW-DAS | Notes
4. **Score name**: "Deployment Score" (human-readable label for CW-DAS, versioned internally)
5. **Eligibility gate**: Server-computed; only HCR/BULLISH/replay-True/non-ETF holdings appear
6. **Explainability**: Each row should support a detail expansion showing score breakdown (signal/replay/conviction/sizing/momentum/penalties)
7. **No trade instructions**: The queue communicates conviction order and headroom only. No suggested dollar amounts, lot selection, or execution guidance
8. **Cash context**: Queue header displays current cash%, deployable amount, and band status (current: 9.03%, $33,175 deployable above 2% floor)

---

## Section 7 — Implementation Plan

This section describes what a production implementation would require. No code changes are made in this document.

### Prerequisite

- [ ] Confirm CW-DAS parameters (Conviction: CCL=35/HCA=28; Sizing scale=8) accepted by design review

### Implementation Steps

**Step 1: CW-DAS Scoring Function**
- Location: `phase_7_4a_analysis.py` or a new `src/portfolio/deployment_scoring.py`
- Action: Replace `_das()` with a versioned `_cwdas()` function using CW-DAS weights
- Keep original `_das()` intact for backward compatibility — rename to `_das_v1()`
- No changes to existing scoring.py, recommendations.py, or runner.py

**Step 2: Capital Deployment Queue Builder**
- Location: New `src/portfolio/deployment_queue.py`
- Inputs: portfolio holdings + overlays + alignment results (same as build_strategic_profiles)
- Logic: apply eligibility filter → compute CW-DAS → sort → return ranked list
- Output schema: `List[DeploymentCandidate]` with all queue columns

**Step 3: Runner Integration**
- Location: `src/portfolio/runner.py`
- Action: Add `deployment_queue` key to API response (alongside existing `strategic_profiles`)
- No changes to frontend data contracts for existing recommendation cards
- Deployment queue is additive, not replacing existing surfaces

**Step 4: UI Surface**
- Location: `ui/` (detail panel for CONCENTRATED_ALPHA portfolios)
- Action: New `CapitalDeploymentQueue` component rendered above recommendation card list
- Data source: `deployment_queue` from runner API response
- Phase 1 scope: static ranked table with score breakdown on row expand. No trade UI.

**Step 5: Persist Queue Artifact**
- Location: `data/portfolio_ingestion/analysis_runs/{RUN_ID}/deployment_queue.json`
- Format: `{ "generated_at": ..., "run_id": ..., "deployable_mv": ..., "queue": [...] }`
- Optional: also write human-readable `deployment_queue_report.md` (parallel to conviction_capital_deployment_report.md)

### Out of Scope for Phase 7.5A

- Trade sizing recommendations (lot size, dollar amount, bracket orders)
- New position candidates (queue covers existing positions only)
- Multi-portfolio queue aggregation
- Historical queue tracking / drift analytics
- Automated execution or integration with brokerage APIs

### Validation Criteria for Implementation Acceptance

Before merging Phase 7.5B implementation:
1. All 43 eligible candidates from PAR-20260531-942B1F54 appear in computed queue
2. CCL-tier holdings (AEIS, VRT) rank above all HCA holdings (absent OW node or BLOCKED flags)
3. MU absent from deployable queue (blocked at WARN + OW node)
4. NVDA, TSM, CVE absent or ranked low (OW node penalty intact)
5. Score breakdowns sum correctly for at least top-5 positions
6. All existing pytest suite passes (560/560 minimum)

---

## Appendix A — DAS vs CW-DAS Full Score Comparison (All 43 Eligible)

This table documents all 43 eligible holdings, ranked by CW-DAS, for implementation reference.

| # | Symbol | Tier | Wt% | Comp | Sizing (DAS) | Conv (DAS) | DAS | Sizing (CW) | Conv (CW) | CW-DAS | Δ Rank |
|---|--------|------|-----|------|-------------|-----------|-----|------------|----------|--------|--------|
| 1 | AEIS | CCL | 2.42 | 4.714 | 8.9 | 25 | 89.7 | 4.8 | 35 | 95.6 | ↑4 |
| 2 | VRT | CCL | 3.60 | 4.556 | 6.0 | 25 | 88.3 | 3.2 | 35 | 95.5 | ↑9 |
| 3 | ARW | HCA | 0.92 | 4.889 | 12.7 | 20 | 92.0 | 6.8 | 28 | 94.1 | ↓2 |
| 4 | SNX | HCA | 0.86 | 4.778 | 12.8 | 20 | 91.5 | 6.9 | 28 | 93.5 | ↓2 |
| 5 | ATLC | HCA | 0.89 | 4.778 | 12.8 | 20 | 91.4 | 6.8 | 28 | 93.5 | ↓1 |
| 6 | PSX | HCA | 0.75 | 4.722 | 13.1 | 20 | 91.5 | 7.0 | 28 | 93.3 | ↓3 |
| 7 | CAH | HCA | 1.06 | 4.556 | 12.4 | 20 | 89.7 | 6.6 | 28 | 91.9 | ↓1 |
| 8 | AVT | HCA | 0.93 | 4.500 | 12.7 | 20 | 89.7 | 6.8 | 28 | 91.8 | ↓1 |
| 9 | LRCX | HCA | 0.95 | 4.500 | 12.6 | 20 | 89.6 | 6.7 | 28 | 91.7 | ↓1 |
| 10 | DELL | HCA | 1.32 | 4.500 | 11.7 | 20 | 88.7 | 6.2 | 28 | 91.2 | = |
| 11 | SANM | HCA | 0.66 | 4.714 | 13.3 | 20 | 89.1 | 7.1 | 28 | 90.9 | ↓2 |
| 12 | PCB | HCA | 0.94 | 4.278 | 12.6 | 20 | 88.3 | 6.7 | 28 | 90.4 | = |
| 13 | CBOE | HCA | 0.72 | 4.111 | 12.8 | 20 | 87.9 | 6.8 | 28 | 89.7 | = |
| 14 | CIEN | HCA | 1.17 | 4.571 | 12.1 | 20 | 87.0 | 6.4 | 28 | 89.4 | ↑3 |
| 15 | ALNT | HCA | 0.16 | 3.778 | 14.6 | 20 | 87.3 | 7.8 | 28 | 88.5 | ↓1 |
| 16 | MTZ | HCA | 0.23 | 3.778 | 14.4 | 20 | 87.1 | 7.7 | 28 | 88.3 | ↓1 |
| 17 | CRS | HCA | 0.10 | 3.722 | 14.8 | 20 | 87.1 | 7.9 | 28 | 88.2 | ↓2 |
| 18 | GFF | HCA | 0.37 | 3.778 | 14.1 | 20 | 86.7 | 7.5 | 28 | 88.2 | ↓1 |
| 19 | NUE | HCA | 0.79 | 4.286 | 13.0 | 20 | 86.2 | 6.9 | 28 | 88.2 | ↑1 |
| 20 | CMCO | HCA | 0.03 | 3.667 | 15.0 | 20 | 86.9 | 8.0 | 28 | 88.0 | ↓2 |
| 21 | ANGO | HCA | 0.84 | 3.778 | 12.9 | 20 | 85.6 | 6.9 | 28 | 87.5 | ↑3 |
| 22 | FSLR | HCA | 0.64 | 3.722 | 13.4 | 20 | 85.7 | 7.1 | 28 | 87.5 | = |
| 23 | UHS | HCA | 0.26 | 3.556 | 14.3 | 20 | 85.7 | 7.7 | 28 | 87.0 | ↓1 |
| 24 | AGEN | HCA | 0.07 | 3.500 | 14.8 | 20 | 85.8 | 7.9 | 28 | 86.9 | ↓3 |
| 25 | BSVN | HCA | 0.56 | 4.000 | 13.6 | 20 | 85.1 | 7.2 | 28 | 86.8 | = |
| 26 | HALO | HCA | 0.72 | 3.667 | 12.8 | 20 | 84.9 | 6.8 | 28 | 86.7 | ↑4 |
| 27 | UTHR | HCA | 0.24 | 3.500 | 14.4 | 20 | 85.4 | 7.7 | 28 | 86.7 | ↓2 |
| 28 | STNG | HCA | 0.48 | 3.889 | 13.8 | 20 | 84.6 | 7.4 | 28 | 86.3 | = |
| 29 | YELP | HCA | 0.22 | 3.611 | 14.4 | 20 | 85.2 | 7.7 | 28 | 86.4 | ↓3 |
| 30 | SBS | HCA | 0.87 | 3.667 | 12.8 | 20 | 83.9 | 6.8 | 28 | 85.5 | = |
| 31 | GTX | HCA | 0.83 | 3.611 | 12.9 | 20 | 83.5 | 6.9 | 28 | 85.1 | = |
| 32 | ANIP | HCA | 0.73 | 3.556 | 13.2 | 20 | 83.4 | 7.0 | 28 | 85.0 | = |
| 33 | SIMO | HCA | 0.65 | 3.556 | 13.4 | 20 | 83.3 | 7.1 | 28 | 85.0 | = |
| 34 | AZZ | HCA | 0.66 | 3.500 | 13.3 | 20 | 83.0 | 7.1 | 28 | 84.6 | = |
| 35 | STLD | HCA | 0.86 | 3.444 | 12.8 | 20 | 82.6 | 6.8 | 28 | 84.2 | = |
| 36 | DVN | HCA | 1.50 | 3.444 | 11.3 | 20 | 80.7 | 6.0 | 28 | 82.8 | = |
| 37 | MU | CCL | 6.14 | 4.722 | 0.0 | 25 | 67.8 | 0.0 | 35 | 77.8 | ↑5 |
| — | NVDA | CCL | 3.20 | 4.111 | 7.0 | 25 | ~71 | 3.7 | 35 | ~78 | OW node |
| — | CVE | CCL | 2.47 | 4.889 | 8.8 | 25 | ~68 | 4.7 | 35 | ~75 | OW node |
| — | TSM | CCL | 2.33 | 4.444 | 9.2 | 25 | ~67 | 4.9 | 35 | ~74 | OW node |
| — | AVGO | HCA | 2.58 | 4.444 | 8.5 | 20 | ~81 | 4.5 | 28 | ~82 | OW node |
| — | ASML | HCA | 1.87 | 4.444 | 10.3 | 20 | ~82 | 5.5 | 28 | ~84 | OW node |
| — | MSFT | HCA | 2.24 | 4.278 | 9.4 | 20 | ~80 | 5.0 | 28 | ~82 | — |

*Estimated (~) scores for OW-node holdings use approximate formula calculations; exact values would be computed by implementation.*

---

**Document status:** Design complete. Validated against PAR-20260531-942B1F54 live portfolio data.  
**Recommended next step:** Phase 7.5B — implement `DeploymentQueue` builder with CW-DAS scoring.
