# Portfolio Alignment — UX Backlog Candidates

Repository: security-intelligence-hub  
Audit Date: 2026-06-09

## Issues Ranked by Operator Impact × Implementation Complexity

### CRITICAL / S-M Complexity

#### UX-PA-01: Rename "Legacy Alignment" to "Allocation Alignment"

**Problem:** "Legacy Alignment 41%" is the most visible KPI on the page. The word "Legacy" implies the metric is outdated or superseded.  
**Fix:** Rename to "Allocation Alignment" or "Strategic Alignment" (S complexity — label change only)  
**Impact:** High — affects operator confidence in every session  
**Complexity:** S  
**Priority:** P0

#### UX-PA-02: Reconciliation FAIL Explainability

**Problem:** "FAIL (11/13 checks PASS)" appears without explanation of which check failed, why, and whether it affects the analysis.  
**Fix:** Add a collapsible "What failed and does it matter?" section with human-readable check names and severity guidance  
**Impact:** High — undermines trust in the entire analysis  
**Complexity:** S-M  
**Priority:** P0

#### UX-PA-03: Reorder Page — PAP and CRA before Security Intelligence Overlay

**Problem:** The Security Intelligence Overlay (81-row table) appears before the CRA and PAP, which are the primary execution surfaces. Operator must scroll past 81 rows to reach actionable guidance.  
**Fix:** Move Security Intelligence Overlay to a collapsible section below PAP, or move PAP/CRA above it.  
**Impact:** High — affects every session; operators miss action surfaces  
**Complexity:** S (HTML reorder)  
**Priority:** P0

---

### HIGH / S-M Complexity

#### UX-PA-04: Multi-Dimensional Scores Need Action Links

**Problem:** 4 scores (Allocation Alignment, Portfolio Quality, Implementation Quality, Replay Alignment) are shown with no action path. "Portfolio Quality 23/100 — what do I do?"  
**Fix:** Add a small tooltip/link per score to the relevant section. Example: "Portfolio Quality → see Deployment Queue" or "Replay Alignment → see Replay Alignment section"  
**Impact:** High — converts 4 confusing gauges into navigation aids  
**Complexity:** S  
**Priority:** P1

#### UX-PA-05: Allocation Map — Show Top 3 Overweight Nodes First

**Problem:** 40-node allocation map overwhelms with detail. Operator needs to see the 3 most actionable drift items immediately.  
**Fix:** Add a "Top Drift" summary row above the full table (or a pinned top-N view)  
**Impact:** High — reduces drift-to-action latency  
**Complexity:** S  
**Priority:** P1

#### UX-PA-06: BLOCKED Actions Must Show "What Would Unblock"

**Problem:** 3 recommendations show BLOCKED_BY_POLICY state. Operator sees "BLOCKED" but doesn't know that revoking DO_NOT_SELL on TSLA would unblock it.  
**Fix:** Add a "To unblock: revoke policy for [SYMBOL]" callout inside the blocked action card  
**Impact:** Medium-High — operator may leave policy in place unknowingly  
**Complexity:** S  
**Priority:** P1

#### UX-PA-07: Deployed Cash Context Explanation

**Problem:** KPI shows $21,711 deployable cash (4.67% excess) but nowhere explains why the cash is elevated or what the mandate floor means.  
**Fix:** Add a tooltip or inline note: "Excess above 7% mandate floor. Full cash: $54,257."  
**Impact:** High — operators asked "where did the $21K come from?" in portfolio review  
**Complexity:** S  
**Priority:** P1

---

### MEDIUM / M Complexity

#### UX-PA-08: Rename "Intentional Asymmetry" to Operator-Facing Language

**Problem:** "Intentional Asymmetry: HIGH_CONVICTION_ASYMMETRY 87%" sounds like a risk alert. It is actually a positive governance signal.  
**Fix:** Rename to "Mandate Conviction Assessment: HIGH_CONVICTION (87%)" or "Portfolio Philosophy Alignment: Strong"  
**Impact:** Medium — affects first-impressions in investor/bank demos  
**Complexity:** S-M (label + tooltip change)  
**Priority:** P2

#### UX-PA-09: INCREASE + REDUCE Simultaneously — Add Explanation

**Problem:** "Build US Large (-6.2%)" and "Reduce International (+6.1%)" appear in the same recommendations list. First-time operators think this is contradictory.  
**Fix:** Add a brief note at the top of the Actions lane: "Actions target different allocation sleeves and are independently evaluated."  
**Impact:** Medium — demo scenario issue  
**Complexity:** S  
**Priority:** P2

#### UX-PA-10: Phase Labels Must Not Appear in UI Text

**Problem:** "Phase 7.3B", "Phase C", "Phase 23.5" appear in block diagnostic and optimizer panel text. These are developer-internal labels.  
**Fix:** Audit all visible strings and replace phase references with operator-facing descriptions  
**Impact:** Medium — credibility/trust issue in demos  
**Complexity:** S (string search + replace)  
**Priority:** P2

---

### LOWER PRIORITY / L Complexity

#### UX-PA-11: Mandate Label Plain-Language Alias

**Problem:** "CONCENTRATED_ALPHA" is a valid investment term but unintuitive for non-portfolio clients.  
**Fix:** Add display alias: "Concentrated Alpha (High Conviction Growth)"  
**Complexity:** S  
**Priority:** P3

#### UX-PA-12: Replay Alignment Score Plain-English Threshold

**Problem:** 58/100 is unclear without context.  
**Fix:** Add threshold context: "58/100 · Target: 70+ for strong conviction"  
**Complexity:** S  
**Priority:** P3

#### UX-PA-13: Dislocation Watchlist Discoverability

**Problem:** Watchlist panel is hidden when no events exist. Operators do not know it exists.  
**Fix:** Show a subtle "No active dislocations" placeholder when the section would otherwise be hidden  
**Complexity:** S  
**Priority:** P3

---

## Backlog Summary

| ID | Title | Priority | Complexity |
|---|---|---|---|
| UX-PA-01 | Rename "Legacy Alignment" | P0 | S |
| UX-PA-02 | Reconciliation FAIL explainability | P0 | S-M |
| UX-PA-03 | Move PAP/CRA before Security Overlay | P0 | S |
| UX-PA-04 | Multi-Dim score action links | P1 | S |
| UX-PA-05 | Allocation Map Top-3 summary | P1 | S |
| UX-PA-06 | BLOCKED action "what would unblock" | P1 | S |
| UX-PA-07 | Deployable cash explanation | P1 | S |
| UX-PA-08 | Rename "Intentional Asymmetry" | P2 | S-M |
| UX-PA-09 | INCREASE+REDUCE coexistence note | P2 | S |
| UX-PA-10 | Remove Phase labels from UI | P2 | S |
| UX-PA-11 | Mandate plain-language alias | P3 | S |
| UX-PA-12 | Replay score threshold context | P3 | S |
| UX-PA-13 | Dislocation watchlist placeholder | P3 | S |
