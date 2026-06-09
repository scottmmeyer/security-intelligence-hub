# SI-REFRESH-02 Final Verdict

Repository: security-intelligence-hub  
Audit Date: 2026-06-09

## Q1: What badge_state is actually produced for Yahoo today?

**badge_state = FRESH**

Evidence: Yahoo primary fields (price_target 98.1%, analyst_count 98.1%, current_price 99.9%) are all above 0%. Coverage is 99.9% (above 95% threshold). No FRESH_PARTIAL trigger is met.

The `eps_growth_5yr` 0% gap is surfaced as a `pill-degraded-advisory` advisory tag in the UI, not as a FRESH_PARTIAL badge change.

---

## Q2: Is eps_growth_5yr treated as primary or supplemental?

**Supplemental.** It appears in `_ALL_SCORE_FIELDS["yahoo"]` but not in `_PRIMARY_FIELDS["yahoo"]`.

Yahoo primary fields are: `price_target`, `analyst_count`, `current_price`.

---

## Q3: Does 0% coverage of eps_growth_5yr produce FRESH or FRESH_PARTIAL?

**FRESH** — with an advisory note. Not FRESH_PARTIAL.

The FRESH badge with advisory "0% today: eps_growth_5yr" is the correct and designed behavior. The operator sees the gap; the badge color remains green.

---

## Q4: Which documentation artifact is incorrect?

Two artifacts contain incorrect statements:

1. **refresh_coverage_model.md** — states Yahoo badge_state = FRESH_PARTIAL. Incorrect.
2. **provider_status_api_update.md** — header states "badge_state = FRESH_PARTIAL for Yahoo." Incorrect. The implementation note within the same document correctly describes actual behavior.

The certification (si_refresh_02_certification.md) and the UI validation (refresh_ui_validation.md) are correct.

---

## Q5: Is there an implementation defect, or only documentation drift?

**Documentation drift only. No implementation defect.**

The code in `scripts/run_outcome_ui.py` and `ui/outcome_visualization/app.js` is correct and internally consistent. The badge logic, primary field definitions, and advisory rendering all behave as the certification describes.

The documentation gap arose because two planning documents were not updated to reflect the final governance decision to classify `eps_growth_5yr` as supplemental rather than primary.

---

## Q6: Is a new provider refresh required?

**No.** This is a verification audit of SI-REFRESH-02's implementation, not a signal freshness concern. No signal refresh is needed to validate the code logic. The live signal files confirm expected behavior on 2026-06-09.

---

## Q7: Exact Documentation Corrections Required

### refresh_coverage_model.md — "Today's State" table

Current (incorrect):
```
Yahoo | 697 | 696 | 99.9% | ... | FRESH_PARTIAL (eps_growth_5yr: 0%)
```

Correct:
```
Yahoo | 697 | 696 | 99.9% | price_target: 98.1%, analyst_count: 98.1%, current_price: 99.9% | FRESH (eps_growth_5yr in advisory: zero_coverage_fields)
```

### provider_status_api_update.md — first paragraph under "Notes"

Current (incorrect):
> "badge_state = FRESH_PARTIAL for Yahoo is triggered because eps_growth_5yr is in zero_coverage_fields"

Correct:
> "Yahoo badge_state = FRESH. eps_growth_5yr is a supplemental (non-primary) field and does not trigger FRESH_PARTIAL. It appears in zero_coverage_fields and surfaces as an advisory tag in the UI."

No other documentation changes required.

---

## Final Disposition

| Item | Status |
|---|---|
| Implementation correctness | VERIFIED — no defects |
| Badge logic for Yahoo today | CORRECT — badge_state=FRESH with eps_growth_5yr advisory |
| Documentation accuracy | TWO documents require correction (see Q7) |
| Code changes required | None |
| Provider refresh required | No |
| REFRESHING badge state (known open) | Still open; not a defect — documented in certification |
