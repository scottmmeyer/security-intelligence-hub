# ISSUE-05 — UI Validation Report

**Date:** June 5, 2026

---

## Q1: Can operators isolate INTACT opportunities?

**Status:** ✅ YES

Uncheck QUESTIONABLE and DETERIORATING in the Thesis dropdown. Only candidates with `thesis_integrity = "INTACT"` remain visible. Candidates with empty thesis (pre-ISSUE-05 artifacts or insufficient FMP data) pass through.

## Q2: Can operators isolate DETERIORATING opportunities?

**Status:** ✅ YES

Uncheck INTACT and QUESTIONABLE in the Thesis dropdown. Candidates with `thesis_integrity = "DETERIORATING"` remain — useful for identifying names where the fundamental modifier is applying a significant penalty.

## Q3: Can operators isolate negative modifier names?

**Status:** ✅ YES

Select "Negative (<0)" in the Modifier dropdown. In the test queue (32 candidates): 6 candidates have negative modifier. All 6 are visible when this filter is active. The Modifier badge activates (accent color) to indicate the filter is non-default.

## Q4: Can operators combine filters?

**Status:** ✅ YES

Example: Thesis=INTACT only + Consistency=CONSISTENT only + Modifier=POSITIVE.
- All three filter buttons show active (accent) badges simultaneously.
- Filtered count badge shows "X of 32" reflecting the intersection.
- Table re-renders instantly for each change.

## Q5: Do filtered results preserve rank ordering?

**Status:** ✅ YES

Validated: rank sequence from filtered results is `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` (ascending, as expected). Filtering only controls row visibility — the underlying `rank` field on each candidate is never modified.

---

## Filter Controls Validated

| Control | Element ID | State | Result |
|---------|-----------|-------|--------|
| Thesis button | `dq-fb-thesis` | Renders "Thesis ▾" | ✅ |
| Consistency button | `dq-fb-consistency` | Renders "Consistency ▾" | ✅ |
| Modifier button | `dq-fb-modifier` | Renders "Modifier ▾" | ✅ |
| Thesis checkboxes | 3 in `dq-fp-thesis` | All checked by default | ✅ |
| Consistency checkboxes | 4 in `dq-fp-consistency` | All checked by default | ✅ |
| Modifier radios | 4 in `dq-fp-modifier` | "All" selected by default | ✅ |
| Active badge (filtering) | `.dq-filter-active` | Appears on active filters | ✅ |
| Filtered count | `dq-filtered-count` | Shows "X of Y" when filtering | ✅ |
| Panel close on outside click | document listener | Closes panels | ✅ |

---

## No Regressions

- CW-DAS scores unchanged
- Deployment recommendations unchanged
- View-all toggle still works after filtering
- Reset to All restores full 10-row default view
