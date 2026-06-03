# Cash Target Runtime Trace — Phase 22D.6A
**Audit Date:** 2026-06-02  
**Run Audited:** PAR-20260602-A991571C  
**Status:** STALE ARTIFACT — pre-Phase 22D.6 code  
**Constraint:** Read-only audit — no code modifications

---

## 1. Trace: YAML → Source Code

### Layer 1 — `config/allocation_models/concentrated_alpha_profile.yaml`

```yaml
nodes:
  CASH: 7.0
```

- Field name is `CASH` under `nodes:` block
- Value is `7.0` (percent)
- **Status:** YAML is correct and contains the mandate target.
- **Allocation Map correctly reads this value** — confirmed by user observation that CASH target = 7.0% appears in the Allocation Map UI panel.

---

### Layer 2 — `src/portfolio/archetype.py` → `load_archetype_targets()`

`runner.py` calls `load_archetype_targets()` which loads the YAML and returns a flat dict of node keys → percentages.

```python
archetype_targets = load_archetype_targets(...)
# Returns: {"EQUITIES": 88.0, ..., "CASH": 7.0, ...}
```

The `CASH` key maps directly to the `nodes.CASH` entry in the YAML.

---

### Layer 3 — `src/portfolio/runner.py` (lines 718–724)

**Current code (Phase 22D.6 version):**

```python
_cash_target_pct = archetype_targets.get("CASH") if archetype_targets else None
if _cash_target_pct is None:
    raise ValueError(
        f"Mandate profile for '{mandate_type}' is missing a CASH node target. "
        "Add 'CASH: <target_pct>' to the mandate's allocation_models YAML before running."
    )
cash_context = compute_deployable_cash(
    holdings=investable,
    total_market_value=snapshot.total_market_value,
    mandate_cash_target_pct=_cash_target_pct,  # ← 7.0 from YAML
)
```

- **Current code is correct** — it reads `CASH: 7.0` from `archetype_targets` and passes it to `compute_deployable_cash()`.
- **The run PAR-20260602-A991571C was NOT generated with this code.** The artifact pre-dates Phase 22D.6.

---

### Layer 4 — `src/portfolio/deployment_queue.py` → `compute_deployable_cash()`

**Current function signature (Phase 22D.6 version):**

```python
def compute_deployable_cash(
    holdings: list[PortfolioHolding],
    total_market_value: float,
    mandate_cash_target_pct: float,   # ← required parameter added in 22D.6
) -> dict[str, float]:
```

**Current formula (correct):**
```python
effective_floor_pct = max(MIN_CASH_PCT, float(mandate_cash_target_pct))
# = max(2.0, 7.0) = 7.0

floor_mv = total_market_value * effective_floor_pct / 100.0
# = $479,347.59 × 7.0 / 100 = $33,554.33

deployable_mv = max(0.0, cash_mv - floor_mv)
# = max(0, $41,279.15 - $33,554.33) = $7,724.82
```

**Pre-22D.6 behavior (what ran when PAR-20260602-A991571C was generated):**
```python
# Old formula used only MIN_CASH_PCT = 2.0% as the floor
floor_mv = total_market_value * MIN_CASH_PCT / 100.0
# = $479,347.59 × 2.0 / 100 = $9,586.95

deployable_mv = cash_mv - floor_mv
# = $41,279.15 - $9,586.95 = $31,692.20
```

Returns dict **missing**: `mandate_cash_target_pct`, `effective_floor_pct`, `excess_pct`, `excess_mv`.

---

### Layer 5 — `deployment_queue.json` → `cash_context` block

**Actual content in PAR-20260602-A991571C artifact:**

```json
"cash_context": {
  "cash_mv": 41279.15,
  "cash_pct": 8.6115,
  "floor_mv": 9586.95,
  "deployable_mv": 31692.2,
  "deployable_pct": 6.6115
}
```

**MISSING fields** (should be present in Phase 22D.6 artifact):
- `mandate_cash_target_pct` ← not present → UI shows "—" for Mandate Target
- `effective_floor_pct` ← not present
- `excess_pct` ← not present → UI shows "—" for Excess vs Target
- `excess_mv` ← not present

**`floor_mv` confirms old 2% floor**: `$9,586.95 = 2.0% × $479,347.59`  
**Should be**: `$33,554.33 = 7.0% × $479,347.59`

---

### Layer 6 — `deployment_plan.json` → `portfolio_impact` block

**Actual content:**

```json
"portfolio_impact": {
  "cash_before_pct": 8.6115,
  "cash_after_pct": 2.0,          ← WRONG: depletes to 2% floor
  "cash_before_mv": 41279.15,
  "cash_after_mv": 9586.97,       ← = 2% × total_mv
  "total_deployed": 31692.18,     ← WRONG: full $31.7K deployed
  "unallocated_cash": 0.02
}
```

`deployable_cash: 31692.2` — inherited directly from stale `cash_context.deployable_mv`.

**Expected values (mandate-aware):**
- `deployable_cash: 7724.82`
- `cash_after_pct: 7.0`
- `cash_after_mv: 33554.33`
- `total_deployed: ≤7724.82`

---

### Layer 7 — `scripts/run_outcome_ui.py` — Run loader

The server loads the run result via `_load_analysis_run(run_id)` which reads:

```python
dq_path = run_dir / "deployment_queue.json"
if dq_path.exists():
    result["deployment_queue"] = json.load(fh)

dp_path = run_dir / "deployment_plan.json"
if dp_path.exists():
    result["deployment_plan"] = json.load(fh)
```

**No recomputation occurs on load.** The stale JSON artifacts are served verbatim to the UI.

The `/api/portfolio/deployment-plan` on-demand endpoint also reads from the stale `deployment_queue.json`:

```python
dq_data = json.load(fh)  # stale artifact — cash_context.deployable_mv = 31692.2
plan = build_deployment_plan(dq_data, deployable_cash=cash_arg)
# build_deployment_plan reads: deployable_cash = cash_ctx.get("deployable_mv", 0.0)
# = 31692.2 — WRONG
```

On-demand plan generation is also poisoned by the stale artifact.

---

### Layer 8 — `ui/portfolio_alignment/app.js` — Rendering

```javascript
const cashCtx = dq.cash_context || {};

const _cashTargetPct = cashCtx.mandate_cash_target_pct != null
  ? parseFloat(cashCtx.mandate_cash_target_pct).toFixed(1) : "—";
// mandate_cash_target_pct is ABSENT in artifact → renders "—"

const _cashExcessPct = cashCtx.excess_pct != null
  ? parseFloat(cashCtx.excess_pct).toFixed(2) : "—";
// excess_pct is ABSENT in artifact → renders "—"
```

**UI binding logic is correct** — it reads the right field names. The fields simply don't exist in the stale artifact.

---

## 2. Summary: Where the Chain Breaks

| Layer | Status | Finding |
|---|---|---|
| YAML (`CASH: 7.0`) | ✅ CORRECT | Contains mandate target |
| `archetype_targets["CASH"]` | ✅ CORRECT (current code) | Returns 7.0 |
| `runner.py` `_cash_target_pct` wiring | ✅ CORRECT (current code) | Passes 7.0 to function |
| `compute_deployable_cash()` signature | ✅ CORRECT (current code) | Accepts `mandate_cash_target_pct` |
| **`deployment_queue.json` artifact** | ❌ **STALE** | Generated with old 2% floor code |
| `deployment_plan.json` artifact | ❌ **STALE** | Inherits wrong deployable amount |
| Server loader | ✅ Passes through | No re-computation, serves artifact as-is |
| On-demand plan API | ❌ **Downstream poison** | Reads stale `deployable_mv` from artifact |
| `app.js` field bindings | ✅ CORRECT | Reads right field names; fields absent in stale data |

**Single root cause: Run PAR-20260602-A991571C was generated before Phase 22D.6 source code was in place. The persisted artifacts do not contain mandate-aware fields. The source code is correct. A fresh re-run will produce correct artifacts.**
