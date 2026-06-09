# Allocation Intelligence Before / After

Repository: security-intelligence-hub  
Date: 2026-06-09

## The Problem (Before)

The Allocation Intelligence page showed:

**Concentration Risk section:**
- Micro Cap combined: 2.21% / 5% ceiling → PASS ← (from strategic targets)
- DIGITAL: 4.0% / 8% ceiling → OK

**Recalculation Validators:**
- policy_bounds: PASS
- concentration_ceilings: PASS

**Meanwhile (if user looked carefully):**
Some sections referenced actual portfolio values showing 6.5% micro-cap without clear attribution.

**Operator experience:** Contradictory signals with no explanation. "If PASS, why does it show OVER?"

---

## After Implementation

### Concentration Risk (renamed to clarify: Strategic Target Compliance)

Each bar now includes "— strategic target" suffix in label.
Dataset banner: "📌 Strategic Target Compliance — bars show strategic target percentages vs policy ceilings. A PASS here means the allocation model is within policy, not that current holdings are."

| Indicator | Before label | After label | Value | Badge |
|---|---|---|---|---|
| Mega Cap | "EQUITIES.US.MEGA" | "EQUITIES.US.MEGA — strategic target" | 18.0% | PASS |
| Micro Cap | "Micro Cap combined" | "Micro Cap combined — strategic target" | 2.21% | PASS |

### New Section: Current Portfolio Compliance

Added directly below Concentration Risk.

Dataset banner: "📊 Current Portfolio Allocation — bars show actual portfolio holdings vs policy ceilings."

| Indicator | Value | Badge | Notes |
|---|---|---|---|
| EQUITIES.US.MEGA actual | ~18.7% | PASS | |
| Micro Cap combined actual | ~6.5% | ADVISORY | +1.5pp drift from 5% ceiling |
| DIGITAL actual | ~1.5% | PASS | |
| CASH actual | ~9.0% | PASS | |

Explainability note (always visible):
> "Why might Strategic Targets show PASS while Current Portfolio shows OVER? Strategic Target Compliance validates the allocation planning model. Current Portfolio Compliance evaluates your actual holdings today. The difference is allocation drift — natural movement as market prices change."

### Recalculation Validators

Banner added: "ℹ️ Strategic Target Recalculation Compliance — validates the allocation model, not current portfolio holdings."

PASS badges now clearly scoped to "does the recalculation model satisfy governance?" not "does the portfolio satisfy governance?"

### Strategic Allocation Targets Table

Banner added: "📌 Strategic Target Allocation — these are the planned target percentages from the current allocation model."

### Effective Allocation Recommendation

Banner added: "📈 Effective Allocation After Overlays — strategic target percentages adjusted by active tactical momentum overlays."

---

## Operator Experience Transformation

| Question | Before | After |
|---|---|---|
| "What does this PASS mean?" | Ambiguous | Clearly scoped to strategic targets |
| "Is my portfolio in compliance?" | Unclear, inferred | Explicit Current Portfolio Compliance section |
| "Why PASS and OVER at the same time?" | No answer | Explainability note answers directly |
| "What are these percentages?" | Unlabeled | Every display labelled with data source |
