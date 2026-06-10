# Reduction Action Analysis — FIS, PRIM, XYZ, KGC

**Date:** 2026-06-09  
**PAR:** PAR-20260609-87134CE1

---

## Overview

These four symbols appear in the security overlays with BEARISH/WATCH signals. This analysis determines whether any would become higher-priority actions than current deployment candidates if the system had a unified action queue.

---

## Signal Summary

| Symbol | Opportunity Flag | ESS Score | Composite | Portfolio % | DQ Rank | Exec State | RPS |
|---|---|---|---|---|---|---|---|
| FIS | WATCH | BEARISH | 2.22 | 1.27% | Not in DQ | EXECUTABLE | 0 |
| PRIM | WATCH | BEARISH | 2.06 | 1.06% | Not in DQ | EXECUTABLE | 0 |
| XYZ | WATCH | BEARISH | 2.22 | 0.75% | Not in DQ | EXECUTABLE | 0 |
| KGC | HOLD | BEARISH | 2.61 | 1.42% | Not in DQ | EXECUTABLE | 42 |

---

## Individual Analysis

### FIS (Fidelity NatSec Inc. / FIS Processing)

- **Signal:** BEARISH ESS, WATCH flag, composite 2.22
- **Position:** 1.27% of portfolio
- **RPS:** 0 — not part of any REDUCE_OVERWEIGHT rec (not in an overweight node)
- **DQ:** Not eligible (BEARISH signal)
- **In CRA pool?** Yes — via TAX_AWARE_EXIT (unrealized loss position) at $1,475 estimated proceeds
- **Reduction rank:** #15 (not material in RPS ranking; low proceeds)
- **Would FIS outrank any current buy candidate?** No. CRA TAX_AWARE_EXIT at $1,475 proceeds is a low-priority capital source. FIS does not have an RPS score and cannot be compared directly to CW-DAS buy scores.
- **Assessment:** FIS is a signal-watch position, not an immediate reduction candidate.

### PRIM (Primoris Services)

- **Signal:** BEARISH ESS, WATCH flag, composite 2.06 (lowest of the group)
- **Position:** 1.06% of portfolio
- **RPS:** 0 — not in an overweight node
- **DQ:** Not eligible (BEARISH)
- **In CRA pool?** Yes — via SIGNAL_DETERIORATION at $1,228 estimated proceeds (25% sizing, MODERATE priority)
- **Reduction rank:** #15
- **Would PRIM outrank current buy candidates?** No. MODERATE priority with $1,228 proceeds is well below the top of the buy queue.
- **Assessment:** Weakest signal of the group. Lowest composite. Legitimate reduction candidate but low urgency.

### XYZ (Xylem Inc.)

- **Signal:** BEARISH ESS, WATCH flag, composite 2.22
- **Position:** 0.75% of portfolio
- **RPS:** 0 — not in overweight node
- **DQ:** Not eligible (BEARISH)
- **In CRA pool?** Yes — via SIGNAL_DETERIORATION at $874 estimated proceeds (25% sizing, HIGH priority)
- **Reduction rank:** #15
- **Would XYZ outrank current buy candidates?** No. Despite HIGH priority flag, $874 proceeds is de minimis relative to the buy queue.
- **Assessment:** High-priority signal deterioration but small position. Monitor, not urgent.

### KGC (Kinross Gold)

- **Signal:** BEARISH ESS, HOLD flag, composite 2.61 (highest of the group)
- **Position:** 1.42% of portfolio (largest of the group)
- **RPS:** **42** — appears in the REDUCE_OVERWEIGHT rec for EQUITIES.INTERNATIONAL (DEFERRED_BY_POLICY)
- **DQ:** Not eligible (BEARISH)
- **In CRA pool?** Yes — via SIGNAL_DETERIORATION at $3,310 estimated proceeds (50% sizing, HIGH priority)
- **Reduction rank:** **#5** (behind TSLA 85, DODFX 58, VEA 56, TTNDY 55)
- **Would KGC outrank current buy candidates?** No under naive comparison (RPS 42 vs CW-DAS 88–98). But KGC is the most actionable of the four targets.
- **Assessment:** **KGC is the most actionable reduction candidate among the four targets.** RPS=42 with $3.3K proceeds and HIGH priority in CRA. The DEFERRED state means it's executable in principle but deprioritized behind non-SELL_LAST assets.

---

## Comparison to Current Buy Queue

| Symbol | Best Score | Score Source | vs. #10 Buy Candidate (CRS 91.36) | vs. #20 Buy Candidate (GTX 86.11) |
|---|---|---|---|---|
| FIS | ~10 (CRA MODERATE) | CRA priority | Far below | Far below |
| PRIM | ~10 (CRA MODERATE) | CRA priority | Far below | Far below |
| XYZ | ~25 (CRA HIGH) | CRA priority | Far below | Far below |
| KGC | 42 (RPS) | RPS | Below | Below |

**None of these symbols would outrank any current Top 20 buy candidate** under a naive unified ranking using RPS vs CW-DAS.

---

## Key Finding on KGC

KGC is a notable edge case: HOLD flag (not TRIM), BEARISH ESS, composite 2.61, but caught in SELL_LAST DEFERRED state because the REDUCE_OVERWEIGHT rec for EQUITIES.INTERNATIONAL includes DODFX which carries SELL_LAST. KGC's DEFERRED state is a **policy propagation artifact** — KGC itself has no SELL_LAST policy; it inherits the deferral because it's in the same multi-symbol rec as DODFX.

This is a design issue: the most-restrictive-wins precedence in `apply_policy_to_recommendations()` means KGC's reduction is deferred even though KGC has no individual policy constraint.
