# Phase 23.6A — API Contract

**Date:** 2026-06-04

---

## GET /api/cra/proposal

### Description
Returns a RotationProposal built from the latest COMPLETE PAR run.

This endpoint is read-only. It does not modify any PAR run artifacts, scores, or operator state.

### Request
```
GET /api/cra/proposal
```
No parameters required.

### Success Response — 200 OK
```json
{
  "proposal_id":        "CRA-20260604-2844185D",
  "run_id":             "PAR-20260604-E9E5717E",
  "as_of_date":         "2026-06-04",
  "portfolio_mv":       472454.19,
  "total_capital_pool": 99011.20,
  "proposal_status":    "OPERATOR_REVIEW_REQUIRED",
  "review_flags":       ["Capital pool (20.7% of portfolio) exceeds 10% threshold — operator review recommended"],
  "created_at_utc":     "2026-06-04T14:00:00+00:00",
  "cra_version":        "1.0",
  "source_count":       39,
  "deployment_count":   2,
  "sources": [
    {
      "symbol":                    "TSLA",
      "current_value_usd":         14271.50,
      "estimated_proceeds":        14271.50,
      "sizing_pct":                1.0,
      "category":                  "SIGNAL_DETERIORATION",
      "priority":                  "URGENT",
      "evidence_summary":          "ESS=VERY_BEARISH | overweight node",
      "tax_bucket":                "C",
      "tax_annotation":            "Long-term gain ~$2,100 — no deferral concern",
      "policy_type":               "DO_NOT_SELL",
      "blocked_by_policy":         true,
      "operator_review_required":  false,
      "ess_score_text":            "VERY_BEARISH",
      "signal_direction":          "BEARISH",
      "is_overweight":             true,
      "drift_pct":                 4.53,
      "cost_basis":                12171.00,
      "unrealized_gain_loss":      2100.50
    }
  ],
  "deployments": [
    {
      "rank":                 1,
      "symbol":               "VRT",
      "deployment_score":     95.14,
      "allocation_node":      "EQUITIES.US.LARGE",
      "narrative_tier":       "CORE_CONVICTION_LEADER",
      "current_weight_pct":   3.8495,
      "market_value":         18187.35,
      "suggested_amount":     49505.60,
      "suggested_pct_add":    10.4789,
      "projected_weight_pct": 14.3284,
      "score_breakdown":      { "signal": 27.33, "replay": 20.0, "conviction": 35.0, "sizing": 2.87, "momentum": 10.0, "redundancy_pen": 0.0, "conc_pen": 0.0 },
      "headroom_pct":         35.8,
      "allocation_note":      "35.8% headroom available | CCL tier | 36% headroom"
    }
  ],
  "impact": {
    "alignment_score_before":  0.4142,
    "alignment_score_after":   0.5542,
    "alignment_delta":         0.14,
    "concentration_before":    27.4967,
    "concentration_after":     36.8345,
    "concentration_delta":     9.3378,
    "overweight_nodes_before": ["EQUITIES.INTERNATIONAL", "EQUITIES.US.MEGA.ULTRA_MEGA"],
    "overweight_nodes_after":  ["EQUITIES.INTERNATIONAL", "EQUITIES.US.MEGA.ULTRA_MEGA"],
    "newly_underweight_nodes": [],
    "impact_narrative":        "Rotating 28 position(s) into 2 CW-DAS target(s) | improves alignment by ~0.140 pts.",
    "is_estimate":             true
  }
}
```

### Error Responses

| Status | Condition | Body |
|--------|-----------|------|
| 404 | No manifest found | `{"error": "No portfolio manifest found. Run a portfolio analysis first."}` |
| 404 | No COMPLETE runs | `{"error": "No COMPLETE portfolio analysis run found. Run a portfolio analysis first."}` |
| 404 | Required PAR files missing | `{"error": "Required PAR files missing: ..."}` |
| 500 | Unexpected error | `{"error": "CRA proposal generation failed: ..."}` |

---

## Data Contract Details

### CapitalSourceRecord fields

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Holding ticker |
| `current_value_usd` | float | Current market value |
| `estimated_proceeds` | float | `current_value_usd × sizing_pct` |
| `sizing_pct` | float | 0.0–1.0; fraction of position to liquidate |
| `category` | string | `SIGNAL_DETERIORATION \| STRATEGIC_EXIT \| OVERWEIGHT_REDUCTION \| TAX_AWARE_EXIT \| LOW_CONVICTION_REDUCTION` |
| `priority` | string | `URGENT \| HIGH \| MODERATE \| LOW \| DEFER` |
| `evidence_summary` | string | Human-readable rationale (merged if multi-category) |
| `tax_bucket` | string\|null | `A \| C \| D` (B and E require holding_days — not yet supported) |
| `tax_annotation` | string | Tax context description |
| `policy_type` | string\|null | Active operator policy type |
| `blocked_by_policy` | bool | True if DO_NOT_SELL; excluded from capital pool but visible in source list |
| `operator_review_required` | bool | True if CORE_ANCHOR, Bucket D, or large pool |
| `ess_score_text` | string\|null | ESS text from overlay |
| `signal_direction` | string\|null | Signal direction from overlay |
| `is_overweight` | bool | True if `is_overweight_vs_target=True` |
| `drift_pct` | float\|null | Maximum positive drift across allocation nodes |
| `cost_basis` | float\|null | From holdings.csv |
| `unrealized_gain_loss` | float\|null | `market_value − cost_basis` |

### RotationDeploymentTarget fields

| Field | Type | Description |
|-------|------|-------------|
| `rank` | int | CW-DAS rank (IMMUTABLE from deployment_queue.json) |
| `symbol` | string | Holding ticker |
| `deployment_score` | float | CW-DAS score (IMMUTABLE) |
| `allocation_node` | string | Derived allocation node key |
| `narrative_tier` | string | `CORE_CONVICTION_LEADER \| HIGH_CONVICTION_ANCHOR` |
| `current_weight_pct` | float | Current portfolio weight |
| `market_value` | float | Current market value |
| `suggested_amount` | float | USD capital allocated from pool (guidance) |
| `suggested_pct_add` | float | Percentage point addition (guidance) |
| `projected_weight_pct` | float | `current_weight_pct + suggested_pct_add` (guidance) |
| `score_breakdown` | object | CwDasBreakdown (IMMUTABLE copy from queue) |
| `headroom_pct` | float | From CW-DAS queue (how far below WARN threshold) |
| `allocation_note` | string | Why this amount was suggested |

### proposal_status values

| Value | Meaning |
|-------|---------|
| `DRAFT` | No sources or deployments; rotation not actionable |
| `READY` | Sources and deployments present; no review flags |
| `OPERATOR_REVIEW_REQUIRED` | CORE_ANCHOR, Bucket D, large pool, or concentration flag |
