# Analyst Target Enrichment — Final Recommendation
## CII-005 Phase Assessment — June 5, 2026

---

## Verdict: APPROVED WITH CONDITIONS

Add analyst target intelligence to the Deployment Queue Signal Profile.
No scoring changes. No ranking changes. Display-only.

---

## Q1 — What Analyst Target Data Is Already Collected?

**Already in the system (fully operational):**

| Field | Coverage | Location |
|---|---|---|
| `price_target` (mean) | 97.9% | `latest_yahoo_supplemental.csv` |
| `upside_pct` | 97.9% | `latest_yahoo_supplemental.csv` |
| `current_price` | 99.9% | `latest_yahoo_supplemental.csv` |
| `abr` (direction) | 65.4% | `latest_yahoo_supplemental.csv` |

**Known gap — never fetched:**

| Field | yfinance key | Gap status |
|---|---|---|
| `analyst_count` | `numberOfAnalystOpinions` | ISSUE-08 fix defined. In model (`Optional[int]`), always null. |
| `targetMedianPrice` | `targetMedianPrice` | Not fetched, not needed |
| `targetHighPrice` | `targetHighPrice` | Not fetched, not recommended |
| `targetLowPrice` | `targetLowPrice` | Not fetched, not recommended |

The primary missing data element is `analyst_count` (ISSUE-08). Everything else needed for a useful target display is already in `latest_yahoo_supplemental.csv`.

---

## Q2 — Recommended Display Design

**Option B: Dedicated Analyst Target card block** placed in the DQ Signal Profile expansion, after the Signal Agreement panel and before the CW-DAS Score Breakdown.

```
┌──────────────────────────────────────────────┐
│ ANALYST TARGET INTELLIGENCE                  │
│ Target $483.83  Upside +12.4%  23 analysts  │
│ Sourced 2026-06-05                           │
│ ⚠ Guidance only — not a price forecast      │
└──────────────────────────────────────────────┘
```

Rationale: visual separation from CW-DAS scoring cards prevents operator
misinterpretation. The governance advisory is structurally embedded (not a
tooltip or footnote).

---

## Q3 — Should Analyst Count Be Shown?

**YES — required for correct ABR interpretation.**

ABR without analyst count is incomplete context. "STRONG BUY from 3 analysts"
and "STRONG BUY from 35 analysts" carry fundamentally different levels of
confidence. Suppressing count invites overconfidence in thin-coverage names.

ISSUE-08 should be implemented before or alongside the display enhancement.

---

## Q4 — Should Upside Percentage Be Shown?

**YES, with a mandatory governance advisory.**

Benefits outweigh risks when:
1. The advisory note is visible in the same block ("not a price forecast")
2. The `sourced_date` is shown to flag freshness
3. The upside field is NOT used in any scoring calculation

---

## Q5 — Should Analyst Targets Influence Scoring?

**NO — for all five systems. Recommendation unchanged from prior research.**

| System | Decision |
|---|---|
| Composite score | NO — analyst price targets have positive bias; direction-only signals are preferred |
| Fundamental Modifier | NO — targets are forward opinions, not evidence of fundamental health |
| CW-DAS | NO — ABR direction is already in Layer 1 via composite; adding magnitude would double-count analyst opinion |
| CRA | NO — rotation targets are driven by deployment queue rank and strategic profiles |
| Deployment Queue ranking | NO — CW-DAS is the ranking engine; analyst target is context, not input |

**The prior research conclusion was correct. It is now formally reconfirmed by full system review.**

---

## Q6 — Philosophy Conflict with CII v1.1?

**Displaying analyst targets STRENGTHENS CII. No conflict.**

| CII Layer | Impact |
|---|---|
| Layer 1 (Consensus) | STRENGTHENED — price target gives magnitude context to ABR direction |
| Layer 2 (Fundamental) | NEUTRAL — fundamental modifier unchanged |
| Layer 3 (Historical) | NEUTRAL — replay unchanged |
| Layer 4 (Portfolio Discipline) | NEUTRAL — CW-DAS and allocation logic unchanged |

The analyst price target adds context to an existing Layer 1 signal (ABR) without
adding a new scoring dependency. The CII v1.1 version label is unchanged.

---

## Q7 — Recommended Implementation Specification

### UI Placement
- **Primary:** New `dq-analyst-target-block` in DQ Signal Profile (per-row expansion), after signal agreement panel, before CW-DAS breakdown
- **Secondary:** Add `analyst_count` to existing recommendation card `_consensusPanelHtml` (after ISSUE-08)

### Fields to Display
- `price_target` — Mean consensus target (`$X.XX`)
- `upside_pct` — Color-coded (`+X.X%` / `−X.X%`)
- `analyst_count` — `N analysts` (after ISSUE-08; omit if null)
- `refresh_date` — Freshness context (`YYYY-MM-DD`)

### Fields to Suppress
- `targetHighPrice`, `targetLowPrice` — anchoring risk, not actionable
- `targetMedianPrice` — low marginal value
- `averageAnalystRating` text — redundant with derived `consensus_label`

### Governance Requirements
- `⚠ Guidance only — not a price forecast` advisory is **mandatory**, not optional
- Block must be visually separate from CW-DAS component cards
- No field in this block may influence any score

### Version Impact
- `app.js`: v23 → v24
- `index.html`: v23 → v24
- CW-DAS: 1.1 (unchanged)
- CII: v1.1 (unchanged)

---

## Implementation Sequence Recommendation

```
ISSUE-08 (analyst_count fix — XS, ~30 min)
   ↓
ISSUE-10 (Analyst Target block in DQ Signal Profile — XS, 1–2 hrs)
   ↓
Optional: ISSUE-04 (Dislocation Watchlist — S, 2–4 hrs)
```

ISSUE-08 can be completed independently. ISSUE-10 can ship without ISSUE-08
and degrade gracefully (analyst_count shows nothing until ISSUE-08 lands).
But the full value of the feature requires both. Sequencing them together is
the clean path.

---

## Deliverables Written

1. `docs/phase_cii005/analyst_target_data_inventory.md` ✅
2. `docs/phase_cii005/analyst_target_display_options.md` ✅
3. `docs/phase_cii005/analyst_target_philosophy_assessment.md` ✅
4. `docs/phase_cii005/analyst_target_implementation_spec.md` ✅
5. `docs/phase_cii005/analyst_target_final_recommendation.md` ✅ (this document)

---

## No Code Changes Made

This phase was assessment-only per specification. No files outside
`docs/phase_cii005/` were created or modified.
