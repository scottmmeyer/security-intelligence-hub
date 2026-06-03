# Q7 — Final Governance Recommendation
## Phase 22D.5 — Strategic Cash Governance & DCA Deployment Policy

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D.5  
**Question:** Does SIH behave like a disciplined long-term portfolio manager, or like an optimizer trying to minimize cash?

---

## Verdict

**E. HYBRID_MODEL — With Corrective Action Required**

SIH currently behaves like **an optimizer minimizing cash**, not a disciplined long-term portfolio manager. The mandate says "dry powder, not idle drag" — but the deployment engine deploys 77% of the cash position in a single cycle, leaving only the 2% governance floor. This is behaviorally inconsistent with the stated philosophy.

The recommended corrective action is **Option E (Target-Aligned Floor)**: raise the effective deployment floor in `compute_deployable_cash()` from 2% to the mandate's strategic cash target (7%), so the deployment engine only offers genuine excess as deployable capital.

---

## The Core Tension

### What the Mandate Says

`config/allocation_models/concentrated_alpha_profile.yaml`:
```yaml
philosophy: >
  Cash treated as dry powder, not idle drag. Fixed income optional; currently
  minimal. Mega cap targets reduced to reflect conviction in undervalued tiers.

nodes:
  CASH: 7.0    # Strategic cash target
```

**Interpretation:** Cash at 7% is the *intended state*. It is a deliberate reserve, not excess. The mandate assigns a higher cash target than any other profile (vs. 3% for GROWTH, 5% for BALANCED) precisely because CONCENTRATED_ALPHA takes fewer, higher-conviction positions and waits for compelling opportunities.

### What the Deployment Engine Does

`src/portfolio/deployment_queue.py`, line 42:
```python
MIN_CASH_PCT = 2.0   # mandate floor — reserve never deployed below this level
```

The deployment engine treats 2% as the floor — deploying everything above 2% when cash is elevated. With 8.66% cash, the engine classifies $31,683 (6.66%) as "deployable" and proposes reducing cash from 8.66% to 2.00% in one execution.

### The Result

| Perspective | Cash at 8.66% means... |
|-------------|----------------------|
| Strategic mandate | "In-band — slight excess above 7% target" |
| Deployment engine | "Massive deployment opportunity — $31.7K available" |

These two readings of the same fact are not reconciled anywhere in the system. The deployment engine's logic dominates the operator-facing output.

---

## Evidence Summary

All evidence was gathered without code execution — read-only forensic analysis:

| Finding | Source | Impact |
|---------|--------|--------|
| 7.0% strategic target defined | `concentrated_alpha_profile.yaml:18` | Sets expected steady-state cash |
| "dry powder, not idle drag" philosophy | `concentrated_alpha_profile.yaml:7` | Explicitly anti-minimization |
| `MIN_CASH_PCT = 2.0` hardcoded | `deployment_queue.py:42` | Deployment floor is governance min, not strategy target |
| No integration between 7% and 2% | Absence of any connecting code | Neither subsystem knows about the other |
| `compute_deployable_cash()` has no strategy_target param | `deployment_queue.py` function signature | Floor cannot be externally configured |
| 2% floor documentation frames it as growth-portfolio minimum | `ALLOCATION_PRIMER_WHY_THESE_NUMBERS.md:96` | Wrong mandate context |
| Phase 7.5W simulation used "fresh injection" model | `operator_trust_assessment.md` | Not a one-time depletion model |
| Deployment plan proposes `cash_after_pct = 2.0%` | `deployment_plan.json` | Confirms engine intends to deplete to floor |
| Scenario C (7% floor) reduces HHI delta by 78% | Q4 analysis | Strategy-aligned floor is quantifiably better |
| Test asserts `MIN_CASH_PCT == 2.0` | `test_7_5b_deployment_queue.py:681` | Any floor change requires test update |

---

## Four Policy Options Evaluated

### Option 1 — Status Quo (Not Recommended)

Keep `MIN_CASH_PCT = 2.0`. Accept that the deployment engine minimizes cash to the governance floor.

- **Justification possible?** Yes — if the operator's intent is "deploy now and rebuild cash over time"
- **Mandate alignment:** LOW — contradicts "dry powder" philosophy
- **Operator action:** Deploy all $31.7K, then wait 8–12 months for cash to rebuild to 7%
- **Verdict:** Acceptable only if the operator explicitly endorses a "deploy aggressively now" posture

---

### Option 2 — Operator Manual Override (Minimal Change)

Keep the architecture unchanged but document an operator-level guideline: "Only execute deployments up to the excess above the 7% strategic target."

- **Operator calculation:** cash_mv - (total_mv × 7%) = $41,199 - $33,305 = **$7,894 only**
- **Code change:** NONE
- **Test change:** NONE
- **Risk:** Operator must remember to manually calculate this every cycle; the system still shows "$31.7K deployable" which creates anchoring pressure
- **Verdict:** Low-overhead but cognitively burdensome; risk of operator ignoring the guideline

---

### Option 3 — Raise Deployment Floor to 5% (Intermediate)

Set `MIN_CASH_PCT = 5.0` in `deployment_queue.py`. Add corresponding update to `allocation_policy.yaml`.

- **Deployable at 8.66% cash:** $17,410 (3.66%)
- **Cash after:** 5.00%
- **Mandate alignment:** MODERATE — preserves more cash but still below 7% target
- **Code impact:** 1 constant change + 1 YAML change + 1 test update
- **Test impact:** `assert MIN_CASH_PCT == 2.0` must be updated to `5.0`
- **Verdict:** Better than status quo, but philosophically incomplete

---

### Option 4 — Target-Aligned Deployment Floor (Recommended)

Introduce a `strategy_cash_target_pct` parameter to `compute_deployable_cash()`. Default to the mandate's strategic CASH target (7.0%). The floor used for deployment is `max(MIN_CASH_PCT, strategy_cash_target_pct)`.

```python
def compute_deployable_cash(
    holdings: list[PortfolioHolding],
    total_market_value: float,
    strategy_cash_target_pct: float = 7.0,   # NEW: loaded from mandate profile
) -> dict:
    cash_mv  = sum(h.market_value for h in holdings if h.is_cash_equivalent)
    # Use the higher of governance floor or strategic target
    effective_floor_pct = max(MIN_CASH_PCT, strategy_cash_target_pct)
    floor_mv = total_market_value * effective_floor_pct / 100.0
    deployable_mv = max(0.0, cash_mv - floor_mv)
    ...
```

- **Deployable at 8.66% cash:** $7,894 (1.66% — genuine excess above mandate target)
- **Cash after:** 7.00% — exactly at strategic target
- **Mandate alignment:** HIGH
- **Code impact:** 1 function signature change + 1 call-site update + 1 constant comment update
- **Test impact:** Existing test at line 681 (`assert MIN_CASH_PCT == 2.0`) still passes (MIN_CASH_PCT unchanged); new parameter default tests needed
- **Verdict:** **RECOMMENDED** — aligns architecture with mandate philosophy, minimal disruption

---

## Recommendation Detail — Option 4

### Change 1 — `src/portfolio/deployment_queue.py`

```python
# Before:
MIN_CASH_PCT = 2.0   # mandate floor — reserve never deployed below this level

def compute_deployable_cash(holdings, total_market_value):
    cash_mv  = sum(h.market_value for h in holdings if h.is_cash_equivalent)
    floor_mv = total_market_value * MIN_CASH_PCT / 100.0
    deployable_mv = max(0.0, cash_mv - floor_mv)
    ...

# After:
MIN_CASH_PCT = 2.0   # governance floor — hard minimum, never deployed below

def compute_deployable_cash(
    holdings,
    total_market_value,
    strategy_cash_target_pct: float = 7.0,  # mandate strategic cash target; default = CONCENTRATED_ALPHA
):
    cash_mv  = sum(h.market_value for h in holdings if h.is_cash_equivalent)
    # Effective floor = max of governance minimum and strategic mandate target
    effective_floor_pct = max(MIN_CASH_PCT, strategy_cash_target_pct)
    floor_mv  = total_market_value * effective_floor_pct / 100.0
    deployable_mv = max(0.0, cash_mv - floor_mv)
    ...
    return {
        "cash_mv":              round(cash_mv, 2),
        "floor_mv":             round(floor_mv, 2),
        "effective_floor_pct":  round(effective_floor_pct, 4),   # NEW
        "deployable_mv":        round(deployable_mv, 2),
        "deployable_pct":       round(deployable_mv / total_market_value * 100, 4),
    }
```

### Change 2 — Call site in `src/portfolio/runner.py`

The `compute_deployable_cash()` call site must pass the active mandate's CASH target:
```python
# Before:
cash_ctx = compute_deployable_cash(holdings, total_mv)

# After:
cash_target = mandate_profile.nodes.get("CASH", 7.0)  # read from active mandate
cash_ctx = compute_deployable_cash(holdings, total_mv, strategy_cash_target_pct=cash_target)
```

### Change 3 — UI Display in `app.js`

The deployment gauge should display the effective floor (mandate target), not just the governance minimum:
```javascript
// Before:
{ label: "Cash Floor", value: `${sp.cash_floor_pct ?? "—"}%` }

// After:
{ label: "Cash Reserve (Strategy Target)", value: `${cash_ctx.effective_floor_pct ?? sp.cash_floor_pct ?? "—"}%` }
```

### Change 4 — Documentation in `allocation_policy.yaml`

Add a comment clarifying the relationship between governance floor and strategy target:
```yaml
structural_policy:
  cash_floor_pct: 2.0   # Governance hard minimum; deployment engine uses max(this, mandate.cash_target)
```

---

## Policy Decision Framework

| If you want... | Use floor... | Deploy per cycle... |
|----------------|-------------|---------------------|
| Maximum capital deployment velocity | 2% (current) | $31,683 |
| Maintain operational liquidity | 5% | $17,410 |
| Respect CONCENTRATED_ALPHA mandate intent | 7% (recommended) | $7,894 |
| Maximum dry powder preservation | 10% | $0 (no deployment) |

---

## What Changes and What Stays the Same

**Stays the same:**
- `MIN_CASH_PCT = 2.0` constant (the governance floor never changes)
- CW-DAS scoring and ranking logic
- Queue eligibility gates (all unchanged)
- Test assertion at line 681 (`assert MIN_CASH_PCT == 2.0` still passes)
- Phase 7.5W simulation results (it modeled fresh-injection DCA, which is unaffected)

**Changes:**
- `compute_deployable_cash()` accepts a new optional parameter
- Deployable cash shown in UI drops from $31,683 to $7,894 when mandate target = 7%
- `deployment_plan.json: cash_after_pct` would show `7.0%` not `2.0%`
- 2 existing test cases for `compute_deployable_cash()` with explicit floor behavior need updating to pass the new parameter
- `effective_floor_pct` key added to `cash_context` dict (additive, not breaking)

---

## Q7 Final Answer

**Does SIH currently behave like a disciplined long-term portfolio manager, or an optimizer minimizing cash?**

**Answer: An optimizer minimizing cash — by default.**

The mandate philosophy is correct. The allocation model is correct (7% target, "dry powder"). The deployment engine is the mismatch. It was built using the governance minimum (2%) as its operational floor, not the mandate's strategic target (7%). Because these are independently maintained with no integration point, the deployment engine consistently overrides the mandate's intent.

**The fix is small and surgical.** One function parameter change — `strategy_cash_target_pct` passed to `compute_deployable_cash()` — makes the deployment engine aware of the mandate's cash philosophy. After this change, SIH deploys only genuine excess above the strategic target, preserving the dry-powder reserve at all times.

**Urgency:** MEDIUM. The current system is not broken — the governance floor is enforced, the CW-DAS scoring is correct, and the operator can manually choose not to execute the full deployment plan. However, the architectural misalignment creates a misleading default: the system presents $31.7K as deployable when the mandate says only $7.9K is genuinely excess. This misleading default increases the probability that a future operator deploys more capital than the mandate intends.

**Recommended course of action:**
1. Implement Option 4 (target-aligned floor) in a future development cycle
2. In the interim, use Option 2 (operator manual calculation) — deploy only the $7,894 genuine excess
3. Update the UI to display both the governance floor (2%) and the effective strategy reserve (7%)
4. Add a note to `deployment_plan.json` distinguishing "governance-deployable" from "strategy-aligned-deployable"
