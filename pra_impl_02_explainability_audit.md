# PRA-IMPL-02 Explainability Audit

## Scope

Independent audit of AI-003 integration in `src/sih/allocation_explainability.py`.
Evidence from code inspection and live runtime execution.

---

## Q13. Are explanations derived from actual recommendation inputs?

**Yes, with one important constraint.**

The `_funding_drivers(rec)` function operates exclusively on:
1. `rec["rationale"]` — the persisted recommendation rationale string

It parses three regex patterns:
- `_FUNDING_RE` → extracts source type, symbols, available pct
- `_FUNDING_ALTERNATIVES_RE` → extracts alternatives list
- `_FUNDING_POLICY_RE` → extracts policy alignment text

All three patterns match against the **actual recommendation rationale**, which is the
same text stored in `recommendations.json`. There is no independent re-inference,
no model invocation, and no hallucination path.

**Constraint:** Pre-PRA persisted recommendations do NOT have the Why/Alternatives/Policy
clauses in their rationale. `_FUNDING_ALTERNATIVES_RE` and `_FUNDING_POLICY_RE` will
find no match on old records, producing only the basic `funding_source` driver.

This is correct and expected behavior — explainability is limited by what was
written at recommendation-generation time. It is not a bug.

---

## Q14. Are explanations deterministic?

**Yes.**

All three parsers are deterministic regex operations. Same input → same output.
No random state, no LLM calls, no external lookups involved in `_funding_drivers(...)`.

The `build_recommendation_explanation(...)` function itself is also deterministic:
- `_primary_reason()` splits rationale on sentence boundaries → deterministic
- `_supporting_reasons()` uses the same split → deterministic
- `_signal_drivers()` reads persisted overlay CSV and JSON files → deterministic
- `_philosophy_scores()` is a pure function of `recommendation_type` → deterministic

---

## Q15. Can funding rationale be traced back to scoring inputs?

**Partially.**

The funding clause in the rationale contains:
- Source type and symbols
- Available percentage (from `FundingSourceEntry.available_pct`)
- Reduction reason (from `FundingSourceEntry.reduction_reason`)
- Alternatives (from `funding.sources[1:3]`)
- Policy alignment (from `FundingSourceEntry.policy_alignment_reason`)

An operator reading `"Why this source: Cash/sweep allocation (9.0%) exceeds the
operational reserve floor (2%)."` can trace this back to:
1. Cash holdings in portfolio (SPAXX at 9.0%)
2. Reserve floor constant `_CASH_RESERVE_FLOOR_PCT = 2.0`

An operator reading `"Score 107.0"` in the recommendation summary can relate this
to the scoring formula.

**Gap:** The actual numeric scoring components (base + available + bonuses) are not
surfaced in the rationale or explanation. The operator sees the final score but cannot
reproduce the component breakdown from the UI alone. This is an explainability
surface gap, not a correctness gap.

---

## Q16. Is any explanation fabricated or inferred post hoc?

**No.**

All driver types are extracted from persisted rationale text:

1. `funding_source`: extracted from `"Funding source: ... (~X% available)."` clause
   — this clause is written from `FundingSourceEntry.source_type` and `.available_pct`
   at recommendation-generation time.

2. `funding_alternatives`: extracted from `"Alternatives considered: ..."` clause
   — written from `funding.sources[1:3]` at recommendation-generation time.

3. `funding_policy_alignment`: extracted from `"Policy alignment: ..."` clause
   — written from `FundingSourceEntry.policy_alignment_reason` at recommendation-generation time.

None of these are inferred independently after the fact. The AI-003 engine is
purely a parser of existing text, not a generator of new content.

---

## Live Extraction Test

Synthetic recommendation with post-PRA rationale format:

```
"Funding source: Excess Cash (SPAXX, ~7.0% available). Why this source: Cash/sweep
allocation (9.0%) exceeds the operational reserve floor (2%). Approximately 7.0% is
deployable without affecting liquidity. Alternatives considered: Trim Candidate,
Overweight Reduction. Policy alignment: Uses excess liquidity before forcing equity
reductions, preserving optionality."
```

**Extracted drivers:**

```json
[
  {
    "driver_type": "funding_source",
    "source_type": "EXCESS_CASH",
    "symbols": ["SPAXX"],
    "available_pct": 7.0
  },
  {
    "driver_type": "funding_alternatives",
    "alternatives": ["TRIM_CANDIDATE", "OVERWEIGHT_REDUCTION"]
  },
  {
    "driver_type": "funding_policy_alignment",
    "value": "Uses excess liquidity before forcing equity reductions, preserving optionality"
  }
]
```

All 3 driver types correctly extracted. Live test confirmed: `126 passed`.

---

## Known Limitation: Primary Reason Displacement

In post-PRA rationale for `INCREASE_UNDERWEIGHT` recommendations, the rationale
structure is:

```
"Portfolio is underweight [NODE] by [X]pp... [prescriptive]... [suitability]...
Funding source: [SOURCE] (~X% available). Why this source: [WHY]. Alternatives: ...
Policy alignment: ..."
```

The `_primary_reason()` function extracts the **first sentence** of the rationale.
For `INCREASE_UNDERWEIGHT`, the first sentence is the underweight description —
correct. The funding clause appears mid-rationale, not first.

However, in the synthetic test (`_rec` with rationale starting directly with
"Funding source:"), `_primary_reason()` would return the funding clause as the
primary reason, which is semantically wrong (the funding source is a supporting
factor, not the primary reason for the recommendation).

**Risk:** If any recommendation is ever constructed with a funding clause as the
literal first sentence, the primary reason will be misidentified. In practice, all
`INCREASE_UNDERWEIGHT` recommendations start with `"Portfolio is underweight..."`,
so this risk is currently not realized. No fix is required now but should be noted.
