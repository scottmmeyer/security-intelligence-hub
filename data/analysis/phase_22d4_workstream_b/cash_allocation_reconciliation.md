# Q4 — Cash Allocation Reconciliation
## Workstream B: SPAXX / Cash Equivalent Governance Certification

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D — Workstream B  
**Scope:** SPAXX contribution to allocation hierarchy — CASH node only, never equity/other nodes  

---

## Verdict: SPAXX Contributes to the CASH Node and ONLY the CASH Node

SPAXX contributes zero weight to EQUITIES, FIXED_INCOME, DIGITAL, COMMODITIES, or any equity sub-node.

---

## Section 1 — Live Alignment Evidence

From `data/portfolio_ingestion/analysis_runs/PAR-20260602-1BF2ADA5/alignment.csv`:

```
CASH node:
  node_key:         CASH
  actual_pct:       8.6592
  target_pct:       7.0
  drift_pct:        1.6592
  drift_direction:  OVERWEIGHT
  severity:         NONE
```

From `holdings.csv` (SPAXX row):
```
percent_of_portfolio: 8.6592
```

**Match:** SPAXX's `percent_of_portfolio` (8.6592%) equals the CASH node's `actual_pct` (8.6592%) exactly. SPAXX is the **only cash-equivalent position** in the portfolio. Therefore 100% of the CASH node allocation is attributable to SPAXX.

---

## Section 2 — Exposure Decomposition (CASH node only)

**File:** `src/portfolio/enrichment.py` (enrichment output):
```
exposure_market_cap_mix:   ()  — empty (no equity-tier analysis for cash)
exposure_mega_subtier_mix: ()  — empty
```

From `config/etf_exposure_decomposition.yaml` (SPAXX registry entry):
```yaml
SPAXX:
  exposure_sector_mix:
    CASH: 100      ← 100% cash sector — no equity sector contribution
  exposure_geography_mix:
    US: 100
  exposure_style_mix:
    INCOME: 100
  exposure_thematic_mix:
    CASH_EQUIVALENT: 100
```

SPAXX's sector decomposition is `{CASH: 100%}` — zero contribution to any equity sector (Technology, Healthcare, etc.).

---

## Section 3 — Optimizer Node Matching Guard

**File:** `src/portfolio/optimizer.py`, lines 352, 361, 368:
```python
is_cash_eq = bool(getattr(holding, "is_cash_equivalent", False))
ac = str(getattr(holding, "asset_class", "")).upper()
if is_cash_eq or ac in ("CASH", "FIXED_INCOME"):
    return False   # not eligible for equity/FI node matching
```

The optimizer is responsible for matching holdings to allocation nodes. SPAXX:
- `is_cash_equivalent = True` → `return False` before reaching any equity node
- `asset_class = "CASH"` → would also return False

SPAXX is **never matched to an EQUITIES, FIXED_INCOME, or DIGITAL allocation node** by the optimizer.

---

## Section 4 — Allocation Model Configuration

**File:** `config/allocation_models/concentrated_alpha_profile.yaml` (active mandate: CONCENTRATED_ALPHA):

The CASH node is defined at the L1 level with:
```
target_pct: 7.0
label: "Cash Floor"
```

SPAXX's 8.6592% actual weight is 1.6592pp above the 7.0% target. This results in a `drift_direction: OVERWEIGHT` alignment state for the CASH node. Severity is `NONE` because cash overweight is a governance-monitored condition, not an alert-level breach.

---

## Section 5 — Cash Mandate Context

**File:** `src/portfolio/runner.py`, lines 654–657:
```python
cash_ar = next((a for a in alignment if a.node_key == "CASH"), None)
cash_mandate_context = get_cash_interpretation(
    cash_actual_pct=cash_ar.actual_pct if cash_ar else 0.0,
    cash_target_pct=cash_ar.target_pct if cash_ar else 0.0,
    mandate_type="CONCENTRATED_ALPHA",
)
```

The mandate context is computed from the CASH alignment result, which is driven by SPAXX's market value. This is the only allocation node that SPAXX affects.

---

## Section 6 — CASH Node Double-Count Prevention (Phase 6.3D Fix)

**File:** `src/portfolio/exposure_decomposition.py` (Phase 6.3D fix):
```python
# Bug 1 fix: sector == asset_class double-count prevention
# SPAXX has sector="Cash" (→ "CASH") == asset_class="CASH"
# The fix prevents the sector block from adding a second contribution
# when sector.upper() already equals asset_class.
```

Prior to Phase 6.3D, SPAXX's `sector="Cash"` caused a double-count: `effective["CASH"]` received 2× the actual weight (18.051% instead of 9.025%). The fix prevents this.

Current live state confirms fix is active:
```
holdings.csv: SPAXX percent_of_portfolio = 8.6592
alignment.csv: CASH actual_pct = 8.6592  ← single-counted, correct
```

---

## Section 7 — Other Nodes (SPAXX Contribution = 0.0%)

From `alignment.csv` (PAR-20260602-1BF2ADA5) — SPAXX contribution to each non-CASH node is 0.0%:

| L1 Node | SPAXX Contribution | Expected |
|---------|-------------------|----------|
| EQUITIES | 0.0% | 0.0% |
| FIXED_INCOME | 0.0% | 0.0% |
| DIGITAL | 0.0% | 0.0% |
| COMMODITIES | 0.0% | 0.0% |
| CASH | 8.6592% | 8.6592% |

---

## Section 8 — Reconciliation Check (RC-04)

**File:** `src/portfolio/reconciliation.py`, RC-04 (allocation integrity check):
Validates that the sum of all L1 allocation node actual percentages equals 100% (within tolerance). If SPAXX were contributing to multiple nodes, this check would fail (double-count).

The RC-04 check passing in the current run confirms SPAXX contributes exactly once, to the CASH node.
