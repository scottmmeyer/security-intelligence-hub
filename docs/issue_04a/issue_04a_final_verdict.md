# ISSUE-04A — Final Verdict
## Dislocation Methodology Design Assessment — June 5, 2026

---

## Q1: What is the Recommended Definition of Dislocation?

**Dislocation:** A condition where fundamental evidence (business execution
quality, thesis integrity, beat rate) and/or historical validation (replay
support) conflict with current market signal quality (ESS, Danelfin) — indicating
that the market's current assessment of the security has diverged from the
evidence SIH can verify.

**Key constraint:** Dislocation requires intact fundamentals — divergence on
top of deteriorating fundamentals is not dislocation; it is signal confirmation.

**What dislocation is NOT:**
- A return prediction
- A buy/sell signal
- A ranking change
- A scoring input

---

## Q2: What Data Should Drive It?

**Approved data sources (in priority order):**

1. **Thesis Integrity** (GATING — must be INTACT)
2. **Beat Rate / 8Q** (PRIMARY — drives Class A1/A3)
3. **ESS** (PRIMARY divergence signal — Classes A1, B1, B2, D1)
4. **Danelfin** (PRIMARY divergence signal — Classes A1, B1, B2)
5. **Replay percentile + replay_supported** (PRIMARY for Class D1)
6. **Fundamental Consistency** (SUPPORTING — CONSISTENT strengthens, CONTRADICTORY suppresses)
7. **ABR + Analyst Count** (SUPPORTING, gated by count ≥ 10, for Classes B1/B2)
8. **Revenue growth** (CONFIRMING — supplements beat rate in Class A1)

---

## Q3: What Should NOT Drive It?

| Field | Reason |
|-------|--------|
| CW-DAS score | Deployment mechanics, not signal quality |
| Composite score | Derived from same inputs; circular |
| Allocation drift | Portfolio construction, not signal divergence |
| Portfolio weight | Deployment priority concern (CW-DAS), not dislocation |
| Market cap | Irrelevant to signal divergence |
| Upside % (standalone) | Systematic upward bias; stale targets |
| ROIC / FCF yield (direct) | Already abstracted into thesis_integrity classification |
| STI classification | Context for display only, not detection input |
| Fundamental Modifier value | Already derived from same FMP inputs |

---

## Q4: Should It Affect Scoring?

**NO — for all scoring systems.**

| System | Decision |
|--------|----------|
| CW-DAS | No change |
| Composite score | No change |
| Fundamental Modifier | No change |
| UCF | No change |
| STI profiles | No change |

**Rationale:** The Fundamental Modifier already adjusts CW-DAS for the
strongest cases of fundamental-signal divergence. Adding an additional
dislocation scoring input would double-count the same evidence.

---

## Q5: Should It Affect Rankings?

**NO.**

Dislocation does not change:
- Deployment queue rank
- CRA rotation priority
- UCF label
- Strategic profile classification

A HIGH CONVICTION DISLOCATION name that ranks #15 in the deployment queue
stays at #15. The queue already reflects its fundamental quality via the
Fundamental Modifier. The dislocation classification tells the operator *why*
that name is interesting — not where to deploy capital next.

---

## Q6: Should It Create a Watchlist?

**YES — this is the primary operator-facing use case.**

The Dislocation Watchlist panel should:

1. Show all holdings currently classified as DISLOCATION (HIGH, MODERATE, WATCH)
2. Display: symbol, tier, class, evidence list, key signal values
3. Allow filtering by tier (HIGH CONVICTION / MODERATE / WATCH)
4. Allow sorting by dislocation class
5. Link to the full Signal Profile expansion for each name
6. Include a panel-level advisory: "These names show evidence of signal divergence
   from fundamental quality. No action is implied — operator judgment required."

**The watchlist should NOT:**
- Show names with DETERIORATING thesis
- Rank names by "dislocation strength"
- Generate automatic recommendations
- Persist across analysis runs without refresh

---

## Q7: What Implementation Phases Should Follow?

**Phase 04B — Backend Classification Module**

- Create `src/portfolio/dislocation.py`
- Implement `classify_dislocation(overlay, fmp_row, ac_entry)` function
- Returns: `DislocationType` dataclass with tier, class, evidence list
- Implement Class A1 (Fundamental Beat Divergence) as the initial class
- Write unit tests: ≥ 10 test cases covering tier thresholds and edge cases
- Wire into `runner.py` → `security_overlays.csv` and API payload
- No UI changes in 04B

**Phase 04C — Watchlist Panel UI**

- Add `Dislocation Watchlist` panel to portfolio alignment UI
- Show HIGH CONVICTION and MODERATE tier names by default
- Filter controls: Tier, Class
- Expand row → link to existing DQ Signal Profile expansion
- New CSS, no new API endpoints (uses existing `security_overlays`)
- app.js v24 → v25

**Phase 04D — Class Extensions**

- Add Class D1 (Replay-Signal Lag) to backend classifier
- Add Class B2 (Analyst-AI Divergence) gated by analyst_count ≥ 10
- Add co-occurrence logic (Class C target gap as co-trigger)
- Update unit tests

**Phase 04E — Calibration and Validation**

- After 3–6 months of operator use, review whether watchlist names
  subsequently received upgraded ESS/Danelfin signals
- Calibrate beat_rate and Danelfin thresholds based on observed outcomes
- Do NOT add scoring influence until this calibration is complete

---

## Q8: Recommended Roadmap

```
04A — Methodology Design (this document) — COMPLETE
  ↓
04B — Backend Classifier (XS-S, ~2–4 hrs)
  • Create dislocation.py
  • Class A1 implementation
  • Unit tests (10+ cases)
  • Wire into security_overlays
  ↓
04C — Watchlist Panel UI (S, ~3–5 hrs)
  • New panel in portfolio_alignment UI
  • Tier filters
  • Evidence display
  ↓
04D — Class Extensions (S, ~3–4 hrs)
  • Class D1: Replay-Signal Lag
  • Class B2: Analyst-AI Divergence
  • Co-occurrence logic (Class C)
  ↓
04E — Calibration (ongoing)
  • Outcome tracking
  • Threshold tuning
  • Scoring influence decision (deferred until evidence)
```

**Total estimated effort (04B + 04C + 04D):** M (~8–12 hrs across 3 issues)

---

## Current State Assessment

The existing `_fmpDislocationType()` function in `app.js` is a display-only
UI heuristic that predates this methodology. It implements a simplified version
of Class A1 using the correct core signals (intact thesis + beat rate +
ESS/Danelfin divergence) but:

- Has no backend equivalent (detection is purely in JavaScript)
- Has no unit tests
- Has no evidence output format
- Uses hardcoded thresholds without methodology documentation
- Cannot be used in watchlist filtering or analytics

**Recommendation for 04B:** Replace `_fmpDislocationType()` with a call to a
backend-computed `dislocation_tier` field served from the API payload — the same
architecture as thesis_integrity and fundamental_consistency.

The `_fmpDislocationType()` function can be preserved for backward compatibility
during the transition, with the backend classification taking precedence when
available.

---

## Approved Methodology Summary

| Dimension | Decision |
|-----------|----------|
| Definition | Signal divergence from verified fundamental quality |
| Primary detection | Thesis integrity + beat rate + ESS/Danelfin |
| Gate | INTACT thesis required |
| Classes | A1, A3, B1, B2 (gated), D1, C (co-occurrence) |
| Tiers | HIGH CONVICTION / MODERATE / WATCH / NONE |
| Scoring influence | None |
| Ranking influence | None |
| Operator surface | Dedicated watchlist panel |
| Required advisory | "Evidence of divergence only — no action implied" |
| CII alignment | Strengthens Layer 2 transparency |
| Phase 04B scope | Class A1 only (Fundamental Beat Divergence) |
| Phase 04C scope | UI watchlist panel |
| Alpha claims | None — opportunity discovery only |
