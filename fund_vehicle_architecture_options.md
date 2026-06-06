# Fund Vehicle Intelligence (FVI) Architecture Options

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-19 FVI Architecture Options  
Date: 2026-06-06

## Q3) Peer Group Methodology

FVI quality evaluation must be peer-relative and category-correct.

Recommended hierarchy:
1. Primary comparator: Morningstar Category (or equivalent canonical category provider)
2. Secondary comparator: Lipper category mapping when Morningstar unavailable
3. Tertiary comparator: SIH custom category mapping (benchmark + style + region + market-cap profile)

### DODFX Recommendation

DODFX should be evaluated against a value-oriented foreign large-cap peer set.

Recommended comparison stack:
1. Primary: Foreign Large Value (Morningstar-aligned naming)
2. Secondary cross-check: International Large Value category equivalent
3. Avoid broad International Blend as sole comparator because it dilutes style-specific validity.

Decision rule:
- Use style-consistent peer groups first.
- Use broader blend categories only as supplemental context.

## Architecture Option A: Advisory Sidecar (Recommended Start)

Description:
- Compute FVI quality labels independently from CRA/CW-DAS scoring.
- Display quality state and replacement confidence as advisory metadata.

Pros:
- Lowest governance risk
- Fastest useful value
- Preserves current scoring integrity
- High explainability

Cons:
- No direct scoring optimization effect

Best use:
- Initial minimum viable FVI.

## Architecture Option B: Recommendation Filter Layer

Description:
- FVI acts as a policy gate for replacement recommendations in CRA/PAP.
- Example: "Do not suggest replacement unless fund quality is weak and switching economics are favorable."

Pros:
- Reduces false positive replacements
- Directly improves recommendation quality

Cons:
- Requires stronger policy testing
- Can alter recommendation throughput

Best use:
- Phase 2, after advisory validation.

## Architecture Option C: Direct Scoring Influence

Description:
- FVI contributes directly to CW-DAS or allocation score math.

Pros:
- Full quantitative integration

Cons:
- Highest governance and methodology risk
- Higher risk of circularity and double counting
- Requires multi-quarter validation and formal scoring governance approval

Best use:
- Long-term only, if evidence burden is met.

## Q7) Minimum Viable FVI

Yes, a simple model is useful.

Minimum useful implementation (advisory-only):
1. Fund Quality Score from three percentiles:
- category-relative risk-adjusted return percentile
- expense percentile
- downside capture percentile
2. Output classes:
- LOW
- MEDIUM
- HIGH
- ELITE
3. Minimum policy output:
- retain/watchlist/consider-replacement (advisory only)

Why this is valuable:
- Immediately separates sleeve pressure from vehicle quality.
- Adds explainable quality context to CRA/Allocation Reduction decisions.
- Requires manageable data and governance overhead.

## Q8) Long-Term Vision (Mature FVI)

Mature record example:

- Vehicle: DODFX
- Sleeve: International Equity
- Fund Quality: ELITE
- Peer Rank: 92nd percentile
- Manager Stability: HIGH
- Switching Economics: unfavorable for replacement
- Replacement Recommendation: NONE
- Allocation Recommendation: reduce only if International sleeve target requires reduction

Mature capability attributes:
1. Peer-normalized quality diagnostics with confidence intervals
2. Explicit switching economics model (loads, taxes, transaction friction)
3. Explainable recommendation graph across CRA, PAP, and Allocation Reduction
4. Full audit trail for every replacement/non-replacement decision
