# ARCH-04: Validation Report

**Date:** 2026-06-09

---

## Regression Outcome

| Suite | Passed | Skipped | Failed |
|---|---|---|---|
| Full test suite (pytest) | 1203 | 1 | **0** |
| Includes 11 new ARCH-04 tests | — | — | — |

---

## Per-Symbol State Verification (live portfolio data)

### REC-5DD333BD — REDUCE EQUITIES.INTERNATIONAL

| Symbol | ARCH-04 State | Expected | Pass? |
|---|---|---|---|
| DODFX | DEFERRED_BY_POLICY (SELL_LAST) | DEFERRED | ✓ |
| KGC | **EXECUTABLE** | EXECUTABLE | ✓ **Fixed** |
| VEA | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |
| TTNDY | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |
| STNG | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |
| NVS | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |
| SIMO | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |
| TSM | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |
| SBS | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |
| CVE | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |
| GTX | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |
| ASML | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |
| **Rec-level** | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |

### REC-F129627C — REDUCE EQUITIES.US.MEGA.ULTRA_MEGA

| Symbol | ARCH-04 State | Expected | Pass? |
|---|---|---|---|
| TSLA | BLOCKED_BY_POLICY (DO_NOT_SELL) | BLOCKED | ✓ |
| MU | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |
| VOO | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |
| FXAIX | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |
| **Rec-level** | **EXECUTABLE** | EXECUTABLE | ✓ Fixed |

---

## Policy Surface Agreement Check

| Surface | TSLA | DODFX | KGC |
|---|---|---|---|
| `apply_policy_to_recommendations()` | BLOCKED | DEFERRED | **EXECUTABLE** ✓ |
| Drilldown holdings annotation | BLOCKED | DEFERRED | **EXECUTABLE** ✓ |
| Security overlay (`ov.execution_state`) | BLOCKED | EXECUTABLE (HOLD flag) | EXECUTABLE ✓ |
| PAP Cat 3 (per-ov policy_type) | BLOCKED | DEFERRED | EXECUTABLE ✓ |
| CRA capital sources | BLOCKED | DEFERRED | EXECUTABLE ✓ |
| Reduction Queue (ARCH-02) | BLOCKED | DEFERRED | EXECUTABLE ✓ |

All surfaces agree on KGC = EXECUTABLE. ✓

---

## Behavioral Change Checklist

| Attribute | Changed? | Notes |
|---|---|---|
| CW-DAS scoring | No | |
| RPS scoring | No | |
| ESS signals | No | |
| STI / trim priority | No | |
| CRA capital source ranking | No | |
| PAP rec generation logic | No | |
| DQ eligibility gates | No | |
| `symbol_execution_states` field | Added | New additive field on sell-context recs |
| Drilldown holdings annotated | Added | Per-symbol execution_state/policy_type |
| Rec-level `execution_state` | Changed semantics | EXECUTABLE if any symbol executable |
| Tests updated | Yes | 11 new ARCH-04 tests, 6 updated (most-restrictive-wins → per-symbol) |
| PAP lane placement | Changed | Both REDUCE_OVERWEIGHT recs move from Blocked → Actions lane |
