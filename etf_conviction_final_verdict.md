# ETF-CONVICTION-01: Final Verdict

**Date:** 2026-06-10  
**PAR:** PAR-20260610-DCF0E31F  
**Status:** Audit complete — No implementation changes. Recommendations documented.

---

## Summary of Findings

### Q1. Is current behavior logically correct?

**Yes — the underlying logic is correct.**

The CRA engine correctly identifies VOO/VB/VO/FXAIX as positions lacking individual ESS conviction data, not in the deployment queue, with no replay evidence. These are accurate descriptions of these positions' relationship to the Concentrated Alpha mandate's conviction framework.

The classification pipeline:
- Correctly excludes ETFs from ESS scoring (they are not individual equities)
- Correctly excludes ETFs from the CW-DAS Deployment Queue (no BULLISH signal by design)
- Correctly categorizes them as capital sources under the LOW_CONVICTION_REDUCTION category
- Correctly assigns MODERATE/LOW priority (not URGENT) reflecting their non-distress status
- Correctly assigns 25% sizing (partial reduction only)

**No bugs were found. No incorrect classifications were found.**

---

### Q2. Is current terminology correct?

**No — the operator-facing label "Low Conviction" is semantically misleading.**

"Conviction" in portfolio management is widely understood to mean investment quality, strength of investment thesis, or analyst confidence in an asset. Using it to describe "the engine has no ESS data for this ETF" creates a false signal.

VOO receiving "Low Conviction" when FVI says "ELITE" appears contradictory without context. The correct framing is:

> "This is a high-quality vehicle held as an allocation completion position. Under the Concentrated Alpha mandate, direct-conviction securities are preferred when capital is available. This ETF represents an opportunity cost position — its capital could be redeployed to fund a higher-conviction direct holding."

The current label communicates the first half (this can be reduced) but fails to communicate the reason (opportunity cost, not quality failure).

---

### Q3. Does the system overstate negative sentiment toward passive vehicles?

**Moderately, through label choice only — not through logic or ranking.**

The OVERSTATEMENT is limited to:
1. The label "Low Conviction" appearing for ELITE-rated vehicles
2. No accompanying disclaimer or explanation in the Reduction Queue

The system does NOT overstate through:
- Priority assignment (MODERATE, not URGENT)
- Sizing (25%, not 100%)
- Evidence string (already says "opportunity cost position")
- CRA display (shows correct category context)
- PAP categorization (ETFs in Cat 3/4 with appropriate framing)

**The logic is nuanced. Only the label is blunt.**

---

### Q4. Should a terminology change be implemented?

**Yes — a targeted label change is recommended.**

This is a small, high-value change:
- One constant in `app.js` (`_RQ_CATEGORY_LABELS`)
- One constant in `app.js` (`_CRA_CATEGORIES`)
- One string in `_computePortfolioActions()`
- No backend changes
- No logic changes
- No scoring changes
- Passes full regression (pure display change)

**The change eliminates operator confusion with minimal implementation risk.**

---

### Q5. Exact proposed wording changes and impacted surfaces

#### Surface 1: Reduction Queue panel (ARCH-02)

| Location | Current | Proposed |
|---|---|---|
| `_RQ_CATEGORY_LABELS["LOW_CONVICTION_REDUCTION"]` | `"Low Conviction"` | `"Opportunity Cost"` |

#### Surface 2: CRA Capital Sources panel

| Location | Current | Proposed |
|---|---|---|
| `_CRA_CATEGORIES[4].label` | `"Low Conviction Reduction"` | `"Opportunity Cost Reduction"` |

#### Surface 3: PAP Funding Sources (Cat 4)

| Location | Current | Proposed |
|---|---|---|
| `fundingReason` fallback | `"Low Conviction"` | `"Opportunity Cost"` |

#### No change needed:

- `capital_source_builder.py` internal constant `CATEGORY_LOW_CONVICTION` — internal code identifier, not operator-facing
- Evidence string — already says "opportunity cost position"
- FVI badges — already correct
- Policy badges — already correct
- Priority labels — already correct

---

## Governance Assessment

### What was found

| Assessment | Result |
|---|---|
| Logic correctness | ✓ CORRECT |
| Classification correctness | ✓ CORRECT |
| FVI consistency | ✓ CONSISTENT (different dimensions) |
| Operator interpretation risk | ⚠ MEDIUM-HIGH due to "Low Conviction" label |
| Recommended action | Terminology change (display only, no logic) |

### Scope of recommended change

- **Governance level:** UI display label only
- **Backend impact:** None
- **Test impact:** None (no assertions on this label string)
- **Risk:** Very low
- **Operator trust impact:** Positive — removes ambiguous signal

### Statement on Philosophy Preservation

A terminology change from "Low Conviction Reduction" to "Opportunity Cost Reduction" does NOT change:
- The Concentrated Alpha mandate's preference for direct-conviction securities
- The correct role of passive vehicles as allocation completion instruments
- The reduction priority assigned to these positions
- The sizing or proceeds calculations
- The FVI tier assessment

It DOES change:
- How the operator interprets the system's intent
- Whether the operator trusts the signal
- Whether the label matches the code's documented intent

---

## Backlog Recommendation

**ETF-CONV-01 (LOW priority, easy):** Rename "Low Conviction Reduction" → "Opportunity Cost Reduction" in three UI locations. Pure display change. Eliminates the most common operator interpretation error for passive vehicles.

**ETF-CONV-02 (MEDIUM priority):** Add a tooltip or advisory note to the Reduction Queue "Opportunity Cost" category explaining: "These are high-quality passive vehicles held for allocation exposure. Reduction frees capital for higher-conviction direct positions under the Concentrated Alpha mandate. FVI quality rating is preserved."

**ETF-CONV-03 (LOW priority, design):** Assign `strategic_role = "CORE_BROAD_US"` to VOO in `_ETF_OVERRIDES` to enable the CRITICAL importance classification. This would move VOO from MEDIUM importance to CRITICAL — which would raise its trim_penalty from 0 to -25pts and reduce trim_priority_score from ~40 to ~15, making it appear less reduction-eligible. This reflects the correct portfolio construction view that VOO is a foundational allocation vehicle. However, this changes actual trim scoring behavior (not just labels) and requires validation.
