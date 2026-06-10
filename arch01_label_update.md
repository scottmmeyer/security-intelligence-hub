# ARCH-01: Label Update

**Date:** 2026-06-09  
**Status:** COMPLETE

---

## Change

| Before | After |
|---|---|
| "Recommended Actions — Top 10" | "Deployment Candidates — Top 10" |

**File changed:** `ui/portfolio_alignment/app.js`  
**Location:** `_daRenderActionCards()` function, `da-action-section-header` div (line 3867 pre-change)

---

## Rationale

The existing label "Recommended Actions — Top 10" implied a comprehensive portfolio action priority view. The CRA-POOL-AUDIT confirmed this surface is structurally limited to buy-side (CW-DAS) candidates only. TRIM, SELL, REDUCE, and ROTATE actions cannot appear there under any code path.

"Deployment Candidates" accurately describes the surface: it shows the ranked list of holdings eligible for capital deployment (purchase), ordered by the Conviction-Weighted DAS score.

---

## Scope

- 1 string change in app.js
- No logic changes
- No data changes
- No scoring changes
- No test changes required (label is UI-only, not in any test assertions)

---

## No Other Label References

Searched for all occurrences of "Recommended Actions" and "Top 10" in app.js and index.html. Only one UI-facing instance existed (the `da-action-section-header` div). The `top10_pct` concentration stat references a different "Top 10" (top-10 position concentration), not this action surface.
