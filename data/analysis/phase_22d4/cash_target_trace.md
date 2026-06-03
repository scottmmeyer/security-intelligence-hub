# Phase 22D.4 — Q1: Cash Target Trace (7.0%)
## Where does the 7.0% cash target come from?

**Investigation run:** PAR-20260602-1BF2ADA5  
**Active mandate:** CONCENTRATED_ALPHA  
**Generated:** Phase 22D.4 — read-only forensic trace

---

## Answer

The `7.0%` cash target is the **strategic allocation model target** for the CASH asset class under the `CONCENTRATED_ALPHA` mandate profile. It represents the **intended steady-state cash weight** within the full portfolio allocation model — not a deployment constraint.

---

## Evidence Chain (step-by-step)

### Step 1 — Active mandate established

**File:** `phase_7_4a_analysis.py`, line 26  
```python
MANDATE = "CONCENTRATED_ALPHA"
```
**Also confirmed by:** `untitled folder/trace_22d3.py`, line 77 (`"CONCENTRATED_ALPHA"`)

The portfolio runs under `CONCENTRATED_ALPHA`. All allocation model targets are loaded from the corresponding profile.

---

### Step 2 — Allocation model YAML defines 7.0%

**File:** `config/allocation_models/concentrated_alpha_profile.yaml`  
```yaml
mandate_type: CONCENTRATED_ALPHA
display_name: "Concentrated Alpha"
philosophy: >
  Cash treated as dry powder, not idle drag. ...

nodes:
  # Asset class level (depth 1) — must sum to 100.0
  EQUITIES: 88.0
  FIXED_INCOME: 2.0
  DIGITAL: 1.0
  COMMODITIES: 2.0
  CASH: 7.0          # <-- THE SOURCE
```

The `CASH: 7.0` node is a depth-1 allocation model node. It means:  
> Under the CONCENTRATED_ALPHA mandate, the target steady-state allocation to cash is **7.0% of total portfolio value**.

---

### Step 3 — Allocation policy confirms 7.0% is valid (above floor)

**File:** `config/allocation_policy.yaml`, `asset_class_governance.CASH`  
```yaml
CASH:
  max_pct: 20.0
  min_pct: 2.0
  notes: "Global liquidity reserve. Structural floor enforced."
```

The policy allows CASH targets between 2.0% and 20.0%. The 7.0% model target is valid within that band.

---

### Step 4 — Validator enforces the floor at model-load time

**File:** `src/allocation/validators.py`, lines 76–80  
```python
if target.asset_class == "CASH" and target.hierarchy_depth == 1:
    if target.target_pct_of_total < policy.cash_floor_pct - _SUM_TOLERANCE:
        errors.append(
            f"CASH: {target.target_pct_of_total:.2f}% is below cash_floor_pct={policy.cash_floor_pct:.1f}%"
        )
```

If the allocation model ever set CASH below 2.0%, this validator would reject it at load time. Since CASH = 7.0% ≥ 2.0%, validation passes. This confirms the 7.0% is the legitimate model target — not a byproduct of an error.

---

### Step 5 — Compare across mandate profiles

| Mandate Profile                    | File                                      | CASH target |
|------------------------------------|-------------------------------------------|-------------|
| `CONCENTRATED_ALPHA` (active)      | `concentrated_alpha_profile.yaml`         | **7.0%**    |
| `BALANCED` (inactive)              | `balanced_allocation_profile.yaml`        | 5.0%        |
| `GROWTH` (inactive)                | `growth_allocation_profile.yaml`          | 3.0%        |

The 7.0% is the **highest** cash target across all current profiles — consistent with the mandate philosophy: "Cash treated as dry powder." CONCENTRATED_ALPHA deliberately maintains a larger cash buffer than growth-oriented mandates.

---

## Summary

| Attribute       | Value |
|-----------------|-------|
| Target value    | **7.0%** |
| Concept type    | Strategic allocation model target (depth-1 CASH node) |
| Source file     | `config/allocation_models/concentrated_alpha_profile.yaml` |
| Source key      | `nodes.CASH` |
| Mandate         | `CONCENTRATED_ALPHA` |
| Governance file | `config/allocation_policy.yaml` (validates it is within 2.0%–20.0%) |
| Loader          | `src/allocation/validators.py` (enforces at model-load time) |

The 7.0% represents the **allocation intelligence layer** — what the portfolio should look like in its steady state. It is **not** the deployment engine's operating constraint.
