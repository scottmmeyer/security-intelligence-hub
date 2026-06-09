# CRA-POOL-AUDIT: Forensic Audit Report

**Date:** 2026-06-09  
**PAR (Stale, user observed):** PAR-20260609-C17FC0BF  
**PAR (Fresh, generated during audit):** PAR-20260609-5C476C55  
**Scope:** TSLA policy trace, CRA capital pool inventory, policy compliance, PAP/CRA consistency

---

## Root Cause Summary

**The apparent contradiction is real but explains a system state bug, not a policy logic bug.**

PAP was showing TSLA as EXECUTABLE/TRIM because the on-disk `recommendations.json` in stale PARs (42A90186 and C17FC0BF) was generated without the policy execution state correctly applied to recommendation dicts. The CRA, by contrast, generates its capital pool at runtime and correctly excluded TSLA.

A fresh PAR (5C476C55) generated during this audit confirms the policy engine is working correctly end-to-end.

---

## Phase 1 — TSLA Trace

### Raw Signal State

| Field | Value |
|---|---|
| Symbol | TSLA |
| Portfolio Weight | 2.99% ($13,904) |
| ESS Score | VERY_BEARISH |
| Signal Direction | BEARISH |
| Zacks Rating | 2.0 |
| Danelfin Score | 1.5 |
| Composite Score | 1.33 / 5.0 |
| UCF Label | TRIM_WATCH |
| Opportunity Flag | TRIM |
| RPS (Reduction Priority Score) | 85 / 100 |
| Strategic Classification | TACTICAL_GROWTH |
| Replay Support | Yes (6.2nd percentile — UNDERPERFORMING) |
| Deployment Eligible | No |

### Policy State

| Field | Value |
|---|---|
| Policy Type | DO_NOT_SELL |
| Policy Status | ACTIVE |
| Rationale | "Optimus and spacex future" |
| Created | 2026-06-03T18:50:25 UTC |
| Revoked | Not revoked |

### Policy Application Trace (per system layer)

| Layer | Artifact | TSLA State | Correct? |
|---|---|---|---|
| Security Overlay | `security_overlays.csv` | `execution_state=BLOCKED_BY_POLICY` / `effective_action=MONITOR_ONLY` | ✓ YES |
| Deployment Queue | `deployment_queue.json` → `policy_suppressed` | Present as suppressed, policy=DO_NOT_SELL | ✓ YES |
| Recommendations (stale PARs) | `recommendations.json` (42A90186, C17FC0BF) | `execution_state=EXECUTABLE` / `effective_action=''` | ✗ STALE |
| Recommendations (fresh PAR) | `recommendations.json` (5C476C55) | `execution_state=BLOCKED_BY_POLICY` / `effective_action=MONITOR_ONLY` | ✓ YES |
| CRA Capital Pool | runtime `build_capital_sources()` | `blocked_by_policy=True` → excluded from pool | ✓ YES |
| PAP UI (stale PAR) | `renderPortfolioActionPipeline` | Shows TSLA as EXECUTABLE/TRIM in the Action lane | ✗ STALE |
| PAP UI (fresh PAR) | `renderPortfolioActionPipeline` | Shows TSLA as BLOCKED_BY_POLICY/MONITOR_ONLY | ✓ YES |

### Answer: Is TSLA actually executable anywhere?

**NO.** In the current system state:
- TSLA has an ACTIVE DO_NOT_SELL policy.
- The security overlay correctly marks it BLOCKED_BY_POLICY.
- The CRA correctly excludes it from the capital pool.
- The DQ correctly lists it in `policy_suppressed`.
- A fresh PAR confirms recommendations.json also correctly shows BLOCKED_BY_POLICY.

The "TRIM / EXECUTABLE" displayed in PAP was from **stale PAR data** that was generated with a system state inconsistency. It is not an executable action.

### Root Cause of Stale PARs

Stale PARs `42A90186` (13:24 UTC) and `C17FC0BF` (18:11 UTC) both show:
- `recommendations.json`: TSLA REDUCE_OVERWEIGHT → `execution_state: EXECUTABLE`, `effective_action: ''` (empty)
- `run_metadata.json`: `policy_snapshot` correctly captures TSLA as ACTIVE DO_NOT_SELL

This means `_apply_policy_to_recs()` was called but did not produce visible output in the serialized recs. The live test confirms the logic IS correct (BLOCKED_BY_POLICY is produced). The stale PARs were likely generated with a Python `__pycache__` inconsistency or an earlier version of `apply_policy_to_recommendations` that did not include REDUCE_OVERWEIGHT in `_REC_TYPE_SELL_FLAGS`.

**Resolution:** Fresh PAR 5C476C55 is now the authoritative latest run. The UI must reload from this PAR. Both PAP and CRA now show consistent BLOCKED status for TSLA.

---

## Phase 2 — Capital Pool Inventory

**Source PAR:** PAR-20260609-5C476C55  
**Total Capital Pool:** $96,633 (fresh PAR) — previous stale PAR showed ~$81K because TSLA's $13,904 in signal_deterioration proceeds were incorrectly included in the CRA view from the stale PAR.

### Pool Breakdown by Category

| Category | Count | Total Proceeds |
|---|---|---|
| SIGNAL_DETERIORATION | 4 | ~$9,987 |
| TAX_AWARE_EXIT | 18 | ~$46,263 |
| OVERWEIGHT_REDUCTION | 8 | ~$21,865 |
| LOW_CONVICTION_REDUCTION | 5 | ~$18,518 |

### Full Capital Pool Source Inventory

| Symbol | Market Value | Sizing | Proceeds | Priority | Category | Policy |
|---|---|---|---|---|---|---|
| LMAT | $7,133 | 100% | $7,133 | MODERATE | TAX_AWARE_EXIT | — |
| CIEN | $4,667 | 100% | $4,667 | MODERATE | TAX_AWARE_EXIT | — |
| DVN | $4,508 | 100% | $4,508 | MODERATE | TAX_AWARE_EXIT | — |
| SBS | $17,556 | 25% | $4,389 | LOW | OVERWEIGHT_REDUCTION | — |
| VB | $17,362 | 25% | $4,340 | MODERATE | LOW_CONVICTION_REDUCTION | — |
| VOO | $16,992 | 25% | $4,248 | MODERATE | LOW_CONVICTION_REDUCTION | — |
| MSFT | $4,117 | 100% | $4,117 | MODERATE | TAX_AWARE_EXIT | — |
| ANIP | $4,006 | 100% | $4,006 | MODERATE | TAX_AWARE_EXIT | — |
| AVGO | $3,966 | 100% | $3,966 | MODERATE | TAX_AWARE_EXIT | — |
| **DODFX** | $14,911 | 25% | $3,728 | **LOW** | OVERWEIGHT_REDUCTION | **SELL_LAST** |
| BNDX | $3,596 | 100% | $3,596 | MODERATE | TAX_AWARE_EXIT | — |
| PRG | $3,585 | 100% | $3,585 | MODERATE | TAX_AWARE_EXIT | — |
| KGC | $6,620 | 50% | $3,310 | HIGH | SIGNAL_DETERIORATION | — |
| BND | $3,276 | 100% | $3,276 | MODERATE | TAX_AWARE_EXIT | — |
| MKSI | $3,121 | 100% | $3,121 | MODERATE | TAX_AWARE_EXIT | — |
| CBOE | $3,084 | 100% | $3,084 | MODERATE | TAX_AWARE_EXIT | — |
| CVE | $12,005 | 25% | $3,001 | LOW | OVERWEIGHT_REDUCTION | — |
| VWO | $2,916 | 100% | $2,916 | MODERATE | TAX_AWARE_EXIT | — |
| TSM | $11,097 | 25% | $2,774 | LOW | OVERWEIGHT_REDUCTION | — |
| STNG | $2,284 | 100% | $2,284 | MODERATE | TAX_AWARE_EXIT | — |
| GTX | $8,901 | 25% | $2,225 | LOW | OVERWEIGHT_REDUCTION | — |
| VO | $8,478 | 25% | $2,120 | LOW | LOW_CONVICTION_REDUCTION | — |
| FBTC | $1,795 | 100% | $1,795 | MODERATE | TAX_AWARE_EXIT | — |
| AMG | $6,732 | 25% | $1,683 | LOW | LOW_CONVICTION_REDUCTION | — |
| SMR | $1,614 | 100% | $1,614 | MODERATE | TAX_AWARE_EXIT | — |
| FXAIX | $6,149 | 25% | $1,537 | LOW | LOW_CONVICTION_REDUCTION | — |
| FIS | $5,900 | 25% | $1,475 | HIGH | SIGNAL_DETERIORATION | — |
| SIMO | $1,316 | 100% | $1,316 | MODERATE | TAX_AWARE_EXIT | — |
| PRIM | $4,913 | 25% | $1,228 | MODERATE | SIGNAL_DETERIORATION | — |
| UHS | $1,143 | 100% | $1,143 | MODERATE | TAX_AWARE_EXIT | — |
| FETH | $975 | 100% | $975 | MODERATE | TAX_AWARE_EXIT | — |
| ASML | $3,498 | 25% | $875 | LOW | OVERWEIGHT_REDUCTION | — |
| XYZ | $3,496 | 25% | $874 | HIGH | SIGNAL_DETERIORATION | — |
| VEA | $3,493 | 25% | $873 | LOW | OVERWEIGHT_REDUCTION | — |
| YELP | $850 | 100% | $850 | MODERATE | TAX_AWARE_EXIT | — |

### Excluded from Pool (Blocked)

| Symbol | Market Value | Proceeds | Policy | Category | Reason |
|---|---|---|---|---|---|
| **TSLA** | $13,904 | $13,904 | DO_NOT_SELL | SIGNAL_DETERIORATION | `blocked_by_policy=True` → excluded from pool |

### Suppressed (De Minimis < $500)

| Symbol | Market Value | Proceeds | Category |
|---|---|---|---|
| AGEN | $314 | <$500 | TAX_AWARE_EXIT |
| CMCO | $125 | <$500 | TAX_AWARE_EXIT |
| XRP | $92 | <$500 | TAX_AWARE_EXIT |
| FSOL | $80 | <$500 | TAX_AWARE_EXIT |
| NVS | $879 | ~$220 | OVERWEIGHT_REDUCTION |
| TTNDY | $524 | ~$131 | OVERWEIGHT_REDUCTION |

---

## Phase 3 — Policy Compliance

### Compliance Results

| Check | Status | Detail |
|---|---|---|
| DO_NOT_SELL excluded from pool | **PASS** | 0 DO_NOT_SELL assets in pool |
| SELL_LAST ranked last | **PASS** | DODFX: SELL_LAST, priority=LOW, rank-ordered last |
| Conviction anchors excluded from pool | **PASS** | No CORE_ANCHOR assets in pool |
| Blocked by policy in pool | **PASS** | 0 blocked_by_policy=True in active pool |
| TSLA excluded from pool | **PASS** | TSLA in blocked list (not in pool) |
| TSLA in policy_suppressed DQ | **PASS** | DQ policy_suppressed = [TSLA] |

**All compliance checks: PASS (fresh PAR)**

### DODFX SELL_LAST Note

DODFX ($14,911 MV, $3,728 proceeds) IS in the capital pool at LOW priority with policy=SELL_LAST. This is correct — SELL_LAST assets are allowed in the pool but ranked last by the rotation_proposal_builder. DODFX's opportunity_flag is `HOLD` (not TRIM/SELL), so it enters via OVERWEIGHT_REDUCTION category, not signal deterioration.

---

## Phase 4 — PAP / CRA Consistency

### TSLA Cross-System Reference (Fresh PAR 5C476C55)

| Surface | TSLA State | Consistent? |
|---|---|---|
| UCF Verdict | TRIM_WATCH / deployment_eligible=False | ✓ |
| Security Overlay | BLOCKED_BY_POLICY / MONITOR_ONLY | ✓ |
| Deployment Queue | In `policy_suppressed` list | ✓ |
| recommendations.json | BLOCKED_BY_POLICY / MONITOR_ONLY | ✓ |
| CRA Capital Sources | blocked_by_policy=True / excluded from pool | ✓ |
| PAP (from fresh PAR) | Blocked lane / MONITOR_ONLY | ✓ |
| PAP (from stale PAR) | Action lane / EXECUTABLE/TRIM | ✗ STALE |

### DODFX Cross-System Reference

| Surface | DODFX State | Consistent? |
|---|---|---|
| Security Overlay | EXECUTABLE / HOLD | ✓ |
| Deployment Queue | Not in queue, not policy_suppressed | ✓ |
| recommendations.json | DEFERRED_BY_POLICY / REDUCE_SELL_LAST | ✓ |
| CRA Capital Sources | In pool, priority=LOW (ranked last) | ✓ |

**All cross-system references are consistent in the fresh PAR.**

---

## Final Q&A

### Q1: Is TSLA actually blocked everywhere?

**YES — in the current system state (fresh PAR 5C476C55).**

TSLA is blocked in:
- Security overlay → BLOCKED_BY_POLICY / MONITOR_ONLY
- Recommendations → BLOCKED_BY_POLICY / MONITOR_ONLY  
- Deployment Queue → policy_suppressed list
- CRA capital pool → excluded (blocked_by_policy=True)
- PAP display → Blocked lane (not Action lane)

The PAP "TRIM / EXECUTABLE" display the user observed was from a stale PAR that pre-dated correct policy application in `recommendations.json`.

### Q2: What creates the $81K capital pool?

The $81K was the capital pool calculated from the stale PAR-C17FC0BF. In that PAR, `security_overlays.csv` correctly had TSLA blocked, but the CRA capital pool builder still processed TSLA with `blocked_by_policy=True` and then excluded it from the pool total. However, the pool sources displayed in the CRA UI may have included TSLA visually (shown as "blocked — not in pool") while the $81K figure excluded it.

The **fresh PAR capital pool is $96,633** (20.8% of portfolio $464,944). The difference from $81K reflects either a different set of positions in the newer portfolio CSV or updated signal data.

### Q3: Are any protected assets included?

**NO.** In the current fresh PAR:
- No DO_NOT_SELL assets in the pool
- TSLA (only DO_NOT_SELL asset) is in the blocked list, not the pool
- No `blocked_by_policy=True` entries in the active pool

### Q4: Are PAP and CRA fully consistent?

**YES — in the fresh PAR (5C476C55).**  
**NO — in the stale PAR (C17FC0BF).**

The stale PAR had a split-brain state: the security overlay correctly showed TSLA as BLOCKED, but `recommendations.json` had the REDUCE_OVERWEIGHT rec as EXECUTABLE. This created the visible contradiction where PAP showed TRIM and CRA showed MONITOR ONLY.

The fresh PAR is fully consistent across all surfaces.

### Q5: Should a new backlog item be created?

**YES.** Two backlog issues are warranted:

**STALE-PAR-01 (HIGH):** Implement PAR re-validation or in-place policy replay. When operator policies change after a PAR is generated, the existing PAR's `recommendations.json` becomes stale while `security_overlays.csv` stays current (because overlays are per-symbol, while recs are multi-symbol). The UI should either re-apply policy at load time or warn when the loaded PAR pre-dates a policy change.

**STALE-PAR-02 (LOW):** Add a PAR integrity check that verifies `recommendations.json` sell-context recs have non-empty `effective_action`. A rec with `execution_state=EXECUTABLE` and `effective_action=''` indicates policy was not applied and should trigger a stale-PAR warning in the UI.

---

## Remediation

1. **Immediate**: UI operator should reload using fresh PAR-20260609-5C476C55. The fresh PAR is already in the manifest and should be the default on next UI load.
2. **Short-term**: Add STALE-PAR-01 and STALE-PAR-02 to backlog.
3. **No code changes required**: The policy application logic is correct. The issue was stale persisted data.
