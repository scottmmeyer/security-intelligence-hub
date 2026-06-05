# FMP Integration Philosophy and Governance Guardrails

**Effective Date:** 2026-06-04  
**Applies To:** All FMP integration phases (8.0B.1A through 8.0B.2 and beyond)  
**Classification:** Architectural governance — binding on all FMP work

---

## Why FMP Is Being Integrated

FMP is not being added to:
- Replace analyst consensus (ESS, Zacks, Danelfin remain authoritative)
- Create a new stock-picking engine
- Predict stock prices or future returns
- Override operator judgment

FMP is being added to provide three specific capabilities:

1. **Thesis Integrity Assessment** — Does the business still support the bullish thesis?
2. **Dislocation Detection** — Is a high-conviction stock temporarily on sale?
3. **Recommendation Context** — What fundamental evidence supports or warns against a signal?

---

## Capability 1: Thesis Integrity Assessment

The fundamental question FMP must help answer is whether the underlying business thesis appears:

| Classification | Description |
|---------------|-------------|
| **INTACT** | Revenue and EPS growth positive; earnings beat rate strong; estimates stable or rising |
| **QUESTIONABLE** | Mixed signals; some deterioration in growth or revisions; warrants monitoring |
| **DETERIORATING** | Multiple consecutive quarters of declining growth; estimate downgrades; persistent misses |

**Evidence used:**
- Revenue Growth (YoY, quarterly)
- Revenue Acceleration (improving or deteriorating trend)
- EPS Growth (YoY, quarterly)
- EPS Acceleration
- Earnings Surprise History (last 8 quarters)
- Estimate Revision Direction (net upgrades/downgrades)

**What this prevents:** Deploying capital into a security where the bullish analyst signal lags a fundamental deterioration. The AVGO scenario — a 15% post-earnings decline where the thesis is intact — must be distinguishable from a 15% decline driven by three consecutive quarters of decelerating growth.

---

## Capability 2: Dislocation Detection

The question FMP must help answer:

> "Is this stock temporarily on sale?"

**A potential dislocation exists when:**
- Business quality remains strong (gross margins intact, FCF positive)
- Growth remains healthy (revenue/EPS growing, not decelerating)
- Analyst conviction remains favorable (no significant downgrade wave)
- Valuation has become materially more attractive (P/E or EV/EBITDA compressed)

**This is not:**
- Predicting a bottom
- Calling a specific entry point
- Guaranteeing a recovery

**This is:**
- Identifying attractive risk/reward situations where a strong business is temporarily cheaper than normal, without a fundamental reason for the cheapness

**Example:** DELL drops 12% in a market correction. Revenue growing 28%, beats EPS for 7 of last 8 quarters, P/E compresses from 22x to 19x. FMP provides evidence that this is a DISLOCATION, not a DETERIORATION — supporting the existing BULLISH signal rather than triggering a false sell.

---

## Capability 3: Recommendation Context

FMP should initially explain existing recommendations. It does not change them.

**Format:**

```
Signal: BULLISH (ESS)

FMP Context:
  ✅ Revenue Growth: +28% YoY (accelerating)
  ✅ Beat Rate: 7/8 quarters (strong)
  ✅ Estimate Revisions: +3 net upgrades (last 90 days)
  → Thesis: INTACT
```

or

```
Signal: BULLISH (ESS)

FMP Context:
  ⚠ Revenue Growth: +8% YoY (decelerating from +22%)
  ⚠ Beat Rate: 3/8 quarters (weakening)
  ⚠ Estimate Revisions: −4 net downgrades (last 90 days)
  → Thesis: QUESTIONABLE
```

The operator sees the signal and the fundamental context side by side. The signal does not change. The context informs judgment.

---

## Non-Negotiable Guardrails

### Phases 8.0B.1A, 8.0B.1B, 8.0B.1B.5 (Intake + Visibility)

During these phases, FMP data is **observational only**. The following are strictly prohibited:

| System | Prohibited Action |
|--------|-----------------|
| CW-DAS scoring | No modification |
| ESS scoring | No modification |
| Replay scoring | No modification |
| Conviction tier (CCL/HCA) | No modification |
| Buy/sell rankings | No modification |
| Portfolio Alignment outputs | No modification |
| Deployment queue ordering | No modification |
| CRA capital sources | No modification |

**The principle:** Visibility first. Scoring later.

FMP data must be visible to the operator and verifiable for a full market cycle before it earns authority over any scoring decision. This is the same principle applied to every signal source introduced into SIH.

### Phase 8.0B.1C and Beyond (Scoring Integration)

When FMP earns scoring authority (after 8.0B.1B.5 operator sign-off), scoring changes must:

1. Be explicitly scoped to one component at a time
2. Be fully reversible (FMP null → existing behavior)
3. Pass the full regression suite
4. Be subject to a forensic validation phase before production
5. Never override ESS authority — FMP supplements; it does not replace

---

## Design Boundaries

### What FMP Signals Are For

| FMP Signal | Use Case | Scoring Role |
|-----------|---------|-------------|
| `beat_rate_8q` | Thesis integrity | Phase 8.0B.1B.5: display; Phase 8.0B.1C: CW-DAS momentum |
| `revenue_growth_q1_yoy` | Thesis integrity | Same |
| `revenue_acceleration` | Dislocation detection | Same |
| `pe_ratio_ttm` | Dislocation detection | Same |
| `fcf_yield_ttm` | Dislocation detection | Same |
| `net_buy_score` | Recommendation context | Same |
| `consensus_label` | Recommendation context | Same |

### What FMP Signals Are Not For

- Predicting short-term price movements
- Replacing analyst signals (ESS, Zacks, Danelfin remain primary)
- Autonomously generating new buy/sell signals without operator visibility
- Creating concentration in any single data source

---

## Implementation Sequence

```
8.0B.1A  Data intake            → COMPLETE
8.0B.1B  Analytical universe    → FMP fields added, nullable, no scoring
8.0B.1B.5 Diagnostic overlay   → Operator sees FMP alongside signals; trust checkpoint
8.0B.1C  CW-DAS integration    → Scoring changes after operator sign-off
8.0B.2   Dislocation framework → CRA integration after 8.0B.1C validation
```

No phase may begin scoring changes without completing the visibility phase immediately before it.

---

## Governance Accountability

This document must be referenced in the implementation plan of every FMP phase. Any proposed deviation from these guardrails requires an explicit governance review before implementation proceeds.

**The operator owns the decision.** FMP informs. It does not decide.
