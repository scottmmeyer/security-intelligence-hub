# Decision Intelligence Layer — UI Concepts

**Date:** 2026-06-10

---

## Design Principles

1. **Secondary to the action signal** — DIL never dominates the UI; it expands on demand
2. **Posture badge first** — operator sees the label in 0.2 seconds; details on click/expand
3. **Always cite sources** — every claim shows its origin
4. **Advisory framing always visible** — "guidance only" never hidden

---

## Concept 1: Reduction Candidate DIL Panel (ARCH-05 extension)

The existing expandable profile row in the Reduction Queue gets a "Decision Intelligence" sub-section added to the bottom of the expanded panel.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PRIM                     HIGH          $1.0K          ─                    │
│  Signal Deterioration BEARISH          25% of $4.2K                         │
│  [▼ Profile]                                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  [Signal Intelligence] [Analyst Consensus] [Portfolio Context]               │
│   ...existing profile content...                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  [INVESTIGATE BEFORE ACTING]                                         │   │
│  │                                                                      │   │
│  │  Key Assessment:                                                     │   │
│  │  ESS bearish signal diverges from Street (BUY, 14 analysts, 18%     │   │
│  │  upside). PRIM has an 85.7% earnings beat rate over 8 quarters.     │   │
│  │  Most recent quarter missed by 30.6% — but revenue grew +18.9%     │   │
│  │  YoY. This pattern suggests a single-quarter operational miss,      │   │
│  │  not a fundamental deterioration. Analyst targets likely stale      │   │
│  │  pending post-Q1 revisions.                                         │   │
│  │                                                                      │   │
│  │  Signal Drivers:                                                     │   │
│  │  • ESS BEARISH — Fidelity StarMine, 2026-06-09                      │   │
│  │  • Zacks STRONG_BUY (1.0) — 2026-06-09                             │   │
│  │  • ABR 1.86 BUY (14 analysts) — Yahoo, 2026-06-05                  │   │
│  │  • EPS Q1 miss: −30.6% vs. beat rate 85.7% (8Q) — FMP, 2026-06-04 │   │
│  │  • Revenue growth Q1 YoY: +18.9% — FMP, 2026-06-04                 │   │
│  │                                                                      │   │
│  │  Advisory: All postures are interpretive. Operator judgment required.│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Posture badge color coding:**
- `HIGH_CONFIDENCE_REDUCTION` → red badge
- `ACTIONABLE` → orange badge
- `INVESTIGATE_BEFORE_ACTING` → amber/yellow badge
- `CONFLICTING_EVIDENCE` → amber badge with ⚠ icon
- `MONITOR` → gray badge
- `PASSIVE_REDUCTION` → neutral badge (blue-gray)

---

## Concept 2: Deployment Candidate DIL Panel

Mirror of the above for Deployment Candidates (Top 10 cards). Each "Deployment Candidates — Top 10" card gets a `[⚡ Intel]` button that expands a DIL panel below.

```
┌──────────────────────────────────────────────────┐
│  BUY    VRT             DP·T1    CCL              │
│  +$4.2K                                          │
│  0.44% → 1.34%                                   │
│  [CORE CONVICTION] [Replay Backed] [No Conflicts]│
│  [⚡ Intel]                                       │
├──────────────────────────────────────────────────┤
│  [HIGH CONFIDENCE BUY]                           │
│                                                   │
│  VRT: CW-DAS #1. ESS VERY_BULLISH. Danelfin 5.0 │
│  Zacks 5.0. Street BUY (ABR 1.8, 19 analysts,   │
│  22% upside). Beat rate 8Q: 87.5%. Revenue accel │
│  positive. FULL ALIGNMENT BULLISH.               │
│  FVI: ELITE — VOO/VTI-equivalent for sector.     │
│                                                   │
│  Signal Drivers:                                  │
│  • ESS VERY_BULLISH — Fidelity, 2026-06-09       │
│  • Zacks 5.0 STRONG_BUY — 2026-06-09            │
│  • ABR 1.8 (19 analysts) — Yahoo, 2026-06-09    │
│  • EPS beat rate 8Q: 87.5% — FMP, 2026-06-04   │
│                                                   │
│  Advisory: Guidance only. Operator decides.       │
└──────────────────────────────────────────────────┘
```

---

## Concept 3: Portfolio-Level DIL Summary (New Section)

A compact "What's New Today" panel near the top of Portfolio Alignment, below the narrative summary, showing the 3 most important decision intelligence items.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Decision Intelligence — Today's Priority Items                          │
├──────────────────────────────────────────────────────────────────────────┤
│  ⚡ VRT    HIGH CONFIDENCE BUY — All signals aligned. CW-DAS #1.        │
│  ⚠  PRIM   INVESTIGATE BEFORE ACTING — ESS/Street diverge. EPS miss.    │
│  ○  VOO    PASSIVE REDUCTION — Allocation rebalance only. ELITE vehicle. │
└──────────────────────────────────────────────────────────────────────────┘
```

This serves as the "executive summary" layer: operator gets the 3 most important postures at a glance without opening any profile.

---

## Concept 4: PRIM Scenario — Full DIL Experience After 15% Drop

**Context:** PRIM falls 15% in one day. This is the scenario that motivated DECISION-INTEL-01.

**What the operator sees today:**

The Reduction Queue shows PRIM with BEARISH ESS and BUY analyst consensus. The operator must manually figure out what happened.

**What the operator would see with DIL Phase 1 (existing data only):**

```
[INVESTIGATE BEFORE ACTING]

PRIM — Primoris Services Corp (Infrastructure EPC)

Signal Picture:
• StarMine ESS: BEARISH — momentum signal reacting to price action
• Zacks: 1.0 STRONG BUY — earnings-estimate momentum model
• Street: BUY (1.86 ABR, 14 analysts, $143.79 target, 18% upside)
• Alignment: PARTIAL ALIGNMENT — ESS alone is bearish

Earnings Context (FMP, sourced 2026-06-04):
• Beat rate 8 quarters: 85.7% — strong historical executor
• Most recent EPS surprise: −30.6% — significant miss last quarter
• Q2–Q4 recent surprises: +13.7%, +42.4%, +58.5% — 3 consecutive strong beats
• Revenue growth Q1 YoY: +18.9% — revenue still growing

Assessment:
PRIM has a strong earnings track record (85.7% beat rate) but missed last quarter
by 30.6%. This is likely the event driving the bearish ESS momentum signal.
The Street remains bullish — analyst targets have not been revised down yet
(Yahoo target date: 2026-06-05, may be pre-earnings).

The combination of: single-quarter miss + strong prior track record + revenue still
growing + street divergence = textbook INVESTIGATE_BEFORE_ACTING case.

Recommended posture: Wait for analyst revisions (typically 3–5 days post-earnings)
before executing the reduction. If targets come down significantly, that
confirms the reduction. If targets hold, the ESS signal may normalize.
```

**What the operator would see with DIL Phase 2 (yfinance price context added):**

```
[INVESTIGATE BEFORE ACTING]

PRIM — Primoris Services Corp
⬇ −15.2% today  |  ⬇ −16.8% 5D  |  52W: $94.20–$152.40 (18th pct. of range)
Next earnings: 2026-08-06 (est.)

[all of the above assessment, plus:]

Price Context:
• Stock down 15% today — likely Q2 earnings reaction or guidance cut
• Currently at 18th percentile of 52-week range (near year lows)
• The sharp move today is likely the event that triggered the ESS BEARISH signal

Catalyst Assessment:
This appears to be a guidance-driven selloff pattern:
  Strong revenue growth (+18.9%) + EPS miss suggests execution gap, not
  business deterioration. Guidance may have been cut. Next catalyst: Q3 earnings.
```

---

## CSS / Visual Design Notes

- Posture badge: same pill-badge style as `rec-policy-badge` / `rq-pri` badges
- `HIGH_CONFIDENCE` = `#c0392b` background (sev-high red) — matches reduction urgency
- `ACTIONABLE` = amber `#e07300`
- `INVESTIGATE` = `#b07800` (amber-dark)  
- `CONFLICTING_EVIDENCE` = `#e07300` with ⚠ icon
- `MONITOR` / `PASSIVE` = `var(--muted)` gray
- DIL panel background: `#f8f5f1` — matches existing `rq-profile-cell`
- Evidence list: monospace-style small text, left-border accent
