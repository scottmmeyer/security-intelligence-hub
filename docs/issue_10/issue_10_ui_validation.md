# ISSUE-10 — UI Validation Report

**Date:** June 5, 2026

---

## Test Environment

- Run: `PAR-20260605-BC438F9E`
- Symbol expanded: DELL (rank #1)
- `app.js`: v24
- `index.html`: v24

---

## Validation Matrix

| Criterion | Expected | Actual | Status |
|-----------|----------|--------|--------|
| Block renders | `.dq-analyst-target-block` present after row click | Present | ✅ |
| Header | "Analyst Target Intelligence" (uppercase via CSS) | Confirmed | ✅ |
| Target field | "$483.83" (DELL consensus mean) | "$483.83" | ✅ |
| Upside field | "+20.6%" (DELL June 5) | "+20.6%" | ✅ |
| Positive upside styling | `.dq-ati-positive` class (green) | Applied | ✅ |
| Negative upside styling | `.dq-ati-negative` class (red) | Applied on synthetic test | ✅ |
| Analyst count: null → hidden | No "Coverage" row when `analyst_count = null` | Hidden | ✅ |
| Analyst count: 23 → visible | "Coverage: 23 analysts" row appears | Confirmed in synthetic test | ✅ |
| Advisory text | "⚠ Guidance only — analyst targets are opinions, not price forecasts. Do not use as trade triggers." | Exact match | ✅ |
| Sourced date | "2026-06-05" | "2026-06-05" | ✅ |
| Placement: after signal agreement | Block after `_signalAgreementPanelHtml` output | Confirmed | ✅ |
| Placement: before CW-DAS breakdown | `compareDocumentPosition()` = FOLLOWING | Confirmed | ✅ |
| null ac → no block | `_dqAnalystTargetHtml(null)` returns `""` | `""` returned | ✅ |
| Both fields null → no block | `{ price_target: null, upside_pct: null }` returns `""` | `""` returned | ✅ |
| No console errors | 0 JS errors on page load + row expand | 0 errors | ✅ |

---

## Positive Upside Rendering

Input: `{ price_target: 120.50, upside_pct: 15.3, analyst_count: null, refresh_date: '2026-06-05' }`

Rendered:
```
Target    Upside     Sourced
$120.50   +15.3%     2026-06-05
⚠ Guidance only — analyst targets are opinions, not price forecasts.
```
- Upside span has class `dq-ati-positive` → green color
- No "Coverage" row (analyst_count is null)

---

## Negative Upside Rendering

Input: `{ price_target: 90.00, upside_pct: -8.5, analyst_count: 23, refresh_date: '2026-06-05' }`

Rendered:
```
Target    Upside     Coverage       Sourced
$90.00    −8.5%      23 analysts    2026-06-05
⚠ Guidance only — analyst targets are opinions, not price forecasts.
```
- Upside span has class `dq-ati-negative` → red color
- "Coverage: 23 analysts" row visible

---

## Empty Block Behavior

| Input | Output |
|-------|--------|
| `null` | `""` (no HTML) |
| `{ price_target: null, upside_pct: null }` | `""` (no HTML) |
| `{ price_target: 120.50, upside_pct: null }` | Block renders with Target and Sourced; Upside shows "—" |

---

## No Regression on Existing Functionality

| Existing element | Status after ISSUE-10 |
|---|---|
| CW-DAS Score Breakdown | Still renders below ATI block ✅ |
| Signal Agreement Panel | Still renders above ATI block ✅ |
| ABR `dq-sig-card` | Still present in signal grid ✅ |
| Why SIH Likes It | Still renders at bottom ✅ |
| Company / Fundamental Snapshots | Still render ✅ |
| ISSUE-05 filters | Still function correctly ✅ |
