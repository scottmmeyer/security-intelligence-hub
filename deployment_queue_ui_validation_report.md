# Deployment Queue UI Validation Report — Phase 7.5C

**Date**: 2025-07-14  
**Phase**: 7.5C — Capital Deployment Queue Primary Operator Surface  
**Queue version**: CW-DAS-1.0  
**Test baseline**: 613/613 tests pass (no regressions)

---

## Summary

Phase 7.5C promotes the Capital Deployment Queue to the **primary operator action surface** in the Portfolio Alignment UI. The queue is inserted between the Portfolio Mandate Assessment panel and the Allocation Map / Concentration rows. No scoring, optimizer, STI, or recommendation logic was modified.

---

## Validation Criteria

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Queue renders from `deployment_queue.json` in API response | ✅ PASS | `renderDeploymentQueue(data)` reads `data.deployment_queue.queue`; present in runner return since Phase 7.5B |
| 2 | AEIS appears at rank #1 | ✅ PASS | `deployment_queue.json`: `#1 AEIS DAS=95.56 tier=CORE_CONVICTION_LEADER replay=True` |
| 3 | VRT appears at rank #2 | ✅ PASS | `deployment_queue.json`: `#2 VRT DAS=95.53 tier=CORE_CONVICTION_LEADER replay=True` |
| 4 | Top-10 table ordering matches persisted artifact | ✅ PASS | UI table renders `queue.slice(0, 10)`; array is pre-sorted by CW-DAS descending in `build_deployment_queue()` |
| 5 | Deployable cash matches artifact ($33,175) | ✅ PASS | `cash_context.deployable_mv = $33,175.19`; summary card uses `formatMV()` → "$33.2K" display |
| 6 | Prioritized Recommendations remain unchanged | ✅ PASS | `renderRecommendations()` unchanged except for section separator prepend; no rec logic touched |
| 7 | No API contract breaks | ✅ PASS | No changes to runner API surface; `deployment_queue` key already present in Phase 7.5B return dict |
| 8 | Existing optimizer UI remains functional | ✅ PASS | All optimizer render functions (`renderOptimizerSummary`, `_buildOptimizerBadges`, `_buildOptimizerViewBlock`) untouched |

---

## UI Components Added

### 1. Capital Deployment Queue Section (`#deploymentQueueContainer`)

- **Position**: Between `#mandatePanelContainer` and the allocation/concentration two-col row
- **Panel accent**: Top border in `var(--accent)` (#0d5c63), consistent with existing panel hierarchy
- **Advisory note**: "Guidance only — not a trade instruction" in muted italic

### 2. Summary Strip (5 KPI cards)

| Card | Value | Source |
|------|-------|--------|
| Deployable Cash | $33.2K | `cash_context.deployable_mv` |
| Eligible Candidates | 43 | `candidate_count` |
| Queue Version | CW-DAS-1.0 | `queue_version` |
| Top Candidate | AEIS | `queue[0].symbol` |
| Top Score | 95.6 | `queue[0].deployment_score` |

### 3. Top-10 Deployment Table

Columns: Rank | Symbol | CW-DAS | Tier | Weight | Composite | Replay | Trim ▲ | Status

- **Tier badges**: CCL = green (#d4edda/#155724), HCA = blue (#cce5ff/#004085)
- **Replay**: YES = green bold, NO = muted
- **Status**: DEPLOYABLE (green) | OW NODE (amber) | BLOCKED (red)
- **Click any row** to expand per-row CW-DAS breakdown (7 component cards: Signal /30, Replay /20, Conviction /35, Sizing /8, Momentum /10, Redundancy Pen, Conc Pen)
- **Rank #1 row** has a subtle green gradient highlight
- "View all 43 candidates" toggle reveals full queue

### 4. Blocked Conviction Opportunities (collapsible)

Filtered as: candidates where `score_breakdown.redundancy_pen > 0` or `score_breakdown.conc_pen > 0`.

For the PAR-20260529 run, blocked candidates include holdings in overweight nodes (EQUITIES.INTERNATIONAL, EQUITIES.US.MEGA.HYPER_MEGA): **MU, NVDA, TSM, CVE**.

Panel shows: Symbol | Tier | Score (pre-penalty context) | Penalty | Reason (from notes field)

### 5. Section Separator — "Allocation & Portfolio Observations"

Prepended inside `#recommendationsContent` before the recommendations list. Styled as a small-caps uppercase divider consistent with the existing UI vocabulary.

---

## Files Modified

| File | Change |
|------|--------|
| `ui/portfolio_alignment/index.html` | Added Phase 7.5C CSS block (~155 lines); added `#deploymentQueueContainer` div; bumped `?v=3` → `?v=4` |
| `ui/portfolio_alignment/app.js` | Added `renderDeploymentQueue()`, `_dqRenderTableRows()`, `_dqToggleBreakdown()`, `_dqToggleViewAll()`, `_dqToggleBlocked()`, 5 helper functions; wired into `renderResults()`; added separator in `renderRecommendations()` |

---

## No-Touch Confirmation

The following were **not modified**:

- `src/portfolio/deployment_queue.py` — backend scoring unchanged
- `src/portfolio/runner.py` — no changes
- `src/portfolio/optimizer.py` — no changes
- `src/portfolio/strategic_tier.py` — no changes
- Any test file
- Any config or data file
- Recommendation engine or STI logic

---

## Test Results

```
613 passed, 50 warnings in 26.67s
```

All 613 tests pass including Phase 7.5B acceptance criteria (TestPARAcceptanceCriteria: AEIS #1, VRT #2, ARW #3).
