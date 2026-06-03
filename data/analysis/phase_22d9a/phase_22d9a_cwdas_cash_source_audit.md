# Phase 22D.9A — Q2: CW-DAS Cash Source Audit

**Phase:** 22D.9A — CW-DAS Settlement-Aware Deployment Audit  
**Date:** 2026-06-02  
**Run:** PAR-20260602-8CF1CB84  
**Question:** Does CW-DAS use reported or adjusted deployable cash for sizing?

---

## Verdict: CW-DAS Uses REPORTED Deployable Cash

The answer to the phase question is definitively:

> **A. Reported Deployable Cash**
>
> `deployable_cash = $7,658.25` — derived from pre-settlement SPAXX balance.
> No settlement adjustment is applied at any stage of the recommendation engine.

---

## 1. Deployment Plan — `deployable_cash` Field

**File:** `deployment_plan.json` (PAR-20260602-8CF1CB84)  
**Field:** `deployable_cash: 7658.25`

This is the operative capital budget that drives every `suggested_add` figure.

**Source trace:**

```
deployment_planner.py :: build_deployment_plan() lines 114–115:

    if deployable_cash is None:
        deployable_cash = float(cash_ctx.get("deployable_mv", 0.0))
```

`deployable_mv` in `cash_context` = $7,658.25 (reported, pre-settlement).

No override is passed from `runner.py` — `deployable_cash=None` is explicit:

```
runner.py line 786:
    deployment_plan = build_deployment_plan(
        deployment_queue_data=dq_payload,
        deployable_cash=None,   # use computed deployable_mv from cash_context
    )
```

---

## 2. "Available to Deploy" — UI Card

**File:** `ui/portfolio_alignment/app.js` line 2225  
**HTML:** `<div class="da-cash-val">${formatMV(plan.deployable_cash)}</div>`  
**Label:** "Available to Deploy"  
**Rendered value:** $7,658

**Source:** `deployment_plan.deployable_cash` = $7,658.25

---

## 3. "Allocated" — UI Card

**File:** `ui/portfolio_alignment/app.js` line 2233 (references `pi.total_deployed`)  
**Also:** line 2619: `plan.total_allocated`  
**Rendered value:** $7,658

**Source calculation:**

```
deployment_planner.py:
    total_deployed = sum(rec.suggested_add for rec in recommendations)
                   = $7,658.26

    ← This is the sum of all suggested_add values, which are proportional fractions
       of deployable_cash ($7,658.25). Every position is oversized relative to the
       correct settlement-adjusted budget ($4,091.70).
```

---

## 4. "Remaining" (Unallocated Cash) — UI Card

**File:** `ui/portfolio_alignment/app.js` line 2233: `pi.unallocated_cash`  
**Rendered value:** -$0 (effectively $0 remaining)

**Source calculation:**

```
deployment_planner.py:
    unallocated = round(deployable_cash - total_deployed, 2)
                = round($7,658.25 - $7,658.26, 2)
                = -$0.01
```

This correctly indicates the full reported deployable budget was consumed.
However, from the settlement-adjusted perspective, $3,566.55 was never available.

---

## 5. Per-Position `suggested_add` Sizing

Each allocation is computed as:

```
raw_alloc_i = (weight_i / total_weight) × deployable_cash
            = (weight_i / total_weight) × $7,658.25    ← reported
```

**Verified from deployment_plan.json:**

| Rank | Symbol | Tier | suggested_add | Pct of Total |
|------|--------|------|--------------|--------------|
| 1 | VRT | T1 | $1,102.54 | 14.4% |
| 2 | ARW | T2 | $550.71 | 7.2% |
| 3 | ATLC | T2 | $447.65 | 5.8% |
| 4 | SNX | T2 | $386.97 | 5.1% |
| 5 | PSX | T2 | $345.63 | 4.5% |
| — | (T2: 13 pos) | — | $3,943.37 | 51.5% |
| — | (T3: 17 pos) | — | $2,612.35 | 34.1% |
| **TOTAL** | **31 positions** | — | **$7,658.26** | **100%** |

**If adjusted deployable ($4,091.70) had been used instead:**

Each `suggested_add` would be scaled by factor:  
$4,091.70 / $7,658.25 = **0.5343×**

| Rank | Symbol | Reported suggested_add | Adjusted suggested_add | Oversize |
|------|--------|----------------------|----------------------|---------|
| 1 | VRT | $1,102.54 | $589.01 | +$513.53 |
| 2 | ARW | $550.71 | $294.17 | +$256.54 |
| 3 | ATLC | $447.65 | $239.20 | +$208.45 |
| T2 total | 13 pos | $3,943.37 | $2,107.03 | +$1,836.34 |
| T3 total | 17 pos | $2,612.35 | $1,395.66 | +$1,216.69 |
| **TOTAL** | 31 pos | **$7,658.26** | **$4,091.70** | **+$3,566.56** |

---

## 6. Portfolio Impact Fields

**File:** `deployment_plan.json → portfolio_impact`

| Field | Reported Value | Source | Correct Post-Settlement? |
|-------|---------------|--------|--------------------------|
| `cash_before_pct` | 8.59% | `cash_context.cash_pct` | No — pre-settlement |
| `cash_after_pct` | 7.00% | `(cash_mv_before - total_deployed) / total_mv × 100` | **No** — would be 6.26% post-settlement |
| `cash_before_mv` | $41,279.15 | `cash_context.cash_mv` | No — pre-settlement |
| `cash_after_mv` | $33,620.89 | $41,279.15 - $7,658.26 | **No** — would be $30,054.35 post-settlement |
| `total_deployed` | $7,658.26 | sum of suggested_add | Overstated by $3,566.56 |
| `unallocated_cash` | -$0.01 | deployable - total_deployed | Misleadingly near-zero |

**Corrected `cash_after_mv` calculation:**

```
cash_after_mv (reported) = $41,279.15 - $7,658.26 = $33,620.89  (shows 7.0%)
cash_after_mv (actual)   = $41,279.15 - $7,658.26 - $3,566.55 = $30,054.34
                         = $30,054.34 / $480,298.55 × 100 = 6.26%
                                                       ↑ MANDATE BREACH
```

---

## 7. "Cash Weight Before → After" UI Display

**File:** `app.js` line 2241  
**Rendered:** `8.6% → 7.0%`

This display shows the portfolio transitioning precisely to the mandate target after
deployment. It appears reassuring — but it is only true if settlement never occurs.

**Post-settlement reality:** `8.6% → 6.3%` (mandate breach by 0.74 percentage points).

---

## 8. On-Demand Plan API Endpoint

**Endpoint:** `POST /api/portfolio/deployment-plan`  
**File:** `scripts/run_outcome_ui.py` lines 430–435

```python
cash_arg = float(cash_override) if cash_override is not None else None
plan = build_deployment_plan(dq_data, deployable_cash=cash_arg)
```

The API **does** accept a `deployable_cash` override from the caller. However:
- The UI sends no override: `JSON.stringify({ run_id })` (no `deployable_cash` field)
- Default behavior: uses `deployable_mv` from `cash_context` = $7,658.25
- An operator **could** manually override to $4,091.70, but the UI provides no mechanism

---

## Summary

| Metric | Uses Reported ($7,658) | Uses Adjusted ($4,092) |
|--------|------------------------|------------------------|
| CW-DAS queue scoring | N/A | N/A (score is rank/conviction-based) |
| `deployable_cash` (plan) | **YES** | No |
| Per-position `suggested_add` | **YES** (proportional to $7,658) | No |
| "Available to Deploy" UI | **YES** | No |
| "Allocated" UI | **YES** | No |
| "Cash → After" UI projection | **YES** (shows 7.0%, not 6.3%) | No |
| Mandate breach detection | **No** (not shown) | Would show breach |

**CW-DAS sizing is entirely based on reported deployable cash.
No settlement-aware adjustment exists anywhere in the recommendation engine.**
