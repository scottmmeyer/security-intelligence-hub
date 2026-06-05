# Phase 23.6 — Capital Rotation Advisor
## Deliverable 5: UI Design

**Date:** 2026-06-04
**Status:** Design Phase

---

## 5.1 Placement

The Capital Rotation Advisor is a new **collapsible section** in the existing Portfolio Alignment UI (`ui/portfolio_alignment/index.html`), positioned between the Deployment Queue panel and the NBA panel.

**Section header:** `Capital Rotation Advisor` (with expand/collapse chevron)

**Badge:** `N rotations available` (count of non-blocked CapitalSourceRecords with priority ≥ MODERATE)

---

## 5.2 Panel Layout — Three Columns

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Capital Rotation Advisor                                            [Collapse ▲] │
│  3 rotation opportunities identified.  Total capital pool: $31,200              │
├─────────────────────────┬──────────────────────┬─────────────────────────────────┤
│  CAPITAL SOURCES         │  ROTATION MAP        │  PORTFOLIO IMPACT               │
│  (What to Sell)          │                      │  (Projected)                    │
├─────────────────────────┼──────────────────────┼─────────────────────────────────┤
│  [Source Cards]          │  [Rotation Lines]    │  [Impact Summary]               │
└─────────────────────────┴──────────────────────┴─────────────────────────────────┘
```

---

## 5.3 Capital Sources Column

### Source Card Design

```
┌─────────────────────────────────────────┐
│  ● FIS                        [HIGH]    │
│  Signal Deterioration                   │
│  BEARISH ESS · Overweight US.Large      │
│                                         │
│  Est. Proceeds:   $12,400 (100% exit)  │
│  Current Weight:  2.8%                  │
│                                         │
│  Tax: [C] LT gain ~$2,100              │
│  Policy: None                           │
│                                         │
│  [✓ Include]  [— Skip]                  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  ● CHGG                      [MODERATE] │
│  Strategic Exit                         │
│  REDUNDANT_EXPOSURE · trim score 68     │
│                                         │
│  Est. Proceeds:   $8,900 (50% trim)    │
│  Current Weight:  1.4%                  │
│                                         │
│  Tax: [A] Loss harvest ~−$1,800        │
│  Policy: None                           │
│                                         │
│  [✓ Include]  [— Skip]                  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  🔒 AAPL                       [HIGH]   │
│  Overweight Reduction                   │
│  US.Large drift +9.8%                   │
│                                         │
│  Est. Proceeds:   $9,900               │
│  Current Weight:  6.2%                  │
│                                         │
│  Tax: [D] LT gain ~$14,200 — Review    │
│  Policy: DO_NOT_SELL — BLOCKED         │
│                                         │
│  [Blocked by Policy]                    │
└─────────────────────────────────────────┘
```

**Color coding:**
- URGENT: red badge
- HIGH: orange badge
- MODERATE: yellow badge
- LOW: grey badge
- Blocked: grey card with lock icon
- Tax bucket A (harvest): green tax badge
- Tax bucket D/E (caution): orange/red tax badge

---

## 5.4 Rotation Map Column

A visual bridge showing which sources map to which deployment targets.

```
CAPITAL SOURCES              DEPLOYMENT TARGETS
                             (from CW-DAS queue, unmodified)

FIS ────────────────┬──────► #1  VRT    $5,800   CCL  ████████████
$12,400             │
                    ├──────► #3  ARW    $4,100   HCA  █████████
                    │
CHGG ───────────────┘──────► #7  DELL   $2,500   HCA  ██████
$8,900 (50%)

                         Capital Remaining: $0
```

**Visual rules:**
- Lines from each source to its allocated targets
- Target cards show: rank, symbol, CW-DAS score bar, narrative tier badge, suggested amount
- Targets are shown in CW-DAS rank order (unchanged from queue)
- A small `[View in Queue]` link on each target card deep-links to the deployment queue entry

---

## 5.5 Portfolio Impact Column

```
┌──────────────────────────────────────┐
│  PROJECTED IMPACT                    │
│  (Approximate — full run required)   │
│                                      │
│  Alignment Score                     │
│  62.1  ──────────►  67.4  (+5.3)    │
│                                      │
│  Concentration (top-5 weight)        │
│  41.2% ──────────►  39.8%  (−1.4%)  │
│                                      │
│  Overweight Nodes                    │
│  EQUITIES.US.LARGE    ✓ Resolved     │
│                                      │
│  New Underweight Risk                │
│  None                                │
│                                      │
│  ⚠ Tax Review Required               │
│  Bucket D position detected          │
│                                      │
│  ─────────────────────────────────── │
│  [Run Full Re-Analysis]              │
│  (triggers POST /api/portfolio/      │
│   analyze with proposed weights)     │
└──────────────────────────────────────┘
```

**Key design rules:**
- Impact numbers are estimates only — clearly labeled
- "Run Full Re-Analysis" button triggers a new PAR run with adjusted weights
- Warning flags for operator review conditions are surfaced here
- No trade execution — this is guidance only

---

## 5.6 Rotation Summary Action Bar

Below the three columns, a fixed action bar:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Rotation Summary                                                                │
│  2 active sources  ·  3 deployment targets  ·  Total pool: $21,300              │
│                                                                                 │
│  [Copy Rotation Summary]  [Export to CSV]  [Save Draft]  [Run Full Re-Analysis] │
└─────────────────────────────────────────────────────────────────────────────────┘
```

- **Copy Rotation Summary** — copies a plain-text SELL/BUY action summary to clipboard
- **Export to CSV** — downloads a `rotation_proposal_YYYY-MM-DD.csv`
- **Save Draft** — persists proposal to `data/operator/rotation_drafts/`
- **Run Full Re-Analysis** — triggers the existing PAR re-run endpoint

---

## 5.7 Clipboard Summary Format

When the operator clicks "Copy Rotation Summary":

```
Capital Rotation Summary — 2026-06-04
Proposal ID: CRA-20260604-A1B2

SELL:
  FIS     $12,400 (100% exit) — Signal Deterioration (BEARISH)
  CHGG     $8,900 (50% trim) — Strategic Exit (REDUNDANT)

BUY (from CW-DAS queue, rank order):
  VRT    $5,800 — Rank 1 · CCL · CW-DAS 92.5
  ARW    $4,100 — Rank 3 · HCA · CW-DAS 84.0
  DELL   $2,500 — Rank 7 · HCA · CW-DAS 76.5

Projected impact: Alignment +5.3 pts · Concentration −1.4% · US.Large OW resolved
Tax: Confirm LT gain on FIS before executing.
```

---

## 5.8 State Persistence

The CRA panel state (which sources are included/skipped, draft rotation) persists in:

```
data/operator/rotation_drafts/{proposal_id}.json
```

The panel reloads the last draft on page load. Draft proposals do not modify any PAR outputs.

---

## 5.9 API Requirements

New API endpoints required for CRA:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cra/proposal` | GET | Build and return a RotationProposal for the current PAR run |
| `/api/cra/proposal/draft` | POST | Save a rotation draft (operator include/skip decisions) |
| `/api/cra/proposal/export` | GET | Export rotation proposal as CSV |

The `/api/cra/proposal` endpoint reads:
- Current PAR run (`deployment_queue.json`, `security_overlays.csv`, `strategic_profiles.json`)
- Current tax state (`/api/operator/tax-state`)
- Current operator policies (`/api/operator/policies`)

It produces a `RotationProposal` without modifying any upstream outputs.
