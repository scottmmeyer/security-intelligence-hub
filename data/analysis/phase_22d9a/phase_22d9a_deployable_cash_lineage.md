# Phase 22D.9A — Q1: Deployable Cash Lineage Trace

**Phase:** 22D.9A — CW-DAS Settlement-Aware Deployment Audit  
**Date:** 2026-06-02  
**Run:** PAR-20260602-8CF1CB84  
**Target value traced:** `deployable_mv = $7,658.25`

---

## Lineage Diagram

```
Fidelity CSV export
  (Portfolio_Positions_Jun-02-2026 (2).csv)
       │
       │  Row: account=Z35123695, symbol=PENDING ACTIVITY, mv=-$3,566.55
       │  Row: account=X20548022, symbol=SPAXX, mv=$69.51
       │  Row: account=Z35123695, symbol=SPAXX, mv=$41,209.64
       ↓
src/portfolio/ingestion.py
  _parse_fidelity_csv() → _classify_operational_state()
       │
       │  PENDING ACTIVITY mv=-$3,566.55 → operational_state="ACCOUNTING_ADJUSTMENT"
       │  SPAXX mv=$69.51 → operational_state="CASH_EQUIVALENT", is_cash_equivalent=True
       │  SPAXX mv=$41,209.64 → operational_state="CASH_EQUIVALENT", is_cash_equivalent=True
       │
       │  Line 416: total_mv = sum(r["market_value"] for r in raw_rows)
       │            = all rows including -$3,566.55
       │            = $480,298.55  ← UNCONDITIONED SUM
       ↓
PortfolioSnapshot
  .total_market_value = $480,298.55
  .holdings = [all PortfolioHolding objects, including ACCOUNTING_ADJUSTMENT]
       │
       ↓
src/portfolio/runner.py
  Line 558: _INVESTABLE_STATES = frozenset({"ACTIVE_POSITION", "CASH_EQUIVALENT"})
  Line 559: investable = [h for h in enriched if h.operational_state in _INVESTABLE_STATES]
       │
       │  ACCOUNTING_ADJUSTMENT is NOT in _INVESTABLE_STATES
       │  → PENDING ACTIVITY holding is excluded from investable list
       │  → investable includes SPAXX ($69.51) + SPAXX ($41,209.64) = $41,279.15
       │
       │  Lines 721–725:
       │    cash_context = compute_deployable_cash(
       │        holdings=investable,                           ← no PENDING ACTIVITY
       │        total_market_value=snapshot.total_market_value, ← $480,298.55 (includes -$3,566.55)
       │        mandate_cash_target_pct=7.0,
       │    )
       ↓
src/portfolio/deployment_queue.py :: compute_deployable_cash()
  Line 427: cash_mv = sum(h.market_value for h in holdings if h.is_cash_equivalent)
            = $69.51 + $41,209.64
            = $41,279.15  ← PRE-SETTLEMENT SPAXX ONLY
       │
  Line 428: cash_pct = $41,279.15 / $480,298.55 × 100 = 8.5945%
  Line 433: effective_floor_pct = max(2.0, 7.0) = 7.0%
  Line 434: floor_mv = $480,298.55 × 7.0 / 100 = $33,620.90
  Line 439: deployable_mv = max(0.0, $41,279.15 - $33,620.90) = $7,658.25
       │
       │  Returns dict:
       │    {"cash_mv": 41279.15, "cash_pct": 8.5945,
       │     "mandate_cash_target_pct": 7.0, "effective_floor_pct": 7.0,
       │     "floor_mv": 33620.9, "excess_mv": 7658.25, "excess_pct": 1.5945,
       │     "deployable_mv": 7658.25, "deployable_pct": 1.5945}
       ↓
runner.py :: dq_payload
  Line 730: {"cash_context": cash_context, ...}
  Serialized to: deployment_queue.json → cash_context.deployable_mv = 7658.25
       │
       │  Line 784–786:
       │    deployment_plan = build_deployment_plan(
       │        deployment_queue_data=dq_payload,
       │        deployable_cash=None,   ← explicit None: use cash_context
       │    )
       ↓
src/portfolio/deployment_planner.py :: build_deployment_plan()
  Line 114: if deployable_cash is None:
  Line 115:     deployable_cash = float(cash_ctx.get("deployable_mv", 0.0))
                                 = 7658.25
       │
       │  Rank-weighted proportional allocation:
       │    weight_i = deployment_score_i × conviction_mult_i / sqrt(rank_i)
       │    raw_alloc_i = (weight_i / total_weight) × deployable_cash
       │                = (weight_i / total_weight) × $7,658.25
       │
       │  Per-position WARN cap applied, overflow redistributed.
       │
       │  total_allocated = $7,658.26 (rounding artifact)
       │  unallocated_cash = $7,658.25 - $7,658.26 = -$0.01
       ↓
deployment_plan.json
  deployable_cash: 7658.25
  total_allocated: 7658.26
  portfolio_impact.cash_before_mv: 41279.15
  portfolio_impact.cash_after_mv:  33620.89   (= 41279.15 - 7658.26)
  portfolio_impact.cash_before_pct: 8.5945%
  portfolio_impact.cash_after_pct:  7.0%
  recommendations[0].suggested_add: $1,102.54  (VRT, Tier 1)
  recommendations[1].suggested_add: $550.71    (ARW, Tier 2)
  ... (31 total with non-zero suggested_add)
       ↓
API: GET /api/portfolio/run → returns analysis result including deployment_plan
API: POST /api/portfolio/deployment-plan → re-computes using deployable_cash from
     cash_context unless overridden by caller
       ↓
ui/portfolio_alignment/app.js :: _daCashSummaryHtml(plan)
  Line 2225: plan.deployable_cash        → "Available to Deploy" = $7,658
  Line 2233: pi.unallocated_cash         → "Remaining"           = -$0
  Line 2619: plan.total_allocated        → "Deployed" (plan view) = $7,658

ui/portfolio_alignment/app.js :: cashContextHtml
  Line 2083: cashCtx.deployable_mv       → "Deployable" card      = $7,658
  Line 2091: cashCtx.deployable_mv       → "Deployable Cash" summary card = $7,658
  Line 2204: cashCtx.deployable_mv       → override hint text = "$7,658"
```

---

## Key Decision Points in the Lineage

### Decision Point 1: ingestion.py line 416 — `total_market_value`

```python
total_mv = sum(r["market_value"] for r in raw_rows)  # UNCONDITIONED
```

Includes PENDING ACTIVITY (-$3,566.55). This makes `total_market_value = $480,298.55`
(which is $3,566.55 lower than the true post-settlement portfolio value of $483,865.10).

**Effect on deployable cash:** Understates floor by $249.66.

### Decision Point 2: runner.py line 559 — `investable` filter

```python
investable = [h for h in enriched if h.operational_state in _INVESTABLE_STATES]
```

`ACCOUNTING_ADJUSTMENT` is excluded. PENDING ACTIVITY does NOT reduce `cash_mv`.

**Effect on deployable cash:** Overstates `cash_mv` by $3,566.55 (full pending debit ignored).

### Decision Point 3: deployment_planner.py line 114–115 — `deployable_cash` source

```python
if deployable_cash is None:
    deployable_cash = float(cash_ctx.get("deployable_mv", 0.0))
```

When called from runner.py with `deployable_cash=None`, the planner unconditionally uses
the reported (pre-settlement) `deployable_mv = $7,658.25` as the total capital budget
for ALL allocation recommendations.

**This is the propagation point where the overstatement reaches CW-DAS recommendation sizing.**

---

## Summary

| Stage | Value | Correct? |
|-------|-------|---------|
| total_market_value (ingestion) | $480,298.55 | Slightly understated (by $249.66) |
| cash_mv (SPAXX only) | $41,279.15 | Overstated (by $3,566.55) |
| floor_mv | $33,620.90 | Slightly understated (by $249.66) |
| deployable_mv (reported) | $7,658.25 | Overstated (by $3,566.55) |
| deployable_cash (plan budget) | $7,658.25 | Overstated (by $3,566.55) |
| total_allocated | $7,658.26 | All allocations proportionally oversized |
| suggested_add per position | varies | Each oversized by factor ≈ 1.87× |
