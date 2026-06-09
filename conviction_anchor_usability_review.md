# Conviction Anchor Usability Review

Repository: security-intelligence-hub  
Date: 2026-06-09  
Scope: Post-PRA-IMPL-03 Phase 3 assessment

## Q1 — Is a List of 25 Conviction Anchors Excessive?

Yes. 25 items in a single section, even collapsed by default, creates a wall of content when expanded.

An operator typically reviews conviction anchors to answer one question: "Which positions am I most confident in, and why?" This question is answered by the top 5–8 holdings, not by 25 entries including tactical growth candidates and watchlist items.

The current set of 25 includes:
- 20 CONVICTION_EXPLAINABILITY_CARDs (full per-holding conviction cards for all ranked holdings)
- 3 STRATEGIC_RETAIN_NARRATIVEs (MU, VRT, CVE)
- 2 STRATEGIC_RETAIN_SIGNALs (DELL, MSFT)

The 20 explainability cards are particularly verbose and most relevant when an operator wants to understand why a specific holding is classified — not as a list to scroll through.

## Q2 — Would a Top Conviction Anchors Subsection Improve Usability?

Yes. A strong pattern would be:

**Top Conviction Anchors** (always visible, ~5 entries)
- CORE_CONVICTION_LEADER tier only
- Ranked by combined signal + replay + portfolio weight

**Full Conviction Registry** (collapsed by default, all 25 entries)
- Full explainability cards
- Accessible on demand

This separation answers the primary operator question immediately while preserving full depth.

## Q3 — Optimal Anchor Ranking Criteria

Recommended ranking approach (composite):

1. **Primary:** conviction tier (CCL > HCA > TGC > WTC)
2. **Secondary within tier:** composite score descending
3. **Tertiary:** replay evidence (replay_supported = True ranked first)
4. **Quaternary:** portfolio weight descending

Rationale:
- Tier ordering reflects the full multi-factor conviction model — it is already the authoritative rank
- Composite score breaks ties within tier cleanly
- Replay evidence distinguishes confirmed vs unconfirmed conviction
- Portfolio weight ensures large positions get appropriate visibility

Alternative (simpler): Sort only by composite score. This is the current deployment queue order and is immediately intuitive.

## Q4 — Optimal Default Display Count

**5 anchors visible by default** — then "Show all 25" link.

Evidence:
- 5 fits above the fold on most screen sizes without scrolling
- 5 covers all CORE_CONVICTION_LEADERs (current run: MU, VRT, CVE, GTX, AEIS approximately)
- 5 is the standard "top of mind" working set in portfolio management contexts
- A "Show all" pattern is widely understood and adds zero cognitive load

## Summary Recommendation

| Finding | Recommendation |
|---|---|
| 25 anchors in a flat list | Excessive for default view |
| Top Conviction Anchors subsection | Yes — implement with CCL tier filter |
| Ranking criteria | Tier → composite score → replay → weight |
| Default display count | 5 (with "Show all" expansion) |
| Full conviction registry | Retain as collapsed deep-dive |
| Appropriate for new backlog issue? | Yes — PRA-IMPL-06 |
