# Phase 23.6 — Capital Rotation Advisor
## Deliverable 2: Capital Source Taxonomy

**Date:** 2026-06-04
**Status:** Design Phase

---

## Overview

A capital source is a holding (or partial position) that is a candidate for liquidation to fund redeployment into higher-conviction targets. The CRA defines five canonical capital source categories, each with distinct detection logic, evidence requirements, and sizing heuristics.

All categories are READ from existing system outputs. No new scoring logic is introduced.

---

## Category 1: Signal Deterioration

**Definition:** A holding whose composite signal score has degraded to BEARISH or VERY_BEARISH, indicating the investment thesis is weakening.

**Detection Source:**
- `SecurityIntelligenceOverlay.signal_direction` = `BEARISH` or `VERY_BEARISH`
- `SecurityIntelligenceOverlay.opportunity_flag` = `TRIM` or `WATCH`
- `SecurityIntelligenceOverlay.ess_score_text` in `{BEARISH, VERY_BEARISH}`

**Evidence Fields (read from overlay):**
- `composite_score` — current signal level
- `ess_score_text` — ESS textual direction
- `zacks_rating` — supplemental confirmation

**Priority Ranking:**
- Signal = VERY_BEARISH → URGENT
- Signal = BEARISH, overweight node → HIGH
- Signal = BEARISH, not overweight → MODERATE

**Sizing Heuristic:**
- Full position if signal = VERY_BEARISH and no DO_NOT_SELL policy
- 50% reduction if signal = BEARISH and overweight
- 25% reduction if signal = BEARISH, not overweight (operator discretion)

**Policy Interaction:**
- DO_NOT_SELL → blocked (display only, no capital estimate surfaced)
- SELL_LAST → downranked within cohort
- CORE_ANCHOR → operator confirmation gate in UI

---

## Category 2: Strategic Exit

**Definition:** A holding where the strategic role has been superseded — a better vehicle exists for the same exposure, the holding is thematically redundant within its cluster, or a deliberate portfolio construction decision has rendered the holding expendable.

**Detection Source:**
- `HoldingStrategicProfile.strategic_classification` in `{REDUCIBLE, REDUNDANT_EXPOSURE}`
- `HoldingStrategicProfile.trim_priority_score` ≥ 60
- `HoldingStrategicProfile.thematic_redundancy_score` ≥ 50

**Evidence Fields (read from HoldingStrategicProfile):**
- `trim_factors` — tuple of named factor contributions
- `overlap_peers` — symbols with shared thematic exposure
- `trim_rationale` — explainability string
- `thematic_overlap_clusters` — cluster labels

**Priority Ranking:**
- `REDUCIBLE` with trim_priority_score ≥ 80 → HIGH
- `REDUNDANT_EXPOSURE` with high-conviction peer in deployment queue → HIGH
- `REDUCIBLE` with trim_priority_score 60–79 → MODERATE

**Sizing Heuristic:**
- Full exit if `REDUCIBLE` and a dominant peer covers the same thematic exposure
- Partial (50%) if `REDUNDANT_EXPOSURE` and no clear replacement in queue

**Policy Interaction:**
- Same as Category 1

---

## Category 3: Overweight Reduction

**Definition:** A holding that participates in an allocation node that is overweight its target, where the drift requires structural correction.

**Detection Source:**
- `SecurityIntelligenceOverlay.is_overweight_vs_target` = `True`
- `AllocationAlignmentResult.drift_pct` > 0 for the holding's allocation node
- `PortfolioRecommendation.rec_type` = `REDUCE_OVERWEIGHT`

**Evidence Fields:**
- `overlay.weight_vs_target` — overweight magnitude
- `alignment.drift_pct` — node-level drift
- `alignment.node_label` — allocation node description

**Priority Ranking:**
- drift_pct > 15% → HIGH
- drift_pct 8–15% → MODERATE
- drift_pct < 8% → LOW (monitor only)

**Sizing Heuristic:**
- Proceeds required = drift_pct × portfolio_total_mv / 100
- Distribute across implicated holdings by trim_priority_score (highest first)
- Operator retains final sizing authority

**Policy Interaction:**
- DO_NOT_SELL → exclude from proceeds calculation; recompute drift using remaining holdings
- Highest trim_priority holding in overweight node is the default candidate

---

## Category 4: Tax-Aware Exit

**Definition:** A holding where tax considerations make near-term liquidation advantageous — either because a loss position can offset gains elsewhere, or because a position approaching long-term status warrants deferral.

**Detection Source (read from existing Phase 23.0A tax infrastructure):**
- `PortfolioHolding.cost_basis` present and below current `market_value`
- `tax_state` bucket = A (harvest candidate) or E (defer — approaching LT threshold)
- `holding_days` inferred from tax state

**Tax Action Bucket Reference (existing Phase 23.0A schema):**

| Bucket | Label | CRA Implication |
|--------|-------|-----------------|
| A | Loss harvest candidate | Elevate in sell ordering |
| B | Short-term gain, no special action | Neutral |
| C | Long-term gain, acceptable | Neutral |
| D | Long-term gain, significant | Downweight; operator review |
| E | Approaching LT threshold | Defer; exclude from rotation unless thesis broken |

**Sizing Heuristic:**
- Bucket A: full position or enough to offset realized gains
- Bucket E: defer (surface as "watch" only, not active capital source)

**Policy Interaction:**
- Tax is a modifier to priority ranking, not a standalone trigger
- Does not override DO_NOT_SELL or CORE_ANCHOR

---

## Category 5: Low Conviction Reduction

**Definition:** A holding that is not in the deployment queue, not flagged for strategic exit, but where the absence of strong conviction signals (ESS NEUTRAL, no replay support, mid-tier STI classification) makes it an opportunity cost position.

**Detection Source:**
- `SecurityIntelligenceOverlay.opportunity_flag` = `HOLD`
- `HoldingStrategicProfile.strategic_classification` = `TACTICAL_GROWTH` or `STRATEGIC_CORE` (not top-tier)
- `SecurityIntelligenceOverlay.replay_supported` = `False`
- Not present in `DeploymentCandidate` queue

**Priority Ranking:**
- No replay + NEUTRAL ESS + size > 3% → MODERATE
- No replay + NEUTRAL ESS + size 1–3% → LOW
- Below 1% → do not surface (de minimis)

**Sizing Heuristic:**
- Partial reduction to fund a higher-priority deployment candidate
- Operator discretion; CRA shows headroom calculation only

**Policy Interaction:**
- PREFERRED_ACCUMULATION policy → exclude from this category entirely

---

## Category Priority Stack

When multiple categories apply to the same holding, priority order is:

```
1. Signal Deterioration (thesis broken — highest urgency)
2. Strategic Exit (construction correction)
3. Overweight Reduction (structural alignment)
4. Tax-Aware Exit (efficiency harvesting)
5. Low Conviction Reduction (opportunity cost)
```

A holding may appear in multiple categories simultaneously. The CRA surfaces all applicable categories but uses the highest-priority category for proceeds estimation.

---

## Capital Source Summary Schema

Each capital source instance carries:

```
CapitalSourceRecord:
  symbol              str        # holding ticker
  current_value_usd   float      # current market value
  estimated_proceeds  float      # estimated liquidation value (current_value × sizing_pct)
  sizing_pct          float      # 0.0–1.0
  category            str        # SIGNAL_DETERIORATION | STRATEGIC_EXIT | OVERWEIGHT_REDUCTION | TAX_AWARE_EXIT | LOW_CONVICTION_REDUCTION
  priority            str        # URGENT | HIGH | MODERATE | LOW
  evidence_summary    str        # human-readable rationale
  tax_bucket          str | None # A–E from Phase 23.0A, if available
  policy_type         str | None # active operator policy, if any
  blocked_by_policy   bool       # True if DO_NOT_SELL prevents execution
```
