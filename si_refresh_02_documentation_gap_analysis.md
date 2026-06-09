# SI-REFRESH-02 Documentation Gap Analysis

Repository: security-intelligence-hub  
Audit Date: 2026-06-09

## Documents Reviewed

1. refresh_coverage_model.md
2. freshness_badge_logic_update.md
3. provider_status_api_update.md
4. refresh_ui_validation.md
5. si_refresh_02_certification.md

---

## Document 1: refresh_coverage_model.md

### Stated Yahoo badge for today

> "Yahoo: ... badge_state FRESH_PARTIAL (eps_growth_5yr: 0%)"

**Status: INCORRECT**

Actual badge_state = FRESH. The document claims Yahoo gets FRESH_PARTIAL from the eps_growth_5yr 0% coverage, but this is wrong: eps_growth_5yr is not a primary field and does not trigger FRESH_PARTIAL.

This is the one factually incorrect statement in the SI-REFRESH-02 documentation set.

---

## Document 2: freshness_badge_logic_update.md

Content reviewed — no inaccuracies found. The before/after logic description is accurate.

---

## Document 3: provider_status_api_update.md

Under "Notes":

> "badge_state = FRESH_PARTIAL for Yahoo is triggered because eps_growth_5yr is in zero_coverage_fields"

**Status: INCORRECT**

The same factual error appears here. The document then immediately corrects itself:

> "Implementation note: The current implementation triggers FRESH_PARTIAL only for primary field 0% or <95% row coverage. eps_growth_5yr (a non-primary field) at 0% surfaces in zero_coverage_fields and shows the advisory badge in the UI."

The "Implementation note" is correct and supersedes the erroneous header statement, but the contradiction within the same document creates ambiguity.

---

## Document 4: refresh_ui_validation.md

Under "Test Scenarios and Expected Badge Outcomes":

> "Non-primary field 0% (eps_growth_5yr) | Today | 99.9% rows | all primary: OK | FRESH + advisory"

**Status: CORRECT**

The table entry for the non-primary field scenario accurately states FRESH (not FRESH_PARTIAL).

---

## Document 5: si_refresh_02_certification.md

At Q2:

> "badge_state: FRESH (eps_growth_5yr is non-primary — does not trigger FRESH_PARTIAL)"

**Status: CORRECT**

At Q3:

> "yes, FRESH is still possible if row coverage is high and primary fields are populated, even if supplemental fields are empty"

**Status: CORRECT**

At Q5 (Remaining issues):

> "REFRESHING badge state not implemented in server — OPEN"

**Status: CORRECT**

---

## Summary of Documentation Gaps

| Document | Gap | Severity |
|---|---|---|
| refresh_coverage_model.md | States Yahoo badge = FRESH_PARTIAL — incorrect | HIGH |
| provider_status_api_update.md | Header says FRESH_PARTIAL for Yahoo, then immediately corrects in notes — contradictory | MEDIUM |
| refresh_ui_validation.md | Correct — no gap | None |
| freshness_badge_logic_update.md | Correct — no gap | None |
| si_refresh_02_certification.md | Correct — no gap | None |

## Root Cause of Documentation Gap

The documentation was written during implementation planning when the governance decision (whether eps_growth_5yr should be primary or supplemental) was still open. The final implementation correctly placed it as supplemental. `refresh_coverage_model.md` and the header of `provider_status_api_update.md` were not updated to reflect the final decision.

The code and the certification are correct. Two planning documents contain stale text from a pre-decision state.
