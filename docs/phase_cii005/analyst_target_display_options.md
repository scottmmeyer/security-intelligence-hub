# Analyst Target Display Options Assessment
## CII-005 Phase Assessment — June 5, 2026

---

## 1. Current State

Analyst target data **already appears in the UI** in two places:

1. **Recommendation card expansion → Analyst Consensus panel** (`_consensusPanelHtml`):
   - Shows: Consensus label, ABR value, Price Target, Current Price, Upside %, Refresh date
   - Shows: CONSENSUS_ALIGNED / DIVERGENCE / NEUTRAL conflict badge

2. **Deployment Queue signal profile → Yahoo ABR card** (after row expand):
   - Shows: `ABR X.XX · CONSENSUS_LABEL` in a single dq-sig-card
   - Does NOT show: price_target, upside_pct, analyst_count

The gap being assessed: **Signal Profile in the Deployment Queue** does not yet show the full target picture — only the ABR consensus label. The recommendation card already has the fuller panel.

---

## 2. Option A — Single Row Summary

```
Target $483.83 | Upside +12.4% | 23 Analysts
```

**Description:** One compact line added to the existing Signal Profile, placed below or beside the current ABR card.

**Pros:**
- Minimal screen space
- All key data in one scannable line
- Easy to implement in the existing `dq-sig-card` grid

**Cons:**
- No visual differentiation from other signal cards
- Analyst count (pending ISSUE-08) missing until that fix ships
- Price target easily misread as a score or target weight if context is absent

**Fit for DQ Signal Profile:** ACCEPTABLE — works as a direct addition to the existing grid.

---

## 3. Option B — Dedicated Analyst Target Card

A dedicated card block separate from the signal grid, styled distinctly from the CW-DAS component cards:

```
┌────────────────────────────────────────────┐
│  ANALYST TARGET INTELLIGENCE               │
│  Target: $483.83  ↑+12.4%  23 analysts    │
│  ABR 1.80 · Buy                            │
│  Sourced: 2026-06-05                       │
│  ⚠ Guidance only — not a price forecast   │
└────────────────────────────────────────────┘
```

**Pros:**
- Clear visual separation from scoring data
- Governance advisory can be embedded inline
- Easy to read; unambiguous that it is target intelligence, not a score

**Cons:**
- Adds screen real estate to an already information-dense panel
- Requires new CSS component
- Slightly heavier implementation than Option A

**Fit for DQ Signal Profile:** GOOD — the strongest option if the goal is full presentation with governance clarity.

---

## 4. Option C — Integrated into Existing Signal Profile Grid

Extend the existing `dq-sig-card` grid with up to 3 new cards:
- Card: `Price Target` → `$483.83`
- Card: `Upside` → `+12.4%`
- Card: `# Analysts` → `23`

These would sit alongside the existing ESS / Danelfin / Zacks / ABR cards.

**Pros:**
- Visually consistent with existing layout
- Requires no new CSS; uses `dq-sig-card` pattern
- Familiar operator experience

**Cons:**
- Risk of misinterpretation: analyst price target next to UCF Score and ESS Score could imply equal weighting or scoring influence
- Grid is already wide at 10+ cards; 3 more adds cognitive load
- ABR card is already present — splitting target data into individual cards fragments context

**Fit for DQ Signal Profile:** ACCEPTABLE but suboptimal. Higher misinterpretation risk than Option B.

---

## 5. Placement Comparison: Recommendation Panel vs. DQ Signal Profile

| Location | Current state | Gap |
|---|---|---|
| Recommendation card expansion | Full panel (`_consensusPanelHtml`) showing all 5 fields + conflict badge | Mostly complete. Analyst count shows "—" (ISSUE-08). |
| DQ Signal Profile (per-row expand) | Only ABR card (`abrNative2`) | Missing price_target, upside_pct, analyst_count |
| Signal Agreement Panel | Uses `upside_pct` for divergence flag | No change needed |

The Recommendation panel already has a well-formed analyst target display. The DQ Signal Profile is the primary gap.

---

## 6. Recommendation

**Recommended approach: Option B — Dedicated Analyst Target Card, placed in the DQ Signal Profile after the existing signal grid.**

Rationale:
1. Visual separation from CW-DAS scoring cards prevents misinterpretation
2. An inline governance advisory (`⚠ Guidance only — not a price forecast`) is appropriate and easy to embed in a dedicated block
3. The recommendation card already has a fully-formed analyst panel; consistency at that level is maintained
4. Analyst count fits naturally with the target row — together they form the complete target context: `$X | +Y% | N analysts`
5. The block design scales: if `targetHighPrice` / `targetMedianPrice` are later added, they slot into the card without redesigning the signal grid

**Secondary recommendation:** Also add `analyst_count` to the existing `_consensusPanelHtml` recommendation card (currently missing due to ISSUE-08). This should be done when ISSUE-08 is implemented, not as a standalone change.

---

## 7. Fields to Display vs. Fields to Suppress

| Field | Display | Rationale |
|---|---|---|
| `price_target` (mean) | ✅ YES | Primary target signal; already in recommendation panel |
| `upside_pct` | ✅ YES | Immediate context alongside target; already computed |
| `analyst_count` | ✅ YES — after ISSUE-08 | Critical for confidence interpretation (3 vs. 35 analysts) |
| `targetMedianPrice` | ⚠ Optional | Median vs. mean can flag skewed distributions; low priority |
| `targetHighPrice` | ❌ NO | High targets invite anchoring to best-case scenarios |
| `targetLowPrice` | ❌ NO | Adds risk framing not aligned with SIH's actionability focus |
| `abr` (numeric) | ✅ Already shown | ABR card already present in signal grid — no change |
| `averageAnalystRating` text | ❌ NO | Redundant with existing `consensus_label` derivation |
