# Phase 8.0B.0 — Dislocation Framework (Stocks on Sale)

**Date:** 2026-06-04  

---

## Framework Concept

A **High Conviction Dislocation** occurs when:
- A high-quality business with strong fundamentals
- Experiences a price decline (earnings miss, macro selloff, sector rotation)
- That compresses the valuation below historical or peer levels
- While the underlying business trajectory remains intact or improving

This is the classic "good stock temporarily on sale" scenario.

**SIH cannot identify this today.** It sees the price decline, the potentially deteriorating analyst signal, and either generates no signal or generates a false SIGNAL_DETERIORATION.

---

## The Framework SIH Could Build with FMP

### Dislocation Score (5 components)

| Component | FMP Source | What It Measures | Weight |
|-----------|-----------|-----------------|--------|
| **Valuation Compression** | key-metrics-ttm vs 12-month trailing average | P/E or EV/EBITDA vs own history | 30% |
| **Growth Trajectory** | income-statement-growth (3-quarter trend) | Revenue and EPS growth acceleration/deceleration | 25% |
| **Earnings Surprise History** | earnings (last 8 quarters) | Beat/miss pattern | 20% |
| **Estimate Revision Direction** | grades (upgrades/downgrades) | Net analyst sentiment post-decline | 15% |
| **Fundamental Quality** | ratios-ttm (gross margin, FCF margin) | Business quality preservation | 10% |

---

### Classification Rules

```
DISLOCATION_HIGH (buying opportunity):
  - Valuation Compression: Forward P/E declined > 20% in 30 days
  - Growth Trajectory: Revenue growth positive and stable/accelerating
  - Earnings History: Beat in ≥ 5 of last 8 quarters
  - Revisions: Net positive (more upgrades than downgrades) or stable
  - Quality: Gross margin within 200bps of 12-month average

DISLOCATION_NONE (no opportunity):
  - Valuation Compression: Modest or none
  - Growth Trajectory: Neutral or stable

DETERIORATION (thesis break — not a dislocation):
  - Growth Trajectory: Revenue growth decelerating for ≥ 3 consecutive quarters
  - Earnings History: Miss in ≥ 3 of last 8 quarters
  - Revisions: Net negative (more downgrades than upgrades)
  - Even if valuation looks cheap by price metrics
```

---

### Integration with Existing SIH Framework

The Dislocation Framework would interact with existing signals:

```
Signal Chain:
  ESS BULLISH + Replay Supported + Dislocation Score HIGH
  → "High Conviction Dislocation" narrative tier
  → CW-DAS rank elevated / deployment pool candidate
  → CRA DOES NOT generate a sell signal

  ESS shifts BEARISH + Revenue Growth Decelerating + Dislocation Score NONE
  → Thesis Break
  → CW-DAS rank depressed
  → CRA correctly generates SIGNAL_DETERIORATION source
```

**The key distinction FMP enables:**
- AVGO after a 15% selloff with accelerating revenue = Dislocation → BUY signal
- AVGO after a 15% selloff with decelerating revenue = Deterioration → SELL signal

Today SIH treats both identically (both may generate SIGNAL_DETERIORATION).

---

## Can SIH Support This Framework After FMP Integration?

**Yes — with the right 4 FMP integrations:**

1. **`/key-metrics-ttm?symbol=X`** — get current P/E, EV/EBITDA, FCF yield
2. **`/income-statement-growth?symbol=X&period=quarter`** — 4 quarters of revenue/EPS growth rates
3. **`/earnings?symbol=X`** — last 8 quarters of EPS surprise %
4. **`/grades?symbol=X`** — last 90 days of upgrades/downgrades

These four endpoints are sufficient to build the Dislocation Score. No complex modeling. No new algorithms. Pure data enrichment.

---

## Example: DELL After a Hypothetical 12% Pullback

DELL is currently CW-DAS rank #1 in SIH (DAS 99.3, CCL tier).

Hypothetical: DELL drops 12% on a Q3 earnings call where:
- Revenue grew 24% YoY (above consensus)  
- EPS beat by 7%
- Decline attributed to market-wide tech rotation

**Current SIH response:** Danelfin score would drop. If ESS holds BULLISH, SIH correctly keeps DELL as a deployment candidate. But if ESS lags or Danelfin drops enough to affect composite_score, CW-DAS rank could slip.

**With FMP:** Revenue growth confirmed 24% → Dislocation Score HIGH. ESS softening is identified as signal noise, not a thesis break. DELL stays rank #1 or moves higher on the "buy the dip" signal.

---

## Framework Verdict

**SIH can support a Stocks-on-Sale / High Conviction Dislocation framework after FMP integration.**

The framework requires 4 FMP endpoints, uses existing SIH scoring infrastructure, and would prevent the single biggest SIH failure mode: selling high-quality businesses during temporary valuation compression.

This is the highest-value use case for FMP integration.
