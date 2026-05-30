# Hierarchical Allocation Model

## Overview

The SIH Hierarchical Allocation Model defines how strategic portfolio targets are structured, computed, governed, and evolved over time. It is implemented across `src/allocation/`, `config/allocation_*.yaml`, and `scripts/recalculate_allocation_targets.py`.

---

## Model Components

### 1. Structural Policy (`config/allocation_policy.yaml`)

The investment policy statement equivalent. Defines hard limits:

- `cash_floor_pct` — minimum cash allocation at all times
- `max_digital_assets_pct` — cap on digital asset exposure
- `max_mega_concentration_pct` — cap on US mega-cap subtree
- `max_micro_cap_pct` — cap on combined micro-cap nodes
- `max_single_asset_class_pct` — no single asset class exceeds this
- `min_international_pct` — minimum international + emerging exposure
- `max_single_recalculation_delta_pct` — single-cycle change limit
- `confidence_threshold` — minimum evidence confidence to accept a proposed delta

### 2. Dimension Nodes (`config/allocation_dimensions.yaml`)

All 30 hierarchy nodes. Each node knows its position in the tree and how to find relevant replay data:

```yaml
- key: EQUITIES.US.MEGA
  label: "US Mega Cap"
  parent_key: EQUITIES.US
  dimension_type: MARKET_CAP
  hierarchy_level: 3
  children:
    - EQUITIES.US.MEGA.HYPER_MEGA
    - EQUITIES.US.MEGA.ULTRA_MEGA
    - EQUITIES.US.MEGA.EXTENDED_MEGA
  replay_filter_mapping:
    filter_market_cap_bucket: MEGA
    filter_geography: US
  replay_sophistication: HIGH
```

### 3. Methodology Basis (`config/allocation_methodology.yaml`)

The investment rationale for each node's baseline target. Covers:

- `evidence_basis` — list of research/analytical reasons for the target
- `risk_factors` — known risks to monitor
- `baseline_target_pct_of_parent` — the seed percentage
- `confidence_level` — HIGH / MEDIUM / LOW

This YAML is the **source of truth for first-run seeding** and for LOW/NONE nodes that never receive evidence-driven updates.

### 4. Strategic Allocation Targets

Each `StrategicAllocationTarget` represents the approved target for one node at one recalculation snapshot:

| Field | Description |
|-------|-------------|
| `target_pct_of_parent` | % allocation within the parent node's sub-portfolio |
| `target_pct_of_total` | % of total portfolio (propagated from ancestry chain) |
| `prior_target_pct_of_total` | previous cycle's value |
| `delta_pct` | change from prior cycle |
| `confidence_score` | 0.0–1.0 based on evidence quality |
| `evidence_ids` | links to supporting evidence records |
| `policy_bounded` | whether policy ceiling was applied |

### 5. Evidence Records

Each `AllocationEvidence` record links a metric to a node:

- `REPLAY_OUTPERFORMANCE` — relative return evidence from replay data
- `FACTOR_PERSISTENCE` — outperformance persistence score (0–1)
- `VOLATILITY_WARNING` — high volatility penalty flag
- `METHODOLOGY_BASELINE` — static rationale for LOW/NONE nodes

### 6. Tactical Overlays

Short-term momentum tilts that sit *above* strategic targets. Equity-only. Must not exceed governance bounds. Applied by `tactical_overlay.py` to produce `AllocationRecommendation`.

### 7. Allocation Recommendation

The final output after applying tactical overlays and enforcing policy ceilings:

```
effective_target_pct = strategic_target_pct + tactical_overlay_pct
                       (bounded by policy ceiling)
```

---

## Recalculation Cycle

```
1. Load policy + dimensions + methodology
2. Load existing targets (or seed from methodology on first run)
3. Extract replay evidence → AllocationEvidence per node
4. Propose recalculation:
   a. For each HIGH-sophistication node with evidence:
      evidence_weight = outperformance_persistence × (1 − volatility_penalty)
      proposed_delta  = (evidence_weight − 0.5) × max_delta × 2
   b. Apply governance caps (max_recalculation_delta_pct)
   c. Apply minimum meaningful change threshold
   d. Renormalize siblings proportionally (sum invariant)
   e. Recompute pct_of_total for all nodes
5. Compute effective allocations (strategic + overlays)
6. Run 8 validators
7. Print change_summary + validator results
8. On --commit: publish to data/current/, archive snapshot, update manifest
```

---

## Data Flow Diagram

```
config/allocation_policy.yaml
        │
        ▼
StructuralPolicy ─────────────────────────────────────┐
                                                       │
config/allocation_dimensions.yaml                      │
        │                                              │
        ▼                                              │
AllocationDimensionNode[30] ─────────────────────┐    │
                                                  │    │
config/allocation_methodology.yaml               │    │
        │                                         │    │
        ▼                                         │    │
AllocationMethodologyBasis[30]                    │    │
        │                                         │    │
        ▼                                         │    │
extract_seed_targets()                            │    │
        │                                         │    │
data/current/replay_inputs.csv                   │    │
data/current/replay_performance_series.csv       │    │
        │                                         │    │
        ▼                                         │    │
AllocationEvidence[n] ────────────────────────────┤    │
                                                  │    │
        ▼                                         ▼    │
propose_recalculation() ◄──── AllocationDimensionNode ─┘
        │
        ▼
StrategicAllocationTarget[30]
        │
        ▼
compute_effective_allocations() ◄── TacticalMomentumOverlay
        │
        ▼
AllocationRecommendation[30]
        │
        ▼
run_all_validators() ── 8 validators (must all pass for --commit)
        │
        ▼
save_proposed_targets() → data/allocation/proposed/
[--commit] publish_proposed_targets() → data/current/ + archive
```

---

## Validators Reference

| # | Name | What it checks |
|---|------|----------------|
| 1 | `hierarchy_sums` | Every parent's children sum to 100.0 ±0.01 |
| 2 | `policy_bounds` | pct_of_total ≤ asset class ceilings; cash ≥ floor |
| 3 | `tactical_overflow` | strategic + max_overlay ≤ ceiling (equity only) |
| 4 | `overlay_staleness` | No ACTIVE overlay with past expiry_date |
| 5 | `recalculation_churn` | \|delta_pct\| ≤ max_recalculation_delta_pct |
| 6 | `evidence_alignment` | Evidence direction matches delta sign |
| 7 | `concentration_ceilings` | Mega/digital/micro concentration within policy |
| 8 | `lineage_completeness` | Required fields present; evidence_ids non-empty |

---

## Seed Percentages (Review-Sensitive)

These are the initial methodology YAML seed values. They represent investment policy statement starting positions, not static truths. Evidence-driven recalculation will adjust equity nodes over time.

| Level 1 | % |
|---------|---|
| EQUITIES | 70% |
| FIXED_INCOME | 20% |
| DIGITAL | 4% |
| COMMODITIES | 4% |
| CASH | 2% |

Within EQUITIES: US 72%, International 20%, Emerging 8%.  
Within US: Mega 45%, Large 30%, Mid 15%, Small 7%, Micro 3%.  
Mega subtiers: Hyper 35%, Ultra 35%, Extended 30%.
