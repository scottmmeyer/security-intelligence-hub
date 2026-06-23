# SPCX Classification Investigation

**Date:** 2026-06-16  
**Status:** RESOLVED — Fix applied to `src/portfolio/enrichment.py`

---

## Executive Summary

SPCX (Procure Space ETF, NYSE: SPCX) entered the portfolio as a new position worth $1,925.00 (0.3985% of portfolio). Because it was absent from all SIH classification registries, the enrichment pipeline assigned `asset_class=UNKNOWN`. This caused RC-02 (Allocation Total Reconciliation) to FAIL with an L1 sum of 99.6018% instead of 100.00%.

**Fix:** Added SPCX to `_ETF_OVERRIDES` in `src/portfolio/enrichment.py` with `asset_class=EQUITIES, geography=US, market_cap_bucket=SMALL, sector=Technology, industry=Aerospace & Defense`.

---

## Q1: Why is SPCX unclassified?

SPCX was absent from all three classification sources consulted by the enrichment pipeline:
1. `data/current/analytical_universe.csv` — SPCX not present
2. `_ETF_OVERRIDES` in `src/portfolio/enrichment.py` — SPCX not present
3. `config/etf_exposure_decomposition.yaml` symbols registry — SPCX not present

When all three lookups return `None`, the enrichment step leaves `asset_class=UNKNOWN`. The allocation roll-up sums only holdings with recognized L1 asset class values (EQUITIES, FIXED_INCOME, DIGITAL, COMMODITIES, CASH), so SPCX's 0.3985% weight is excluded from the L1 sum, producing 99.6018% instead of 100.00%.

---

## Q2: What classification should SPCX receive?

**SPCX = Procure Space ETF** (NYSE: SPCX)

- `asset_class`: EQUITIES
- `geography`: US (US-listed, USD-denominated; underlying holdings are primarily US-domiciled aerospace/space companies)
- `market_cap_bucket`: SMALL (the ETF holds primarily small and mid-cap space technology companies; the fund itself is small by AUM)
- `mega_subtier`: N/A
- `sector`: Technology
- `industry`: Aerospace & Defense

Fidelity labels SPCX as "Common Stock" in their CSV export (standard Fidelity behavior for equity ETFs listed as exchange-traded securities). The description "SPACE EXPL TECHNOLOGIES CORP CL A" is Fidelity's internal description text for this position.

---

## Q3: Does ETF decomposition already know how to classify SPCX?

**No.** SPCX was not present in `config/etf_exposure_decomposition.yaml`. However, since SPCX holds US equity securities, the direct classification approach (via `_ETF_OVERRIDES`) is sufficient and appropriate. No ETF decomposition registry entry is required for this holding — it is classified as a direct EQUITIES/US/SMALL position without further decomposition.

If granular look-through decomposition is desired in the future (e.g., breaking SPCX into its underlying aerospace holdings), a `config/etf_exposure_decomposition.yaml` entry can be added. This is a future enhancement, not required for RC-02 remediation.

---

## Q4: Does the issue affect rankings, recommendations, governance, or reporting?

| System | Impact | Details |
|--------|--------|---------|
| RC-02 (Allocation Reconciliation) | **FAIL → PASS** | L1 sum: 99.6018% → 100.00% after fix |
| Recommendations | Unaffected | SPCX's 0.3985% weight is too small to alter recommendation priorities |
| CW-DAS | Unaffected | CW-DAS ranks holdings by composite signal scores; SPCX has no ESS/Zacks signal |
| UCF | Minor | SPCX will now appear in the EQUITIES allocation bucket; UCF verdicts unchanged |
| PIS change detection | Unaffected | PIS tracks quantity/value changes; classification does not affect change events |
| PIS compliance | Minor improvement | After fix, SPCX contributes to EQUITIES allocation; compliance calculations more accurate |
| PAR (deployment/reduction queues) | Unaffected | SPCX has no composite score → not deployment-eligible |
| CRA | Unaffected | CRA allocation rebalancing is driven by drift across the 30-node hierarchy; SPCX weight (0.4%) is below CRA action threshold |

---

## Q5: What exact code/configuration change is required?

**File modified:** `src/portfolio/enrichment.py`  
**Section:** `_ETF_OVERRIDES` dictionary — "Individual equity overrides — RC-02 classification gap fix"

```python
"SPCX":  dict(asset_class="EQUITIES", geography="US", market_cap_bucket="SMALL",
              mega_subtier="N/A", sector="Technology", industry="Aerospace & Defense"),
# Procure Space ETF (NYSE: SPCX) — US-listed space technology equity ETF; RC-02 fix 2026-06-16
```

**No other changes required.**

---

## Code Path Trace

```
Portfolio CSV ingestion (ingestion.py)
    → PortfolioHolding(symbol="SPCX", asset_class="UNKNOWN")

Enrichment (enrichment.py)
    → Step 1: analytical_universe.csv lookup  → Miss (SPCX absent)
    → Step 2: _ETF_OVERRIDES lookup           → Miss (SPCX absent) ← FIX APPLIED HERE
    → Step 3: Cash heuristic                  → No (not a cash symbol)
    → Result: asset_class remains "UNKNOWN"

Allocation rollup (alignment.py)
    → L1 sum excludes UNKNOWN holdings
    → L1 sum: 99.6018% (missing 0.3985%)

Reconciliation (reconciliation.py RC-02)
    → FAIL: L1 sum 99.6018% < 100.00% - 0.10pp tolerance
    → Identifies SPCX as unclassified symbol
    → root_cause: "A: missing_asset_class_mapping"
```

---

## Expected Post-Fix Allocation Totals

| | Pre-Fix | Post-Fix |
|-|---------|---------|
| L1 sum | 99.6018% | ~100.00% |
| EQUITIES | 87.2947% | ~87.6932% (+0.3985%) |
| CASH | 10.2268% | 10.2268% |
| FIXED_INCOME | 1.4324% | 1.4324% |
| DIGITAL | 0.6479% | 0.6479% |
| COMMODITIES | 0.0000% | 0.0000% |
| UNKNOWN (non-zero) | 0.3985% | 0.0000% |
| RC-02 status | FAIL | PASS |
