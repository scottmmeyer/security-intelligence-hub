# RC-02 Reconciliation Validation

**Date:** 2026-06-09  
**Validation PAR:** PAR-20260609-87134CE1

---

## Pre-fix State (PAR-20260609-5C476C55)

| Check | Status | Detail |
|---|---|---|
| RC-02 | **FAIL** | L1 sum = 98.6452% (gap = −1.3548pp) |
| Unclassified holdings | 3 | BSVN, STNG, SIMO (asset_class=UNKNOWN) |
| RC-06 | WARN | SPAXX advisory (no change) |
| Overall | FAIL | 11/13 PASS, 1 WARN, 1 FAIL |

## Post-fix State (PAR-20260609-87134CE1)

| Check | Status | Detail |
|---|---|---|
| RC-02 | **PASS** | L1 sum = 99.9997% (gap = −0.0003pp, within 0.10pp tolerance) |
| Unclassified holdings | 0 | BSVN, STNG, SIMO now classified |
| RC-06 | WARN | SPAXX advisory (unchanged — expected) |
| Overall | WARN | 12/13 PASS, 1 WARN |

**RC-02 moved from FAIL → PASS. ✓**

## Classification Validation

| Symbol | Before | After |
|---|---|---|
| BSVN | `asset_class=UNKNOWN, geography=UNKNOWN, market_cap_bucket=UNKNOWN` | `asset_class=EQUITIES, geography=US, market_cap_bucket=MICRO, sector=FINANCIAL SERVICES` |
| STNG | `asset_class=UNKNOWN, geography=UNKNOWN, market_cap_bucket=UNKNOWN` | `asset_class=EQUITIES, geography=INTERNATIONAL, market_cap_bucket=SMALL, sector=ENERGY` |
| SIMO | `asset_class=UNKNOWN, geography=UNKNOWN, market_cap_bucket=UNKNOWN` | `asset_class=EQUITIES, geography=INTERNATIONAL, market_cap_bucket=SMALL, sector=TECHNOLOGY` |

## Recommendation Count Check

| PAR | Rec Count |
|---|---|
| Pre-fix (5C476C55) | 34 |
| Post-fix (87134CE1) | 34 |

**No recommendation count change. ✓**

## L1 Allocation Sum

| PAR | L1 Sum | Status |
|---|---|---|
| Pre-fix | 98.6452% | RC-02 FAIL |
| Post-fix | 99.9997% | RC-02 PASS (gap < 0.10pp tolerance) |

The residual 0.0003pp gap is floating-point rounding in the alignment computation — well within the 0.10pp tolerance.

## Overall Reconciliation

Post-fix overall status: **WARN** (was FAIL)

The single remaining WARN is RC-06 (SPAXX in ETF registry — advisory only). This is a known advisory condition with no operator action required. It does not affect allocation scoring or recommendations.

## Allocation Map Impact

BSVN (0.58%): now contributes to `EQUITIES.US.MICRO`  
STNG (0.49%): now contributes to `EQUITIES.INTERNATIONAL`  
SIMO (0.28%): now contributes to `EQUITIES.INTERNATIONAL`  

Combined 1.35pp now correctly accounted for in L1 EQUITIES node.
