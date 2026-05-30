# Unified Portfolio Optimizer Design

**Phase 7.3 — Architecture Design**
**Document type:** Next-generation architecture specification
**Status:** Design proposal — not implemented

---

## 1. Design Objective

Replace the current sequential, gap-first recommendation pipeline with a unified
optimizer that answers a single question:

> **"What action creates the largest net portfolio improvement?"**

instead of:

> **"What vehicle fills this node gap?"**

This shift changes the architecture's center of gravity from allocation mechanics
to portfolio quality. Drift repair is one input to the optimizer — not the
controlling variable.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    UNIFIED PORTFOLIO OPTIMIZER (UPO)                    │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  INPUT ASSEMBLY LAYER                                            │  │
│  │                                                                  │  │
│  │  • AllocationAlignmentResult[]   (drift, severity, per node)     │  │
│  │  • SecurityIntelligenceOverlay[] (ESS, composite, replay)        │  │
│  │  • HoldingStrategicProfile[]     (STI tier, trim score, overlap) │  │
│  │  • PortfolioMandate              (CONCENTRATED_ALPHA, etc.)       │  │
│  │  • InvestableVehicleRegistry     (ETF universe)                  │  │
│  │  • ExposureDecomposition         (node weights per holding/ETF)   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  CANDIDATE GENERATION LAYER                                      │  │
│  │                                                                  │  │
│  │  For each underweight node (MODERATE+ severity):                 │  │
│  │    A. Pull all portfolio securities in target node               │  │
│  │    B. Pull all registered ETF vehicles for target node           │  │
│  │    C. Union → candidate set C(node)                              │  │
│  │                                                                  │  │
│  │  For each overweight node (MODERATE+ severity):                  │  │
│  │    A. Pull all portfolio securities in overweight node           │  │
│  │    B. Rank by trim_priority_score (descending)                   │  │
│  │    C. → trim candidate set T(node)                               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  PORTFOLIO IMPROVEMENT SCORING LAYER                             │  │
│  │                                                                  │  │
│  │  For each candidate c in C(node):                                │  │
│  │    PIS(c) = Σ(dimension weights × dimension scores)              │  │
│  │                                                                  │  │
│  │  Dimensions (see Section 4):                                     │  │
│  │    • Node Coverage Score     (D1)                                │  │
│  │    • Conviction Quality      (D2)                                │  │
│  │    • Concentration Impact    (D3, penalty if additive)           │  │
│  │    • Overlap Penalty         (D4)                                │  │
│  │    • Cross-Node Conflict     (D5, penalty if conflicts exist)    │  │
│  │    • Mandate Compatibility   (D6, INFORMATIONAL = near-zero)     │  │
│  │    • Deployment Efficiency   (D7)                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  CONFLICT DETECTION LAYER                                        │  │
│  │                                                                  │  │
│  │  Run conflict detection algorithms:                              │  │
│  │    T1: Direct node conflict check                                │  │
│  │    T2: Vehicle redundancy check                                  │  │
│  │    T3: PMI-engine contradiction check                            │  │
│  │                                                                  │  │
│  │  Apply conflict resolution rules (suppress / merge / demote)     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  RECOMMENDATION ASSEMBLY LAYER                                   │  │
│  │                                                                  │  │
│  │  Assign recommendation tier to each surviving action:            │  │
│  │    HIGH_CONVICTION_BUY    PIS ≥ 65, no conflicts                 │  │
│  │    REPLAY_OPPORTUNITY     PIS ≥ 50, replay_supported = True      │  │
│  │    ALLOCATION_REPAIR      PIS ≥ 35, ETF path, no conflict        │  │
│  │    TRIM_RECOMMENDED       trim_priority_score ≥ 60               │  │
│  │    REBALANCE_ONLY         PIS 20–34, node improvement only       │  │
│  │    INFORMATIONAL          conflicts suppressed or mandate INFO    │  │
│  │                                                                  │  │
│  │  Sort output by PIS descending.                                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  CASH DEPLOYMENT MODEL (optional overlay)                        │  │
│  │                                                                  │  │
│  │  Given: deployable_cash = actual_cash% − target_cash%            │  │
│  │  IF deployable_cash > 0:                                         │  │
│  │    Take top N candidates by PIS                                  │  │
│  │    Compute allocation split by PIS weight                        │  │
│  │    Output: "Best use of next $X" ranked deployment list          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Input Assembly Layer

The unified optimizer requires all signal types to be assembled before scoring.
This is the key architectural change from the current pipeline — signals that
are currently computed downstream (Steps 4–6 in the existing flow) must be
available at recommendation generation time.

### Required Inputs at Scoring Time

| Input | Current Source | Available in Time? | Notes |
|-------|---------------|-------------------|-------|
| AllocationAlignmentResult | alignment.py | ✓ Step 2 | No change needed |
| SecurityIntelligenceOverlay | recommendations.py | ✗ Step 4 (after recs) | Must be moved or pre-computed |
| HoldingStrategicProfile | trim_intelligence.py | ✗ Step 6 (after recs) | Must be moved or pre-computed |
| PortfolioMandate | mandate.py | ✓ Step 5 (post-recs) | Needs to gate rec generation |
| ETF exposure decomposition | exposure_decomposition.py | ✓ | Extend to include ETF vehicles |

### Proposed Pre-Computation Sequence

```
run_analysis() orchestration:

1. Ingest + enrich holdings         (no change)
2. Compute alignment                (no change)
3. Build security overlays          (MOVED EARLIER — currently Step 4)
4. Build strategic profiles         (MOVED EARLIER — currently Step 6)
5. Evaluate mandate                 (MOVED EARLIER — currently Step 5)
6. ─── ALL INPUTS NOW AVAILABLE ───
7. Run Unified Portfolio Optimizer  (REPLACES current Step 3 generate_recommendations)
8. Compute multi-dimensional score  (no change)
9. Persist artifacts                (no change)
```

**Implementation note:** Steps 3 and 4 are independent of each other and
independent of Step 7. They can be parallelized. Step 6 requires no changes —
it produces the same artifacts as today.

---

## 4. Portfolio Improvement Score (PIS) Specification

PIS is a single scalar that measures how much net portfolio quality improvement
a given action (buy or trim) creates.

### Full PIS Formula

```
PIS(candidate, action_type) =

  [NODE_COVERAGE_COMPONENT]
  + node_coverage_score(candidate, target_node)   × weight_node_coverage

  [CONVICTION_COMPONENT]
  + conviction_score(candidate)                    × weight_conviction

  [REPLAY_COMPONENT]
  + (30 if replay_supported else 0)                × weight_replay

  [STI_COMPONENT]
  + sti_tier_bonus(candidate)                      × weight_sti

  [CROSS_NODE_IMPACT_COMPONENT]
  − cross_node_conflict_penalty(candidate)         × weight_conflict

  [CONCENTRATION_COMPONENT]
  − concentration_penalty(candidate)               × weight_concentration

  [OVERLAP_COMPONENT]
  − overlap_penalty(candidate)                     × weight_overlap

  [TRIM_PENALTY_COMPONENT — for Buy candidates only]
  − (trim_priority_score / 100) × 20               × weight_trim
```

### Proposed Weights (v1.0)

| Component | Formula | Weight | Max Contribution |
|-----------|---------|--------|-----------------|
| Node Coverage | NCS × 100 | 0.20 | 20 pts |
| Conviction | composite_score × 6 | 0.20 | 30 pts |
| Replay | 30 if supported else 0 | 0.20 | 30 pts |
| STI Tier | CCL=10, HCA=7, TGC=3, WTC=0 | 0.15 | 15 pts |
| Cross-node conflict | −20 if T1 conflict, −8 if T2 | 0.10 | −20 pts |
| Concentration | −15 if worsens existing OW | 0.05 | −15 pts |
| Overlap | −10 if top-10 overlap > 25% | 0.05 | −10 pts |
| Trim penalty | trim_priority_score/100 × 20 | 0.05 | −20 pts |

### PIS Interpretation Scale

| Range | Interpretation |
|-------|---------------|
| ≥ 70 | Exceptional — high-conviction, replay-supported, no conflicts |
| 55–69 | Strong — multiple positive signals, minor penalties |
| 40–54 | Solid — positive expected improvement, some trade-offs |
| 25–39 | Marginal — weak positive expected, use caution |
| 10–24 | Weak — likely REBALANCE_ONLY tier, monitor |
| < 10 | Suppress — no net improvement expected |

### Ranked vs Severity Ordering — Analysis

**Current system:** Recommendations are ordered by allocation drift severity
(HIGH before MODERATE before LOW).

**Proposed system:** Recommendations ordered by PIS descending.

**Pros of PIS ordering:**
- Surfaces the action with the largest expected net improvement first
- Integrates conviction, replay, and node correction into a single rank signal
- Eliminates the problem of a HIGH-severity rec that creates negative net value
  appearing above a MODERATE rec that creates genuine improvement

**Cons of PIS ordering:**
- Less intuitive for users who expect "biggest drift = top rec"
- Requires accurate weights; miscalibrated weights could produce unexpected orderings
- Mandates must be incorporated into PIS (not a separate layer) to avoid a
  HIGH-PIS rec that mandate would actually suppress

**Recommendation:** PIS ordering is correct for the optimization objective. Mandate
compatibility (D6) must be a hard gate — mandate INFORMATIONAL → PIS floored at 0
regardless of other signals — not a soft weight.

---

## 5. Conviction Gate Design

The conviction gate is a pre-filter applied before PIS scoring. Any candidate that
fails the conviction gate is excluded from PIS ranking entirely, not merely penalized.

### Gate Criteria (proposed)

```
CONVICTION_GATE(candidate):

  PASS if ANY of:
    • STI_tier in (CCL, HCA) AND composite_score ≥ 3.5
    • replay_supported = True AND composite_score ≥ 3.0
    • ess_score = BULLISH AND composite_score ≥ 3.5

  SOFT_PASS (eligible for ALLOCATION_REPAIR tier only) if:
    • candidate is ETF AND node_coverage_score ≥ 25%
    • mandate_urgency ≠ INFORMATIONAL

  FAIL (excluded) if:
    • composite_score < 2.0 (or None for ETF)
    • STI_tier = WTC
    • mandate_urgency = INFORMATIONAL (hard gate — mandate is authoritative)
```

For ETFs: No composite score exists. ETFs pass the conviction gate only via
the SOFT_PASS path (node coverage + mandate alignment). SOFT_PASS candidates
cannot reach HIGH_CONVICTION_BUY or REPLAY_OPPORTUNITY tiers.

---

## 6. Recommendation Tier Specification

| Tier | PIS Range | Requirements | PMI Condition | UI Prominence |
|------|-----------|-------------|---------------|---------------|
| HIGH_CONVICTION_BUY | ≥ 65 | CCL/HCA + replay + no conflicts | mandate ≠ INFORMATIONAL | Primary CTA |
| REPLAY_OPPORTUNITY | ≥ 50 | replay_supported + conviction pass | mandate ≠ INFORMATIONAL | Highlighted card |
| ALLOCATION_REPAIR | ≥ 35 | ETF soft-pass + NCS ≥ 25% | mandate ≠ INFORMATIONAL | Standard rec card |
| TRIM_RECOMMENDED | trim ≥ 60 | Any STI class except CCL alone | — | Warning card |
| REBALANCE_ONLY | 20–34 | Positive net improvement | mandate = any | Informational card |
| INFORMATIONAL | < 20 or mandate=INFO | Any | mandatory for INFO | Collapsed/footnote |

**UI guidance:**
- `HIGH_CONVICTION_BUY` and `REPLAY_OPPORTUNITY`: appear in a "Deploy Capital" section
- `TRIM_RECOMMENDED`: appear in a "Reduce Exposure" section
- `ALLOCATION_REPAIR`: appear in a "Balance Allocations" section
- `REBALANCE_ONLY` and `INFORMATIONAL`: collapsed by default, expandable

---

## 7. Cash Deployment Model

### Inputs
- `deployable_cash_pct`: actual_cash% − target_cash%
- `deployable_cash_usd`: total_mv × deployable_cash_pct
- `candidates`: all holdings with PIS > 25, sorted by PIS descending

### Allocation Method: PIS-Weighted

```
weight_i = PIS_i / Σ(PIS for all candidates in top-N)
amount_i = deployable_cash_usd × weight_i
```

### Output Contract

```
{
  "deployable_usd": 9424.18,
  "target_cash_pct": 7.0,
  "actual_cash_pct": 9.00,
  "deployment_candidates": [
    {
      "rank": 1,
      "symbol": "VRT",
      "pis": 76.7,
      "allocated_usd": 2847.50,
      "rationale": "CCL, replay, US Large node, no conflicts"
    },
    ...
  ]
}
```

**Constraint:** Minimum position allocation = $500 (avoid sub-threshold lots).
**Constraint:** No single candidate receives > 40% of deployable cash.

---

## 8. Key Behaviors of the New Architecture

### Behavior 1 — VOO Disappears
Under the new architecture, VOO for US Large:
- NCS = −3% → fails conviction gate hard (ETF, NCS < 10%)
- Cross-node conflict = T1 with HYPER_MEGA → PIS penalty −20
- mandate_urgency = INFORMATIONAL → hard gate, PIS = 0

**Result:** VOO never surfaces as a recommendation under CONCENTRATED_ALPHA mandate
for this portfolio.

### Behavior 2 — VRT, LRCX, DELL Emerge
VRT (PIS 76.7), LRCX (73.6), DELL (73.6):
- 100% US Large node coverage
- CCL/HCA tier, replay-supported
- No cross-node conflicts
- Mandate compatible (no intentional underweight label for direct position sizing)

**Result:** These three surface as HIGH_CONVICTION_BUY candidates in the
"Deploy Capital" section.

### Behavior 3 — Reduce Recs Remain Coherent
REDUCE_HYPER_MEGA, REDUCE_INTERNATIONAL, REDUCE_INTERNATIONAL_LARGE:
- No conflicting Build recs that undermine them (Build recs are suppressed)
- Trim candidates (NVDA, MSFT, AVGO in HYPER_MEGA) surface via TRIM_RECOMMENDED
- The Reduce + Trim pairing is synergistic and coherent

### Behavior 4 — PMI Is Authoritative, Not Additive
Under the new architecture, PMI runs once before recommendation generation and
sets hard gates. It does not annotate completed recommendations after the fact.
The result is a single, coherent recommendation signal — not two signals that
the user must reconcile.

---

## 9. Data Model Changes Required

The unified optimizer requires the following new or modified model fields:

### PortfolioRecommendation (new fields)
```python
portfolio_improvement_score: float          # PIS value
recommendation_tier: str                    # HIGH_CONVICTION_BUY | REPLAY_OPPORTUNITY | etc.
conflict_ids: tuple[str, ...]               # IDs of conflicting recs
conflict_types: tuple[str, ...]             # T1 | T2 | T3
mandate_gate_result: str                    # PASS | SOFT_PASS | FAIL
raw_severity: str                           # preserved original drift severity
node_coverage_score: float                  # D1 value
conviction_score_components: dict           # debug/audit breakdown
```

### No changes needed to:
- PortfolioHolding
- AllocationAlignmentResult
- SecurityIntelligenceOverlay
- HoldingStrategicProfile
- PortfolioMandate

The new architecture is purely additive. Existing data contracts are fully preserved.
