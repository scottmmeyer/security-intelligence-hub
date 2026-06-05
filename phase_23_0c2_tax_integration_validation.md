# Phase 23.0C.2 — Tax Integration Validation
**PAR Run:** PAR-20260603-B66B00E3  
**Source:** `ui/portfolio_alignment/app.js` (v8), lines 260–340 (tax functions), lines 435–621 (`_computePortfolioActions`)  
**Phase:** 23.0C.2 — PAP Validation + Reconciliation Governance Corrections  
**Scope:** Read-only forensic analysis. No code changes.

---

## 1. Scope and Question

This deliverable answers the question: **Does the tax state influence which candidates appear in the Portfolio Action Pipeline (PAP), their priority, or their sort order?**

The Phase 23.0C implementation added tax input fields to the UI. There was a risk that `_taxState` might have been inadvertently passed into `_computePortfolioActions` or used as a ranking signal. This audit confirms whether that risk materialized.

---

## 2. Tax State Architecture

### 2.1 Module-Level State Variable

`_taxState` is a module-level variable in `app.js`, initialized as:

```js
let _taxState = {
  tax_year:                    null,
  net_realized_ytd:            null,
  potential_additional_losses: null,
  capital_loss_carryforward:   null,
};
```

It is populated on page load via `loadTaxState()` (GET `/api/operator/tax-state`) and updated by `saveTaxState()`.

**Operator state file values for PAR-20260603-B66B00E3:**
```json
{
  "tax_year": 2026,
  "net_realized_ytd": null,
  "potential_additional_losses": null,
  "capital_loss_carryforward": null,
  "strategic_exit_symbols": ["FIS"]
}
```

All tax fields are null in the current operator state. No tax capacity has been entered for this run.

### 2.2 Tax Display Functions

`updateTaxComputed()` (lines 260–275) computes display-only values:
```js
const available = Math.max(0, -ytd + carry);  // realized losses + carryforward
const projected = available + addl;            // + potential additional losses
```

Results are written to DOM elements `taxAvailableCapacity` and `taxProjectedCapacity`. These are display values only — they are never stored back into `_taxState` and are never read by any PAP function.

### 2.3 Tax Persistence Function

`saveTaxState()` (lines 293–332) POSTs to `/api/operator/tax-state`, updates `_taxState` on success, and then:

```js
if (_analysisResult) renderPortfolioActionPipeline(_analysisResult);
```

This re-render call passes `_analysisResult` (the unchanged PAR result), not `_taxState`. The PAP re-renders with identical input data. Tax save is a UI refresh trigger, not a data mutation for the pipeline.

---

## 3. Code-Level Isolation Proof

### 3.1 `_computePortfolioActions` Signature

```js
function _computePortfolioActions(data) {
```

The function accepts exactly one argument: `data` — the full PAR result object (contains `security_overlays`, `recommendations`, `deployment_queue`, `holdings`, etc.).

**`_taxState` is not passed as an argument. It never could be implicitly injected because JavaScript does not capture outer scope variables into named function arguments.**

### 3.2 Static Code Analysis — Tax References Inside `_computePortfolioActions`

```
_taxState references in _computePortfolioActions:  0
_readTaxInputs references in _computePortfolioActions:  0
"tax" substring references in _computePortfolioActions:  0
```

Zero tax-related identifiers appear anywhere inside `_computePortfolioActions` (lines 435–621, ~186 lines of logic). This is confirmed by programmatic substring search of the extracted function body.

### 3.3 Execution Flow from Tax Save to Pipeline Render

```
saveTaxState()
  └─ POST /api/operator/tax-state (persist to disk)
  └─ _taxState = { ...inputs }       (update module state)
  └─ updateTaxComputed()             (update DOM display elements)
  └─ renderPortfolioActionPipeline(_analysisResult)
       └─ _computePortfolioActions(_analysisResult)  ← only PAR data used
            └─ cat1: iterate security_overlays → signal flags/scores
            └─ cat2: iterate _strategicExitSymbols
            └─ cat3: iterate recommendations (REDUCE_OVERWEIGHT)
            └─ cat4: iterate security_overlays → size/flag/score filters
```

At no point in this chain does `_taxState` enter the PAP computation. The `renderPortfolioActionPipeline` call after `saveTaxState` is purely cosmetic — it ensures the accordion UI reflects the current analysis state, but produces identical pipeline output to the previous render.

---

## 4. Intended Design vs. Actual Implementation

### 4.1 Intended Design

Tax capacity context is intentionally a **display-only advisory tool**. The operator sees:
- Available tax capacity: realized losses already shield future gains
- Projected tax capacity: with potential additional harvesting losses included

This context helps the operator make informed decisions about which PAP candidates to act on (e.g., prioritizing harvesting losses when tax capacity is available). However, the **candidates themselves** are always driven by signal quality and allocation structure, not tax optimization.

### 4.2 Implementation Correctness

The implementation correctly reflects this design separation. Tax state is:
- **Stored**: in `_taxState` module variable + `/api/operator/tax-state` endpoint
- **Displayed**: via `taxAvailableCapacity` / `taxProjectedCapacity` DOM elements
- **Not computed from PAR data**: all tax values come from operator input only
- **Not injected into PAP**: zero references inside `_computePortfolioActions`

### 4.3 Potential Future Consideration (Not a Bug)

A future Phase could add tax-aware sorting within Cat4 (e.g., elevating short-term loss candidates when tax capacity is available). This would require passing `_taxState` into `_computePortfolioActions` as an additional argument and adding a secondary sort key. This does NOT exist in the current implementation and is out of scope for Phase 23.0C.

---

## 5. Null Tax State Behavior

With `net_realized_ytd: null`, `potential_additional_losses: null`, and `capital_loss_carryforward: null`, the `updateTaxComputed()` function falls back to `0` for all inputs (via `|| 0` coercion). The displayed values are:

```
taxAvailableCapacity = $0
taxProjectedCapacity = $0
```

This is informative: the operator sees that no tax context has been configured. It does not affect the PAP in any way.

---

## 6. Verdict

**Tax Integration: VALIDATED — Display-Only, Correctly Isolated.**

The tax state is confirmed non-operative with respect to PAP candidate generation, priority assignment, and sort ordering. The implementation correctly separates tax display context from signal-driven portfolio action recommendations. Zero code defects identified in tax integration.

---

*Phase 23.0C.2 — Tax Integration Validation*  
*Run: PAR-20260603-B66B00E3 | Generated: Phase 23 governance hardening*
