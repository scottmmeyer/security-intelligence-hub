# DIL Phase 1 — Posture Rules

**Date:** 2026-06-10

---

## Reduction Posture Decision Tree

Rules are evaluated in priority order. First match wins.

```
1. isETFNoSignal (no ESS, no composite, category=LOW_CONVICTION_REDUCTION)
   → PASSIVE REDUCTION

2. isConvictionProtected (UCF = CCL or HCA) AND isESSBearish
   → INVESTIGATE BEFORE ACTING
   (conviction anchors require higher evidence standard)

3. Full alignment bearish + FUNDAMENTAL_DETERIORATION (beat_rate < 50%, revenue < 0)
   → HIGH CONFIDENCE REDUCTION

4. SINGLE_QUARTER_MISS (beat_rate > 70%, eps_surprise < -20%) AND isESSBearish AND isStreetBullish
   → INVESTIGATE BEFORE ACTING
   (strong historical executor, one-quarter miss, analyst divergence)

5. MAJOR_DIVERGENCE alignment AND STRONG_FUNDAMENTAL
   → CONFLICTING EVIDENCE
   (model and street fundamentally disagree with strong FMP backing street)

6. isESSBearish AND (Zacks >= 3.5 OR composite < 2.5)
   → ACTIONABLE
   (ESS corroborated by at least one additional signal)

7. isESSBearish (no corroboration OR street diverges)
   → INVESTIGATE BEFORE ACTING

8. Default
   → MONITOR
```

---

## Deployment Posture Decision Tree

```
1. FULL_ALIGNMENT_BULLISH AND (STRONG_FUNDAMENTAL OR IN_LINE_FUNDAMENTAL)
   → HIGH CONFIDENCE BUY

2. isESSBullish AND alignment != MAJOR_DIVERGENCE
   → ACTIONABLE

3. MAJOR_DIVERGENCE
   → CONFLICTING EVIDENCE

4. Default (CW-DAS conviction without strong signal confirmation)
   → ACTIONABLE
```

---

## Earnings Context Classification (FMP)

| Classification | Criteria |
|---|---|
| `FUNDAMENTAL_DETERIORATION` | beat_rate < 50% AND revenue_growth < 0 |
| `SINGLE_QUARTER_MISS` | beat_rate > 70% AND eps_surprise < -20% |
| `STRONG_FUNDAMENTAL` | beat_rate > 75% AND revenue_growth > 10% |
| `IN_LINE_FUNDAMENTAL` | FMP available but no extreme pattern |
| `EARNINGS_CONTEXT_UNKNOWN` | FMP not available for this symbol |

---

## Signal Direction Flags

| Flag | Condition |
|---|---|
| `isESSBearish` | essText includes "BEARISH" OR fidRating in {SELL, STRONG_SELL} |
| `isESSBullish` | essText includes "BULLISH" OR fidRating in {BUY, STRONG_BUY} |
| `isStreetBullish` | ABR <= 2.5 AND consLabel includes "BUY" |
| `isStreetBearish` | ABR >= 3.5 OR consLabel includes "SELL" |
| `isETFNoSignal` | no ESS + no composite + category == LOW_CONVICTION_REDUCTION |
| `isConvictionProtected` | ucfLabel in {CORE_CONVICTION_LEADER, HIGH_CONVICTION_ANCHOR} |

---

## Posture CSS Classes

| Posture | CSS Class | Color |
|---|---|---|
| HIGH CONFIDENCE REDUCTION | `dil-high-confidence-red` | Red |
| HIGH CONFIDENCE BUY | `dil-high-confidence-buy` | Green |
| ACTIONABLE | `dil-actionable` | Orange |
| INVESTIGATE BEFORE ACTING | `dil-investigate` | Amber |
| CONFLICTING EVIDENCE | `dil-conflict` | Amber-dark |
| MONITOR | `dil-monitor` | Gray |
| WAIT ADDITIONAL DATA | `dil-wait` | Gray |
| PASSIVE REDUCTION | `dil-passive` | Blue-gray |
