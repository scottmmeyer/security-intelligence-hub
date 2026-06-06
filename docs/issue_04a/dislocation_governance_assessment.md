# Dislocation Governance Assessment
## ISSUE-04A Design Phase — June 5, 2026

---

## Q1: Is Dislocation a Scoring Input?

**Decision: NO.**

Dislocation is not a scoring input to any existing system (CW-DAS, composite
score, UCF, Fundamental Modifier).

Rationale:

Dislocation is a derived observation — it is computed from signals that are
already represented in the scoring systems. Adding dislocation back into a
scoring system would create circular dependency: the same ESS/Danelfin/beat
rate inputs that produce the Fundamental Modifier would also produce a
"dislocation bonus" that feeds into another scoring system, effectively
double-counting those inputs.

Additionally, dislocation classification requires intact thesis AND signal
weakness simultaneously. Signal weakness already suppresses the composite
score. Adding a dislocation bonus to counteract that suppression would fight
against the signal — exactly the kind of opacity CII is designed to avoid.

**Dislocation is an explanatory layer, not a scoring layer.**

---

## Q2: Is Dislocation Informational Only?

**Decision: YES, at the operator intelligence level.**

Dislocation belongs to the same informational category as:
- The Signal Agreement Panel (CONSENSUS_ALIGNED / DIVERGENCE)
- The Analyst Target Intelligence block
- The "Why SIH Likes It" panel

It surfaces evidence for operator review. It does not trigger automated
recommendations, override strategic profiles, or modify deployment priority.

**Governance classification: INFORMATIONAL INTELLIGENCE — OPERATOR ADVISORY**

---

## Q3: Should Dislocation Influence CW-DAS?

**Decision: NO.**

CW-DAS is a deployment priority engine. Its purpose is to rank which holdings
should receive incremental capital under current portfolio conditions. The
Fundamental Modifier already adjusts CW-DAS scores based on FMP fundamental
quality.

A dislocation condition (intact fundamentals + weak signal) would not be a
reason to deploy more capital immediately — the weak signals may persist, and
the deployment decision must account for mandate constraints, replay support,
and conviction tier, none of which are changed by a dislocation observation.

Moreover, the current system correctly handles the most important case:
- DELL with INTACT + 100% beat + CONSISTENT + VERY_BULLISH ESS → high CW-DAS (correctly)
- PSX with DETERIORATING thesis → lower CW-DAS (correctly)
- A name with INTACT + 87.5% beat + BEARISH ESS → Fundamental Modifier +2.0 already
  reflects the fundamental quality; the CW-DAS score is appropriately elevated

The Fundamental Modifier already does the right thing for the overlap case.
No additional CW-DAS influence from dislocation is needed.

**Verdict: CW-DAS unchanged. Fundamental Modifier already handles the overlap.**

---

## Q4: Should Dislocation Influence Composite Score?

**Decision: NO.**

The composite score is derived from signal inputs (ESS, Danelfin, Zacks, ABR).
These signals represent current market intelligence. If ESS is BEARISH and
Danelfin is 1.8, the composite score should reflect that weakness — the market
is telling us something, even if fundamentals are intact.

Adjusting the composite score upward because a dislocation heuristic fired would
override the signal layer with a derived meta-observation. This creates a
compound problem: the composite score is used in UCF, STI, and CW-DAS calculations.
Contaminating it with a dislocation signal would corrupt all downstream uses.

**Verdict: Composite score unchanged.**

---

## Q5: Should Dislocation Influence CRA?

**Decision: NO.**

The Capital Rotation Advisor proposes rotation from weak positions into strong
ones based on deployment queue rank and strategic profiles. A dislocation
observation on a holding does not change whether it should be a capital source
(SIGNAL_DETERIORATION) or capital destination (deployment queue rank).

A HIGH CONVICTION DISLOCATION name could plausibly be a rotation destination —
but this is already handled: if the thesis is INTACT and beat rate is high, the
Fundamental Modifier will have boosted its CW-DAS score, improving its deployment
queue rank, which the CRA already reads.

No additional CRA influence is required.

**Verdict: CRA unchanged.**

---

## Q6: Is Dislocation Alpha Generation or Opportunity Discovery?

**Decision: OPPORTUNITY DISCOVERY.**

Alpha generation would imply that dislocation detection predicts superior
returns — a claim that would require backtesting evidence, forward-performance
tracking, and careful statistical validation before incorporation.

SIH makes no alpha claims. The system identifies where analyst consensus,
fundamental evidence, and historical replay support appear to diverge from
current market signals. What the operator does with that observation is their
decision, based on their investment thesis, their portfolio constraints, and
their own conviction.

**SIH Dislocation is: "Here is evidence of a gap. You decide what it means."**

It is not: "This is mispriced. Buy it."

This framing is essential for:
- Maintaining operator trust (no false forecasts)
- Preserving regulatory defensibility (no investment advice claims)
- Aligning with CII's philosophy of evidence-based opportunity discovery

---

## Q7: Does Dislocation Create Philosophy Drift from CII v1.1?

**Decision: NO — when correctly scoped.**

CII v1.1 states:
- Layer 1: Analyst consensus
- Layer 2: Fundamental validation of consensus
- Layer 3: Historical validation
- Layer 4: Portfolio discipline

Dislocation as defined in ISSUE-04A is a cross-layer synthesis observation:
it identifies when Layer 2 (fundamentals intact) conflicts with Layer 1 (signals
weak). This is a natural and valuable CII intelligence product — it answers
the question "Where has CII Layers 2 and 3 detected quality that Layer 1 has
not yet priced in?"

**What would create philosophy drift:**
- Using dislocation to override Layer 4 constraints (allocation mandate)
- Using dislocation to generate buy recommendations
- Allowing dislocation to automatically elevate a position above its conviction tier
- Using dislocation tier as a scoring input that feeds back into Layers 1–3

**What is aligned with CII:**
- Surface dislocation as an informational panel in the operator workspace
- Allow operators to filter/watchlist dislocated names
- Explain the evidence clearly
- Leave the action decision with the operator

**Verdict: No philosophy drift when correctly scoped as informational.**

---

## Summary: Governance Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Q1: Scoring input? | NO | Circular dependency risk; already in Fundamental Modifier |
| Q2: Informational only? | YES | Operator advisory; no automated triggers |
| Q3: Influence CW-DAS? | NO | Fundamental Modifier already handles overlap |
| Q4: Influence composite score? | NO | Would corrupt all downstream uses |
| Q5: Influence CRA? | NO | CRA reads CW-DAS rank, which already reflects fundamentals |
| Q6: Alpha generation or discovery? | DISCOVERY | No return prediction claims |
| Q7: Philosophy drift? | NO (when scoped) | Cross-layer synthesis within CII framework |
