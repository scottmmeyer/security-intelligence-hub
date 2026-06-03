# Conviction Framework Inventory
## Phase 7.6 — Signal Census

**Reference Run:** PAR-20260531-F794D952 (81 holdings, 56.8% replay coverage)
**Scope:** All conviction-related signals, surfaces, and decision frameworks currently in the system

---

## Part 1 — Signal Inventory

### 1.1 Composite Score

| Attribute | Value |
|-----------|-------|
| **Name** | Composite Score |
| **Range** | 1.0 – 5.0 (float) |
| **Source file** | `src/history/analytical_universe_manager.py` |
| **Producing function** | `_compute_composite_score()` (called from universe build) |
| **Description** | Weighted average of up to 4 provider signals. Weights renormalize if any source is absent. |

**Formula:**
```
composite = (ESS × 0.50) + (Zacks × 0.225) + (Danelfin × 0.175) + (Yahoo × 0.10)
            ─────────────────────────────────────────────────────────────────────
                            Σ(weights for available sources)
```

**Thresholds used downstream:**
- ≥ 3.5 → BULLISH
- ≥ 2.0 → NEUTRAL
- < 2.0 → BEARISH

**Where it flows:** `SecurityIntelligenceOverlay.composite_score` → trim score → CW-DAS Signal component → narrative tier gate → recommendations → deployment queue ranking

---

### 1.2 ESS (Starmine Earnings Quality)

| Attribute | Value |
|-----------|-------|
| **Name** | ESS — Earnings Sentiment Score |
| **Range** | Categorical: VERY_BULLISH, BULLISH, NEUTRAL, BEARISH, VERY_BEARISH |
| **Source file** | `src/pipeline/stages/ess_intake_stage.py`, `src/normalize/ess_normalizer.py` |
| **Producing function** | `EssIntakeStage.process()` |
| **Mapping to numeric** | VERY_BULLISH=5.0, BULLISH=4.0, NEUTRAL=3.0, BEARISH=2.0, VERY_BEARISH=1.0 |
| **Weight in composite** | 50% |

**Special behavior:** ESS takes priority over composite in signal direction assignment. Exception: if ESS=BEARISH but composite ≥ 2.5, signal is overridden to NEUTRAL (secondary consensus protection).

**Where it flows:** `SecurityIntelligenceOverlay.ess_score_text` → signal direction → trim score Signal Weakness factor → CW-DAS Momentum component

---

### 1.3 Zacks Rating

| Attribute | Value |
|-----------|-------|
| **Name** | Zacks Rank |
| **Range** | STRONG_BUY (1) → STRONG_SELL (5), mapped 5.0 → 1.0 |
| **Source file** | `src/scoring/fetch_zacks_scores.py` |
| **Producing function** | `fetch_zacks_scores()` |
| **Mapping to numeric** | STRONG_BUY→5.0, BUY→4.0, HOLD→3.0, SELL→2.0, STRONG_SELL→1.0 |
| **Weight in composite** | 22.5% |

---

### 1.4 Danelfin Score

| Attribute | Value |
|-----------|-------|
| **Name** | Danelfin AI Score |
| **Range** | 1–10, normalized to 1.0–5.0 via direct mapping |
| **Source file** | `src/scoring/fetch_danelfin_scores.py` |
| **Producing function** | `fetch_danelfin_scores()` |
| **Weight in composite** | 17.5% |

---

### 1.5 Yahoo Analyst Consensus (ABR)

| Attribute | Value |
|-----------|-------|
| **Name** | Yahoo ABR (Average Broker Recommendation) |
| **Range** | 1.0–5.0 (pre-normalized) |
| **Source file** | `src/scoring/fetch_yahoo_supplemental.py` |
| **Producing function** | `fetch_yahoo_supplemental()` |
| **Weight in composite** | 10% |

---

### 1.6 Signal Direction

| Attribute | Value |
|-----------|-------|
| **Name** | Signal Direction |
| **Range** | BULLISH, NEUTRAL, BEARISH, UNKNOWN |
| **Source file** | `src/portfolio/recommendations.py` |
| **Producing function** | `_compute_signal_direction()` (approx. line 157) |

**Priority logic:**
1. ESS explicit (BULLISH or BEARISH) → use ESS, unless ESS=BEARISH and composite ≥ 2.5 (→ NEUTRAL override)
2. ESS absent or NEUTRAL → derive from composite thresholds
3. Fallback → UNKNOWN

**Where it flows:** `SecurityIntelligenceOverlay.signal_direction` → CW-DAS Momentum component → deployment eligibility gate → narrative tier gate

---

### 1.7 Replay Support

| Attribute | Value |
|-----------|-------|
| **Name** | Replay Supported |
| **Range** | Boolean |
| **Source file** | `src/replay/stock_replay_service.py`, `src/replay/replay_engine.py` |
| **Producing function** | `StockReplayService.is_replay_supported()` (or equivalent) |
| **Source data** | `data/current/replay_inputs.csv` |
| **Description** | True if symbol appears in TOP_N_STRATEGY of any cross-sector or industry-specific replay run. Cross-sector "ALL" replays take first-priority acceptance. |

**Where it flows:** `SecurityIntelligenceOverlay.replay_supported` → CW-DAS Replay component (0 or +20) → narrative tier gate (CCL requirement) → trim score Replay Weakness factor → Phase E explainability cards

---

### 1.8 Replay Percentile

| Attribute | Value |
|-----------|-------|
| **Name** | Replay Percentile |
| **Range** | 0–100 (float) |
| **Source file** | `src/replay/stock_replay_service.py` |
| **Producing function** | `_compute_percentile()` (within replay engine) |
| **Formula** | `percentile = round(rank / n × 100)` where rank is position in tier's top-N, n is total tier candidates |

**Where it flows:** `SecurityIntelligenceOverlay.replay_percentile` → Replay Alignment Score quality component → trim score Replay Weakness factor (percentile < 25 penalized) → Phase E explainability text

---

### 1.9 Narrative Tier (CCL / HCA / TGC)

| Attribute | Value |
|-----------|-------|
| **Name** | Narrative Tier |
| **Range** | CORE_CONVICTION_LEADER, HIGH_CONVICTION_ANCHOR, TACTICAL_GROWTH_CANDIDATE, (WATCH_TRIM_CANDIDATE) |
| **Source file** | `src/portfolio/trim_intelligence.py` |
| **Producing function** | `_assign_narrative_tiers()` (line ~630) |

**Assignment logic:**
```
CORE_CONVICTION_LEADER (CCL):
  - signal_direction == BULLISH
  - replay_supported == True
  - composite_score >= 4.0
  - percent_of_portfolio >= 1.5%
  - trim_priority_score < 30

HIGH_CONVICTION_ANCHOR (HCA):
  - strategic_classification == HIGH_CONVICTION_RETAIN
  (does NOT require replay)

TACTICAL_GROWTH_CANDIDATE (TGC):
  - all other non-trim holdings
```

**Where it flows:** `HoldingStrategicProfile.narrative_tier` → CW-DAS Conviction component (CCL=35, HCA=28, other=10) → deployment queue eligibility → recommendations → explainability cards → UI tier badges

---

### 1.10 Strategic Classification (STI)

| Attribute | Value |
|-----------|-------|
| **Name** | Strategic Classification |
| **Source file** | `src/portfolio/trim_intelligence.py` |
| **Producing function** | `_assign_strategic_classification()` (approx. line 396) |

**Retain classifications:**
| Value | Meaning |
|-------|---------|
| `HIGH_CONVICTION_RETAIN` | Strong signal + replay-backed + low overlap → maps to HCA tier |
| `CORE_COMPOUNDER` | Foundational broad-market anchor |
| `STRATEGIC_CORE` | Fills unique allocation role |
| `THEMATIC_LEADER` | Highest-conviction within a thematic cluster |

**Trim classifications:**
| Value | Meaning |
|-------|---------|
| `REDUCIBLE` | Safe to trim without structural loss |
| `REDUNDANT_EXPOSURE` | Significant overlap with other holdings |
| `CONCENTRATION_RISK` | Contributes to node overweight |

**Where it flows:** HCA tier gate → trim score Strategic Role factor (CRITICAL→-25pts) → deployment eligibility

---

### 1.11 Trim Priority Score

| Attribute | Value |
|-----------|-------|
| **Name** | Trim Priority Score |
| **Range** | 0–100 (float, clamped) |
| **Source file** | `src/portfolio/trim_intelligence.py` |
| **Producing function** | `_compute_trim_priority_score()` (approx. line 198) |
| **Description** | Higher = more candidate for trimming. CCL gate requires score < 30. |

**Factor model (raw sum, then clamped 0–100):**

| Factor | Max Pts | Formula |
|--------|---------|---------|
| Concentration Pressure | +25 | `(overweight_nodes × 8) + min(pct × 0.45, 9)` |
| Thematic Overlap | +25 | `thematic_redundancy × 0.25` |
| Signal Weakness | +20 | BEARISH→20, UNKNOWN→12, NEUTRAL→7, BULLISH→0 (reduced by high composite) |
| Replay Weakness | +15 | not_in_replay→15, percentile<25→15, percentile≥75→0 |
| Allocation Pressure | +10 | Drift magnitude sum in OW nodes |
| Diversification | +5 | `(pct − target) × scale` |
| Strategic Role | −25 to +5 | CRITICAL→−25, HIGH→−15, MEDIUM→0, LOW→+5 |
| Direct Ownership | −5 | Direct stock slightly harder to trim |

---

### 1.12 Strategic Anchor Rank

| Attribute | Value |
|-----------|-------|
| **Name** | Strategic Anchor Rank |
| **Range** | Integer; 1 = highest globally |
| **Source file** | `src/portfolio/trim_intelligence.py` |
| **Producing function** | `_assign_narrative_tiers()` (rank ordering within tier) |

**Anchor score components:**

| Component | Max | Formula |
|-----------|-----|---------|
| Composite | 30 | `composite × 6.0` (capped 30) |
| Replay | 20 | +20 if supported |
| Weight | 15 | `min(pct × 2.5, 15)` |
| ESS Bonus | 10 | VERY_BULLISH→10, BULLISH→7, NEUTRAL→3, BEARISH→0 |
| Retain Bonus | 5 | +5 if HIGH_CONVICTION_RETAIN |
| Trim Penalty | −20 | `−min(trim_score × 0.2, 20)` |
| Diversification | 5 | `min(diversification / 20, 5)` |

---

### 1.13 CW-DAS (Capital-Weighted Deployment Attractiveness Score)

| Attribute | Value |
|-----------|-------|
| **Name** | CW-DAS |
| **Range** | 0–103 (float, practically 0–100 before penalties) |
| **Source file** | `src/portfolio/deployment_queue.py` |
| **Producing function** | `compute_cw_das()` (line ~112) |
| **Version** | CW-DAS-1.0 |

**Formula:**
```
CW-DAS = Signal + Replay + Conviction + Sizing + Momentum − Redundancy_Pen − Conc_Pen
```

| Component | Range | Formula |
|-----------|-------|---------|
| Signal | 0–30 | `min(composite / 5.0 × 30, 30)` |
| Replay | 0 or 20 | `20 if replay_supported else 0` |
| Conviction | 10, 28, or 35 | CCL=35, HCA=28, other=10 |
| Sizing | 0–8 | `8 × max(0, 1 − pct / 6.0%)` |
| Momentum | 0/4/7.5/10 | ESS_BULLISH + signal_BULLISH → 10; one → 7.5; neutral → 4; bearish → 0 |
| Redundancy Pen | 0 or −15 | −15 if holding's allocation node is MODERATE+ overweight |
| Conc Pen | 0 to −20 | `−min((pct − 6%) × 4, 20)` if pct > 6% |

**Constants:** `WARN_POSITION_PCT = 6.0%`, `MAX_POSITION_PCT = 8.0%`, `MIN_CASH_PCT = 2.0%`

**Eligibility filter:** Only `CORE_CONVICTION_LEADER` and `HIGH_CONVICTION_ANCHOR` tiers enter the queue.

---

### 1.14 Thematic Redundancy

| Attribute | Value |
|-----------|-------|
| **Name** | Thematic Redundancy |
| **Range** | 0–100 (float) |
| **Source file** | `src/portfolio/trim_intelligence.py` |
| **Producing function** | Called during `_compute_trim_priority_score()` |
| **Description** | Measures how many other holdings share the same thematic cluster. Higher = more redundant. Used as Thematic Overlap factor in trim score (×0.25). |

---

### 1.15 Portfolio Weight / Headroom

| Attribute | Value |
|-----------|-------|
| **Name** | percent_of_portfolio / headroom_pct |
| **Range** | 0–100 (pct); headroom = max(0, 6.0 − pct) / 6.0 |
| **Source file** | `src/portfolio/ingestion.py`, `src/portfolio/deployment_queue.py` |
| **Producing function** | Ingestion / `build_deployment_queue()` |
| **Description** | Headroom_pct = how far below the 6% soft warn threshold. Used in CW-DAS Sizing component and Concentration Penalty. |

---

### 1.16 Mandate Compatibility

| Attribute | Value |
|-----------|-------|
| **Name** | Mandate Type |
| **Range** | CONCENTRATED_ALPHA, GROWTH, BALANCED, DEFENSIVE, REPLAY_OPTIMIZED |
| **Source file** | `src/portfolio/archetype.py`, `src/portfolio/mandate.py` |
| **Producing function** | `MandateArchetype.from_string()` |
| **Description** | Does NOT directly modify conviction signals. Reinterprets drift semantics (tolerance levels and priority weights). CONCENTRATED_ALPHA allows intentional asymmetry; REPLAY_OPTIMIZED gives replay signals override authority. |

---

## Part 2 — Surface Map

### Surface 1: Capital Deployment Queue

| Attribute | Value |
|-----------|-------|
| **Purpose** | Rank eligible holdings by deployment attractiveness — where new cash should go |
| **Audience** | Portfolio operator (primary action surface) |
| **Decision supported** | "Where do I put new money?" |
| **Inputs consumed** | narrative_tier, composite_score, replay_supported, signal_direction, percent_of_portfolio, allocation drift |
| **Outputs** | Ranked list (CW-DAS score), blocked panel, cash context |
| **Source** | `src/portfolio/deployment_queue.py`, `build_deployment_queue()` |
| **Artifact** | `deployment_queue.json` |
| **Conviction signals used** | Narrative tier (CCL/HCA gate), composite, replay, ESS/signal direction, weight, allocation drift |

---

### Surface 2: Strategic Trim Intelligence (STI) / Strategic Assessment

| Attribute | Value |
|-----------|-------|
| **Purpose** | Classify each holding by retention vs. reduction priority |
| **Audience** | Portfolio operator |
| **Decision supported** | "What should I reduce? What must I keep?" |
| **Inputs consumed** | composite_score, signal_direction, replay_supported, replay_percentile, thematic_redundancy, portfolio_weight, strategic_role, allocation drift |
| **Outputs** | strategic_classification (retain/trim), trim_priority_score (0–100), narrative_tier, strategic_anchor_rank |
| **Source** | `src/portfolio/trim_intelligence.py`, `build_strategic_profiles()` |
| **Artifact** | Embedded in `run_metadata.json` / `holdings.csv` |
| **Conviction signals used** | All signals (most comprehensive consumer) |

---

### Surface 3: Recommendations

| Attribute | Value |
|-----------|-------|
| **Purpose** | Generate actionable portfolio observations — alignment, conviction, allocation |
| **Audience** | Portfolio operator |
| **Decision supported** | "What observations and structural moves are warranted?" |
| **Inputs consumed** | signal_direction, composite_score, narrative_tier, replay_supported, replay_percentile, allocation drift, concentration_risk |
| **Outputs** | PortfolioRecommendation list (ACTION_NEEDED, MONITOR, INFO), severity, rationale |
| **Source** | `src/portfolio/recommendations.py` |
| **Artifact** | `recommendations.json` |
| **Conviction signals used** | signal_direction (primary), replay_supported, narrative_tier |

---

### Surface 4: Security Overlay / Explainability Cards (Phase E)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Per-holding conviction narrative — explain why a holding has the signals it does |
| **Audience** | Portfolio operator seeking individual holding context |
| **Decision supported** | "Why is this ranked where it is? What is driving signal?" |
| **Inputs consumed** | All overlay fields: composite, ess, zacks, danelfin, replay_supported, replay_percentile, signal_direction |
| **Outputs** | Structured narrative sentences, phase E synthesis |
| **Source** | `src/portfolio/phase_e_synthesis.py` |
| **Artifact** | Embedded in run output (`drilldown.json`) |
| **Conviction signals used** | All individual provider signals + replay + tier |

---

### Surface 5: Replay Intelligence

| Attribute | Value |
|-----------|-------|
| **Purpose** | Validate which holdings have replay-backed conviction; measure coverage quality |
| **Audience** | Portfolio operator |
| **Decision supported** | "Is my conviction backed by systematic replay evidence?" |
| **Inputs consumed** | replay_supported, replay_percentile, portfolio_weight |
| **Outputs** | Replay Alignment Score (0–100), coverage %, quality score |
| **Source** | `src/portfolio/scoring.py` (Replay Alignment Score), `src/replay/` |
| **Conviction signals used** | replay_supported, replay_percentile |

---

### Surface 6: Portfolio Quality Score

| Attribute | Value |
|-----------|-------|
| **Purpose** | Aggregate portfolio health across 4 dimensions |
| **Audience** | Portfolio operator (summary / reporting) |
| **Decision supported** | "How healthy is this portfolio overall?" |
| **Inputs consumed** | All signals (aggregated across holdings) |
| **Outputs** | 4 scores (0–100): Allocation Alignment, Portfolio Quality, Implementation Quality, Replay Alignment |
| **Source** | `src/portfolio/scoring.py` |
| **Conviction signals used** | signal_direction (% bullish), strategic_classification (% retain), replay_supported/percentile |

---

### Surface 7: Optimizer

| Attribute | Value |
|-----------|-------|
| **Purpose** | Suggest allocation weight adjustments to close drift gaps |
| **Audience** | Portfolio operator |
| **Decision supported** | "What weight changes close my allocation gaps?" |
| **Inputs consumed** | allocation drift, portfolio weights, mandate type |
| **Outputs** | Suggested add/reduce weight changes |
| **Source** | `src/portfolio/optimizer.py` |
| **Conviction signals used** | Mandate type (indirect); does NOT consume CCL/HCA/CW-DAS directly |

---

## Part 3 — Signal Crosswalk Summary

| Signal | STI | Deploy Queue | Recs | Phase E | Replay | Quality Score | Optimizer |
|--------|-----|-------------|------|---------|--------|---------------|-----------|
| Composite Score | ✅ Primary | ✅ Signal/30 | ✅ | ✅ | — | ✅ | — |
| ESS | ✅ Weakness | ✅ Momentum | ✅ Primary | ✅ | — | ✅ | — |
| Zacks | ✅ (via comp) | ✅ (via comp) | — | ✅ | — | — | — |
| Danelfin | ✅ (via comp) | ✅ (via comp) | — | ✅ | — | — | — |
| Signal Direction | ✅ | ✅ Momentum | ✅ Primary | ✅ | — | ✅ | — |
| Replay Supported | ✅ Weakness | ✅ +20 binary | ✅ | ✅ | ✅ Primary | ✅ | — |
| Replay Percentile | ✅ Weakness | — | ✅ | ✅ | ✅ Quality | — | — |
| Narrative Tier | ✅ Output | ✅ Gate + pts | ✅ | ✅ | — | — | — |
| Strategic Class | ✅ Output | ✅ (via tier) | — | ✅ | — | ✅ | — |
| Trim Score | ✅ Output | — | — | — | — | — | — |
| Anchor Rank | ✅ Output | — | — | — | — | — | — |
| CW-DAS | — | ✅ Output | — | — | — | — | — |
| Portfolio Weight | ✅ Conc | ✅ Sizing/Pen | — | — | — | — | ✅ |
| Thematic Redundancy | ✅ Overlap | — | — | ✅ | — | — | — |
| Mandate Type | ✅ (indirect) | — | ✅ | — | — | — | ✅ Primary |
| Allocation Drift | ✅ Pressure | ✅ Redundancy | ✅ Primary | — | — | ✅ | ✅ |

---

## Part 4 — Reconciliation Burden on Operator

The operator currently receives these independently-calculated conviction signals per holding:

1. **ESS** from overlay
2. **Composite Score** from overlay
3. **Signal Direction** from recommendations
4. **narrative_tier** from STI
5. **strategic_classification** from STI
6. **trim_priority_score** from STI
7. **strategic_anchor_rank** from STI
8. **CW-DAS** from deployment queue
9. **Deployment rank** from deployment queue
10. **replay_supported / replay_percentile** from overlay

For a holding like AEIS:
- Composite = 4.71, ESS = BULLISH → BULLISH signal direction
- narrative_tier = CORE_CONVICTION_LEADER
- strategic_classification = HIGH_CONVICTION_RETAIN
- trim_priority_score = low (< 30)
- strategic_anchor_rank = 1 (or near it)
- CW-DAS = 95.56, deployment_rank = 1
- replay_supported = True

**These all say the same thing.** The operator must mentally confirm that 10 separate signals converge before they can act with confidence. The UCF design (conviction_framework_design.md) collapses this into a single verdict.
