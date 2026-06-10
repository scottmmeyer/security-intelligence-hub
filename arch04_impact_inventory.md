# ARCH-04: Impact Inventory

**Date:** 2026-06-09  
**PAR:** PAR-20260609-87134CE1

---

## All Active Multi-Symbol REDUCE_OVERWEIGHT Recommendations

### REC-5DD333BD — Reduce EQUITIES.INTERNATIONAL (+5.9% drift)

| Symbol | Policy | Before ARCH-04 | After ARCH-04 | Correct? |
|---|---|---|---|---|
| **DODFX** | SELL_LAST | DEFERRED | DEFERRED | ✓ (correct — has individual policy) |
| **VEA** | None | **DEFERRED (inherited)** | **EXECUTABLE** | ✓ Fixed |
| **TTNDY** | None | **DEFERRED (inherited)** | **EXECUTABLE** | ✓ Fixed |
| **KGC** | None | **DEFERRED (inherited)** | **EXECUTABLE** | ✓ Fixed |
| **STNG** | None | **DEFERRED (inherited)** | **EXECUTABLE** | ✓ Fixed |
| **NVS** | None | **DEFERRED (inherited)** | **EXECUTABLE** | ✓ Fixed |
| **SIMO** | None | **DEFERRED (inherited)** | **EXECUTABLE** | ✓ Fixed |
| **TSM** | None | **DEFERRED (inherited)** | **EXECUTABLE** | ✓ Fixed |
| **SBS** | None | **DEFERRED (inherited)** | **EXECUTABLE** | ✓ Fixed |
| **CVE** | None | **DEFERRED (inherited)** | **EXECUTABLE** | ✓ Fixed |
| **GTX** | None | **DEFERRED (inherited)** | **EXECUTABLE** | ✓ Fixed |
| **ASML** | None | **DEFERRED (inherited)** | **EXECUTABLE** | ✓ Fixed |

**Rec-level state:** DEFERRED_BY_POLICY → **EXECUTABLE**  
**Symbols incorrectly inheriting deferral:** 11 (all except DODFX)

### REC-F129627C — Reduce EQUITIES.US.MEGA.ULTRA_MEGA (+4.3% drift)

| Symbol | Policy | Before ARCH-04 | After ARCH-04 | Correct? |
|---|---|---|---|---|
| **TSLA** | DO_NOT_SELL | BLOCKED | BLOCKED | ✓ (correct — has individual policy) |
| **MU** | None | **BLOCKED (inherited)** | **EXECUTABLE** | ✓ Fixed |
| **VOO** | None | **BLOCKED (inherited)** | **EXECUTABLE** | ✓ Fixed |
| **FXAIX** | None | **BLOCKED (inherited)** | **EXECUTABLE** | ✓ Fixed |

**Rec-level state:** BLOCKED_BY_POLICY → **EXECUTABLE**  
**Symbols incorrectly inheriting block:** 3 (MU, VOO, FXAIX)

---

## Summary of Incorrectly Inherited States

| Symbol | Was | Now | Root Cause |
|---|---|---|---|
| KGC | DEFERRED_BY_POLICY | EXECUTABLE | Inherited from DODFX SELL_LAST |
| VEA | DEFERRED_BY_POLICY | EXECUTABLE | Inherited from DODFX SELL_LAST |
| TTNDY | DEFERRED_BY_POLICY | EXECUTABLE | Inherited from DODFX SELL_LAST |
| STNG | DEFERRED_BY_POLICY | EXECUTABLE | Inherited from DODFX SELL_LAST |
| NVS | DEFERRED_BY_POLICY | EXECUTABLE | Inherited from DODFX SELL_LAST |
| SIMO | DEFERRED_BY_POLICY | EXECUTABLE | Inherited from DODFX SELL_LAST |
| TSM | DEFERRED_BY_POLICY | EXECUTABLE | Inherited from DODFX SELL_LAST |
| SBS | DEFERRED_BY_POLICY | EXECUTABLE | Inherited from DODFX SELL_LAST |
| CVE | DEFERRED_BY_POLICY | EXECUTABLE | Inherited from DODFX SELL_LAST |
| GTX | DEFERRED_BY_POLICY | EXECUTABLE | Inherited from DODFX SELL_LAST |
| ASML | DEFERRED_BY_POLICY | EXECUTABLE | Inherited from DODFX SELL_LAST |
| MU | BLOCKED_BY_POLICY | EXECUTABLE | Inherited from TSLA DO_NOT_SELL |
| VOO | BLOCKED_BY_POLICY | EXECUTABLE | Inherited from TSLA DO_NOT_SELL |
| FXAIX | BLOCKED_BY_POLICY | EXECUTABLE | Inherited from TSLA DO_NOT_SELL |

**Total symbols incorrectly classified:** 14 across 2 recommendations.

---

## Symbols Correctly Constrained (Unchanged)

| Symbol | Policy | State | Correct |
|---|---|---|---|
| TSLA | DO_NOT_SELL | BLOCKED_BY_POLICY | ✓ |
| DODFX | SELL_LAST | DEFERRED_BY_POLICY | ✓ |
