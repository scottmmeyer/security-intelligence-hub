# Operator Conviction Dashboard Design
## Phase 7.6 — Single-Page Operator View

**Status:** Design only. No code changes.
**Objective:** One page that answers the six operator questions without requiring signal reconciliation.

---

## 1. The Six Operator Questions

The dashboard is organized around the six questions an operator asks at every review cycle:

| # | Question | UCF Label(s) | Action |
|---|----------|-------------|--------|
| 1 | What are my best holdings? | CORE_CONVICTION_LEADER | Confirm, deploy if cash available |
| 2 | Where should new money go? | CORE_CONVICTION_LEADER + HIGH_CONVICTION_ANCHOR (deployment-eligible) | Deploy here |
| 3 | What should I avoid adding to? | MAINTAIN + TRIM_WATCH + OW-blocked | Hold flat or reduce |
| 4 | What am I monitoring? | TACTICAL_GROWTH + DEPLOYMENT_CANDIDATE | Watch for signal change |
| 5 | What is weakening? | TRIM_WATCH + conflict: CONVICTION_OW_TENSION | Review for reduction |
| 6 | What is strengthening? | TACTICAL_GROWTH approaching CCL gates | Potential deployment upgrade |

---

## 2. Page Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CONVICTION INTELLIGENCE  ·  Run PAR-20260531-F794D952  ·  CONCENTRATED_ALPHA │
│  Portfolio: $472K  ·  Deployable Cash: $33.2K  ·  Replay Coverage: 57%       │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│  SECTION 1 — BEST HOLDINGS                                                   │
│  Question answered: "What are my best holdings?"                             │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│  SECTION 2 — DEPLOY                                                          │
│  Question answered: "Where should new money go?"                             │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│  SECTION 3 — HOLD FLAT                                                       │
│  Question answered: "What should I avoid adding to?"                         │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│  SECTION 4 — MONITORING                                                      │
│  Question answered: "What am I monitoring?"                                  │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│  SECTION 5 — WEAKENING                                                       │
│  Question answered: "What is weakening?"                                     │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│  SECTION 6 — STRENGTHENING                                                   │
│  Question answered: "What is strengthening?"                                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Section Specifications

### Section 1 — Best Holdings (CORE_CONVICTION_LEADER)

**Header:** "BEST HOLDINGS" · badge: `CCL tier` · count: `{n} positions`

**Display:** Card grid, one card per CCL holding, sorted by ucf_score desc.

**Card fields:**

```
┌───────────────────────────────────────────────────┐
│  #1  AEIS                          UCF 93.4        │
│  Advanced Energy Industries                        │
│                                                    │
│  ████████████████████████ 95.6 CW-DAS             │
│  Signal: BULLISH · Composite: 4.71 · ESS: BULLISH │
│  Replay: ✓ supported · Weight: 2.4%               │
│  Headroom: 60% to 6% limit                        │
│                                                    │
│  ✓ All conviction gates met                        │
└───────────────────────────────────────────────────┘
```

**Conflict flag display:**
If `CONVICTION_OW_TENSION` flag is active, card shows:
```
  ⚠ Blocked from deployment — OW node: EQUITIES.INTERNATIONAL
```
The card still appears in Best Holdings (conviction is intact) but with the block indicator.

**Why this works:** CCL holdings that are OW-blocked (CVE, TSM, NVDA) remain your best-conviction holdings. They should still appear here — they are just not available for deployment. Separating "best holding" from "deploy here" is a key design insight.

---

### Section 2 — Deploy (Deployment-Eligible + Ranked)

**Header:** "WHERE TO DEPLOY" · badge: `$33.2K available` · count: `43 candidates`

**Display:** Top-10 table by CW-DAS rank. Expand to full 43.

**Columns:**

| Rank | Symbol | CW-DAS | Tier | Weight | Composite | Replay | Status |
|------|--------|--------|------|--------|-----------|--------|--------|
| #1 | AEIS | 95.6 | CCL | 2.4% | 4.71 | ✓ | DEPLOY |
| #2 | VRT | 95.5 | CCL | 3.6% | 4.56 | ✓ | DEPLOY |
| #3 | ARW | 94.1 | HCA | 0.9% | 4.89 | ✓ | DEPLOY |
| ... | | | | | | | |

**Note:** This section = the existing Capital Deployment Queue. In the UCF dashboard, it is renamed and reframed as answering "Where should new money go?" The section is already built (Phase 7.5C). The UCF dashboard wraps it.

**Blocked sub-panel:** (Already exists as "Blocked Conviction Opportunities")
Reframed label: "Blocked from deployment — conviction present, allocation constrained"

---

### Section 3 — Hold Flat (MAINTAIN + TRIM_WATCH + blocked)

**Header:** "HOLD FLAT — do not add"

**Three sub-groups:**

**3A — Structurally Neutral (MAINTAIN)**
ETFs, funds, bonds. No signal. Hold for allocation reasons, not conviction reasons.

```
VOO    3.68%  Broad US exposure          Structure only
VB     3.71%  Small-cap exposure         Structure only
BND    0.70%  Investment-grade fixed      Structure only
...
```

**3B — OW-Blocked Conviction (Blocked CCL/HCA)**
Conviction is strong. Allocation node is overweight. Add nothing until node rebalances.

```
CVE   CCL  84.0 ⚠ OW: INTL  — strong conviction, wrong allocation node
TSM   CCL  81.6 ⚠ OW: INTL  — strong conviction, wrong allocation node  
NVDA  CCL  78.4 ⚠ OW: MEGA  — strong conviction, concentration pressure
MU    CCL  77.8 ⚠ OW: MEGA  — above 6% warn threshold
```

**3C — Under Watch (TRIM_WATCH)**
Active holdings with weakening signal or concentration pressure.

```
PRIM  BEARISH  composite=2.06  trim_score=HIGH  — reduce
KGC   NEUTRAL  ESS BEARISH     composite=2.61   — monitor closely
```

---

### Section 4 — Monitoring (TACTICAL_GROWTH + DEPLOYMENT_CANDIDATE)

**Header:** "MONITORING — signal positive, not full conviction"

**Purpose:** These are BULLISH or NEUTRAL holdings that don't yet meet CCL/HCA gates. They are not deployment priorities now, but could become so if signal strengthens or replay coverage expands.

**Display:** Compact table sorted by composite_score desc.

```
Symbol  Signal    Composite  ESS           Weight  Gap-to-CCL
PRG     BULLISH   4.72       VERY_BULLISH  0.78%   Missing: replay support
FHI     BULLISH   3.56       BULLISH       2.84%   Missing: replay support
MKSI    BULLISH   3.94       BULLISH       0.69%   Missing: replay support
LMAT    BULLISH   3.78       BULLISH       1.49%   Missing: replay support
IVZ     BULLISH   3.61       BULLISH       1.53%   Missing: replay support
JBL     BULLISH   3.61       BULLISH       1.31%   Missing: replay support
HCI     BULLISH   3.83       BULLISH       0.98%   Missing: replay support
MCB     BULLISH   3.50       —             0.88%   Missing: replay support + ESS
SMR     NEUTRAL   3.43       —             0.37%   Below composite threshold
PLTR    NEUTRAL   3.29       —             0.03%   Below composite threshold
```

**"Gap-to-CCL" column** is the key innovation here — instead of just showing signal, show what specific gate the holding is missing to become a CCL. This directs operator attention: "PRG's VERY_BULLISH ESS is already at CCL-level signal. The only gap is replay support. If replay expands to consumer finance, PRG becomes a deployment candidate."

---

### Section 5 — Weakening

**Header:** "WEAKENING — flag for review"

**Content:**

**5A — Active TRIM_WATCH positions**
(Repeats Section 3C for emphasis in the time-action context)

**5B — Conflict flags**

```
CONVICTION_OW_TENSION:
  CVE: CCL conviction blocked by EQUITIES.INTERNATIONAL OW
  TSM: CCL conviction blocked by EQUITIES.INTERNATIONAL OW
  NVDA: CCL conviction blocked by EQUITIES.US.MEGA.HYPER_MEGA OW
  → Action: Allocation rebalance required to unlock these positions

COMPOSITE_ESS_DIVERGE:
  KGC: ESS=BEARISH, composite=2.61 — secondary consensus partially rescues
  → Action: Monitor; validate ESS reading at next cycle
```

**5C — Replay coverage trend** (requires run history — design for future)
```
[Run history needed — not available in current system]
Holdings that dropped replay support since last run would appear here.
```

---

### Section 6 — Strengthening

**Header:** "STRENGTHENING — watch for tier upgrades"

**Content:**

**Holdings approaching CCL gates:**
Show TACTICAL_GROWTH holdings that are close to meeting all CCL criteria.

```
Gate check algorithm:
  1. Is signal_direction == BULLISH?          → [yes/no]
  2. Is replay_supported == True?             → [yes/no]
  3. Is composite_score >= 4.0?              → [yes/no, current value]
  4. Is percent_of_portfolio >= 1.5%?        → [yes/no, current value]
  5. Is trim_priority_score < 30?            → [yes/no, current value]

Gates missing: 1 = "approaching CCL"
Gates missing: 2 = "monitoring"
Gates missing: 3+ = "tactical"
```

**Example (current run):**

```
PRG   1 gate missing: replay support  — signal already CCL-level (4.72)
HCI   1 gate missing: replay support  — ESS BULLISH (3.83)
MKSI  1 gate missing: replay support  — composite near CCL threshold (3.94)
```

These are the "one gate away" positions. When replay strategy expands to their sectors, they upgrade automatically without any portfolio action.

---

## 4. Header Bar Design

```
┌────────────────────────────────────────────────────────────────────────────┐
│  CONVICTION INTELLIGENCE                                                   │
│  Run: PAR-20260531-F794D952  ·  Date: 2026-05-31  ·  Mandate: Concentrated Alpha │
│                                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │     CCL      │  │     HCA      │  │   Monitoring │  │  Trim Watch  │  │
│  │   2 positions│  │  10 positions│  │  10 positions│  │   4 positions│  │
│  │  $33.2K avail│  │              │  │              │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                            │
│  Replay Coverage: 57%  ·  Conflict Flags: 5  ·  Quality Score: 74        │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Conflict Flag Display Design

Conflict flags appear inline on holding cards as compact warnings, not as separate panels.

```
Card with flag:
┌───────────────────────────────────────────────────┐
│  CVE  · CCL tier  · UCF 78.4                      │
│  Canadian Natural Resources                        │
│                                                    │
│  Signal: BULLISH · Composite: 4.71 · Replay: ✓   │
│  Weight: 4.9% · OW Node: EQUITIES.INTERNATIONAL  │
│                                                    │
│  ⚠ CONVICTION_OW_TENSION                         │
│  Strong holding — blocked from deployment until   │
│  international allocation rebalances.             │
└───────────────────────────────────────────────────┘
```

Flag badge colors:
- `CONVICTION_OW_TENSION` → amber (⚠)
- `SIGNAL_TIER_MISMATCH` → blue (ℹ)
- `COMPOSITE_ESS_DIVERGE` → amber (⚠)
- `TRIM_RETAIN_CONFLICT` → red (✖)
- `REPLAY_LOSS` → amber (⚠)

---

## 6. Design Notes for Implementation

> **No code in this document. These are specifications.**

### 6.1 Data Source

The dashboard reads from `ucf_verdicts.json` (produced by `build_ucf_verdicts()` in the proposed Layer 1 from `conviction_framework_design.md`). This single artifact contains all fields needed for all six sections.

### 6.2 Rendering Approach

Consistent with the existing UI stack: vanilla JS + CSS, no framework. The dashboard is a new page at `ui/portfolio_alignment/conviction_dashboard.html` — it does not replace the existing Portfolio Alignment UI.

### 6.3 Section Ordering Rationale

Sections 1 and 2 answer the most important questions (where is conviction, where does cash go). Sections 3 and 4 are passive (hold). Sections 5 and 6 are time-sensitive signals (weakening/strengthening). This ordering matches how an operator's attention flows at review time.

### 6.4 Relationship to Existing UI

The existing Portfolio Alignment UI surfaces retain all their current content:
- Portfolio Mandate Assessment (phase 7.1+)
- Capital Deployment Queue (phase 7.5C)
- Allocation & Portfolio Observations (recommendations)

The Conviction Dashboard is a **new companion view** at the conviction-intelligence level. It synthesizes across all existing surfaces without replacing them. An operator uses both:
- Portfolio Alignment: allocation and recommendation detail
- Conviction Dashboard: conviction ranking and decision routing

### 6.5 "Gap-to-CCL" Column Implementation Note

The gap-to-CCL check is a read-only evaluation against the 5 existing CCL gates. It does not modify narrative_tier. It is purely a display computation:

```python
def _ccl_gaps(profile, overlay) -> list[str]:
    gaps = []
    if not overlay.signal_direction == "BULLISH":       gaps.append("signal not BULLISH")
    if not overlay.replay_supported:                     gaps.append("replay support missing")
    if not (overlay.composite_score or 0) >= 4.0:       gaps.append(f"composite {composite:.2f} < 4.0")
    if not profile.weight_pct >= 1.5:                    gaps.append(f"weight {weight:.1f}% < 1.5%")
    if not profile.trim_priority_score < 30:             gaps.append(f"trim score {trim:.0f} >= 30")
    return gaps
```

### 6.6 Mobile/Minimal View

For a compact view (or future mobile adaptation), collapse to:
- Summary bar only (counts per label)
- Section 2 (deploy table) — most action-critical
- Section 5 (weakening flags) — most time-sensitive

All other sections are secondary.
