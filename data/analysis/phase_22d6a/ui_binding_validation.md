# UI Binding Validation — Phase 22D.6A
**File:** `ui/portfolio_alignment/app.js`  
**Audit Date:** 2026-06-02  
**Verdict:** UI BINDINGS ARE CORRECT — fields absent from stale artifact, not bad JS

---

## 1. Cash Context Strip (lines 2050–2084)

### Source of `cashCtx`:

```javascript
const cashCtx = dq.cash_context || {};
```

Where `dq = data.deployment_queue` — the parsed `deployment_queue.json` artifact from the run.

### Mandate Target binding:

```javascript
const _cashTargetPct = cashCtx.mandate_cash_target_pct != null
  ? parseFloat(cashCtx.mandate_cash_target_pct).toFixed(1)
  : "—";
```

- **Field read:** `cashCtx.mandate_cash_target_pct`
- **Stale artifact has:** `__MISSING__` (key not present)
- **Null-check result:** `null != null` evaluates false → renders `"—"`
- **Binding verdict:** ✅ CORRECT — reads right field name; field absent in artifact

### Excess vs Target binding:

```javascript
const _cashExcessPct = cashCtx.excess_pct != null
  ? parseFloat(cashCtx.excess_pct).toFixed(2)
  : "—";
const _cashExcessMv = cashCtx.excess_mv != null
  ? formatMV(cashCtx.excess_mv)
  : "—";
```

- **Fields read:** `cashCtx.excess_pct`, `cashCtx.excess_mv`
- **Stale artifact has:** both missing
- **Result:** renders `"—"` for both
- **Binding verdict:** ✅ CORRECT — reads right field names; fields absent in artifact

### Deployable amount:

```javascript
<div class="dq-cash-ctx-val dq-gold">${formatMV(cashCtx.deployable_mv)}</div>
```

- **Field read:** `cashCtx.deployable_mv`
- **Stale artifact has:** `31692.2` (computed with 2% floor)
- **Renders:** `$31,692.20` — wrong value, but correct binding to existing field

---

## 2. Deployment Plan Summary (`_daCashSummaryHtml`, lines 2213–2254)

### Cash Wt Before → After:

```javascript
const pi = plan.portfolio_impact || {};

<div class="da-cash-val">
  ${pi.cash_before_pct != null ? parseFloat(pi.cash_before_pct).toFixed(1) : "—"}%
  →
  ${pi.cash_after_pct != null ? parseFloat(pi.cash_after_pct).toFixed(1) : "—"}%
</div>
```

- **Fields read:** `plan.portfolio_impact.cash_before_pct`, `plan.portfolio_impact.cash_after_pct`
- **Stale artifact has:** `cash_before_pct: 8.6115`, `cash_after_pct: 2.0`
- **Renders:** `8.6% → 2.0%` — wrong value but correct binding
- **Binding verdict:** ✅ CORRECT — reads right field names; stale artifact has wrong value in field

### Available to Deploy:

```javascript
<div class="da-cash-val">${formatMV(plan.deployable_cash)}</div>
```

- **Field read:** `plan.deployable_cash`
- **Stale artifact has:** `31692.2`
- **Renders:** `$31,692.20`
- **Binding verdict:** ✅ CORRECT — reads right field; value wrong in artifact

---

## 3. Generate Deployment Plan button (`_dpGeneratePlan`, line 2561)

```javascript
function _dpGeneratePlan() {
  const plan = _analysisResult && _analysisResult.deployment_plan;
  if (plan && plan.recommendations && plan.recommendations.length > 0) {
    _dpRenderPlan(plan);  // ← uses pre-loaded deployment_plan.json from artifact
    return;
  }
  // Fallback: fetch on-demand from backend
  fetch("/api/portfolio/deployment-plan", { ... body: JSON.stringify({ run_id }) })
```

- **Primary path:** Uses pre-loaded `deployment_plan` from run artifact. Since `deployment_plan.json` exists for this run, the API is **never called** — the stale plan is used directly.
- **Fallback path (if plan absent):** Calls `/api/portfolio/deployment-plan` which reads `deployable_mv` from the stale `deployment_queue.json` (= $31,692.20) — also wrong.
- **Both paths are poisoned by the stale artifact.**

---

## 4. Allocation Map — Why It Shows 7.0% Correctly

The Allocation Map reads from a completely different data path:

```javascript
const cashCtx = data.cash_mandate_context || "";
```

Where `data.cash_mandate_context` is the text output of `get_cash_interpretation()` from `src/portfolio/mandate.py`.

This function reads the YAML allocation targets directly (or uses the alignment result) — it does **not** read `deployment_queue.json`. That is why the Allocation Map correctly shows `CASH: 7.0%` while the Deployment Queue shows wrong values.

The two panels read cash targets from entirely separate code paths:

| UI Panel | Data Source | Cash Target Source |
|---|---|---|
| Allocation Map | `data.cash_mandate_context` (mandate interpretation) | YAML via `mandate.py` — always fresh |
| Deployment Queue | `data.deployment_queue.cash_context` | `deployment_queue.json` artifact — stale |

---

## 5. Summary

| UI Element | Field Read | Stale Artifact Value | Expected Value | Root Cause |
|---|---|---|---|---|
| Mandate Target | `cashCtx.mandate_cash_target_pct` | MISSING | 7.0% | Field absent in pre-22D6 artifact |
| Excess vs Target | `cashCtx.excess_pct` / `cashCtx.excess_mv` | MISSING | +1.61% ($7,724.82) | Field absent in pre-22D6 artifact |
| Deployable Cash | `cashCtx.deployable_mv` | $31,692.20 | $7,724.82 | Wrong floor (2%) in pre-22D6 artifact |
| Cash Wt After | `pi.cash_after_pct` | 2.0% | 7.0% | Wrong deployable amount in stale plan |

**All 4 app.js field bindings are semantically correct.** The bug is not in the JavaScript — it is in the persisted JSON artifacts generated before Phase 22D.6 code was in place.
