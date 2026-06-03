# Recommendation Narrative Audit
**Phase 22D.1 — Audit Objective #3**  
**Reference Date:** 2026-06-01  
**Status:** FULLY DIAGNOSED

---

## Audit Question

When a portfolio has an `INCREASE_UNDERWEIGHT` recommendation and the optimizer determines that **all implementation vehicles are blocked** (ETF gate failures, mandate block, or no viable candidates), does the main recommendation card text accurately communicate this to the operator?

---

## What the Operator Sees vs. What Is True

### Main Card Text (Always Shown)

For any `INCREASE_UNDERWEIGHT` recommendation, the main card renders:

**Title:**  
`"Build {node_label} allocation ({drift_pct:+.1f}% drift)"`

**Rationale:**  
`"Portfolio is underweight {node_label} by {|drift|}pp (actual X.X% vs target Y.Y%)."`  
followed by a prescriptive ETF vehicle recommendation (hardcoded text from `_PRESCRIPTIVE_RATIONALE` dict in `src/portfolio/recommendations.py` lines 787–858), and optionally a top vehicle suitability note.

**Example:**  
> "Portfolio is underweight US Mega Cap by 5.2pp (actual 14.8% vs target 20.0%).  
> US Mega Cap equities are underweight. VOO (Vanguard S&P 500), IVV (iShares Core S&P 500), and SPY are the preferred vehicles for balanced mega-cap completion..."

**This text is generated unconditionally** — the same title and rationale are produced whether or not any vehicles actually pass implementation gates.

---

### What the Optimizer Knows (Hidden by Default)

**File:** `src/portfolio/optimizer.py`, lines 893–921  

When all ETF and security candidates fail their gates, the optimizer assigns one of:
- `optimizer_decision = "NO_CANDIDATES"` — no security or ETF candidates scored actionable
- `optimizer_decision = "MANDATE_BLOCKED"` — mandate interpretation explicitly blocks the increase

These are populated in the `optimizer_result` block attached to the recommendation.

**File:** `ui/portfolio_alignment/app.js`, line 1820 — `_buildOptimizerViewBlock()`  

The ETF gate failures and `NO_CANDIDATES` decision are rendered **inside a collapsible "Optimizer View" section**. This section is:
- Hidden by default (collapsed)
- Labeled with a generic "Optimizer View" button
- Positioned below the main rationale card body
- Not highlighted visually when the outcome is `NO_CANDIDATES`

The main recommendation card (lines 1308–1429) **never references** `optimizer_decision` or shows any "vehicles blocked" indicator in the primary visible area.

---

## Code Evidence

### `src/portfolio/recommendations.py` — `_build_recommendation_narrative()` (lines 527–580, `src/portfolio/mandate.py`)

Handles INTENTIONAL_OVERWEIGHT, INTENTIONAL_UNDERWEIGHT, TOLERATED_OVERWEIGHT, TOLERATED_UNDERWEIGHT, and STANDARD cases. **No case exists for "all vehicles blocked."** Blocked vehicle state is not a mandate narrative variant; the narrative function has no knowledge of optimizer output.

### `src/portfolio/recommendations.py` — INCREASE_UNDERWEIGHT construction (lines 287–345)

```python
title = f"Build {ar.node_label} allocation ({ar.drift_pct:+.1f}% drift)"
rationale = (
    f"Portfolio is underweight {ar.node_label} by {abs(ar.drift_pct):.1f}pp ..."
    + prescriptive
    + decomposition_note
    + suitability_note_str
    + _top_funding_str
)
```

`prescriptive` is computed by `_prescriptive_rationale()` which returns hardcoded vehicle recommendations regardless of whether those vehicles pass ETF gates. The suitability notes (`suitability_note_str`) mention the top vehicle's suitability tier but do not distinguish between PASS and FAIL gate outcomes for the full candidate set.

### `src/portfolio/optimizer.py` — `NO_CANDIDATES` decision path (lines 912–920)

```python
elif top["candidate_type"] == "ETF" and top["optimizer_status"] == "ACTIONABLE":
    optimizer_decision = "ETF_ADEQUATE"
else:
    optimizer_decision = "NO_CANDIDATES"
```

When all ETF candidates have `optimizer_status != "ACTIONABLE"` (gate failures) and no security candidates have `pis > 0`, the decision becomes `NO_CANDIDATES`. This is stored in the optimizer result payload but **never surfaced in the recommendation title or rationale**.

---

## Gap Summary

| Layer | Gap |
|-------|-----|
| **Recommendation generation** (`recommendations.py`) | Title always says "Build..." and rationale prescribes vehicles unconditionally. No blocked-state variant. |
| **Mandate narrative** (`mandate.py`) | `_build_recommendation_narrative()` has no branch for all-vehicles-blocked scenario. |
| **UI main card** (`app.js` lines 1308–1429) | Renders `r.title` and `r.rationale` directly; never references `optimizer_decision`. |
| **UI optimizer block** (`app.js` line 1820) | ETF gate failures shown only in collapsible hidden "Optimizer View" panel — not visible in primary card area. |
| **Visual distinction** | A `NO_CANDIDATES` card is visually identical to a `SECURITY_SUPERIOR` card in the main recommendation list. |

---

## Operator Impact

An operator who sees **"Build US Mega Cap allocation (+5.2% drift)"** with vehicle names in the rationale text has no visible indication that:
- All named ETFs failed their implementation gates
- The optimizer found no actionable path to execute this recommendation
- The recommendation is structurally unactionable at current allocation state

The operator must actively click "Optimizer View" on each card, read the gate failure details, and infer that no action is available. This is a **silent actionability failure** — the directive language implies action is warranted when the system has already determined it cannot be executed.

---

## Classification

**Severity: HIGH**  
- Operators may execute "Increase" directives that the optimizer has already gated as inactionable
- Blocked status is buried in a collapsed secondary panel, not visible in the primary recommendation narrative
- Affects operational trust when operators act on blocked recommendations and find no viable vehicles
