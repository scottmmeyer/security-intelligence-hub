# GitHub Issue Priority Review — Phase CII-003

## Current Open Issues

| # | Title | Labels | Current Priority |
|---|-------|--------|-----------------|
| 13 | ISSUE-07: Fundamental Conviction Modifier | enhancement, fmp, cwdas, priority-high, needs-design | HIGH |
| 11 | ISSUE-05: Queue Filter by Thesis Integrity | enhancement, ui-ux, priority-medium, ready | MEDIUM |
| 10 | ISSUE-04: Dislocation Watchlist Panel | enhancement, ui-ux, fmp, priority-medium, needs-design | MEDIUM |
| 6 | EPIC: Governance and Tooling | epic, governance | Epic |
| 5 | EPIC: Signal Intelligence Evolution | epic, cwdas, sti, ess | Epic |
| 4 | EPIC: Company Context and Methodology | epic, ui-ux | Epic |
| 3 | EPIC: Portfolio Action Pipeline (PAP) | epic, pap | Epic |
| 2 | EPIC: Capital Rotation Advisor (CRA) | epic, cra | Epic |
| 1 | EPIC: FMP Integration | epic, fmp, provider | Epic |

---

## Q5: Is ISSUE-07 now the highest-value open implementation issue?

**YES — by clear margin.**

ISSUE-07 (Fundamental Conviction Modifier) is the highest-value open implementation issue because:

1. **Most impactful to ranking quality:** The PSX case (DETERIORATING fundamentals at #4) demonstrates a real, current ranking distortion that ISSUE-07 directly corrects.

2. **Highest strategic importance:** It operationalizes the "validates consensus against fundamentals" language in the CII philosophy — moving Layer 2 from display-only to an active component of the framework.

3. **No peer-level competitor:** ISSUE-05 (queue filter) and ISSUE-04 (dislocation watchlist) are useful but do not affect ranking or alpha generation.

4. **Well-defined:** The formula is fully specified in `phase_8_0b1c_recommendation.md`. The implementation path is clear.

---

## Q6: Are any currently-open issues lower priority than ISSUE-07?

**Yes — ISSUE-04 and ISSUE-05 are both lower priority than ISSUE-07.**

| Issue | Value | Effort | Priority vs. ISSUE-07 |
|-------|-------|--------|----------------------|
| ISSUE-07 | HIGH (ranking improvement) | L | Highest |
| ISSUE-05 | MEDIUM (UI convenience) | XS | Lower |
| ISSUE-04 | MEDIUM (UI convenience) | S | Lower |

**Specific analysis:**

**ISSUE-05 (Queue Filter by Thesis Integrity):**
- Labeled `ready` and `priority-medium` — correct
- Good quick-win but zero impact on alpha or ranking
- After ISSUE-07, the filter becomes MORE valuable because the fundamental modifier will have changed rankings — but the filter itself should still come after ISSUE-07

**ISSUE-04 (Dislocation Watchlist):**
- Labeled `needs-design` and `priority-medium` — correct
- Displays dislocation signals that already exist (Phase 8.0B.1B.5)
- Valuable but lower priority than improving the scoring mechanism

---

## Q7: Recommended Label/Priority Updates

### ISSUE-07 — Change status from `needs-design` to `ready`
The design is complete. `phase_8_0b1c_recommendation.md` provides the exact formula, pseudocode, acceptance criteria, and bounded ranges. The `needs-design` label no longer applies.

**Change:** Remove `needs-design`, add `ready`

### ISSUE-05 — No change needed
Labels and priority are correct.

### ISSUE-04 — No change needed
Labels and priority are correct.

### New issue to create: ISSUE-08 (analyst_count bug fix)
**Title:** `ISSUE-08: Fix analyst_count bug in fetch_yahoo_supplemental.py`  
**Labels:** `bug`, `provider`, `data-quality`, `priority-low`, `ready`  
**Description:** Add `numberOfAnalystOpinions` to yfinance fetch. Returns `None` for all symbols currently despite being in schema. Quick fix (~30 minutes).

---

## Summary

| Action | Item |
|--------|------|
| Update ISSUE-07 label | `needs-design` → `ready` |
| Create ISSUE-08 | analyst_count bug fix |
| No other changes | ISSUE-04 and ISSUE-05 labels correct |
