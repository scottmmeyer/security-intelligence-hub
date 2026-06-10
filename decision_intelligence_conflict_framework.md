# Decision Intelligence Layer — Signal Conflict Framework

**Date:** 2026-06-10

---

## Conflict Classification System

The SIH already computes `consensus_matrix.classification` with three values. DIL extends this into a full 4×4 conflict framework covering signal direction, earnings context, and price action.

---

## Core Conflict Matrix

### Signal Agreement Dimension

| ESS Direction | Yahoo/Street | Zacks | Classification | Operator Implication |
|---|---|---|---|---|
| BEARISH | BEARISH | BEARISH | `FULL_ALIGNMENT_BEARISH` | High confidence reduction signal |
| BULLISH | BULLISH | BULLISH | `FULL_ALIGNMENT_BULLISH` | High confidence retain/buy signal |
| BEARISH | BULLISH | BEARISH | `PARTIAL_ALIGNMENT_ESS_LED` | ESS + Zacks agree; Yahoo outlier |
| BEARISH | BULLISH | BULLISH | `MAJOR_DIVERGENCE` | ESS vs. Street fully disagree |
| BEARISH | BULLISH | NEUTRAL | `PARTIAL_ALIGNMENT` | Mixed — investigate required |
| BULLISH | BEARISH | NEUTRAL | `MAJOR_DIVERGENCE` | Model bullish, Street bearish |
| NEUTRAL | NEUTRAL | NEUTRAL | `NO_SIGNAL` | Insufficient data |

---

## Earnings Context Dimension

The FMP data provides a critical additional dimension:

| Last EPS Surprise | Beat Rate 8Q | Revenue Growth | Context Classification |
|---|---|---|---|
| Miss > 20% | < 50% | Negative | `FUNDAMENTAL_DETERIORATION` — signal likely justified |
| Miss > 20% | > 75% | Positive | `SINGLE_QUARTER_MISS` — track record strong; investigate before acting |
| Beat > 10% | > 75% | Positive | `STRONG_FUNDAMENTAL` — bear signal may be momentum-only |
| Miss < 10% | > 60% | Moderate | `IN_LINE_FUNDAMENTAL` — neutral earnings context |
| No data | — | — | `EARNINGS_CONTEXT_UNKNOWN` — FMP not covered |

**Example: PRIM**
- Last EPS surprise: -30.6% (Q1 miss)
- Beat rate 8Q: 85.7%
- Revenue growth Q1 YoY: +18.9%
- → `SINGLE_QUARTER_MISS`: Strong historical executor had one miss; reduction signal requires investigation

---

## Composite Conflict Scenarios

### Scenario 1: Full Agreement (Reduction Case)
```
ESS: BEARISH (2.0)
Zacks: SELL (4.0–5.0)  
Yahoo: BEARISH
EPS Surprise: -40% miss
Beat Rate 8Q: 37.5%
Revenue Growth: Negative

Classification: FULL_ALIGNMENT_BEARISH + FUNDAMENTAL_DETERIORATION
Posture: HIGH_CONFIDENCE_REDUCTION
Commentary: "All signals agree — ESS, Zacks, and Yahoo are bearish. 
EPS misses are consistent (37.5% beat rate), and revenue is declining.
Reduction signal is well-supported across all sources."
```

### Scenario 2: PRIM Case (Partial Alignment, One-Quarter Miss)
```
ESS: BEARISH (2.0)
Zacks: STRONG BUY (1.0)
Yahoo: BUY (1.86 ABR)
EPS Surprise: -30.6% (one quarter)
Beat Rate 8Q: 85.7%
Revenue Growth: +18.9%

Classification: PARTIAL_ALIGNMENT + SINGLE_QUARTER_MISS
Posture: INVESTIGATE_BEFORE_ACTING
Commentary: "ESS is bearish (likely momentum from recent price drop) but both
Zacks and Yahoo disagree. PRIM has an 85.7% beat rate over 8 quarters, and 
Q1 revenue grew 18.9% YoY. The recent EPS miss (-30.6%) appears to be an 
exception to a strong track record. Analyst targets may be pre-revision and 
could be stale. Recommended: wait for analyst target updates (3–5 days) 
before executing the reduction."
```

### Scenario 3: Value Trap Risk
```
ESS: BEARISH
Zacks: BUY
Yahoo: BUY (high upside)
EPS Surprise: -55% miss
Beat Rate 8Q: 25%
Revenue Growth: -12%

Classification: MAJOR_DIVERGENCE + FUNDAMENTAL_DETERIORATION
Posture: CONFLICTING_EVIDENCE (leaning REDUCE)
Commentary: "Street consensus is bullish with large upside vs. target, but 
fundamental trajectory is deteriorating. This divergence pattern often reflects 
stale analyst targets. ESS and FMP fundamentals are internally consistent; 
Street may not have updated post-earnings. Consider prioritizing the ESS signal 
over the ABR in this case — value trap risk is elevated."
```

### Scenario 4: Retain Signal Despite Bearish ESS
```
ESS: BEARISH
Zacks: STRONG BUY
Yahoo: BUY (very high upside)
EPS Surprise: +42% beat
Beat Rate 8Q: 87.5%
Revenue Growth: +28%
UCF: HIGH_CONVICTION_ANCHOR

Classification: MAJOR_DIVERGENCE + STRONG_FUNDAMENTAL
Posture: MONITOR (hold reduction)
Commentary: "ESS bearish signal is not corroborated by any other source.
FMP fundamentals are very strong (87.5% beat rate, 28% revenue growth, 
+42% EPS beat). UCF ranks this as a HIGH_CONVICTION_ANCHOR. The bearish 
ESS may reflect short-term price momentum rather than fundamental weakness.
Reduction not recommended under current evidence. Monitor for confirmation."
```

### Scenario 5: No Signal (Passive Vehicle)
```
ESS: — (ETF, no ESS coverage)
Zacks: — 
Yahoo: — 
FVI: ELITE
Category: OPPORTUNITY_COST_REDUCTION

Classification: NO_SIGNAL
Posture: ACTIONABLE (passive reduction)
Commentary: "This is a passive vehicle (ELITE FVI) held for allocation 
completion. Reduction recommendation is based on mandate allocation context 
rather than signal deterioration. No active signal evidence for or against — 
this is a portfolio construction decision, not a signal-driven one."
```

---

## Operator Posture Taxonomy

| Posture | Color | Criteria | Recommended Action |
|---|---|---|---|
| `HIGH_CONFIDENCE_REDUCTION` | Red | Full agreement bearish + fundamental deterioration | Proceed with confidence |
| `ACTIONABLE` | Orange | Bearish ESS + partial agreement + no strong counterevidence | Proceed with standard diligence |
| `INVESTIGATE_BEFORE_ACTING` | Yellow | Partial alignment + strong fundamental record OR single-quarter miss | Wait 3–5 days; check analyst revisions |
| `CONFLICTING_EVIDENCE` | Amber | Major divergence with mixed fundamentals | Operator judgment required; do not act mechanically |
| `MONITOR` | Gray | Bearish ESS not corroborated by any source + strong fundamentals | Hold; revisit next signal refresh |
| `WAIT_ADDITIONAL_DATA` | Gray | Signal refresh > 14 days stale OR data gaps | Refresh signals before acting |
| `PASSIVE_REDUCTION` | Neutral | ETF/passive vehicle — no ESS | Allocation decision only; check FVI tier |

---

## Conflict Resolution Rules

**Rule 1 — ESS vs. Street Divergence:** When ESS is BEARISH and ABR is BUY with > 10 analysts, default to INVESTIGATE posture unless fundamentals corroborate.

**Rule 2 — Stale Analyst Targets:** If Yahoo `refresh_date` is older than 7 days AND `latest_eps_surprise_pct` is < -15%, flag analyst targets as potentially stale.

**Rule 3 — Single Quarter Exception:** If `beat_rate_8q` > 70% AND `latest_eps_surprise_pct` < -20%, classify as single-quarter miss, not trend.

**Rule 4 — Revenue Confirms or Negates:** Strong `revenue_growth_q1_yoy` (> 10%) with a bearish ESS → lean toward INVESTIGATE. Negative revenue + bearish ESS → lean toward ACTIONABLE.

**Rule 5 — UCF Override:** If UCF is `HIGH_CONVICTION_ANCHOR` or `CORE_CONVICTION_LEADER`, set posture floor at INVESTIGATE (never go to ACTIONABLE or REDUCE for conviction anchors without confirming signal).
