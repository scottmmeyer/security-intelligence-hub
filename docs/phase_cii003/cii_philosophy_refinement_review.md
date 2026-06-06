# CII Philosophy Refinement Review — Phase CII-003

## Current Philosophy State (Post-CII-002)

The CII methodology is documented across:
- `docs/methodology/01_methodology_classification.md` through `09_final_verdict.md`
- The CII modal in `ui/portfolio_alignment/index.html` (v19)

The current official statement reads:

> "Consensus Intelligence Investing (CII) is a portfolio construction methodology that begins with professional analyst consensus, validates that consensus against business fundamentals and historical evidence, scores opportunities using an internal conviction framework, and deploys capital through a risk-managed model designed to maximize long-term portfolio growth."

The current Objective reads:

> "Identify and allocate capital toward opportunities where analyst consensus, business fundamentals, historical evidence, and portfolio discipline align most favorably in pursuit of superior long-term risk-adjusted returns."

---

## Q1: Does the philosophy adequately explain superior long-term risk-adjusted returns?

**PARTIALLY — the returns objective is present but the mechanism is underspecified.**

The current Objective statement mentions "superior long-term risk-adjusted returns" — but does not explain the dual mechanism:

1. **Identifying superior opportunities** (consensus + fundamentals + replay alignment)
2. **Reducing allocation mistakes** (avoiding DETERIORATING theses, disciplined sizing)

The alpha framework section in the CII modal mentions four sources but frames them primarily as selection sources, not error-reduction sources. The error-reduction case (avoiding value traps, not deploying into deteriorating theses) is equally important and is the primary mechanism for ISSUE-07.

**Recommended addition:** Make the dual mechanism explicit: "CII seeks to generate superior long-term risk-adjusted returns through two complementary mechanisms: identifying high-conviction opportunities where multiple evidence layers align, and reducing allocation errors by detecting thesis deterioration before the consensus catches up."

---

## Q2: Does the philosophy explain that alpha comes from BOTH identifying opportunities AND reducing mistakes?

**NO — this distinction is currently implicit, not explicit.**

The "Expected Sources of Alpha" section in the modal focuses on the positive (consensus intelligence, fundamental confirmation, historical validation) but does not explicitly name "error reduction" or "mistake avoidance" as an alpha source.

Yet the most actionable finding from the Phase 8.0B.1C assessment is exactly this: the ISSUE-07 fundamental modifier primarily reduces errors (PSX at #4 with DETERIORATING fundamentals) rather than identifying new opportunities.

**Recommended language addition:**

"Alpha is generated through two complementary channels:
1. **Opportunity identification** — directing capital toward positions where consensus, fundamentals, and history all align
2. **Error reduction** — detecting and downweighting positions where the consensus narrative has outrun business reality"

---

## Q3: Does the philosophy properly distinguish the four layers?

**YES — but with one gap.** Layer 2 (Fundamental Validation) is currently described as display-only / classification-only. The philosophy does not yet acknowledge that it is transitioning to an active scoring role (ISSUE-07).

This is appropriate — ISSUE-07 is not yet implemented. But the philosophy documents should be updated after ISSUE-07 is delivered to reflect the evolution.

**Current:**
- Layer 1: Active scoring (composite 0–5 → CW-DAS Signal component)
- Layer 2: Display + classification only (Thesis Integrity, Fundamental Consistency)
- Layer 3: Hard eligibility gate (replay_supported must be True)
- Layer 4: Active scoring (CW-DAS Sizing, Momentum, penalties)

**After ISSUE-07:**
- Layer 2 will gain a bounded scoring role (conviction modifier ±5 pts)

---

## Q4: Recommended Updated Objective Language

### Current Objective (Modal)
> "Identify and allocate capital toward opportunities where analyst consensus, business fundamentals, historical evidence, and portfolio discipline align most favorably in pursuit of superior long-term risk-adjusted returns."

### Proposed Enhancement (for post-ISSUE-07 update)
> "Identify and allocate capital toward high-conviction opportunities where analyst consensus, business fundamentals, historical evidence, and portfolio discipline align — while systematically reducing allocation errors where consensus has outrun business reality — in pursuit of superior long-term risk-adjusted returns."

**What changed:** Added "while systematically reducing allocation errors where consensus has outrun business reality" — this explicitly names the error-reduction alpha mechanism and prepares the ground for the ISSUE-07 fundamental modifier.

**Timing:** This update should be applied to the CII modal after ISSUE-07 is implemented and certified. Not before, since the error-reduction mechanism is not yet active in scoring.

---

## Summary

| Question | Assessment | Action |
|----------|-----------|--------|
| Q1: Superior returns adequately explained? | PARTIALLY | Enhance objective language post-ISSUE-07 |
| Q2: Dual alpha mechanism explicit? | NO | Add to modal after ISSUE-07 |
| Q3: Four layers properly distinguished? | YES with gap | Update Layer 2 description after ISSUE-07 |
| Q4: Updated objective recommended? | YES | Draft ready; apply post-ISSUE-07 |
