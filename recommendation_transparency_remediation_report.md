# Recommendation Transparency Remediation Report
**Phase:** 22D.2 — Workstream C  
**Reference Date:** 2026-06-01  
**Status:** COMPLETE  

---

## Finding Addressed

**Phase 22D.1 Finding:** Recommendation cards for `INCREASE_UNDERWEIGHT`
recommendations with `optimizer_decision=NO_CANDIDATES` or `MANDATE_BLOCKED`
displayed prescriptive vehicle language ("Add via ETF exposure…") in the rationale
without any visible indication that the recommended action is currently blocked.
The only block-related information was buried in: (a) the `optimizer-badge-row`
(small badge, below meta), and (b) the hidden collapsible "Optimizer View" panel.

Neither location was sufficient for an advisor scanning recommendation cards
quickly — the top-of-card rationale created a false impression of actionability.

---

## Changes Made

### `ui/portfolio_alignment/app.js` — `renderRecommendations()`

Added blocked banner logic before the card template return:

```javascript
let blockedWarningHtml = "";
if (recType === "INCREASE_UNDERWEIGHT" && r.optimizer_metadata) {
  const decision = r.optimizer_metadata.optimizer_decision || "";
  if (decision === "NO_CANDIDATES" || decision === "MANDATE_BLOCKED") {
    const isMandate = decision === "MANDATE_BLOCKED";
    const bannerLabel = isMandate ? "Mandate Blocked" : "No Actionable Path";
    const bannerMsg   = isMandate
      ? "This increase is blocked by the active portfolio mandate. No deployment action is currently available."
      : "All implementation vehicles failed optimizer gates. No actionable implementation path is available.";
    const bannerMod   = isMandate ? " rec-blocked-banner-mandate" : "";
    blockedWarningHtml = `<div class="rec-blocked-banner${bannerMod}">
      <span class="rec-blocked-banner-label">⚑ ${escHtml(bannerLabel)}</span>
      <span>${escHtml(bannerMsg)}</span>
    </div>`;
  }
}
```

`${blockedWarningHtml}` is inserted in the card template immediately after
`<div class="rec-rationale">` — always visible, non-collapsible.

### `ui/portfolio_alignment/index.html` — `<style>` block

Added CSS classes:

```css
.rec-blocked-banner {
  display: flex; align-items: flex-start; gap: 8px;
  margin: 6px 0 8px; padding: 8px 12px;
  background: #fff3cd; border-left: 4px solid #e6a817; border-radius: 3px;
  font-size: 0.83rem; color: #7a5800; line-height: 1.4;
}
.rec-blocked-banner-label {
  font-weight: 800; text-transform: uppercase;
  letter-spacing: 0.05em; white-space: nowrap;
}
.rec-blocked-banner-mandate { border-left-color: #c0392b; background: #fdecea; color: #7b1e1e; }
```

- `NO_CANDIDATES` — amber/yellow warning palette (consistent with WARNING-tier alerts)
- `MANDATE_BLOCKED` — red palette (visually distinct, signals harder constraint)

---

## Acceptance Criteria Verification

| ID | Criterion | Result |
|----|-----------|--------|
| AC-C1 | Blocked banner visible (non-collapsible) in main card body | PASS — inserted after rationale, always rendered |
| AC-C2 | Banner appears only for INCREASE_UNDERWEIGHT + blocked optimizer_decision | PASS — type and decision guards in place |
| AC-C3 | Existing optimizer badges and Optimizer View panel unchanged | PASS — no modifications to `_buildOptimizerBadges()` or `_buildOptimizerViewBlock()` |
| AC-C4 | No change to recommendation generation logic | PASS — UI-only change; no Python files touched in this workstream |

---

## Design Notes

- The recommendation `title` and `rationale` text are intentionally not changed. The banner adds transparency on top of existing rationale without altering recommendation logic.
- `escHtml()` is applied to all user-visible string values from `optimizer_metadata` to guard against injection.
- The banner is absent for non-INCREASE_UNDERWEIGHT recommendation types and for INCREASE_UNDERWEIGHT records where `optimizer_decision` is `SECURITY_SUPERIOR`, `ETF_ADEQUATE`, or any other non-blocked value.
