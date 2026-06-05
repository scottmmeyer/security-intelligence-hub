# Recommendation Rationale Mapping — Phase 8.0B.X.3

## Field-to-Bullet Mapping (Implementation Reference)

This document provides the exact field paths, conditions, and bullet text for implementation in `_dqWhySIHLikesItHtml()`.

### Input Object Shape

```javascript
{
  c:    { rank, deployment_score, replay_supported, trim_score, notes },
  ucf:  { ucf_label, ucf_rank, ucf_score, signal_summary },
  ov:   { ess_score_text, danelfin_score, zacks_rating, replay_percentile,
           replay_supported, signal_direction, opportunity_flag, effective_action,
           percent_of_portfolio, is_overweight_vs_target },
  bd:   { signal, replay, conviction, sizing, momentum, redundancy_pen, conc_pen },
  dp:   { suggested_add, projected_weight_pct },  // may be null
  trim: <float>
}
```

### Bullet Derivation Table

| Bullet ID | Condition | Text |
|-----------|-----------|------|
| RANK_1 | `c.rank === 1` | `#1 CW-DAS deployment priority` |
| RANK_TOP3 | `c.rank <= 3 && c.rank > 1` | `Top-${c.rank} CW-DAS deployment candidate` |
| UCF_CORE | `ucf_label` contains `CORE` | `Core Conviction Leader` |
| UCF_HIGH | `ucf_label` contains `HIGH` | `High Conviction Anchor` |
| UCF_STRONG | `ucf_label` contains `STRONG` | `Strong signal conviction` |
| UCF_RANK | `ucf.ucf_rank <= 25` | `Top-25 universe conviction rank` |
| ESS_VERY | `ess` contains `VERY_BULLISH` | `Very Bullish ESS signal` |
| ESS_BULL | `ess` contains `BULLISH` (not VERY) | `Bullish ESS signal` |
| REPLAY_ELITE | `replay && percentile >= 80` | `Elite replay backing — ${pctile}th percentile` |
| REPLAY_STRONG | `replay && percentile >= 60` | `Replay-backed thesis — ${pctile}th percentile` |
| REPLAY_YES | `replay && percentile < 60` | `Replay-backed thesis` |
| DAN_STRONG | `danelfin_score >= 4.5` (normalized) | `Strong AI signal (Danelfin ${score})` |
| ZACKS_SB | `zacks_rating <= 1.5` | `Zacks Strong Buy rating` |
| ZACKS_BUY | `zacks_rating > 1.5 && <= 2.5` | `Zacks Buy rating` |
| NO_CONFLICT | `redundancy_pen === 0 && conc_pen === 0` | `No concentration conflicts` |
| LOW_TRIM | `trim <= 20` | `Low trim pressure` |
| ACTIONABLE | `dp.suggested_add > 0` | `Actionable — new capital can deploy` |
| UNDERWEIGHT | `ov.is_overweight_vs_target === false && ov.percent_of_portfolio < 3` | `Underweight vs. target — sizing opportunity` |

### Priority Ordering

Bullets are evaluated in this order and first 5 are displayed:
1. Rank bullets (RANK_1, RANK_TOP3)
2. UCF bullets (UCF_CORE, UCF_HIGH, UCF_STRONG, UCF_RANK)
3. ESS bullets (ESS_VERY, ESS_BULL)
4. Replay bullets (REPLAY_ELITE, REPLAY_STRONG, REPLAY_YES)
5. Signal quality (DAN_STRONG, ZACKS_SB, ZACKS_BUY)
6. No-conflict (NO_CONFLICT)
7. Sizing (LOW_TRIM, ACTIONABLE, UNDERWEIGHT)

### UCF Label Patterns (from live data)

Based on observed UCF labels in production:

| Raw Label | Contains Check | Assigned Tier |
|-----------|---------------|---------------|
| CORE_CONVICTION_LEADER | CORE | UCF_CORE |
| HIGH_CONVICTION_ANCHOR | HIGH | UCF_HIGH |
| STRONG_MOMENTUM | STRONG | UCF_STRONG |
| EMERGING_SIGNAL | (none of above) | no UCF bullet |
| WATCHLIST | (none of above) | no UCF bullet |

### ESS Score Text Patterns

| ESS Text | Bullet |
|----------|--------|
| VERY_BULLISH | ESS_VERY |
| STRONG_BULLISH | ESS_VERY |
| BULLISH | ESS_BULL |
| NEUTRAL, BEARISH | no bullet |

### Danelfin Score Interpretation

The `danelfin_score` field in overlays is a normalized 1–5 value.
Threshold for DAN_STRONG: `>= 4.5` (top of scale).

### Zacks Rating Interpretation

The `zacks_rating` field in overlays is a normalized 1–5 value.
- `<= 1.5` → Zacks Strong Buy
- `<= 2.5` → Zacks Buy

### Replay Percentile

`ov.replay_percentile` is a float (0–100).
- `>= 80` → REPLAY_ELITE
- `>= 60` → REPLAY_STRONG
- any value (replay_supported=true) → REPLAY_YES

## Validation Examples

### VRT (expected)
- Rank: #2 → `Top-2 CW-DAS deployment candidate`
- UCF: CORE_CONVICTION_LEADER → `Core Conviction Leader`
- ESS: VERY_BULLISH → `Very Bullish ESS signal`
- Replay: supported, percentile ~85 → `Elite replay backing — 85th percentile`
- Penalties: 0 → `No concentration conflicts`

### DELL (expected)
- Rank: #1 → `#1 CW-DAS deployment priority`
- UCF: CORE_CONVICTION_LEADER → `Core Conviction Leader`
- ESS: BULLISH → `Bullish ESS signal`
- Replay: supported → `Replay-backed thesis`
- Add: > 0 → `Actionable — new capital can deploy`
