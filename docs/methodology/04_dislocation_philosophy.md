# 04 — Dislocation Philosophy

## The Central Question

When a stock declines in price while its signals weaken — is this the market correctly reassessing the thesis, or is it an overreaction creating an opportunity?

This is the most difficult question in investing. SIH does not answer it definitively. It provides a framework for thinking about it clearly.

---

## The AVGO Catalyst

In the current portfolio analysis (June 2026), AVGO presents the purest example of the dislocation question:

**Analyst signal picture:**
- ESS: BULLISH
- Danelfin: 4.0 / 5.0 (strong, but not top)
- Zacks: 3.0 (neutral — not a strong buy signal)

**Fundamental picture:**
- Revenue growth: +23.9% YoY
- Beat rate: 100% (8/8 quarters)
- ROIC: 19.5%
- FCF Yield: 1.7%
- Analyst consensus: BUY (net buy score: +51)

**SIH classification:**
- Thesis Integrity: **INTACT**
- Fundamental Consistency: **CONSISTENT**
- Dislocation: **POTENTIAL**

**The gap:** AVGO has near-perfect fundamentals — 100% beat rate, 24% revenue growth, strong returns. Yet the AI scoring model (Danelfin 4.0) and Zacks (3.0) are not at their maximum readings. The system correctly identifies: business is excellent, but composite signals are not maxed out. This gap between business quality and signal intensity is the definition of a potential dislocation.

**What this means practically:** Either (a) analysts haven't fully priced in the fundamental strength — buy opportunity, or (b) analysts see something the FMP data doesn't (sector rotation headwinds, forward guidance concerns, margin pressure) — the lower signal is correct. SIH presents both possibilities to the operator rather than choosing one.

---

## "Stock on Sale" vs. "Thesis Breaking"

### Stock on Sale (Dislocation)

**Pattern:**

```
Thesis Integrity: INTACT
Fundamental Consistency: CONSISTENT or MIXED
Signal direction: NEUTRAL or weakening from BULLISH
Dislocation: POTENTIAL or HIGH CONVICTION
```

**Characteristics:**
- Revenue growing or flat (not declining)
- Beat rate ≥ 75%
- ROIC positive and stable
- Signal weakness is recent, not persistent
- No catalyst for fundamental deterioration

**The interpretation:** The market or analyst sentiment has moved ahead of (or behind) the actual business. The business is executing. The signals may be lagging, or temporary sentiment is suppressing the score. This is a potential opportunity.

**What SIH does:** Flags as POTENTIAL DISLOCATION. Presents evidence. Does not recommend a buy. Puts the operator on alert.

---

### Thesis Breaking (Value Trap)

**Pattern:**

```
Thesis Integrity: DETERIORATING
Fundamental Consistency: CONTRADICTORY or MIXED
Signal direction: Still BULLISH (lagging)
Dislocation: NONE
```

**Characteristics:**
- Revenue declining for 2+ consecutive quarters
- Beat rate falling below 65%
- Analyst ratings still elevated (haven't caught up)
- Revenue acceleration negative and deepening
- No obvious catalyst for recovery

**The interpretation:** The business is deteriorating faster than analyst ratings are adjusting. The BULLISH ESS is not identifying an opportunity — it's identifying an analyst who hasn't downgraded yet. This is a value trap.

**What SIH does:** Classifies as DETERIORATING + CONTRADICTORY. This is the strongest warning signal in the framework. The system will not deploy capital into a CONTRADICTORY signal, and the "Why SIH Likes It" section will show no bullets for the fundamentals.

---

## The Four Cases

| Thesis Integrity | Signal Direction | Classification | Operator Action |
|-----------------|-----------------|----------------|-----------------|
| INTACT | BULLISH | CONSISTENT | Normal deployment — high confidence |
| INTACT | NEUTRAL/WEAK | CONTRADICTORY | **POTENTIAL DISLOCATION** — opportunity signal |
| DETERIORATING | BEARISH | CONSISTENT | Do not deploy; consider reduction |
| DETERIORATING | BULLISH | CONTRADICTORY | **VALUE TRAP WARNING** — analyst lagging |

---

## The Dislocation Threshold Design

Dislocation detection requires **multiple layers of supporting evidence** to flag POTENTIAL. A single data point (e.g., Danelfin score below 3.0) is not sufficient.

**HIGH CONVICTION dislocation requires:**
- Thesis Integrity = INTACT
- Beat rate ≥ 87.5% (7/8 or 8/8 quarters)
- Signal: BEARISH or NEUTRAL
- Danelfin < 1.5 (AI model strongly disagrees with fundamentals)

**POTENTIAL dislocation requires:**
- Thesis Integrity = INTACT
- Beat rate ≥ 75%
- Danelfin < 3.0 (AI model moderately below fundamental strength)

**NONE:**
- Everything else — including when signals and fundamentals agree in either direction

---

## What Dislocation Detection Is NOT

- Not a buy recommendation
- Not a price target
- Not a prediction that the stock will recover
- Not an override of the signal system
- Not a substitute for analyst research

It is a diagnostic flag that says: "The fundamental evidence and the signal evidence are pointing in different directions. An operator should be aware of this gap before making a decision."

---

## Philosophical Grounding

The dislocation philosophy is grounded in a fundamental market observation: **prices overshoot in both directions**. Stocks decline below their fundamental value when sentiment deteriorates faster than business quality. They rise above fundamental value when narrative exceeds reality.

SIH cannot predict which is happening in any specific case. But it can provide the operator with a structured view of which evidence supports a recovery thesis and which evidence supports a deterioration thesis — and let the operator decide which interpretation is more credible given context the system cannot access (management quality, competitive dynamics, macro environment, the operator's own conviction).

This is the essence of advisory intelligence over autonomous decision-making.
