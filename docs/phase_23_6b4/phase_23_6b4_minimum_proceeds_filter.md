# Phase 23.6B.4 — Minimum Proceeds Filter

**Date:** 2026-06-04  

---

## Problem

CRA included 6+ sources with proceeds below any rational execution threshold:
- XRP: $92
- FSOL: $81
- CMCO: $137
- NVS: $221
- TTNDY: $135
- AGEN: $340

These diluted operator attention alongside genuine $5,000–$7,000 tax harvest opportunities.

---

## Fix

**File:** `src/portfolio/cra/capital_source_builder.py`

Added `MINIMUM_ACTIONABLE_PROCEEDS = 500.0` constant and updated return type to tuple:

```python
MINIMUM_ACTIONABLE_PROCEEDS = 500.0

def build_capital_sources(..., minimum_proceeds: float = MINIMUM_ACTIONABLE_PROCEEDS
) -> tuple[List[CapitalSourceRecord], List[CapitalSourceRecord]]:
```

At the end of the function:
```python
sources, suppressed = [], []
for rec in all_records:
    if rec.estimated_proceeds < minimum_proceeds:
        suppressed.append(rec)
    else:
        sources.append(rec)
return sources, suppressed
```

**File:** `src/portfolio/cra/models.py`

Added `suppressed_sources` field to `RotationProposal` and `suppressed_source_count` to `to_dict()`.

**File:** `src/portfolio/cra/rotation_proposal_builder.py`

Updated to handle tuple return from `build_capital_sources` and pass `suppressed_sources` to the proposal.

---

## Live Validation

```
XRP     ($92):   main=False suppressed=True  ✅ PASS
FSOL    ($81):   main=False suppressed=True  ✅ PASS
CMCO    ($137):  main=False suppressed=True  ✅ PASS
NVS     ($221):  main=False suppressed=True  ✅ PASS
TTNDY   ($135):  main=False suppressed=True  ✅ PASS
AGEN    ($340):  main=False suppressed=True  ✅ PASS
Suppressed count: 6
```

Suppressed sources accessible via `proposal.suppressed_sources` / `suppressed_source_count` in API for diagnostic purposes.

FETH ($1,025) and YELP ($873) remain in main list — both are above $500 threshold and are legitimate tax harvest candidates with actual loss positions.
