# CII Scoring Alignment Review — Phase 8.0B.1C

## CII Philosophy Recap

> "Consensus Intelligence Investing begins with professional analyst consensus, validates that consensus against business fundamentals and historical evidence, scores opportunities using an internal conviction framework, and deploys capital through a risk-managed model designed to maximize long-term portfolio growth."

The phrase "validates that consensus against business fundamentals" is the critical line. It establishes fundamentals as a **validation layer**, not a primary scoring input.

---

## Q1: Is consensus currently the primary signal source?

**YES.**

The composite score is:
```
Composite = ESS × 55% + Zacks × 20% + Danelfin × 25%
```
CW-DAS Signal component: `min(composite / 5.0 × 30, 30)` — up to 30 of 103 max points.

100% of the composite derives from analyst consensus signals (ESS, Zacks, Danelfin). No fundamental data currently influences the composite.

---

## Q2: Would direct fundamental scoring violate the philosophy?

**Partially, depending on the mechanism.**

| Integration Approach | Philosophy Violation? | Reasoning |
|---------------------|----------------------|-----------|
| Fundamentals as display-only (current) | None | Current state, fully compliant |
| Fundamentals as an eligibility gate | None | "Validate consensus" implies gates are acceptable |
| Fundamentals as a small conviction modifier | Minor | Shifts from pure consensus slightly but aligns with "validates against business fundamentals" |
| Fundamentals as a dedicated scoring component | Moderate | Moves toward multi-factor investing, away from consensus-first |
| Fundamentals as primary signal | **VIOLATES** | Would contradict "begins with professional analyst consensus" |

**Verdict:** A small conviction modifier that penalizes DETERIORATING thesis or rewards CONSISTENT + high beat rate is defensible within the CII philosophy. It operationalizes the "validates" language. Anything larger begins to move CII toward multi-factor investing.

---

## Q3: What role should fundamentals play?

**Recommended classification: CONVICTION MODIFIER**

Not VALIDATION ONLY (too passive — already implemented in display layer).  
Not PRIMARY SCORING INPUT (violates philosophy).

A conviction modifier means:
- The analyst consensus and replay gate still control eligibility and primary ranking
- Fundamentals apply a bounded adjustment (±3–5 points) to the CW-DAS score
- A DETERIORATING + CONTRADICTORY security receives a small penalty
- An INTACT + CONSISTENT + strong beat rate security receives a small bonus
- The modifier never overrides conviction tier (CCL still outranks HCA)

---

## Alignment Test

> "CII does not attempt to predict markets. It seeks to improve **decision quality** through collective market intelligence, business fundamentals, empirical evidence, and disciplined portfolio management."

A conviction modifier directly serves "improve decision quality through business fundamentals." This is the strongest language in the CII philosophy in favor of fundamental integration.

---

## Verdict

**A bounded fundamental conviction modifier is philosophically aligned with CII.**

The implementation must satisfy three constraints:
1. Consensus remains the primary scoring driver (Signal component unchanged)
2. Replay gate remains (no bypass for fundamentally strong but replay-absent candidates)
3. The modifier is bounded (cannot flip a CCL below an HCA or move a security more than ±5 points)
