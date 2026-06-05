# Phase 23.6 — Capital Rotation Advisor
## Deliverable 6: Data Contract

**Date:** 2026-06-04
**Status:** Design Phase

---

## 6.1 Input Contracts (Read-Only)

The CRA reads from the following existing PAR outputs. None of these are modified.

### 6.1.1 deployment_queue.json
```
Path: data/portfolio_ingestion/analysis_runs/{run_id}/deployment_queue.json
Schema (existing):
{
  "run_id": str,
  "as_of_date": str,
  "queue": [
    {
      "rank": int,
      "symbol": str,
      "current_weight_pct": float,
      "market_value": float,
      "composite_score": float,
      "narrative_tier": str,        // CCL | HCA
      "replay_supported": bool,
      "deployment_score": float,    // CW-DAS score
      "score_breakdown": {
        "signal": float,
        "replay": float,
        "conviction": float,
        "sizing": float,
        "momentum": float,
        "redundancy_pen": float,
        "conc_pen": float
      },
      "allocation_node": str,       // e.g. "EQUITIES.US.LARGE"
      "policy_type": str | null,
      "policy_annotation": str | null,
      "policy_protected": bool,
      "notes": str
    }
  ]
}
```

### 6.1.2 security_overlays.csv
```
Path: data/portfolio_ingestion/analysis_runs/{run_id}/security_overlays.csv
Key fields consumed by CRA:
  symbol, opportunity_flag, signal_direction, ess_score_text,
  composite_score, is_overweight_vs_target, weight_vs_target,
  market_value, percent_of_portfolio, replay_supported
```

### 6.1.3 strategic_profiles.json  *(if Phase D data available)*
```
Path: data/portfolio_ingestion/analysis_runs/{run_id}/strategic_profiles.json
Key fields consumed by CRA:
  symbol, strategic_classification, trim_priority_score,
  thematic_overlap_clusters, overlap_peers, thematic_redundancy_score,
  trim_rationale, narrative_tier, strategic_anchor_rank
```

### 6.1.4 alignment.csv
```
Path: data/portfolio_ingestion/analysis_runs/{run_id}/alignment.csv
Key fields consumed by CRA:
  node_key, node_label, current_weight_pct, target_weight_pct,
  drift_pct, is_overweight
```

### 6.1.5 tax-state (API)
```
Endpoint: GET /api/operator/tax-state
Response fields consumed by CRA:
  per-symbol tax_bucket (A–E), estimated_gain_loss, holding_days, cost_basis_available
```

### 6.1.6 policies (API)
```
Endpoint: GET /api/operator/policies
Response fields consumed by CRA:
  per-symbol policy_type (DO_NOT_SELL | SELL_LAST | CORE_ANCHOR | PREFERRED_ACCUMULATION | None)
```

---

## 6.2 Output Contracts (New CRA Artifacts)

### 6.2.1 CapitalSourceRecord
```python
@dataclass(frozen=True)
class CapitalSourceRecord:
    symbol:              str
    current_value_usd:   float
    estimated_proceeds:  float       # current_value_usd × sizing_pct
    sizing_pct:          float       # 0.0–1.0
    category:            str         # SIGNAL_DETERIORATION | STRATEGIC_EXIT |
                                     # OVERWEIGHT_REDUCTION | TAX_AWARE_EXIT |
                                     # LOW_CONVICTION_REDUCTION
    priority:            str         # URGENT | HIGH | MODERATE | LOW | DEFER
    evidence_summary:    str
    tax_bucket:          str | None  # A | B | C | D | E | None
    tax_annotation:      str
    policy_type:         str | None
    blocked_by_policy:   bool
    operator_review_required: bool
```

### 6.2.2 RotationDeploymentTarget
```python
@dataclass(frozen=True)
class RotationDeploymentTarget:
    rank:                int
    symbol:              str
    deployment_score:    float       # CW-DAS; unchanged from queue
    allocation_node:     str
    narrative_tier:      str
    current_weight_pct:  float
    suggested_amount:    float       # USD from capital pool
    suggested_pct_add:   float       # percentage point addition (guidance only)
    projected_weight_pct: float      # current + suggested_pct_add (guidance only)
    score_breakdown:     dict        # CwDasBreakdown fields; unchanged
    allocation_note:     str
```

### 6.2.3 PortfolioImpactEstimate
```python
@dataclass(frozen=True)
class PortfolioImpactEstimate:
    alignment_score_before:   float
    alignment_score_after:    float   # approximation
    alignment_delta:          float
    concentration_before:     float   # top-5 weight sum
    concentration_after:      float   # approximation
    concentration_delta:      float
    overweight_nodes_before:  list[str]
    overweight_nodes_after:   list[str]  # nodes that resolve after rotation
    newly_underweight_nodes:  list[str]
    impact_narrative:         str
    is_estimate:              bool = True   # always True; full re-run required for precision
```

### 6.2.4 RotationProposal
```python
@dataclass(frozen=True)
class RotationProposal:
    proposal_id:          str        # CRA-{YYYYMMDD}-{8char hash}
    run_id:               str        # parent PAR run_id
    as_of_date:           str
    portfolio_mv:         float
    total_capital_pool:   float
    sources:              list[CapitalSourceRecord]
    deployments:          list[RotationDeploymentTarget]
    impact:               PortfolioImpactEstimate
    proposal_status:      str        # DRAFT | READY | OPERATOR_REVIEW_REQUIRED
    review_flags:         list[str]  # reasons for OPERATOR_REVIEW_REQUIRED
    created_at_utc:       str
```

---

## 6.3 API Response Schema

### GET /api/cra/proposal
```json
{
  "proposal_id": "CRA-20260604-A1B2C3D4",
  "run_id": "PAR-20260604-XXXXXXXX",
  "as_of_date": "2026-06-04",
  "portfolio_mv": 441200.00,
  "total_capital_pool": 21300.00,
  "proposal_status": "OPERATOR_REVIEW_REQUIRED",
  "review_flags": ["Bucket D position detected: FIS"],
  "sources": [ ... CapitalSourceRecord objects ... ],
  "deployments": [ ... RotationDeploymentTarget objects ... ],
  "impact": {
    "alignment_score_before": 62.1,
    "alignment_score_after": 67.4,
    "alignment_delta": 5.3,
    "concentration_before": 41.2,
    "concentration_after": 39.8,
    "concentration_delta": -1.4,
    "overweight_nodes_before": ["EQUITIES.US.LARGE"],
    "overweight_nodes_after": [],
    "newly_underweight_nodes": [],
    "impact_narrative": "Rotating FIS/CHGG to VRT/ARW/DELL resolves US Large OW and improves alignment by 5.3 pts.",
    "is_estimate": true
  }
}
```

### POST /api/cra/proposal/draft
```json
Request body:
{
  "proposal_id": "CRA-20260604-A1B2C3D4",
  "operator_decisions": [
    { "symbol": "FIS", "action": "INCLUDE" },
    { "symbol": "CHGG", "action": "SKIP" }
  ]
}

Response: { "saved": true, "draft_path": "data/operator/rotation_drafts/CRA-20260604-A1B2C3D4.json" }
```

---

## 6.4 Storage

```
data/operator/rotation_drafts/
  CRA-20260604-A1B2C3D4.json     # persisted draft with operator decisions
  CRA-20260603-XXXXXXXX.json     # prior drafts (not auto-deleted)
```

Rotation drafts are operator-authored artifacts. They do not affect any PAR outputs. They are suitable for export to a trade execution log.

---

## 6.5 Versioning

All CRA output carries a `cra_version` field (e.g., `"1.0"`). If the rotation framework formula changes, the version is incremented and existing drafts retain their original version tag for historical integrity.
