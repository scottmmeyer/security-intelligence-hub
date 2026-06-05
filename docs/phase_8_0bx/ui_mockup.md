# Company Snapshot UI Mockup

**Date:** 2026-06-04  
**Placement:** Inside the expandable CW-DAS candidate detail card (below CW-DAS breakdown grid)

---

## Placement in Existing Card

The existing expandable row in the Deployment Queue already contains:
- Signal Profile section (UCF score, ESS, Danelfin, etc.)
- Signal Agreement Panel
- CW-DAS Breakdown Grid

The Company Snapshot is a new section added **below** the CW-DAS breakdown, collapsible.

---

## Visual Mockup (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  #1  VRT   CCL  DAS 95.1  3.85%→5.36%   YES  +$5,800  DEPLOYABLE      │
├─────────────────────────────────────────────────────────────────────────┤
│  ── Signal Profile ──────────────────────────────────────────────────── │
│  UCF 9.2   #2   CORE CONVICTION LEADER   Composite 4.56                 │
│  ESS: VERY_BULLISH   Danelfin: 4/10   Replay: 80th   Zacks: 4.5/5     │
│                                                                          │
│  ── CW-DAS Breakdown ─────────────────────────────────────────────────  │
│  Signal 27.3  Replay 20  Conviction 35  Sizing 2.9  Momentum 10         │
│                                                                          │
│  ── Company Snapshot ─────────────────────────────────────────────────  │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │  VRT — Vertiv Holdings                                          │     │
│  │  ┌──────────────────────┬──────────────────────┐              │     │
│  │  │  Sector              │  Industrials          │              │     │
│  │  │  Industry            │  Electrical Equip. &  │              │     │
│  │  │                      │  Parts                │              │     │
│  │  │  Country             │  United States        │              │     │
│  │  │  Cap Tier            │  LARGE                │              │     │
│  │  │  HQ                  │  — (Phase 8.0B.1B)    │              │     │
│  │  └──────────────────────┴──────────────────────┘              │     │
│  └────────────────────────────────────────────────────────────────┘     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## International Example (TSM)

```
── Company Snapshot ──────────────────────────────────────────────────
  TSM — Taiwan Semiconductor ADR

  Sector    Technology             Country   Taiwan
  Industry  Semiconductors         Cap Tier  MEGA
  HQ        — (Phase 8.0B.1B)
```

---

## ETF Example (VXUS)

```
── Company Snapshot ──────────────────────────────────────────────────
  VXUS — Vanguard Total International ETF

  Sector    Exchange-Traded Fund   Country   —
  Industry  —                      Cap Tier  LARGE
```

---

## CSS Design Principles

- Matches existing `dq-bd-*` card style (small, dense, consistent)
- Muted label color (`var(--muted)`)
- Foreground value color for data
- No additional icons — text-only for clarity
- Minimal visual weight — this is context, not a signal

---

## Component Name

`_dqCompanySnapshotHtml(symbol, holdingsLookup, metadataLookup)`

Returns HTML string inserted into the expandable row, after `dq-breakdown-notes`.
