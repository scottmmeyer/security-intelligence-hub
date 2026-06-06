# ISSUE-10 — Before / After Documentation

**Date:** June 5, 2026

---

## Before ISSUE-10

### Deployment Queue Signal Profile expansion (pre-ISSUE-10)

When an operator expanded a deployment queue row, the panel showed:

```
[Signal Profile Cards: UCF Score | UCF Rank | UCF Label | Composite | ESS | Danelfin | Zacks | Yahoo ABR | Replay Pctile | Proj. Weight]

[Signal Agreement Panel — CONSENSUS_ALIGNED / DIVERGENCE badge + freshness strip]

=== CW-DAS Score Breakdown — DELL ===
[Signal /30] [Replay /20] [Conviction /35] [Fund.Mod] [Sizing /8] [Momentum /10] [Redund.Pen] [Conc.Pen] [Trim Score]

[Company Snapshot]
[Fundamental Snapshot]
[Why SIH Likes It]
```

**Gap:** The ABR card showed "ABR 1.80 · Buy" but had no context:
- No price target shown
- No upside/downside percentage
- No analyst count
- No freshness date specific to the target

An operator reading "STRONG BUY" had to open the recommendation card expansion to find the analyst target — and even then, analyst count was always "—" due to ISSUE-08.

---

## After ISSUE-10

### Deployment Queue Signal Profile expansion (post-ISSUE-10)

```
[Signal Profile Cards: UCF Score | UCF Rank | UCF Label | Composite | ESS | Danelfin | Zacks | Yahoo ABR | Replay Pctile | Proj. Weight]

[Signal Agreement Panel — CONSENSUS_ALIGNED / DIVERGENCE badge + freshness strip]

┌──────────────────────────────────────────────────────┐
│ ANALYST TARGET INTELLIGENCE                          │
│                                                      │
│ Target       Upside        Sourced                   │
│ $483.83      +20.6%        2026-06-05                │
│                                                      │
│ ⚠ Guidance only — analyst targets are opinions, not  │
│   price forecasts. Do not use as trade triggers.     │
└──────────────────────────────────────────────────────┘

=== CW-DAS Score Breakdown — DELL ===
[Signal /30] [Replay /20] [Conviction /35] [Fund.Mod] [Sizing /8] [Momentum /10] [Redund.Pen] [Conc.Pen] [Trim Score]
```

---

## Key Changes

| Dimension | Before | After |
|-----------|--------|-------|
| Price target in DQ panel | Not shown | `$483.83` |
| Upside to target | Not shown | `+20.6%` (green) or `−X.X%` (red) |
| Analyst count | Not shown | Hidden (ISSUE-08 pending); will auto-appear when ISSUE-08 lands |
| Freshness | Not shown in DQ | `2026-06-05` (sourced date) |
| Governance advisory | Not shown | `⚠ Guidance only — not a price forecast` |
| ABR card | "ABR 1.80 · Buy" | Still present in signal grid (unchanged) |
| Placement | N/A | After signal agreement panel, before CW-DAS breakdown |

---

## What Did Not Change

| Element | Status |
|---------|--------|
| CW-DAS Score Breakdown | Unchanged — still shows all 8 components |
| Signal Profile cards | Unchanged |
| ABR card in signal grid | Unchanged |
| Deployment queue rank | Unchanged |
| CW-DAS scores | Unchanged |
| Deployment recommendations | Unchanged |
| All 1,037 tests | Passing |

---

## Analyst Count (Post-ISSUE-08)

Once ISSUE-08 is implemented (adds `numberOfAnalystOpinions` to the fetch pipeline), the ATI block will automatically expand to:

```
Target        Upside        Coverage        Sourced
$483.83       +20.6%        23 analysts     2026-06-05
```

No code change will be required at that point — the `analyst_count` field is already wired in `_dqAnalystTargetHtml()`. The row is conditionally hidden when null and automatically appears when the value is populated.
