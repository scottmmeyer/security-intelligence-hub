# Phase 22D.9A — Q4: UI Surface Inventory

**Phase:** 22D.9A — CW-DAS Settlement-Aware Deployment Audit  
**Date:** 2026-06-02  
**Scope:** All UI surfaces, API payloads, and data fields that render or carry  
deployable cash values for run PAR-20260602-8CF1CB84

---

## Surface 1: CW-DAS Panel — Cash Context Strip (Portfolio Alignment UI)

**URL:** `/ui/portfolio_alignment/index.html`  
**Component:** Deployment Queue tab → Cash Context strip  
**File:** `app.js` lines 2073–2085  

| UI Label | Field | Value | Source |
|----------|-------|-------|--------|
| Current Cash | `cashCtx.cash_pct` | 8.59% | `cash_context.cash_pct` |
| Mandate Target | `cashCtx.mandate_cash_target_pct` | 7.0% | `cash_context.mandate_cash_target_pct` |
| Excess vs Target | `cashCtx.excess_pct`, `cashCtx.excess_mv` | +1.59% ($7,658) | `cash_context.excess_pct/mv` |
| **Deployable** | **`cashCtx.deployable_mv`** | **$7,658** | **`cash_context.deployable_mv`** |

**Rendered HTML (line 2083):**
```javascript
<div class="dq-cash-ctx-val dq-gold">${formatMV(cashCtx.deployable_mv)}</div>
<div class="dq-cash-ctx-lbl">Deployable</div>
```

**Settlement-aware?** No. Single figure. No pending activity disclosure.

---

## Surface 2: CW-DAS Panel — Summary Strip (Deployable Cash Card)

**URL:** `/ui/portfolio_alignment/index.html`  
**Component:** Deployment Queue tab → Summary strip  
**File:** `app.js` lines 2087–2095  

| UI Label | Field | Value | Source |
|----------|-------|-------|--------|
| **Deployable Cash** | **`cashCtx.deployable_mv`** | **$7,658** | **`cash_context.deployable_mv`** |
| Eligible Candidates | `dq.candidate_count` | 42 | `deployment_queue.candidate_count` |

**Rendered HTML (line 2091):**
```javascript
<div class="dq-summary-val dq-gold">${formatMV(cashCtx.deployable_mv)}</div>
<div class="dq-summary-lbl">Deployable Cash</div>
```

**Settlement-aware?** No. No pending disclosure.

---

## Surface 3: CW-DAS Panel — Deployment Plan Override Hint

**URL:** `/ui/portfolio_alignment/index.html`  
**Component:** Deployment Queue tab → "Recalculate" button hint  
**File:** `app.js` line 2204  

```javascript
<span class="dp-generate-hint">
  Override: allocate custom amount instead of ${formatMV(cashCtx.deployable_mv)}
</span>
```

**Rendered text:** "Override: allocate custom amount instead of $7,658"  
**Settlement-aware?** No. Suggests $7,658 as the baseline for manual override.

---

## Surface 4: Deployment Plan Panel — "Available to Deploy" Card

**URL:** `/ui/portfolio_alignment/index.html`  
**Component:** Deployment Plan tab → Cash Allocation summary  
**File:** `app.js` line 2225  

| UI Label | Field | Value | Source |
|----------|-------|-------|--------|
| **Available to Deploy** | **`plan.deployable_cash`** | **$7,658** | **`deployment_plan.deployable_cash`** |
| Allocated | `pi.total_deployed` | $7,658 | `deployment_plan.portfolio_impact.total_deployed` |
| Remaining | `pi.unallocated_cash` | -$0 | `deployment_plan.portfolio_impact.unallocated_cash` |
| Positions Allocated | count of recs with suggested_add > 0 | 31 | computed in JS |
| Cash Wt Before → After | `pi.cash_before_pct → pi.cash_after_pct` | 8.6% → 7.0% | deployment_plan |

**Rendered HTML (line 2225):**
```javascript
<div class="da-cash-val">${formatMV(plan.deployable_cash)}</div>
<div class="da-cash-lbl">Available to Deploy</div>
```

**Settlement-aware?** No. Shows $7,658 as "Available". The 7.0% "after" projection is false.

---

## Surface 5: Deployment Plan Panel — Tier Allocation Badges

**URL:** `/ui/portfolio_alignment/index.html`  
**Component:** Deployment Plan tab → Tier badges  
**File:** `app.js` lines 2246–2248  

| UI Label | Value | Source |
|----------|-------|--------|
| T1 badge | `1 pos $1,103 (14%)` | `tier_summaries[TIER_1]` |
| T2 badge | `13 pos $3,943 (51%)` | `tier_summaries[TIER_2]` |
| T3 badge | `17 pos $2,612 (34%)` | `tier_summaries[TIER_3]` |

All tier allocations are oversized (proportional fractions of $7,658 instead of $4,092).  
**Settlement-aware?** No.

---

## Surface 6: Deployment Plan Detail — Per-Position "Suggested Add"

**URL:** `/ui/portfolio_alignment/index.html`  
**Component:** Deployment Plan tab → recommendation rows  
**File:** `app.js` (renders `deployment_plan.recommendations`)  

31 recommendations each contain `suggested_add` — the amount CW-DAS proposes to buy.
All are proportionally derived from the reported deployable budget of $7,658.25.

Sample:
| Symbol | Tier | suggested_add (reported) | suggested_add (adjusted) |
|--------|------|--------------------------|--------------------------|
| VRT | T1 | $1,102.54 | $589.01 |
| ARW | T2 | $550.71 | $294.17 |
| ATLC | T2 | $447.65 | $239.20 |

**Settlement-aware?** No. Every recommendation is oversized by 1.87×.

---

## Surface 7: Deployment Plan Detail — "Deployed" and "Impact" Section

**URL:** `/ui/portfolio_alignment/index.html`  
**Component:** Deployment Plan tab → Impact section  
**File:** `app.js` lines 2619–2631  

| UI Label | Field | Value |
|----------|-------|-------|
| Deployed (total) | `plan.total_allocated` | $7,658 |
| Cash Before → After | `impact.cash_before_pct → impact.cash_after_pct` | 8.6% → 7.0% |
| Unallocated Remaining | `impact.unallocated_cash` | -$0 |

The `cash_after_pct = 7.0%` is the most misleading field. It implies the portfolio will
land exactly at the mandate floor, which is only true if settlement never occurs.

**Settlement-aware?** No. Shows 7.0% "after" — true post-settlement value is 6.26%.

---

## Surface 8: API Payload — `GET /api/portfolio/run` (analysis result)

**Endpoint:** `GET /api/portfolio/run?run_id=PAR-20260602-8CF1CB84`  
**Returns:** Full analysis result including embedded `deployment_plan`  

Relevant fields in JSON payload:
```json
{
  "cash_context": {
    "cash_mv": 41279.15,
    "deployable_mv": 7658.25
  },
  "deployment_plan": {
    "deployable_cash": 7658.25,
    "total_allocated": 7658.26,
    "portfolio_impact": {
      "cash_after_pct": 7.0,
      "cash_after_mv": 33620.89,
      "unallocated_cash": -0.01
    }
  }
}
```

**Settlement-aware?** No. No `adjusted_*` or `pending_settlement_*` fields exist.

---

## Surface 9: API Payload — `POST /api/portfolio/deployment-plan`

**Endpoint:** `POST /api/portfolio/deployment-plan`  
**File:** `scripts/run_outcome_ui.py` lines 403–446  
**Purpose:** On-demand deployment plan computation; used when UI recalculates  

The endpoint accepts an optional `deployable_cash` override. If not provided,
uses `cash_context.deployable_mv` from the stored `deployment_queue.json`.

**Default behavior:** uses reported $7,658.25. No settlement adjustment.  
**Override capability:** YES — an operator or caller could pass `4091.70` manually.  
**UI exposes override?** YES — the "Recalculate with Custom Cash Amount" button
sends the run_id with no override by default, defaulting to $7,658.25.  
**Settlement-aware hint in UI?** No. The hint shows "$7,658" as the override baseline.

---

## Surface 10: Persisted Artifacts

| File | Field | Value | Settlement-Aware? |
|------|-------|-------|-------------------|
| `deployment_queue.json` | `cash_context.deployable_mv` | $7,658.25 | No |
| `deployment_plan.json` | `deployable_cash` | $7,658.25 | No |
| `deployment_plan.json` | `portfolio_impact.cash_after_pct` | 7.00% | No (overstated) |
| `deployment_plan.json` | `recommendations[*].suggested_add` | varies | No (all oversized) |
| `recommendations.json` | (separate rec format) | — | No |

---

## Summary: All Deployable Cash Surfaces

| Surface | Location | Value Shown | Settlement-Aware? | Severity |
|---------|----------|-------------|-------------------|----------|
| Cash Context — Deployable card | app.js:2083 | $7,658 | No | High |
| Summary strip — Deployable Cash | app.js:2091 | $7,658 | No | High |
| Plan override hint | app.js:2204 | "$7,658" | No | High |
| Available to Deploy card | app.js:2225 | $7,658 | No | **Critical** |
| Cash Before → After | app.js:2241 | 8.6% → 7.0% | No | **Critical** |
| Tier allocation badges | app.js:2246–2248 | T1/T2/T3 totals | No | High |
| Per-position suggested_add | plan recs | each oversized | No | **Critical** |
| Deployed / Remaining | app.js:2619 | $7,658 / -$0 | No | High |
| API `cash_context` payload | /api/portfolio/run | $7,658.25 | No | High |
| API `deployment_plan` payload | /api/portfolio/run | $7,658.25 | No | **Critical** |
| Persisted deployment_plan.json | file system | $7,658.25 | No | High |

**No surface anywhere in the system displays or transmits a settlement-adjusted figure.**
