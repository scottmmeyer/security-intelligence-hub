# ETF-CONVICTION-01: Terminology Recommendation

**Date:** 2026-06-10

---

## Part 3: Semantic Review

### Current Terminology Analysis

**"Low Conviction"** as applied to VOO/VB/VO/FXAIX is:

| Criterion | Assessment |
|---|---|
| Technically accurate? | Partially — reflects the ENGINE's lack of ESS conviction data, not an investment judgment |
| Operationally accurate? | No — "conviction" in portfolio management connotes investment quality, not signal availability |
| Risk of misinterpretation? | **HIGH** — operator may conclude system believes VOO is a poor investment |
| Consistent with FVI = ELITE? | Semantically conflicting — requires explanation to reconcile |

---

## Candidate Terminology Evaluation

| Term | Accuracy | Clarity | Risk of Misinterpretation | Notes |
|---|---|---|---|---|
| **Low Conviction** (current) | Partial | Low | HIGH | Implies poor investment quality |
| Passive Vehicle | High | High | Low | Accurate but doesn't explain WHY to reduce |
| Broad Market Exposure | High | High | Low | Good — no negative connotation |
| Allocation Completion Vehicle | Very High | Moderate | Very Low | Precise but verbose |
| Lower Alpha Potential | High | Moderate | Moderate | Still implies inferiority |
| Non-Preferred Implementation | Moderate | Low | High | Negative framing without clarity |
| Generic Market Exposure | High | High | Low | Good — neutral description |
| ETF Exposure | High | High | Very Low | Simple, accurate |
| Passive Diversifier | High | High | Very Low | Accurate, neutral |
| **Opportunity Cost Position** | **Very High** | **High** | **Very Low** | Already used in evidence string |

**Recommendation: "Opportunity Cost Reduction"**

### Rationale for "Opportunity Cost Reduction"

1. **Technically accurate** — the CRA engine treats these as positions that consume portfolio weight without providing individual alpha conviction, creating opportunity cost vs. direct-conviction alternatives.

2. **Already embedded in the code** — `capital_source_builder.py` line 595 already uses the phrase "opportunity cost position" in the evidence string. Adopting this for the label creates internal consistency.

3. **Non-judgmental** — "opportunity cost" is a neutral financial term that expresses a tradeoff without implying the vehicle is defective.

4. **Operator-appropriate** — a sophisticated operator will understand "opportunity cost" immediately: "This position is taking up space that could be used for higher-conviction positions."

5. **Compatible with ELITE FVI** — "This is an ELITE vehicle that represents an opportunity cost under the current mandate" is a coherent statement. "This is an ELITE vehicle with low conviction" is confusing.

---

## Impacted UI Surfaces

If terminology changes are implemented, the following surfaces would need updating:

### 1. Reduction Queue Panel (ARCH-02)

**File:** `ui/portfolio_alignment/app.js`  
**Location:** `_RQ_CATEGORY_LABELS` constant (~line 4268)

```javascript
// Current:
"LOW_CONVICTION_REDUCTION": "Low Conviction",

// Proposed:
"LOW_CONVICTION_REDUCTION": "Opportunity Cost",
```

### 2. CRA Capital Sources Panel

**File:** `ui/portfolio_alignment/app.js`  
**Location:** `_CRA_CATEGORIES` constant (~line 5205)

```javascript
// Current:
{ key: "LOW_CONVICTION_REDUCTION", label: "Low Conviction Reduction", num: 5 },

// Proposed:
{ key: "LOW_CONVICTION_REDUCTION", label: "Opportunity Cost Reduction", num: 5 },
```

### 3. Reduction Queue Evidence Strip

**No code change needed** — the evidence string already says "opportunity cost position" and will remain accurate.

### 4. PAP Cat 4 (Funding Sources)

**File:** `ui/portfolio_alignment/app.js`  
**Location:** `fundingReason` variable in `_computePortfolioActions()`

```javascript
// Current:
const fundingReason = isCat1 ? "Signal Deterioration" : isCat3 ? "Allocation Reduction" : "Low Conviction";

// Proposed:
const fundingReason = isCat1 ? "Signal Deterioration" : isCat3 ? "Allocation Reduction" : "Opportunity Cost";
```

---

## Part 4: Portfolio Construction Philosophy Verification

The system is expressing **Statement B** (correct):

> "VOO is a high-quality vehicle but a lower-conviction expression than direct ownership of top-ranked securities under the Concentrated Alpha mandate."

**Evidence chain:**
1. FVI = ELITE → vehicle quality acknowledged
2. CRA priority = MODERATE (not URGENT) → not a distress signal
3. CRA sizing = 25% → partial reduction; not recommending full exit
4. Evidence string explicitly says "opportunity cost position"
5. CRA notes: `capital_source_builder.py` docstring: *"LOW_CONVICTION_REDUCTION — HOLD flag, no replay, above de minimis threshold"* — a technical filter, not a quality judgment
6. The reduction rationale is mandate-relative: under Concentrated Alpha, direct securities with high ESS conviction are preferred over passive exposure

**Statement A** ("VOO is a poor investment") is NOT what the system expresses.

---

## Operator Risk Assessment

**Current risk of misinterpretation: MEDIUM-HIGH**

An unsophisticated operator viewing the Reduction Queue would see:
```
VOO | Low Conviction | Moderate | [ELITE badge]
```

The dissonance between "Low Conviction" and "ELITE" without explanatory context creates a trust issue. The operator may:
1. Dismiss the Reduction Queue as inconsistent / wrong → **loses trust in the tool**
2. Sell VOO because "the system says it's low conviction" → **incorrect action for wrong reason**
3. Correctly understand the distinction (sophisticated operator) → **no risk**

A terminology change to "Opportunity Cost Reduction" eliminates this risk without any logic changes.
