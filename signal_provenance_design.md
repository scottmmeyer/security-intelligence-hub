# Signal Provenance Design
**Phase:** 7.5M — Signal Provenance, Lineage & Freshness Audit  
**Date:** 2026-05-31  
**Status:** DESIGN ONLY — No implementation in this phase

---

## Objective

Design a consistent signal card footer pattern for surfacing **provenance, freshness, and source attribution** alongside every displayed signal in the SIH operator dashboard.

This design enables operators to answer: *"Where did this number come from, and how fresh is it?"* without consulting documentation.

---

## Design Principles

1. **Non-intrusive:** Provenance information is secondary to the signal value itself — it should not compete for visual attention.
2. **Consistent:** Every signal card that displays a score should use the same footer pattern.
3. **Actionable freshness:** Use color-coded age chips, not just text, to convey urgency.
4. **Honest labeling:** Display the native source concept (e.g., "Zacks Rank #2") alongside the normalized score (4.0) to prevent mislabeling.

---

## Signal Card Footer Template

Each signal card footer should contain three fields:

```
┌──────────────────────────────────────────────────┐
│  [Signal Value / Chip]                           │
│  ─────────────────────────────────────────────  │
│  Source: [Provider Name]                         │
│  Updated: [YYYY-MM-DD]    Age: [N days] [chip]   │
│  Native: [Raw value / scale clarification]       │
└──────────────────────────────────────────────────┘
```

**Freshness chip colors:**

| Status | Color | CSS class |
|--------|-------|-----------|
| FRESH (≤2d) | Green `#2d6a4f` bg | `.fresh-chip` |
| WARNING (≤5d) | Amber `#b5451b` bg | `.warning-chip` |
| STALE (≤10d) | Orange `#a44a08` bg | `.stale-chip` |
| CRITICAL (>10d) | Red `#7b1d1d` bg | `.critical-chip` |

---

## Per-Signal Provenance Footer Specs

### ESS (StarMine Equity Summary Score)
```
Source: StarMine via Fidelity
Updated: 2026-05-26
Age: 5 days  [WARNING]
Native: Fidelity EquitySummaryScores-May2026.csv
```
Display note: Show both the ESS text label (VERY_BULLISH) and the analyst-language alias (STRONG BUY) to reduce operator confusion.

---

### Zacks
```
Source: Zacks Rank
Updated: 2026-05-29
Age: 2 days  [FRESH]
Native: Rank #2 of 5 (BUY) → normalized to 4.0 / 5.0
```
Display note: **Always show native rank alongside normalized score.** The operator who checks Zacks.com will see "#2 BUY" and needs to understand why SIH shows 4.0.

Proposed display format: `Zacks: 4.0  ·  Rank #2 BUY`

---

### Danelfin
```
Source: Danelfin AI (Overall Score)
Updated: 2026-05-29
Age: 2 days  [FRESH]
Native: 7 / 10  →  normalized to 3.5 / 5.0
```
Display note: Clarify this is the **Overall AI Score** only, not Fundamental/Technical/Sentiment sub-scores. 

Proposed display format: `Danelfin: 3.5  ·  AI Score 7/10`

---

### Yahoo ABR
```
Source: Yahoo Finance (Analyst Consensus)
Updated: 2026-05-29
Age: 2 days  [FRESH]
Native: ABR 1.50  (1=Strong Buy … 5=Strong Sell)
```
Display note: ABR scale is **inverted** vs SIH score scale. Show the raw ABR alongside the direction chip to prevent scale confusion.

Proposed display format: `Yahoo ABR: 1.5  [BULLISH]`

---

### Yahoo Price Target
```
Source: Yahoo Finance (Analyst Consensus)
Updated: 2026-05-29
Age: 2 days  [FRESH — but target may be stale at source]
Upside: +18.5%  (at time of fetch)
```
Display note: Add a caution footnote when `ABR ≤ 2.5` (Buy) but `upside_pct < −10%` — this pattern indicates a stale source-level target.

Proposed flag: `⚠️ Target vs ABR divergence` for symbols like DELL.

---

### Composite Score
```
Source: SIH analytical_universe (computed)
Updated: 2026-05-31
Age: 0 days  [FRESH]
Formula: ESS(55%) + Zacks(25%) + Danelfin(10%) / available signals
```
Display note: Show which signals contributed to the composite. For VRT: `ESS + Zacks + Danelfin` (Yahoo absent).

---

### CW-DAS Score
```
Source: SIH deployment_queue (computed)
Updated: [run timestamp]
Age: [since last analysis run]
Formula: Signal(0–30) + Replay(0–20) + Conviction(0–35) + Sizing(0–8) + Momentum(0–10) − penalties
```
Display note: CW-DAS score breakdown is already available via `score_breakdown` sub-dict. The provenance footer should link to the breakdown.

---

### UCF Score
```
Source: SIH unified_conviction (computed)
Updated: [run timestamp]
Age: [since last analysis run]
Formula: Signal×30% + Replay×20% + Tier×25% + Momentum×15% + Sizing×10% − penalties
```

---

### Replay
```
Source: SIH Replay Engine (historical simulation)
Last validated: [replay end_date]
Tier: [replay_tier]
```
Display note: `replay_supported = True` means symbol appeared in top-N selection of at least one replay. The replay is a historical backtest, not a live signal.

---

## Compact Tooltip Version

For table cells (where card footers are too large), use a compact hover tooltip:

```
[signal value]
↳ Source: Zacks (2026-05-29 · 2d · FRESH)
   Native rank #2 → score 4.0
```

---

## Implementation Notes (Future Phase)

This design is deliverable-only in Phase 7.5M. Implementation would require:

1. A JS `provenanceFooter(signal, value, sourceDate, nativeNote)` helper function
2. A `signalMeta` lookup object mapping signal names to source metadata
3. CSS for `.fresh-chip`, `.warning-chip`, `.stale-chip`, `.critical-chip`
4. Server-side: inject `signal_refresh_dates` into the API response (or read from a static config)
5. No Python scoring changes required — provenance is pure display metadata
