# CW-DAS Allocation Drift Assessment — Phase 8.0B.X.4

## Executive Summary

CW-DAS does incorporate allocation drift — but only at a coarse binary level via the Redundancy Penalty. The current architecture has three meaningful gaps relevant to the ARW/AVT/ATLC/PCB vs. DELL/VRT/PSX/CAH/SNX comparison.

---

## Q1: Does CW-DAS currently consider allocation drift?

**YES — partially.**

CW-DAS incorporates allocation drift through one mechanism: the **Redundancy Penalty**.

| Mechanism | How Drift Is Used | Severity Required |
|-----------|-------------------|-------------------|
| Redundancy Penalty (−15) | Applied if holding's node is OVERWEIGHT at MODERATE+ severity | HIGH or MODERATE |

All other components (Signal, Replay, Conviction, Momentum) are completely drift-blind. The Sizing component is position-size-aware but not drift-aware.

---

## Q2: How much does drift affect scores?

**Binary: 0 or −15 points. No graduated response.**

The redundancy penalty is a flat 15-point deduction — it does not scale with drift magnitude.

| Scenario | Penalty |
|----------|---------|
| Node +1.0% OW (LOW severity) | 0 |
| Node +3.26% OW (LOW severity) | 0 |
| Node +5.26% OW (MODERATE severity) | −15 |
| Node +8.0% OW (HIGH severity) | −15 (same as MODERATE) |

**The gap between LOW and MODERATE OW is worth exactly 15 points in CW-DAS.** This is the largest single penalty in the scoring model.

---

## Q3: Are overweight categories outranking underweight categories?

**YES — in the current run, LOW-severity OW nodes (US.SMALL, US.MICRO) have candidates ranked #3–#6 and #9, while MODERATE UW nodes (US.MID, US.LARGE) also have candidates in the top 10.**

However, the overranking is NOT primarily caused by missing drift correction. It is caused by signal quality and tier differences:

### Active OW Nodes with Queue Candidates

| Node | OW Severity | Drift | Queue Candidates | Ranks |
|------|-------------|-------|-----------------|-------|
| EQUITIES.US.SMALL | LOW | +3.26% | ARW, AVT, UHS, HALO, AEIS | #3, #5, #18, #20, #24 |
| EQUITIES.US.MICRO | LOW | +2.00% | ATLC, PCB, ALNT, ANGO, AGEN | #6, #9, #14, #16, #21 |
| EQUITIES.INTERNATIONAL | MODERATE | +5.26% | GTX, CVE, ASML, TSM, SBS | #22, #23, #25, #29, #31 |
| EQUITIES.US.MEGA.ULTRA_MEGA | MODERATE | +4.43% | MU, MSFT, AVGO, NVDA | #26, #27, #28, #30 |

### Active UW Nodes with Queue Candidates

| Node | UW Severity | Drift | Queue Candidates | Ranks |
|------|-------------|-------|-----------------|-------|
| EQUITIES.US.MID | MODERATE | −5.43% | PSX, CAH, SNX, NUE, CRS, SANM, MTZ, FSLR, STLD | #4, #8, #10–#19 |
| EQUITIES.US.LARGE | MODERATE | −5.26% | DELL, VRT, LRCX | #1, #2, #7 |

**Key finding: The UNDERWEIGHT nodes (US.MID −5.43%, US.LARGE −5.26%) have the highest-ranked candidates (DELL #1, VRT #2, PSX #4, CAH #8). This is correct behavior — these candidates win on signal quality and conviction tier, not because the system ignores that their nodes are underweight.**

The US.SMALL and US.MICRO OW candidates (ARW #3, AVT #5, ATLC #6) score above CAH #8 and SNX #10 primarily because:
- ARW has a higher Signal component (29.33 vs 27.00 for CAH)
- AVT has higher Signal than SNX (27.33 vs 25.33)
- ATLC has marginally higher sizing headroom

**The drift gap (LOW OW vs MODERATE UW) contributes at most 0–1 points difference (no penalty vs. no bonus). The signal quality gap is 1–4 points, which dominates.**

---

## Q4: Would a drift-aware component materially alter the top 10?

**PARTIAL EFFECT — most of the top 10 would be unchanged; 2–3 positions could shift.**

### Counterfactual: If a graduated drift penalty were applied to LOW OW nodes

Assume: LOW OW nodes receive −5 penalty (vs current 0), MODERATE UW nodes receive +3 bonus (vs current 0).

| Symbol | Current Score | Drift Adjustment | Adjusted Score | Current Rank | Adj. Rank |
|--------|-------------|-----------------|---------------|-------------|-----------|
| DELL | 99.33 | US.LARGE UW → +3 | 102.33 | #1 | #1 |
| VRT | 94.72 | US.LARGE UW → +3 | 97.72 | #2 | #2 |
| ARW | 93.77 | US.SMALL OW → −5 | 88.77 | #3 | #5 |
| PSX | 93.38 | US.MID UW → +3 | 96.38 | #4 | #3 |
| AVT | 91.91 | US.SMALL OW → −5 | 86.91 | #5 | #7 |
| ATLC | 91.74 | US.MICRO OW → −5 | 86.74 | #6 | #8 |
| LRCX | 91.50 | US.LARGE UW → +3 | 94.50 | #7 | #4 |
| CAH | 91.42 | US.MID UW → +3 | 94.42 | #8 | #5 (tie w/LRCX) |
| PCB | 90.64 | US.MICRO OW → −5 | 85.64 | #9 | #10 |
| SNX | 89.94 | US.MID UW → +3 | 92.94 | #10 | #6 |

**Conclusion: Applying drift-aware adjustments would push ARW from #3→#5, AVT from #5→#7, ATLC from #6→#8, and promote LRCX (#7→#4), CAH (#8→#5), SNX (#10→#6). Top 2 positions unchanged.**

---

## Q5: Is current behavior consistent with Concentrated Alpha mandate intent?

**LARGELY YES — with one structural gap worth noting.**

### What current behavior does correctly

1. **MODERATE+ OW nodes are penalized.** International (+5.26%) and US.MEGA.ULTRA_MEGA (+4.43%) candidates are ranked #22–#31, well below US.SMALL/MICRO candidates. The penalty works as designed.

2. **Signal quality remains the primary driver.** DELL #1 has the highest signal × conviction combination. The ranking reflects fundamental conviction, not allocation drift artifacts.

3. **Concentrated Alpha mandate prioritizes HIGH-conviction signals.** The mandate intent is to deploy into high-conviction positions, not to mechanically balance allocation nodes. The current system correctly weights signal quality above drift correction.

### Gap: LOW OW threshold creates a cliff

The binary transition from LOW (no penalty) to MODERATE (−15 penalty) creates a hard cliff. A node at +3.26% OW (LOW) is treated identically to 0% drift. A node at +5.26% OW (MODERATE) loses 15 points. The region between LOW and MODERATE has no graduated response.

**In this specific run**, US.SMALL (+3.26%) and US.MICRO (+2.00%) are effectively invisible to the penalty mechanism — they are already modestly OW but receive no discouragement.

### Assessment

The gap is real but not urgent under Concentrated Alpha mandate because:
- The OW nodes in question (US.SMALL, US.MICRO) are only modestly OW (+2–3.3%)
- The candidates in those nodes (ARW, AVT, ATLC, PCB) are genuinely high-quality signals
- Adding them to portfolio would not dramatically worsen the allocation gap
- The mandate's primary goal is conviction-quality capital deployment, not drift correction

**A graduated drift penalty would be a refinement, not a correction.** Current behavior is not broken.
