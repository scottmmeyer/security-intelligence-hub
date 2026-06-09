# AI-001 Forensic Trace

Repository: security-intelligence-hub  
Issue: AI-001 Allocation Policy vs Actual Allocation Contradiction (#29)  
Date: 2026-06-09

## Objective

Explain why the Allocation Intelligence UI simultaneously shows "Micro Cap combined 6.5% OVER ceiling" and "policy_bounds PASS / concentration_ceilings PASS".

---

## Layer 1: Policy Source

**File:** `config/allocation_policy.yaml`  
**Key:** `structural_policy.max_micro_cap_pct: 5.0`  
**Owner:** Configuration — version-controlled governance artifact  
**Policy ID:** ALLOCATION_POLICY_V1 (effective 2026-05-20)

This is the canonical ceiling. Value is 5.0%.

---

## Layer 2: Validator Implementation

**File:** `src/allocation/validators.py`  
**Functions:** `validate_policy_bounds()` and `validate_concentration_ceilings()`  
**Entry point:** `run_all_validators()` at line 309–314  
**Called by:** Allocation Intelligence recalculation pipeline

`validate_concentration_ceilings()` computes:
```python
micro_keys = [k for k in target_map if "MICRO" in k.split(".")]
micro_sum = sum(target_map[k].target_pct_of_total for k in micro_keys if k in target_map)
if micro_sum > policy.max_micro_cap_pct + _SUM_TOLERANCE:
    errors.append(...)
```

**Input:** `StrategicAllocationTarget` objects — the strategic allocation targets, NOT the actual portfolio positions.

---

## Layer 3: Strategic Targets (Validator Input)

**File:** `data/current/strategic_allocation_targets.csv`

| Node | target_pct_of_total |
|---|---|
| EQUITIES.US.MICRO | 1.512% |
| EQUITIES.INTERNATIONAL.MICRO | 0.700% |
| **Combined** | **2.212%** |

**Validator evaluation:**  
2.212% < 5.0% ceiling → **PASS** ✓  
This is correct behavior. The strategic targets do not violate the policy.

---

## Layer 4: Actual Portfolio Values (UI Concentration Display)

**File:** `ui/allocation_intelligence/app.js`, `renderConcentration()` function (line ~490)  

The Concentration Risk section computes:
```javascript
{
  label: "Micro Cap combined",
  value: targets.filter(t => t.node_key.includes("MICRO"))
           .reduce((sum, t) => sum + parseFloat(t.target_pct_of_total || 0), 0),
  ceiling: sp.max_micro_cap_pct ?? 5,
}
```

This ALSO reads from `target_pct_of_total` of the targets array loaded by the UI.

**The question is: which targets object does the UI load?**

The UI loads from `data/current/strategic_allocation_targets.csv` for the Allocation Intelligence panel. If the panel shows 6.5%, it is computing from a targets data set where the micro values are 6.0% and 0.5% respectively — either from a different allocation archetype's targets or from portfolio-alignment-derived node calculations.

---

## Layer 5: UI Rendering Source for 6.5% Value

**File:** `ui/allocation_intelligence/app.js`  
**Relevant data binding:**

The Allocation Intelligence UI renders:
1. Strategic allocation targets from the recalculation snapshot
2. Concentration risk bars from the same targets

**CRITICAL FINDING:** The Allocation Intelligence panel and the Portfolio Alignment panel have different data sources for their micro-cap exposure values:

- **Allocation Intelligence panel** (validators): reads from `strategic_allocation_targets.csv` → micro combined = 2.21%
- **Portfolio Alignment panel** / some section of the Allocation Intelligence page: reads from portfolio alignment analysis → actual portfolio positions → US.MICRO actual = 6.0%, INTL.MICRO actual = 0.5% → combined = 6.5%

The 6.5% figure comes from **actual portfolio holdings** as calculated by the portfolio alignment engine. The 2.21% figure comes from **strategic allocation targets**.

---

## Summary of Lineage

| Step | Source | Value | Used By |
|---|---|---|---|
| Policy definition | config/allocation_policy.yaml | max_micro_cap_pct = 5.0% | Validators + UI ceiling display |
| Strategic target US.MICRO | data/current/strategic_allocation_targets.csv | 1.512% | Validators |
| Strategic target INTL.MICRO | data/current/strategic_allocation_targets.csv | 0.700% | Validators |
| Validator input combined | computed | 2.212% | concentration_ceilings validator → PASS |
| Actual portfolio US.MICRO | Portfolio alignment analysis | ~6.0% | UI concentration display |
| Actual portfolio INTL.MICRO | Portfolio alignment analysis | ~0.5% | UI concentration display |
| UI concentration display combined | computed from actual | ~6.5% | Operator sees "OVER" |
