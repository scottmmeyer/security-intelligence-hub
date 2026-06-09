# PRA-IMPL-06 Ranking Methodology

Repository: security-intelligence-hub  
Date: 2026-06-09

## Anchor Ranking Criteria

Anchors are ranked using four criteria applied in priority order:

### Criterion 1: Conviction Tier (primary sort)

| Tier | Rank Value | Description |
|---|---|---|
| CORE_CONVICTION_LEADER | 0 (highest) | Portfolio foundation; full multi-factor conviction |
| HIGH_CONVICTION_ANCHOR | 1 | Strong conviction, below core |
| TACTICAL_GROWTH_CANDIDATE | 2 | Growth opportunity, active monitoring |
| WATCH_TRIM_CANDIDATE | 3 | Under surveillance |
| (none / unresolved) | 4 (lowest) | No tier assigned |

### Criterion 2: Composite Score (secondary, descending)

Higher composite score = higher conviction confidence = ranked higher.

Source: `security_overlays.csv` → `composite_score` field per symbol.

### Criterion 3: Replay Support (tertiary)

Replay-supported symbols (historical conviction evidence) ranked above non-replay symbols within the same tier and composite band.

Source: `security_overlays.csv` → `replay_supported` field.

### Criterion 4: Portfolio Weight (quaternary, descending)

Higher portfolio weight = more material position = ranked higher as tiebreaker.

Source: `security_overlays.csv` → `percent_of_portfolio` field.

## Deduplication Rule

Multiple cards for the same symbol (e.g., CONVICTION_EXPLAINABILITY_CARD + STRATEGIC_RETAIN_NARRATIVE for CVE) are collapsed to one entry for the Top 5 display. The CONVICTION_EXPLAINABILITY_CARD is preferred when available because it contains the most detailed rationale.

All cards are preserved in the Full Conviction Registry.

## Implementation in app.js

The ranking is implemented inside `buildConvictionAnchorLane()` in `renderRecommendations()`. It uses:
- `reasoning_trace` and `title` to detect tier labels
- `drilldown.holdings[0].composite_score` for composite
- `drilldown.holdings[].replay_supported` for replay
- `drilldown.holdings[].percent_of_portfolio` for weight

This uses data already present on every recommendation card with no new backend changes.
