# Phase 22D.6A — Final Verdict: Cash Target Implementation Validation
**Audit Date:** 2026-06-02  
**Run Audited:** PAR-20260602-A991571C  
**Mandate Profile:** CONCENTRATED_ALPHA (`cash_target = 7.0%`)  
**Constraint:** Read-only audit — no code modifications  

---

## VERDICT: STALE ARTIFACT — SOURCE CODE IS CORRECT

The Phase 22D.6 mandate-aware cash implementation **is correctly implemented in source code** but has **not yet been exercised by the current UI-visible run**. All observed symptoms trace to a single root cause: the active run artifact was generated before Phase 22D.6 code was in place.

---

## 1. Failing Layer Identified

**Root cause:** `PAR-20260602-A991571C/deployment_queue.json` was generated with **pre-Phase 22D.6 code** that used a hardcoded 2.0% governance floor instead of reading `mandate_cash_target_pct` from the active mandate profile.

**This is not a code bug in the current codebase.** The current source code at all layers is correct:
- `concentrated_alpha_profile.yaml` — contains `CASH: 7.0` ✅
- `runner.py` — reads `archetype_targets["CASH"]` = 7.0, passes to `compute_deployable_cash()` ✅
- `deployment_queue.py → compute_deployable_cash()` — accepts `mandate_cash_target_pct`, computes correct floor ✅
- `app.js` — binds to correct field names (`mandate_cash_target_pct`, `excess_pct`, `excess_mv`) ✅

The only broken component is the **persisted artifact on disk** from a run that pre-dates the Phase 22D.6 implementation.

---

## 2. Symptom Explanation

### Symptom 1: "Deployable Cash = $31,692.20"
- **Cause:** Old artifact used `floor = 2.0%` → `floor_mv = $9,586.95` → `deployable_mv = $31,692.20`  
- **Expected:** `floor = 7.0%` → `floor_mv = $33,554.33` → `deployable_mv = $7,724.82`  

### Symptom 2: "Cash Wt 8.6% → 2.0%"
- **Cause:** `deployment_plan.json` was built using stale `deployable_mv = $31,692.20`, depleting cash to 2.0% (the old floor)  
- **Expected:** Deploy $7,724.82 → leave 7.0% cash → `cash_after_pct = 7.0%`

### Symptom 3: "Mandate Target = blank (—)"
- **Cause:** `mandate_cash_target_pct` key does not exist in the stale `cash_context` block  
- **App.js behavior:** `cashCtx.mandate_cash_target_pct != null` evaluates to `false` → renders "—"  
- **No JS bug** — the null-check guard is working as designed; the data is simply absent

### Symptom 4: "Excess vs Target = blank (—)"
- **Cause:** `excess_pct` and `excess_mv` keys do not exist in the stale `cash_context` block  
- **App.js behavior:** Same null-check guard → renders "—"  
- **No JS bug**

### Symptom 5: "Allocation Map correctly shows CASH = 7.0%"
- **Cause:** Allocation Map reads from `data.cash_mandate_context` (output of `mandate.py → get_cash_interpretation()`), which reads the YAML directly on every run load — completely independent of `deployment_queue.json`  
- **Confirms:** YAML is correct and accessible; only the deployment queue code path is affected

---

## 3. Validation: Expected Values After Correct Re-Run

Using actual portfolio values from the audited run:

| Metric | Current (Wrong) | Expected (Correct) |
|---|---|---|
| Total Portfolio MV | $479,347.59 | $479,347.59 |
| Cash MV | $41,279.15 | $41,279.15 |
| Cash Weight | 8.6115% | 8.6115% |
| Mandate Target | — (missing) | **7.0%** |
| Effective Floor | — (missing) | **7.0%** |
| Floor MV | $9,586.95 (2%) | **$33,554.33 (7%)** |
| Excess vs Target | — (missing) | **+1.61% ($7,724.82)** |
| Deployable Cash | **$31,692.20** | **$7,724.82** |
| Cash Wt After Deployment | **2.0%** | **7.0%** |

User-reported expected value ("~$7.9K") corresponds to **$7,724.82** — confirmed. ($7.7K vs $7.9K difference is due to rounding of SPAXX balance estimate in user's mental model.)

---

## 4. "Generate Deployment Plan" Button — Also Poisoned

The button's primary path in `app.js`:

```javascript
const plan = _analysisResult && _analysisResult.deployment_plan;
if (plan && plan.recommendations && plan.recommendations.length > 0) {
  _dpRenderPlan(plan);  // ← uses pre-loaded deployment_plan.json
  return;
}
```

Since `deployment_plan.json` exists for this run, the API is never called. The stale `deployment_plan.json` (with `deployable_cash: $31,692.20`, `cash_after_pct: 2.0`) is rendered directly.

The on-demand API fallback would also produce wrong results, because it reads `deployable_mv` from the stale `deployment_queue.json`.

---

## 5. Source Code Status Confirmation

| Component | File | Status |
|---|---|---|
| YAML config | `config/allocation_models/concentrated_alpha_profile.yaml` | ✅ CORRECT — `CASH: 7.0` present |
| Archetype loader | `src/portfolio/archetype.py` | ✅ CORRECT — returns `{"CASH": 7.0, ...}` |
| Runner wiring | `src/portfolio/runner.py` lines 718–724 | ✅ CORRECT — passes CASH target to function |
| Cash computation | `src/portfolio/deployment_queue.py → compute_deployable_cash()` | ✅ CORRECT — mandate-aware formula |
| Planner | `src/portfolio/deployment_planner.py → build_deployment_plan()` | ✅ CORRECT — reads `deployable_mv` from cash_context |
| API server | `scripts/run_outcome_ui.py` | ✅ CORRECT — passes artifact through unchanged |
| Frontend | `ui/portfolio_alignment/app.js` | ✅ CORRECT — reads correct field names |
| **Artifact on disk** | `PAR-20260602-A991571C/deployment_queue.json` | ❌ **STALE** — pre-22D.6 generation |
| **Artifact on disk** | `PAR-20260602-A991571C/deployment_plan.json` | ❌ **STALE** — inherits wrong deployable amount |

---

## 6. Remediation

**Required action: Re-run portfolio analysis** to generate a fresh run with current code.

Steps:
1. Re-ingest the current Fidelity CSV via the portfolio upload UI (or re-trigger the runner)
2. The new run will call `compute_deployable_cash(mandate_cash_target_pct=7.0)` correctly
3. New `deployment_queue.json` will contain all 9 fields including `mandate_cash_target_pct: 7.0`, `excess_pct: 1.6115`, `deployable_mv: 7724.82`
4. New `deployment_plan.json` will show `cash_after_pct: 7.0%`, `deployable_cash: $7,724.82`
5. UI will display Mandate Target = 7.0%, Excess vs Target = +1.61% ($7,724.82), Deployable = $7,724.82, Cash Wt 8.6% → 7.0%

**No code changes required.** Current implementation is complete and correct.

---

## 7. Optional: Artifact Version Stamp

The stale artifact shows `queue_version: CW-DAS-1.0`. Consider bumping `CW_DAS_VERSION` (currently `"1.0"` in `deployment_queue.py`) to `"2.0"` when Phase 22D.6 was applied, so future audits can use artifact version as a sentinel for pre/post-mandate-aware generation. This would make stale artifacts immediately identifiable by version string. This is a recommendation only — not a blocker.

---

## 8. Deliverables Index

| Deliverable | File | Status |
|---|---|---|
| Runtime trace | `cash_target_runtime_trace.md` | ✅ Complete |
| Payload audit | `deployment_payload_audit.json` | ✅ Complete |
| UI binding validation | `ui_binding_validation.md` | ✅ Complete |
| Recalculation validation | `deployment_recalculation_validation.md` | ✅ Complete |
| Final verdict | `phase_22d6a_final_verdict.md` | ✅ This document |
