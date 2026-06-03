# Q3 — Cash Floor Lineage Report
## Phase 22D.5 — Where did the 2% floor come from?

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D.5  
**Question:** Is `MIN_CASH_PCT = 2.0` intentional governance policy or a development-time placeholder?

---

## Summary Finding

The 2.0% cash floor has **legitimate governance provenance** — it is the structural minimum derived from investment methodology, not an arbitrary placeholder. However, its original context was a **growth portfolio methodology baseline**, not the CONCENTRATED_ALPHA mandate's dry-powder philosophy. The floor was established correctly but was not updated when the CONCENTRATED_ALPHA mandate adopted a 7.0% strategic cash target with an explicit "dry powder" rationale.

The 2.0% was the right floor for the wrong mandate context.

---

## Lineage Trace

### Origin Point 1 — Allocation Methodology YAML (Conceptual Foundation)

**File:** `config/allocation_methodology.yaml`
```yaml
- key: CASH
  label: "Cash"
  baseline_target_pct_of_parent: 2.0
  confidence_level: HIGH
  evidence_basis:
    - Minimum liquidity reserve for tactical rebalancing and opportunistic deployment
    - 2% cash floor is the structural minimum enforced by governance policy.
    - At current T-bill yields (4–5%), cash drag is partially offset by money market
      returns, making a 2% floor relatively low-cost in the current rate environment.
```

This is the **methodological seed** — the research-grounded baseline from which all recalculation starts. The 2.0% was set here first, representing the structural minimum liquidity required to maintain operations. Evidence basis: tactical rebalancing, opportunistic deployment, transaction cost reserve.

**Rationale quality:** HIGH. The 2% is justified by the documentation. It is the governance-enforced minimum, not a default. The reasons are documented.

---

### Origin Point 2 — Allocation Policy YAML (Governance Expression)

**File:** `config/allocation_policy.yaml`
```yaml
structural_policy:
  cash_floor_pct: 2.0

asset_class_governance:
  CASH:
    max_pct: 20.0
    min_pct: 2.0
    notes: "Global liquidity reserve. Structural floor enforced."
```

The 2.0% floor is codified in governance policy. The `cash_floor_pct` entry in `structural_policy` and the `min_pct` in `CASH` governance are consistent. This is an architectural choice, not a typo or default.

**Governance chain:** The `StructuralPolicy` dataclass in `src/allocation/structural_policy.py` loads `cash_floor_pct` and validates that all allocation model CASH targets are ≥ `min_pct`. Because CASH = 7.0% ≥ 2.0%, validation passes — but the policy does not enforce that the *deployment engine* respects the 7.0%.

---

### Origin Point 3 — ALLOCATION_PRIMER_WHY_THESE_NUMBERS.md (Design Narrative)

**File:** `docs/ALLOCATION_PRIMER_WHY_THESE_NUMBERS.md`, lines 93–97:
```
Why 2% Cash?

Cash is the structural floor — not an investment choice but an operational requirement.
T-bill yields are currently 4–5%, which partially offsets cash drag.
The 2% cash floor is the governance-enforced minimum. It ensures there is always
liquidity available for tactical rebalancing, opportunistic deployment, and transaction costs.
Holding more than 2–3% cash in a growth portfolio is a drag. Cash drag vs equities
over 10 years at a 5% equity risk premium = 50 basis points per year per additional cash point.
```

This documentation was written with a **growth portfolio context**: "Holding more than 2–3% is drag." This framing is appropriate for a GROWTH_ALLOCATION mandate (which has a 3.0% cash target). It is NOT appropriate framing for CONCENTRATED_ALPHA, which deliberately holds 7.0% as dry powder.

**Key insight:** The WHY_THESE_NUMBERS document treats 2% as "the cash target" in the context of explaining a balanced/growth portfolio. The CONCENTRATED_ALPHA mandate overrides this with 7.0% — but the deployment engine was built using the 2% philosophy from this document.

---

### Origin Point 4 — `phase_7_4a_analysis.py` (Earliest Code Reference)

**File:** `phase_7_4a_analysis.py`, lines 28–31:
```python
# CONCENTRATED_ALPHA target cash band
MAX_CASH_PCT = 15.0
MIN_CASH_PCT = 2.0   # floor
```

This script, which pre-dates `deployment_queue.py`, explicitly names these constants in the context of CONCENTRATED_ALPHA's "target cash band." The intent at this stage was a **band concept**: cash should be between MIN (2%) and MAX (15%).

Critically, the comment here says `# floor` — acknowledging it is a floor, not a target. At this stage, the system design recognized that 2% was the *floor* of the operating range, not the target.

---

### Origin Point 5 — `deployment_queue.py` (Operational Implementation)

**File:** `src/portfolio/deployment_queue.py`, line 42:
```python
MIN_CASH_PCT = 2.0   # mandate floor — reserve never deployed below this level
```

The comment `# mandate floor — reserve never deployed below this level` is accurate — the constant is the floor, not the target. However, the deployment engine uses this constant as the **sole cash constraint** when computing deployable cash. The MAX_CASH_PCT concept from `phase_7_4a_analysis.py` was not carried into the deployment engine; neither was the concept of a strategic cash target.

**What was lost in translation:** `phase_7_4a_analysis.py` had a concept of a "target band" (2–15%). `deployment_queue.py` has only a floor (2%). The band concept — which would have naturally implied "deploy excess only when cash is meaningfully above the band top" — was not implemented.

---

### Origin Point 6 — Why 2.0% Specifically?

Cross-referencing the PRIMER document table:
```
| Asset Class | Target | Role                                           |
|-------------|--------|------------------------------------------------|
| Cash        | 2%     | Structural liquidity floor                     |
```

The 2% comes from the general methodology's "balanced growth" portfolio. It is the **lowest defensible liquidity reserve** for a portfolio:
- Transaction costs: ~0.1–0.5% typical
- Tactical rebalancing: ~1–2% buffer
- Emergency liquidity: ~0.5–1%
- Total: 2–3% minimum

The 2.0% is a reasonable industry-standard minimum liquidity reserve. It is NOT arbitrary. But it is calibrated for a fully-deployed, actively-managed growth portfolio — not for a portfolio that is intentionally using cash as a tactical weapon (dry powder).

---

## Lineage Summary

| Stage | Value | Artifact | Intent |
|-------|-------|----------|--------|
| Methodology seed | 2.0% | `allocation_methodology.yaml` | Structural minimum for growth mandate |
| Governance codification | 2.0% | `allocation_policy.yaml` | Floor enforced by policy |
| Design documentation | 2.0% | `ALLOCATION_PRIMER_WHY_THESE_NUMBERS.md` | "Growth portfolio" floor rationale |
| Analysis script (pre-deployment) | 2.0% (floor of band 2–15%) | `phase_7_4a_analysis.py` | Floor of CONCENTRATED_ALPHA operating range |
| Deployment engine constant | 2.0% | `deployment_queue.py:42` | "Never deploy below this" — operational floor |
| Test regression | 2.0% | `test_7_5b_deployment_queue.py:681` | Asserts constant is 2.0 |
| CONCENTRATED_ALPHA mandate override | **7.0%** | `concentrated_alpha_profile.yaml:18` | Strategic dry-powder target |

---

## What Happened

1. The 2.0% floor was established as the **global structural minimum** in the governance methodology. Justified. Appropriate for all mandates.
2. The CONCENTRATED_ALPHA mandate was designed with a higher 7.0% cash target, explicitly labeled "dry powder."
3. The deployment engine was built using the **global floor (2.0%)** as its deployment threshold — not the mandate-specific strategic target (7.0%).
4. No integration point was created to let the deployment engine read the mandate's strategic cash target.
5. The result: the deployment engine correctly respects the governance floor but **ignores the mandate's higher strategic cash target**.

---

## Is the 2.0% a Bug or a Design Decision?

The 2.0% floor in `deployment_queue.py` is **not a bug** — it correctly implements the governance minimum. The architectural gap is that the deployment engine does not expose the strategic cash target as a configurable input. It is a **completeness gap**, not an error:

- The governance minimum (2.0%) is correctly implemented
- The strategic target (7.0%) is correctly defined in the allocation model
- The **integration between them** (deploy only excess above the strategic target) was not implemented

The deployment engine was built to answer: "What is the maximum safely deployable?"  
It should also answer: "What should the post-deployment cash level be?"  
Currently, those are the same question; they should be separate.
