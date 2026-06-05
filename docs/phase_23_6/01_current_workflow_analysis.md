# Phase 23.6 — Capital Rotation Advisor
## Deliverable 1: Current Workflow Analysis

**Date:** 2026-06-04
**Status:** Design Phase

---

## 1.1 How the System Currently Identifies Sell Signals

The system produces sell signals through four distinct and disconnected mechanisms:

### Mechanism A: opportunity_flag Assignment
**Location:** `src/portfolio/recommendations.py` → `build_security_overlays()`

Each `SecurityIntelligenceOverlay` receives an `opportunity_flag` derived from:

| Condition | Flag Assigned |
|-----------|--------------|
| ESS BEARISH or VERY_BEARISH + overweight node | TRIM |
| ESS BEARISH, not overweight | WATCH |
| ESS BULLISH | HOLD (or ACCUMULATE if in queue) |
| No signal direction | HOLD |

**Critical Gap:** The flag is a binary per-holding label with no capital quantity estimate.

### Mechanism B: Strategic Trim Intelligence (STI)
**Location:** `src/portfolio/recommendations.py` → `_generate_strategic_trim_recs()`  
**Model:** `src/portfolio/models.py` → `HoldingStrategicProfile`

STI assigns each holding a `strategic_classification`:
- `REDUCIBLE` — highest trim priority in cluster
- `REDUNDANT_EXPOSURE` — better peers exist
- `CONCENTRATION_RISK` — high weight + high thematic concentration
- `HIGH_CONVICTION_RETAIN` — core, preserve
- `CORE_COMPOUNDER` — foundational exposure

STI also produces:
- `trim_priority_score` (0–100; higher = more expendable)
- `thematic_overlap_clusters` (AI_INFRA, SEMICONDUCTOR_CONCENTRATION, etc.)
- `trim_rationale` (explainability string)

**Critical Gap:** STI identifies *which* holding to trim but produces no quantity estimate and no downstream linkage to what to buy with the proceeds.

### Mechanism C: Alignment Overweight Reduction
**Location:** `src/portfolio/recommendations.py` → `generate_recommendations()`  
**Type:** `REDUCE_OVERWEIGHT`

When an allocation node drifts above target (e.g., `EQUITIES.US.LARGE` at +12% vs. target), the system generates a `REDUCE_OVERWEIGHT` recommendation listing implicated symbols but no dollar amount.

**Critical Gap:** No proceeds estimate, no rotation target.

### Mechanism D: Policy-Gated Sell List
**Location:** `src/portfolio/operator_policy.py` → `build_sell_execution_list()`

Applies DO_NOT_SELL and SELL_LAST policy filters to produce a sell-eligible cohort. This is purely a filter — not a capital routing mechanism.

**Critical Gap:** Produces a filtered list of symbols but no rotation pairing.

---

## 1.2 How the System Currently Identifies Buy Signals

**Location:** `src/portfolio/deployment_queue.py` → `build_deployment_queue()`  
**Model:** `DeploymentCandidate`

The deployment queue is the system's BUY recommendation mechanism. CW-DAS ranks all eligible holdings by:

| Component | Weight | Description |
|-----------|--------|-------------|
| signal | 0–30 | composite_score contribution |
| replay | 0 or 20 | binary gate on replay_supported |
| conviction | 35/28/10 | CCL, HCA, or other narrative tier |
| sizing | 0–8 | headroom below WARN_POSITION_PCT |
| momentum | 0–10 | ESS + signal direction alignment |
| redundancy_pen | 0 or –15 | overweight node penalty |
| conc_pen | 0–20 | concentration penalty |

**Eligibility gates:** replay_supported=True, signal_direction=BULLISH, strategic_classification=HIGH_CONVICTION_RETAIN, narrative_tier in {CCL, HCA}.

**Critical Gap:** The queue shows what to buy but has no knowledge of where the capital comes from.

---

## 1.3 The Disconnection Map

```
SELL SURFACE                    │  BUY SURFACE
─────────────────────────────── │ ──────────────────────────────
opportunity_flag = TRIM         │  DeploymentCandidate rank 1
STI: REDUCIBLE                  │  DeploymentCandidate rank 2
REDUCE_OVERWEIGHT               │  DeploymentCandidate rank 3
Policy sell list                │  DeploymentCandidate rank N
                                │
        ← NO BRIDGE EXISTS →
```

The operator must:
1. Read the sell surface outputs
2. Estimate proceeds mentally
3. Match to deployment queue manually
4. Assess portfolio impact without tooling

---

## 1.4 What the Capital Rotation Advisor Must Close

| Gap | Symptom | CRA Solution |
|-----|---------|-------------|
| No capital quantity | Sell flags are binary | CapitalSourceRecord with estimated proceeds |
| No rotation pairing | Buy and sell live in separate panels | RotationProposal linking sell → buy |
| No proceeds-to-queue mapping | Operator does this manually | Proceed allocation engine |
| No impact simulation | Operator guesses alignment delta | AlignmentDelta computation |
| No tax integration | Tax state exists but disconnected from sell ordering | TaxContext field on CapitalSourceRecord |
| No capital source categories | All sells look the same | 5-category taxonomy |

---

## 1.5 What the CRA Must NOT Do

Per non-negotiable constraints:

- Must not modify or re-score CW-DAS rankings
- Must not modify ESS scoring or signal direction logic
- Must not introduce new signal providers
- Must not modify replay logic or Danelfin scoring
- Must not replace FMI or Policy engine behavior
- Must not issue trade instructions — guidance only
