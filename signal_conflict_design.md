# Signal Conflict Design — SIGNAL-GOV-02

**Date:** 2026-06-15  
**Status:** Design Phase

---

## Problem Statement

SIH deployment recommendations are driven by a composite signal (ESS 55%, Zacks 25%, Yahoo ABR 10%, Danelfin 10%). Some symbols with a positive composite score carry explicit **sell** recommendations from one or more Street analysts. The operator's stated preference is to avoid deploying new capital when a reputable source explicitly recommends SELL.

This document defines the conflict taxonomy, signal source inventory, and governance design options to evaluate.

---

## Signal Source Inventory

### Tier 1: Sources Actively Scoring the Composite

| Source | Weight | System Field | Coverage |
|--------|--------|-------------|----------|
| LSEG StarMine ESS | 55% | `starmine_ess_text` | ~2,400 symbols |
| Zacks Investment Research | 25% | `zacks_score` (1–5) | ~2,400 symbols |
| Yahoo Finance ABR | 10% | `abr` (1.0–5.0) | ~2,400 symbols |
| Danelfin AI | 10% | `danelfin_raw` (1–10) | ~2,660 symbols |

### Tier 2: ESS Sub-Sources (Within StarMine Composite)

The LSEG StarMine ESS aggregates recommendations from multiple analyst providers. Based on ESS export history, confirmed sub-sources available in SIH data:

| Source | ESS Column Available | Notes |
|--------|---------------------|-------|
| Jefferson Research | ✅ Column in ESS export | Explicit hold/buy/sell |
| Zacks Investment Research | ✅ Column in ESS export | Overlaps Tier 1 |
| McLean Capital Management | ✅ Column in ESS export | Boutique quant |
| Trading Central | Within ESS | Not exported separately; contributes to ESS score |
| Refinitiv/Verus | Within ESS | Not exported separately; contributes to ESS score |
| ISS-EVA | Within ESS | Not exported separately |
| Argus Quant | Within ESS | Not exported separately |
| Argus Analyst | Within ESS | Not exported separately |

**Note:** Trading Central, Refinitiv/Verus, ISS-EVA, Argus Quant, and Argus Analyst are **ESS sub-providers only**. Their individual opinions are not available as separate data fields in the current SIH data architecture. They influence the ESS composite score but cannot be isolated.

### Tier 3: Aggregate Street Consensus (FMP)

The FMP grades/consensus file provides **aggregate Wall Street analyst counts**:

| Field | Description |
|-------|-------------|
| `buy_count` | Analysts with BUY recommendation |
| `strong_buy_count` | Analysts with STRONG BUY |
| `hold_count` | Analysts with HOLD |
| `sell_count` | Analysts with SELL |
| `strong_sell_count` | Analysts with STRONG SELL |
| `total_analysts` | Total coverage count |
| `consensus_label` | BUY / HOLD / SELL |

This is the **primary actionable conflict signal** — it aggregates the views of all covered analysts including Trading Central, Refinitiv/Verus, Argus, and others into a single measurable count.

---

## Conflict Level Taxonomy

### Level 0 — Full Alignment
No explicit sell votes. Consensus label = BUY.

**ESS criteria:** BULLISH or VERY_BULLISH  
**Zacks criteria:** Score ≥ 3 (NEUTRAL or better)  
**FMP criteria:** sell_count = 0, strong_sell_count = 0  
**Yahoo criteria:** ABR ≤ 2.5 (Buy/Strong Buy zone)

Examples in current data: VRT (18B/1H/0S), MTZ (32B/4H/0S), ATLC (5B/1H/0S), CAH (18B/15H/0S)

---

### Level 1 — Mild Conflict
No explicit sell votes but HOLD consensus or high hold ratio (>40% holds).

**Characteristics:** Analyst community is cautious but not bearish.

Examples in current data: PCB (1B/4H/0S — HOLD consensus), CAH (18B/15H/0S — 45.5% holds)

---

### Level 2 — Moderate Conflict
One or more explicit sell votes, but BUY consensus maintained.  
Sell rate typically < 15%.

**Characteristics:** Minority bearish dissent. BUY consensus intact.

Examples in current data: DELL (2S/45), LRCX (1S/50), NUE (3S/32), CRS (1S/21), SANM (2S/17), ARW (2S/17), PSX (2S/35), MU (2S/70), NVDA (3S/79)

---

### Level 3 — Significant Conflict
Multiple sell votes, sell rate ≥ 15%, or HOLD consensus despite some buy votes.

**Characteristics:** Material analyst disagreement. Deployment caution warranted.

Examples in current data: TSLA (15S/81 — 18.5% sell), AVT (4S/20 — 20% sell), CBOE (4S/31 — 12.9% sell + 2 strong buys), GTX (2S/8 — HOLD consensus + 25% sell)

---

### Level 4 — Severe Conflict
High-accuracy or high-conviction sources are explicitly split: one prominent source BUY, another prominent source SELL.

**Characteristics:** Named source disagreement (e.g., Trading Central = Buy + Refinitiv/Verus = Sell).

**Current data limitation:** This level requires individual source opinions, which are not available for ESS sub-providers. Level 4 cannot be automatically computed from current SIH data. It must be manually annotated based on operator research.

Example: NUE (per operator research) — Trading Central (score 98) = Buy, Refinitiv/Verus (score 86) = Sell. This would be classified as **L4 per operator annotation**, though the aggregate FMP data shows only L2.

---

## Governance Option Evaluation

### Option A — No Action
Continue using composite scoring. Conflicts are informational only.  
**Verdict:** Insufficient given operator stated preference. Not recommended.

### Option B — Conflict Warning Badge
Display `CONFLICTING_SIGNAL` or `HIGH_ANALYST_DISAGREEMENT` badge prominently in deployment queue.  
**Verdict:** Strongly supported by evidence. Low cost, high operator value.

### Option C — Operator Review Required (Level ≥ 3)
Level 3+ conflict requires explicit acknowledgement before deployment.  
**Verdict:** Reasonable for Level 3 (TSLA, AVT, GTX in current holdings). Premature for Level 2.

### Option D — Ranking Penalty
Conflict levels reduce deployment ranking score (e.g., −3 pts per sell vote).  
**Verdict:** Unsupported by backtest evidence. Attribution data does not show worse outcomes for L2 symbols. Not recommended at this data maturity.

### Option E — Hard Block
Severe conflict prevents deployment.  
**Verdict:** No empirical justification at N=28. Not recommended. May re-evaluate at N=100+.

---

## Recommended Design: Option B with Option C for Level 3+

**Phase 1 (Now):**
- Display `CONFLICTING_SIGNAL` badge for Level 2 symbols in deployment queue
- Display `SIGNIFICANT_CONFLICT` badge for Level 3 symbols with sell rate info
- Display `HOLD_CONSENSUS` badge for Level 1 symbols (PCB-style)
- No ranking changes, no deployment blocks

**Phase 2 (at operator request or 100+ attribution records):**
- Level 3+ triggers operator acknowledgement requirement before deployment
- Level 4 (operator-annotated) triggers mandatory review comment

**Phase 3 (future):**
- Wire conflict level into composite score penalty if empirical evidence develops
