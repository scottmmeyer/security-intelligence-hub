# Decision Intelligence Layer — Problem Definition

**Date:** 2026-06-10  
**Status:** Design Specification

---

## The Gap

The SIH currently answers two questions well:

1. **"What should I buy?"** — Deployment Queue, ranked by CW-DAS
2. **"What should I reduce?"** — Reduction Queue, ranked by CRA priority

What it does not yet answer:

3. **"Why is this action being recommended right now?"**
4. **"Has something changed that I should know about?"**
5. **"Is the market agreeing or disagreeing with this signal?"**
6. **"Should I act on this immediately or investigate first?"**

The operator must currently bridge this gap manually — opening Fidelity, checking news, reviewing earnings calendars, and cross-referencing analyst updates. This is a high-friction, error-prone process that depends on the operator's memory of recent events.

---

## The PRIM Problem

**Scenario:** PRIM (Primoris Services Corp) falls 15% in a single day. The SIH shows:

```
ESS: BEARISH
Danelfin: 5.0 (BULLISH)
Zacks: 1.0 (STRONG_BUY)
ABR: 1.86 (BUY, 14 analysts)
Price Target: $143.79
```

The operator sees a BEARISH ESS score and a BUY analyst consensus — a PARTIAL_ALIGNMENT divergence. The signal picture doesn't explain:

- **Why did the price drop?** (Earnings miss? Guidance cut? Sector rotation?)
- **Are analyst targets stale?** (Pre-earnings vs. post-earnings)
- **Is this a buying opportunity or confirmation of the bearish signal?**
- **Should the reduction proceed or wait for more information?**

Without this context, the operator faces two equally poor choices:
- Reduce immediately (may be selling at the worst point of a temporary event)
- Ignore the signal (may miss a genuine deterioration)

The Decision Intelligence Layer resolves this by providing structured context around why the current signal picture looks the way it does.

---

## What DIL Is

DIL is an **interpretive explainability layer**. It reads existing signals and data already available in SIH, synthesizes them into operator-grade commentary, and presents a recommended operator posture.

DIL is:
- Display-only
- Evidence-based (every conclusion cites a source)
- Non-scoring (never feeds back into CW-DAS, RPS, or any ranking)
- Non-autonomous (never executes or recommends execution)
- Auditable (every output is deterministic from available inputs)

DIL is NOT:
- A prediction model
- An AI agent
- A trade recommendation engine
- A replacement for analyst research

---

## The Value Proposition

**Before DIL:** Operator looks at PRIM in the Reduction Queue and sees BEARISH ESS, 15% drop, BUY analyst consensus. They must manually investigate to determine what happened.

**After DIL:** Operator looks at PRIM and sees:

```
INVESTIGATE BEFORE ACTING

Recent Context:
• Q2 earnings released; revenue beat (+18.9% YoY) but EPS miss (-30.6% surprise)
• Guidance lowered for next quarter
• Analyst targets are pre-earnings revisions; likely stale
• Market reaction: -15.2% (guidance-driven selloff pattern)

Signal Divergence:
• ESS BEARISH (StarMine momentum-based; reacting to price drop)
• Yahoo/Street consensus BUY (analysts may not have revised yet)
• Zacks STRONG BUY (likely pre-earnings; 8-quarter beat rate: 85.7%)

Operator Posture:
This appears to be a guidance-driven selloff. Analyst revisions are likely pending.
Wait 3-5 days for analyst target updates before acting on the reduction signal.
```

This is a materially better operator experience.

---

## Scope Boundaries

**In scope:**
- Synthesizing existing SIH signals into operator-grade commentary
- Classifying signal divergence and explaining each case
- Surfacing FMP fundamental data (EPS surprise, beat rate, revenue growth) as context
- Providing a recommended operator posture taxonomy

**Out of scope (Phase 1):**
- Real-time price data (not yet in SIH)
- News headline ingestion (requires external API)
- Earnings calendar integration (requires external API)
- Analyst revision history (not yet captured)

**Future scope (Phase 2+):**
- Yahoo Finance price history API integration
- Earnings calendar (Yahoo Finance, FMP)
- Analyst revision tracking over time
- News sentiment integration
