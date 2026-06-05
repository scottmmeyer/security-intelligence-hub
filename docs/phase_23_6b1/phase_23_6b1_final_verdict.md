# Phase 23.6B.1 — Final Verdict

**Date:** 2026-06-04  
**PAR Run:** PAR-20260604-A47BD0AF  
**Type:** Forensic analysis only — no code modifications

---

## Q8: Findings Summary

### Snapshot State

**Classification: CURRENT**

| Finding | Detail |
|---------|--------|
| Source file | `Portfolio_Positions_Jun-04-2026 (4).csv` — 4th export of day, post-transaction |
| FIGFX | ABSENT — sale fully reflected |
| VXUS | ABSENT — sale fully reflected |
| FIS | PRESENT at $6,146 (149 shares) — partial sale reflected |
| CRA run mismatch | CRA uses B01C0C82 (same source file, same MV as A47BD0AF — functionally identical) |

Today's transactions are reflected in the portfolio snapshot. The data is not stale. The "(4)" filename and FIGFX/VXUS absence confirm this.

---

### Defect 1 — Capital Pool Inclusion (SPAXX + PENDING ACTIVITY)

**Classification: DEFECT — REQUIRES CORRECTION**

| Incorrectly Included Source | Proceeds Added | Root Cause |
|----------------------------|---------------|-----------|
| SPAXX | $11,012 | `is_cash_equivalent=True` check missing in capital_source_builder |
| PENDING ACTIVITY | $2,551 | `operational_state` check missing; positive-MV PENDING rows treated as positions |

- **Pool overstatement: $13,563 (13.8% of total pool)**
- **Corrected pool: ~$85,081**
- SPAXX should never appear as a sell candidate under any category
- PENDING ACTIVITY is a settlement row — it is not a tradeable position

---

### Defect 2 — Proportional Cap Too Aggressive

**Classification: DEFECT — REQUIRES CORRECTION**

| Metric | Current (50% cap) | Impact |
|--------|------------------|--------|
| Positions funded | 2 | Extreme concentration |
| DELL post-weight | ~11.8% | Exceeds 6% WARN threshold by 2× |
| VRT post-weight | ~14.4% | Exceeds 6% WARN threshold by 2.4× |
| ARW, PSX, AVT, ATLC, LRCX, CAH, SNX, PCB | $0 allocated | Queue candidates ignored |

The 50% per-candidate proportional cap is the direct root cause of the 2-target outcome. For any capital pool, the algorithm guarantees:
- Candidate #1 receives exactly 50% of the pool
- Candidate #2 receives the remaining 50%
- All subsequent candidates receive $0

This produces unrealistic concentration that would immediately trigger WARN/overweight flags in the next PAR run.

---

### Defect 3 — Deployment Methodology Inconsistency

**Classification: INCONSISTENT with existing deployment approach**

| Aspect | CRA | Deployment Plan (Phase 7.5D) |
|--------|-----|------------------------------|
| Method | Sequential + 50% cap | Tiered proportional (T1/T2/T3) |
| Positions | 2 | 31 |
| Max single alloc | 50% of pool | ~16% of pool |
| Respects WARN | No | Yes |
| Consistent with mandate | No | Mostly |

The CRA does not reuse tier allocation logic. It uses a simple sequential algorithm with a proportional cap that is tuned incorrectly for large pools.

---

### Cash Reconciliation

**Classification: CORRECT**

The $10,513.36 deployable cash figure is arithmetically correct given current SPAXX balance ($44,049) and 7% mandate floor. No stale data involved.

The $10,204.59 PENDING ACTIVITY with positive MV represents unsettled sale proceeds that will flow into SPAXX at T+1 settlement. The system correctly reports current SPAXX balance — it does not project future inflows.

---

## Overall Classifications

| Dimension | Classification |
|-----------|--------------|
| **Snapshot State** | **CURRENT** |
| **Transaction Reflection** | **CURRENT** (FIGFX/VXUS absent, FIS partial) |
| **Cash Reconciliation** | **CORRECT** |
| **CRA Capital Pool** | **REQUIRES CORRECTION** (SPAXX + PENDING ACTIVITY included) |
| **CRA Allocation Logic** | **DEFECT** (50% cap → 2 targets, extreme concentration) |
| **Deployment Methodology** | **INCONSISTENT** (vs existing tiered DP approach) |
| **Operator Realism** | **DOES NOT REFLECT REALISTIC WORKFLOW** |
| **Overall CRA State** | **VALID WITH DEFECTS — 3 corrections required before production use** |

---

## Defect Priority List

| Priority | Defect | Correction Needed |
|----------|--------|-------------------|
| P1 (CRITICAL) | SPAXX and PENDING ACTIVITY in capital pool | Add `is_cash_equivalent` and `operational_state` exclusion checks to `capital_source_builder.py` |
| P1 (CRITICAL) | 50% proportional cap too aggressive | Lower cap to ~15–20% OR adopt tiered allocation matching Deployment Plan philosophy |
| P2 (MODERATE) | CRA allocation inconsistent with DP tiered approach | Align CRA deployment logic with Phase 7.5D tier structure for philosophical consistency |

---

## Recommended Next Phase: 23.6B.2 — CRA Allocation Defect Remediation

Before FMP intelligence expansion, the following corrections should be implemented:

1. **Exclude cash equivalents from capital pool** — check `is_cash_equivalent` and `operational_state` in `capital_source_builder.py`
2. **Fix proportional cap** — lower from 50% to 15–20%, or adopt tier-proportional allocation  
3. **Validate corrected output** — re-run forensic check after fix to confirm 5–10 deployment targets appear

No other CRA logic requires modification.
