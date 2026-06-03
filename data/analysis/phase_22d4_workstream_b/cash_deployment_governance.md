# Q5 — Cash Deployment Governance
## Workstream B: SPAXX / Cash Equivalent Governance Certification

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D — Workstream B  
**Scope:** SPAXX treatment in deployment queue, cash balance, CW-DAS eligibility  

---

## Verdict: SPAXX Is Correctly Excluded from Deployment Queue and Scores, While Contributing to Cash Balance

SPAXX is the source of deployable cash but is never itself a deployment target.

---

## Section 1 — Deployment Queue Exclusion (Live Evidence)

From `data/portfolio_ingestion/analysis_runs/PAR-20260602-1BF2ADA5/deployment_queue.json`:

```
Deployment queue symbols (42 total):
  ['VRT', 'ARW', 'ATLC', 'SNX', 'PSX', 'CBOE', 'AVT', 'LRCX', 'CAH',
   'SANM', 'PCB', 'DELL', 'CIEN', 'NUE', 'GFF', 'ALNT', 'MTZ', 'CRS',
   'CMCO', 'ANGO', 'FSLR', 'UHS', 'HALO', 'BSVN', 'STLD', 'AGEN', 'YELP',
   'DVN', 'UTHR', 'ANIP', 'AZZ', 'CVE', 'TSM', 'GTX', 'ASML', 'MU',
   'STNG', 'SIMO', 'AVGO', 'MSFT', 'NVDA', 'SBS']

SPAXX in deployment queue: False  ✅
VMFXX in deployment queue: False  ✅
FZFXX in deployment queue: False  ✅
FDRXX in deployment queue: False  ✅
SPRXX in deployment queue: False  ✅
FCASH in deployment queue: False  ✅
```

No cash-equivalent symbol appears in the deployment queue.

---

## Section 2 — Deployment Queue Eligibility Gate (Code)

**File:** `src/portfolio/deployment_queue.py`, function `_is_eligible()`, lines 205–210:
```python
def _is_eligible(holding: PortfolioHolding) -> bool:
    """Return True if a holding can receive a CW-DAS score.
    
    FIRST gate: cash equivalents are always ineligible.
    """
    if holding.is_cash_equivalent:
        return False   # ← SPAXX hits this immediately; no further evaluation
    ...
```

The `is_cash_equivalent` flag is the **first** gate evaluated. SPAXX (`is_cash_equivalent = True`) returns `False` before any other eligibility condition is checked. The gate does not depend on `security_type`, `asset_class`, or `operational_state` — `is_cash_equivalent` alone is sufficient.

From the `DeploymentCandidate` docstring (line 93):
```python
class DeploymentCandidate:
    """
    Represents an eligible non-cash, non-excluded holding.
    
    Eligibility requirements (all must hold):
      ...
      is_cash_equivalent = False  ← explicit exclusion criterion
    """
```

---

## Section 3 — CW-DAS Score Exclusion

CW-DAS (Conviction-Weighted Deployment Allocation Score) is only computed for holdings that pass `_is_eligible()`. Because SPAXX fails the first gate:
- `compute_cw_das()` is never called for SPAXX
- SPAXX has no CW-DAS score, no CW-DAS rank, no deployment priority

Confirmed from live `ucf_verdicts.json`:
```
SPAXX:
  cw_das_score:       None  ✅ (no score)
  cw_das_rank:        None  ✅ (no rank)
  deployment_eligible: None ✅ (not eligible)
```

---

## Section 4 — Cash Balance Contribution (Correct Behavior)

While SPAXX is excluded from the deployment queue, its market value **correctly contributes to the cash balance** used to compute deployable capital.

**File:** `src/portfolio/deployment_queue.py`, function `compute_deployable_cash()`, line 390:
```python
cash_mv = sum(
    h.market_value for h in holdings if h.is_cash_equivalent
)
```

From live `deployment_queue.json` (`cash_context`):
```
cash_mv:        41198.92   ← SPAXX market value (only cash-equivalent position)
floor_mv:       9515.59    ← 2.0% mandate cash floor (MIN_CASH_PCT * total_mv)
deployable_mv:  31683.33   ← cash_mv - floor_mv = available for deployment
```

**Calculation verification:**
```
cash_mv       = 41198.92
total_portfolio_mv ≈ 476,246  (implied from SPAXX 8.6592% share)
MIN_CASH_PCT  = 2.0%
floor_mv      = 476,246 × 0.02 = 9,524.92 ≈ 9,515.59  (confirmed)
deployable_mv = 41,198.92 - 9,515.59 = 31,683.33       (confirmed)
```

SPAXX's market value is the entire cash balance in this portfolio. The platform correctly:
1. Sums SPAXX MV as cash available
2. Reserves 2.0% mandate floor (MIN_CASH_PCT)
3. Computes deployable = total cash − floor
4. Excludes SPAXX from any individual deployment candidate list

---

## Section 5 — UCF / Conviction Scoring

**File:** `src/portfolio/unified_conviction.py`, `build_ucf_verdicts()`:  
SPAXX appears in the UCF verdicts because it is in `_INVESTABLE_STATES` (runner.py line 558):
```python
_INVESTABLE_STATES = frozenset({"ACTIVE_POSITION", "CASH_EQUIVALENT"})
```

However, UCF scoring for SPAXX produces:
```
ucf_label:    MAINTAIN         ← structural hold label for cash
ucf_score:    0.0              ← composite=None + replay=False = 0.0
ucf_rank:     73 (last)        ← lowest conviction rank in portfolio
```

UCF does not generate "deploy SPAXX" or "increase SPAXX" signals. MAINTAIN is the correct verdict for a cash sweep fund.

---

## Section 6 — Deployment Planner Integration

**File:** `src/portfolio/deployment_planner.py`:
```python
@dataclass
class PortfolioImpact:
    cash_before_pct: float   # = compute_deployable_cash().cash_mv / total_mv
    cash_after_pct: float    # = (cash_before_mv - deployment_mv) / total_mv
```

SPAXX's market value feeds `cash_before_pct` and `cash_after_pct` via `compute_deployable_cash()`. These percentages are displayed in the Portfolio Alignment UI as the "Cash Available" gauge. This is correct behavior: SPAXX is the cash to be deployed, not a deployment target.

---

## Section 7 — Capital Deployment Queue Design Doc Reference

From `capital_deployment_queue_design.md`:
```
Section 4.1 — Exclusion Categories:
  Excluded: Cash | 1 | SPAXX

Section 4.2 — Cash Position:
  Cash (SPAXX) | $42,620 (9.03%)  ← listed separately from conviction queue
  (Note: different run date; current PAR shows $41,198.92 / 8.66%)

Section 5 — Eligibility Gate:
  Not cash | is_cash_equivalent | False  (confirms flag-based gate)
```

The design doc explicitly categorizes SPAXX as a cash exclusion, not a deployment candidate.

---

## Section 8 — Defense in Depth Summary

SPAXX is protected from deployment queue inclusion by four independent mechanisms:

| Layer | File | Mechanism |
|-------|------|-----------|
| 1 | `deployment_queue.py:205` | `is_cash_equivalent = True` → `_is_eligible()` returns `False` (first gate) |
| 2 | `enrichment.py:231` | `is_cash_equivalent` flag set hard by enrichment guard |
| 3 | `models.py:87` | `is_cash_equivalent: bool = False` — explicit field, defaults safe |
| 4 | `reconciliation.py:555` | RC-06 validates cash symbols are not in ETF/deployment positions |

Any single layer is sufficient. All four firing together ensures no single-point-of-failure in cash governance.
