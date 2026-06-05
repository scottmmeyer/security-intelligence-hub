# Recommendation Rationale Design — Phase 8.0B.X.3

## Objective

Design a "Why SIH Likes It" section that explains to an operator why a specific symbol appears in the deployment queue, using only existing data fields — no new scoring, no new calculations.

## Data Sources Available (all in-scope)

All fields are present in `_dqRenderTableRows()` scope at render time:

| Field | Source | Usage |
|-------|--------|-------|
| `c.rank` | Queue entry | CW-DAS rank position |
| `c.deployment_score` | Queue entry | Overall CW-DAS score |
| `ucf.ucf_label` | UCF verdict | Conviction tier label |
| `ucf.ucf_rank` | UCF verdict | Universe rank |
| `ov.ess_score_text` | Security overlay | ESS signal direction |
| `ov.replay_supported` | Security overlay | Replay backing |
| `ov.replay_percentile` | Security overlay | Replay strength |
| `ov.danelfin_score` | Security overlay | Danelfin AI score |
| `ov.zacks_rating` | Security overlay | Zacks rating |
| `bd.redundancy_pen` | Score breakdown | Redundancy pressure |
| `bd.conc_pen` | Score breakdown | Concentration pressure |
| `c.trim_score` | Queue entry | Trim pressure |
| `c.replay_supported` | Queue entry | Replay backing flag |
| `dp` (deployment plan row) | Deployment plan | Actionability |
| `ov.signal_direction` | Security overlay | Signal direction |
| `ov.opportunity_flag` | Security overlay | Opportunity flag |
| `ov.effective_action` | Security overlay | Recommended action |

## Bullet Generation Logic

Each bullet point maps to a specific data condition. Maximum 5 bullets shown.

### Bullet Pool (evaluated in priority order)

| Priority | Condition | Bullet Text |
|----------|-----------|-------------|
| 1 | `c.rank === 1` | `#1 CW-DAS deployment priority` |
| 1 | `c.rank <= 3` | `Top-3 CW-DAS deployment candidate` |
| 2 | `ucf_label` matches `CORE_CONVICTION` or `LEADER` | `Core Conviction Leader` |
| 2 | `ucf_label` matches `HIGH_CONVICTION` | `High Conviction Anchor` |
| 2 | `ucf_label` matches `STRONG_MOMENTUM` | `Strong Momentum signal` |
| 3 | `ess_score_text` contains `VERY_BULLISH` or `STRONG_BULLISH` | `Very Bullish ESS signal` |
| 3 | `ess_score_text` contains `BULLISH` | `Bullish ESS signal` |
| 4 | `replay_supported === true` AND `replay_percentile >= 80` | `Elite replay backing (${pctile}th percentile)` |
| 4 | `replay_supported === true` AND `replay_percentile >= 60` | `Replay-backed thesis (${pctile}th percentile)` |
| 4 | `replay_supported === true` | `Replay-backed thesis` |
| 5 | `danelfin_score >= 4.5` | `Strong AI signal (Danelfin ${score})` |
| 6 | `zacks_rating <= 1.5` | `Zacks Strong Buy rating` |
| 6 | `zacks_rating <= 2.5` | `Zacks Buy rating` |
| 7 | `bd.redundancy_pen === 0 && bd.conc_pen === 0` | `No concentration conflicts` |
| 7 | `bd.redundancy_pen > 0` | `(no positive bullet — omit)` |
| 8 | `trim_score <= 20` | `Low trim pressure` |
| 8 | `trim_score > 50` | `(omit — trim concern is a negative)` |
| 9 | `dp && dp.suggested_add > 0` | `Actionable — new capital can deploy` |
| 9 | `ov.opportunity_flag === true` | `Flagged as opportunity` |

## Sentence Construction Rules

- Plain English, present tense
- No exclamation points
- No "strong buy" recommendations
- No score percentages unless meaningful (e.g., replay percentile)
- Capitalized, no period at end of bullet
- Maximum 60 characters per bullet

## Empty State

If fewer than 2 bullets can be generated, do not show the section.
This prevents near-empty sections for edge cases (ETFs, funds, cash positions).

## Section Placement

Directly below "Why It Matters" in the Company Snapshot card.
Uses the same `.dq-company-snapshot` container — adds a visual divider row inside the grid.
