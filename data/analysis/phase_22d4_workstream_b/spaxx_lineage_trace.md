# Q1 — SPAXX Classification Lineage Trace
## Workstream B: SPAXX / Cash Equivalent Governance Certification

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D — Workstream B  
**Scope:** Full platform lineage, SPAXX from CSV row to UI render  

---

## Overview

This document traces SPAXX through every platform stage, showing the input, transformation, and output at each step.

---

## Stage 1 — Holdings Ingestion (`src/portfolio/ingestion.py`)

### Input
```
Fidelity CSV row:
  Symbol:           SPAXX**
  Description:      FIDELITY GOVERNMENT MONEY MARKET
  Current Value:    $41,198.92
  Percent Of Account: 8.6592%
  Quantity:         --
```

### Transformation
**File:** `src/portfolio/ingestion.py`, function `_normalize_symbol()`, line 80:
```python
def _normalize_symbol(raw: str) -> str:
    """Upper-case, strip whitespace and Fidelity trailing asterisks (e.g. SPAXX**)."""
    sym = str(raw).strip().upper().rstrip("*")
    return sym if sym not in ("--", "", "N/A") else "CASH"
```
- `"SPAXX**"` → stripped asterisks → `"SPAXX"`

**File:** `src/portfolio/ingestion.py`, line 318:
```python
_CASH_KEYWORDS = {"CASH", "SPAXX", "FZFXX", "FDRXX", "FCASH", "PENDING"}
```
SPAXX is in `_CASH_KEYWORDS`. The `_classify_operational_state()` function assigns `ACTIVE_POSITION` during ingestion (enrichment upgrades this — see Stage 2).

### Output (raw holding, pre-enrichment)
```
symbol:           SPAXX
security_type:    Cash  (inferred from description + symbol)
operational_state: ACTIVE_POSITION  (enrichment upgrades this)
market_value:     41198.92
percent_of_portfolio: 8.6592
```

---

## Stage 2 — Enrichment (`src/portfolio/enrichment.py`)

### Input
Pre-enrichment holding from Stage 1.

### Transformation — Part A: Override table lookup

**File:** `src/portfolio/enrichment.py`, lines 84–89 (static override table):
```python
_ETF_OVERRIDES = {
    ...
    "SPAXX": dict(asset_class="CASH", geography="US", market_cap_bucket="N/A",
                  mega_subtier="N/A", sector="Cash", industry="Money Market"),
    ...
}
```
SPAXX has a direct override entry with `asset_class="CASH"`.

### Transformation — Part B: Cash-equivalent protection guard

**File:** `src/portfolio/enrichment.py`, lines 120–122:
```python
_CASH_EQUIVALENT_SYMBOLS: frozenset[str] = frozenset(
    sym for sym, ov in _ETF_OVERRIDES.items() if ov.get("asset_class") == "CASH"
) | frozenset({"FDRXX", "SPRXX", "FCASH", ...})
```
SPAXX is in `_CASH_EQUIVALENT_SYMBOLS` (derived automatically from the override table since `asset_class == "CASH"`).

**File:** `src/portfolio/enrichment.py`, lines 227–234:
```python
if sym in _CASH_EQUIVALENT_SYMBOLS:
    effective_security_type = "Cash"       # NOT promoted to "ETF"
    is_cash_equiv = True
    new_op_state = "CASH_EQUIVALENT"
```
The guard explicitly prevents SPAXX from receiving `security_type="ETF"` even though it appears in the ETF registry YAML.

### Output (enriched holding, confirmed from live holdings.csv PAR-20260602-1BF2ADA5)
```
symbol:             SPAXX
security_type:      Cash
asset_class:        CASH
is_cash_equivalent: True
operational_state:  CASH_EQUIVALENT
market_value:       41198.92
percent_of_portfolio: 8.6592
sector:             Cash
geography:          US
market_cap_bucket:  N/A
mega_subtier:       N/A
exposure_market_cap_mix:  () — empty
exposure_mega_subtier_mix: () — empty
```

---

## Stage 3 — Security Classification (asset-class assignment)

**File:** `src/portfolio/enrichment.py`, override table  
**Assigned:** `asset_class = "CASH"` ← direct, from `_ETF_OVERRIDES["SPAXX"]`  
**No further reclassification occurs.** The `asset_class` field is frozen after enrichment.

Confirmed in live `holdings.csv`:
```
asset_class: CASH  ✅
```

---

## Stage 4 — Allocation Hierarchy

**File:** `src/portfolio/reconciliation.py`, lines 51–54:
```python
_CASH_EQUIVALENT_SYMBOLS = frozenset({
    "SPAXX", "FCASH", "FDRXX", "SPRXX", "VMFXX", "FZFXX", ...
})
```

In `compute_alignment()`, SPAXX contributes its `percent_of_portfolio` (8.6592%) exclusively to the `CASH` L1 node. 

Confirmed in live `alignment.csv`:
```
node_key:       CASH
actual_pct:     8.6592   ← matches SPAXX market_value/total_mv exactly
target_pct:     7.0
drift_pct:      1.6592
drift_direction: OVERWEIGHT
severity:       NONE
```
SPAXX contributes to CASH and ONLY CASH. Zero contribution to EQUITIES, FIXED_INCOME, DIGITAL, or COMMODITIES.

---

## Stage 5 — Overlay Generation (`src/portfolio/recommendations.py`)

**File:** `src/portfolio/recommendations.py`, lines 1346–1347:
```python
is_ce = getattr(h, "is_cash_equivalent", False)
if op_state == "CASH_EQUIVALENT" or is_ce:
    continue   # excluded from ETF contributor accumulation
```

SPAXX receives a security overlay with:
```
signal_direction:  UNKNOWN    (no ESS signal applies)
composite_score:   None       (no analytical universe entry for cash)
replay_supported:  False      (cash cannot have replay universe)
replay_percentile: None
opportunity_flag:  HOLD
```
Confirmed from live `security_overlays.csv`.

---

## Stage 6 — Recommendation Engine

**File:** `src/portfolio/recommendations.py`, line 1393:
```python
_EXCLUDED_OP_STATES = {
    "CASH_EQUIVALENT",  # ← SPAXX excluded here
    "PENDING_SETTLEMENT",
    "ACCOUNTING_ADJUSTMENT",
    "CLOSED_POSITION",
}
```
SPAXX is **not eligible** to receive INCREASE, DECREASE, or MAINTAIN position recommendations. The recommendation engine issues recommendations at the CASH *node* level (e.g. "CASH is 1.66pp overweight — reduce"), not at the SPAXX *holding* level.

Also in the funding source computation (`src/portfolio/recommendations.py`, line 612):
```python
cash_holdings = [h for h in holdings if h.is_cash_equivalent or h.asset_class == "CASH"]
```
SPAXX is correctly identified as the funding source for equity deployment recommendations.

---

## Stage 7 — Deployment Planner (`src/portfolio/deployment_queue.py`)

**File:** `src/portfolio/deployment_queue.py`, line 205:
```python
if holding.is_cash_equivalent:
    return False   # ineligible — cash cannot be a deployment candidate
```

**File:** `src/portfolio/deployment_queue.py`, line 390:
```python
cash_mv = sum(h.market_value for h in holdings if h.is_cash_equivalent)
```
SPAXX contributes to `cash_mv` (the total cash balance), which is used to compute `deployable_mv`.

Confirmed from live `deployment_queue.json`:
```
SPAXX in deployment queue:  False
cash_context.cash_mv:       41198.92   ← includes SPAXX MV
cash_context.floor_mv:      9515.59
cash_context.deployable_mv: 31683.33
```

---

## Stage 8 — UCF (Unified Conviction Framework)

Confirmed from live `ucf_verdicts.json` (PAR-20260602-1BF2ADA5):
```
symbol:             SPAXX
ucf_label:          MAINTAIN
ucf_score:          0.0
ucf_rank:           73      (last rank — lowest conviction)
cw_das_score:       None    (no CW-DAS score — not in deployment queue)
cw_das_rank:        None
deployment_eligible: None
```
SPAXX receives `MAINTAIN` — the structural hold label for cash. UCF score is 0.0 because `composite_score = None` and `replay_supported = False`. No conviction scoring is applied.

---

## Stage 9 — CW-DAS Scoring

**File:** `src/portfolio/deployment_queue.py`, function `_is_eligible()`, line 205:
```python
if holding.is_cash_equivalent:
    return False   # hard gate: cash is never scored by CW-DAS
```

CW-DAS gate checklist for SPAXX:
```
is_cash_equivalent = True  → FAIL gate immediately
```
SPAXX receives **no CW-DAS score**. `cw_das_score = None` confirmed in ucf_verdicts.json.

---

## Stage 10 — PMI (Portfolio Management Intelligence)

SPAXX contributes to the PMI cash balance and cash governance context:
```
cash_mandate_context = get_cash_interpretation(
    cash_actual_pct=8.6592,  ← SPAXX drives this
    cash_target_pct=7.0,
    mandate_type="CONCENTRATED_ALPHA",
)
```
The PMI interprets the CASH node as 1.66pp overweight (SPAXX actual vs 7.0% target). SPAXX does NOT contribute to equity node coverage, overlap analysis, or conviction scoring within PMI.

---

## Stage 11 — Replay

SPAXX is **excluded from all replay calculations**.

**File:** `src/portfolio/runner.py`, line 558:
```python
_INVESTABLE_STATES = frozenset({"ACTIVE_POSITION", "CASH_EQUIVALENT"})
investable = [h for h in enriched if h.operational_state in _INVESTABLE_STATES]
```
SPAXX is included in the `investable` list but only for cash governance purposes.

From `phase_7_4f_replay_consistency_audit.md`:
> "SPAXX is a cash equivalent (`is_cash_equivalent=True`). The investable denominator excludes it on the basis that cash is not eligible for replay evidence."

Confirmed: `security_overlays.csv` shows `replay_supported: False` and `replay_percentile: None` for SPAXX.

---

## Stage 12 — UI Rendering

**Allocation Intelligence UI** (`ui/allocation_intelligence/app.js`):
- CASH node (which includes SPAXX) displayed under the "CASH" asset class category
- `cash_floor_pct` shown in strategy card
- No SPAXX-specific label — aggregated as "CASH" node

**Portfolio Alignment UI** (`ui/portfolio_alignment/app.js`):
- Cash weight shown as `cash_before_pct` (8.7%) in deployment action card
- Cash is identified as funding source in recommendation rationale: `"Funding source: Excess Cash (SPAXX, ~7.0% available)"`
- SPAXX is NOT rendered in any conviction card, overlay table, or signal profile panel

**UCF Dashboard** (`ui/ucf_operator_dashboard/index.html`):
- SPAXX appears in the holdings table with `MAINTAIN` label
- No conviction tier badge, no deployment badge, no replay badge

---

## Summary Table

| Stage | Component | SPAXX Treatment | Evidence Source |
|-------|-----------|-----------------|-----------------|
| 1 | Ingestion | Symbol normalized: `SPAXX**` → `SPAXX` | `src/portfolio/ingestion.py:80` |
| 2 | Enrichment | `asset_class=CASH`, `security_type=Cash`, `is_cash_equivalent=True`, `operational_state=CASH_EQUIVALENT` | `src/portfolio/enrichment.py:231-234` |
| 3 | Classification | `asset_class=CASH` frozen permanently | `enrichment.py _ETF_OVERRIDES["SPAXX"]` |
| 4 | Allocation hierarchy | Contributes to `CASH` node only (8.6592%) | `alignment.csv`, `reconciliation.py` |
| 5 | Overlay generation | `signal=UNKNOWN`, `composite=None`, `replay=False`, `flag=HOLD` | `security_overlays.csv` |
| 6 | Recommendation engine | Excluded from position-level recs; correct funding source | `recommendations.py:1393` |
| 7 | Deployment planner | Not in queue; contributes to `cash_mv` | `deployment_queue.json` |
| 8 | UCF | `MAINTAIN`, `score=0.0`, `rank=73 (last)` | `ucf_verdicts.json` |
| 9 | CW-DAS | Gate fails at `is_cash_equivalent=True`; no score | `deployment_queue.py:205` |
| 10 | PMI | Contributes to cash balance narrative only | `runner.py:654-657` |
| 11 | Replay | Excluded; `replay_supported=False` | `security_overlays.csv`, `runner.py:558` |
| 12 | UI | Rendered as CASH/MAINTAIN only — no conviction/ETF/signal labels | All UI files |
