# Company Snapshot Operator Optimization Final Verdict — Phase 8.0B.X.2

## Verdict

**APPROVED**

All five design questions answered. Full implementation authorized.

---

## Decision Summary

### 1. Should "Business" be renamed?

**YES — rename to "What They Do"**

"Business" is generic. "What They Do" directly answers the operator question.

### 2. Should "What They Do" be introduced with cleaned content?

**YES — apply JS-side cleaning**

Apply `_cleanBusinessSummary()` in the JS render function:
- Strip company name prefix ("Dell Technologies Inc. designs...")
- Strip geographic boilerplate ("in the United States, Europe, and internationally")
- Strip "together with its subsidiaries"
- Capitalize result, ensure period termination

Zero backend changes required. Applied at render time.

### 3. Should "Why It Matters" be introduced?

**YES — implement via sector + industry lookup table**

A deterministic `(sector, industry)` → theme mapping covers ~90% of portfolio holdings.
Each entry is ≤120 characters, written in plain English, present tense.
No investment recommendation implied.

The lookup table is fully defined in `company_snapshot_why_it_matters_design.md`.
Implementation: pure JS object lookup, no API changes.

### 4. Should business model tags be added?

**YES — implement with 3-tag maximum**

Tags are derived from:
1. Primary: `(sector, industry)` → base tags
2. Secondary: keyword scan of business_summary → context boosts (AI, data center, nuclear, defense, EV)

Tags appear as colored pills immediately beneath the "COMPANY SNAPSHOT" title.
CSS: blue pill design consistent with existing badge style.

### 5. What is the optimal layout?

```
COMPANY SNAPSHOT
[TAG 1] [TAG 2] [TAG 3]

Company       <long_name>
Headquarters  <city, state, country>
Sector        <sector>
Industry      <industry>
What They Do  <cleaned business_summary>
Why It Matters <theme string>
Country       <country>
Cap Tier      [LARGE]
```

### 6. HQ format: Recommend `City, State Abbrev, Country` with "United States" → "USA"

Apply at API response assembly time. One-line change to `run_outcome_ui.py`.

---

## Full Implementation Scope

All changes are display-only (JS + CSS). No scoring impact. No backend changes except the "USA" abbreviation in the API endpoint.

| Change | Location | Complexity |
|--------|----------|------------|
| Rename "Business" → "What They Do" | app.js | Trivial |
| Add `_cleanBusinessSummary()` | app.js | Small |
| Add `_getWhyItMatters()` + lookup table | app.js | Medium |
| Add `_getBusinessTags()` + lookup table | app.js | Medium |
| Add tag CSS (`.dq-cs-tag`, `.dq-cs-tags`) | index.html | Small |
| Add "Why It Matters" CSS styling | index.html | Trivial |
| "United States" → "USA" in HQ | run_outcome_ui.py | Trivial |

---

## Success Criteria Met

An operator reviewing a deployment queue recommendation can immediately answer:

> "What does this company do?" — **What They Do** field
> "Why does this business matter to my portfolio?" — **Why It Matters** field
> "What market is this?" — **Business model tags**

without leaving SIH or opening a browser tab.

---

## Governance

- Display-only enrichment
- No scoring changes
- No CCL changes
- No CW-DAS changes
- No ranking changes
- No recommendation changes
- Fail-open: missing data shows "—" or omits the row; section never fully suppresses
- FMP compatibility confirmed: no structural refactoring needed for Phase 8.0B.1C insertion

## Test Count Expectation

1,004 tests pass (no new scoring logic = no new test requirements for display enrichment)
