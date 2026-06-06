# ISSUE-10 — Governance Validation Report

**Date:** June 5, 2026

---

## Governance Principle

Analyst target information is **display-only**. It provides context for
operator interpretation. It does not influence any scoring, ranking, or
recommendation system.

Reference: CII-005 Final Recommendation — Q5 ("No, for all five systems").

---

## Scoring Systems — Verified Unchanged

### Composite Score
- Composite score is derived from ESS, Danelfin, Zacks, and ABR weights
- `_dqAnalystTargetHtml()` is a pure rendering function; it reads `ac` (analyst consensus dict) but writes only to the DOM
- No composite score computation touches this function
- **Verdict: UNCHANGED ✅**

### Fundamental Modifier
- Modifier uses `beat_rate`, `thesis_integrity`, `fundamental_consistency` from FMP data
- `_dqAnalystTargetHtml()` does not read or pass any value to `compute_fundamental_modifier()`
- **Verdict: UNCHANGED ✅**

### CW-DAS Score
- `CW_DAS_VERSION = "1.1"` — unchanged
- `compute_cw_das()` signature and logic unchanged
- No new field was added to `CwDasBreakdown`
- `deployment_queue.py` was not modified in this issue
- **Verdict: UNCHANGED ✅**

### Deployment Queue Ranking
- Queue rank is assigned in `build_deployment_queue()` after `compute_cw_das()` sorting
- `_dqAnalystTargetHtml()` is called after the queue is fully sorted and assigned
- Rank values in the rendered table rows are identical before and after ISSUE-10
- **Verified in browser:** rank sequence `[#1, #2, #3, ...]` unchanged
- **Verdict: UNCHANGED ✅**

### Capital Rotation Advisor (CRA)
- CRA reads `deployment_queue.json` and `security_overlays.csv`
- Neither file was modified
- `_craProposal` logic unchanged
- **Verdict: UNCHANGED ✅**

---

## Governance Requirements — Status

| Requirement | Status |
|-------------|--------|
| ✓ Provides context | ✅ Price target + upside + sourced date visible |
| ✓ Improves transparency | ✅ Layer 1 ABR now has magnitude context |
| ✓ Remains visually separate from scoring | ✅ Distinct block with separate CSS; not inside `dq-breakdown-grid` |
| ✓ Never influences rankings | ✅ Pure rendering function; no ranking input |
| ✗ Must NOT influence Composite Score | ✅ Confirmed no influence |
| ✗ Must NOT influence Fundamental Modifier | ✅ Confirmed no influence |
| ✗ Must NOT influence CW-DAS | ✅ Confirmed no influence |
| ✗ Must NOT influence CRA | ✅ Confirmed no influence |
| ✗ Must NOT influence Deployment Queue ordering | ✅ Confirmed no influence |

---

## Advisory Requirement — Met

The governance advisory is **mandatory** per CII-005 specification. Verified text:

> ⚠ Guidance only — analyst targets are opinions, not price forecasts. Do not use as trade triggers.

This text:
- Is embedded in every rendered ATI block (not a tooltip or footnote)
- Cannot be dismissed or hidden by operator
- Is styled as `font-style: italic` in a border-separated sub-row

---

## Field Suppression — Verified

The following fields are suppressed per CII-005:

| Field | In yfinance? | In CSV? | Displayed? |
|-------|------------|---------|-----------|
| `targetHighPrice` | ✅ (DELL: $700) | ❌ not fetched | ❌ NOT shown |
| `targetLowPrice` | ✅ (DELL: $213) | ❌ not fetched | ❌ NOT shown |
| `targetMedianPrice` | ✅ (DELL: $500) | ❌ not fetched | ❌ NOT shown |
| `averageAnalystRating` text | ✅ ("1.8 - Buy") | ❌ not fetched | ❌ NOT shown |
| Raw Yahoo field names | N/A | N/A | ❌ NOT shown |

---

## CII Philosophy — Not Weakened

CII v1.1 Layer model remains:

| Layer | Change |
|-------|--------|
| Layer 1 (Consensus) | Strengthened — ABR direction now has price magnitude context |
| Layer 2 (Fundamental Validation) | Unchanged |
| Layer 3 (Historical Validation) | Unchanged |
| Layer 4 (Portfolio Discipline) | Unchanged |

CII version remains **v1.1**. The version label change to CII v1.2 is not warranted for a display-only transparency addition.
