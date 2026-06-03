# SANM Counterfactual Analysis
**Phase 7.6D.1 — SANM Replay Forensics**
**Run Reference:** PAR-20260601-9CFD7C63
**Date:** 2026-06-01

---

## Q5: Three Scenarios for SANM Replay Support

### Baseline (Current State — Actual)

| Metric | Value |
|---|---|
| replay_supported | True |
| Coverage source | 6-day CURRENT_RECOMMENDATION (2026-05-20 to 2026-05-26) |
| Replay pts | 20 |
| CW-DAS score | 90.78 |
| CW-DAS rank | 11 |
| UCF score | 89.53 |
| UCF label | HIGH_CONVICTION_ANCHOR |
| Deployment status | Active, rank 11 |

SANM earns the full 20-pt binary replay bonus from a 6-day evidence window. This is the routing artifact state.

---

## Counterfactual A: No Replay Support (`replay_supported = False`)

**Condition:** Replay evidence is absent — SANM does not appear in any replay basket, or `replay_supported=False` is returned by the routing function.

**Scoring change:**
```
CW-DAS (current) = 90.78
replay_pts: 20 → 0  (delta = -20)
CW-DAS (no replay) = 70.78
```

**Rank change:**

Holdings with CW-DAS scores above 70.78:
- All 38 STRONG holdings (scores range 65.65 to 95.50)
- GTX (80.47), SIMO (75.53)
- SANM at 70.78 falls below 39 of 42 holdings

| Metric | No-Replay Value |
|---|---|
| CW-DAS score | 70.78 |
| CW-DAS rank | ~40 (below AVGO at 72.10, above SBS at 65.65) |
| UCF score | ~70.25 (proportional, approximate) |
| UCF label | Likely TACTICAL_GROWTH (insufficient replay confidence) |
| Deployment status | Effectively excluded from near-term deployment |
| Allocation impact | Drops from ~2.5% position share to marginal |

**Assessment:** Without any replay support, SANM's non-replay signal strength alone (~70.78 pts) places it in the bottom 4 of the 42-holding ranked queue. The HIGH_CONVICTION_ANCHOR label would likely not be retained because replay support is one of the criteria for that tier designation.

---

## Counterfactual B: 365-Day Replay Support (Correctly Routed)

**Condition:** The 365-day HISTORICAL_VALIDATION SMALL-ALL replay is registered in `replay_matrix.csv` and `replay_inputs.csv`. SANM is routed to its correct evidence source.

**Evidence:** `REPLAY-2025-05-14-TO-2026-05-14-US-SMALL-ALL-TOP20-WP05D-20260521-ALL-US-SMALL-ALL`
- Coverage: 365 days
- Mode: HISTORICAL_VALIDATION
- SANM position: 10 of 20
- Basket return: +104.6% (+67.2% over ^RUT benchmark)

**Scoring change (current binary Model A):**
```
replay_supported = True (unchanged — same boolean value)
replay_pts = 20 → 20 (no change)
CW-DAS = 90.78 (unchanged)
```

**Under binary scoring (Model A): NO CHANGE.** SANM earns 20 pts regardless of whether the evidence is 6 days or 365 days.

| Metric | Correctly Routed Value |
|---|---|
| CW-DAS score | 90.78 |
| CW-DAS rank | **11** (unchanged) |
| UCF score | 89.53 (unchanged) |
| UCF label | HIGH_CONVICTION_ANCHOR (unchanged) |
| Deployment status | Active, rank 11 (unchanged) |

**Scoring change (depth-aware Model B — THIN=10, STRONG=20):**
```
replay_depth_tier: THIN (6 days) → STRONG (365 days)
replay_pts: 10 → 20 (delta = +10, restoring full bonus)
CW-DAS: 80.78 → 90.78
rank: 33 → 11 (restoring current position)
```

**Under Model B with correct routing: Rank 11 (same as current binary — the routing fix makes SANM immune to Model B's THIN penalty).**

---

## Side-by-Side Summary

| Scenario | Coverage | Mode | replay_pts | CW-DAS | Rank | UCF Label |
|---|---|---|---|---|---|---|
| Current (routing artifact) | 6 days | CURRENT_REC | 20 | 90.78 | **11** | HIGH_CONVICTION_ANCHOR |
| No replay support | 0 days | N/A | 0 | 70.78 | **~40** | TACTICAL_GROWTH |
| 365-day (correct routing), Model A | 365 days | HISTORICAL_VAL | 20 | 90.78 | **11** | HIGH_CONVICTION_ANCHOR |
| 365-day (correct routing), Model B | 365 days | HISTORICAL_VAL | 20 | 90.78 | **11** | HIGH_CONVICTION_ANCHOR |
| Current routing, Model B applied | 6 days | CURRENT_REC | 10 | 80.78 | **33** | HIGH_CONVICTION_ANCHOR |
| Current routing, Model C applied | 6 days | CURRENT_REC | 0.33 | 71.11 | **37** | HIGH_CONVICTION_ANCHOR |

---

## Key Counterfactual Insight

The routing fix and the scoring model change produce **opposite outcomes**:

- **Routing fix alone (register 365-day SMALL-ALL replay):** SANM returns to rank 11 under both Model A and Model B — no deployment change.
- **Model B applied without routing fix:** SANM drops to rank 33 — material deployment impact.
- **Model B applied WITH routing fix:** SANM stays at rank 11 — no deployment impact.

The Phase 7.6D recommendation to add depth-aware scoring was correct in principle, but SANM's case — the primary evidence for the recommendation — is a routing artifact, not a signal quality deficiency. If the routing is fixed first, SANM is no longer a THIN evidence holding, and the Model B reform has no material deployment impact in the current run.

---

## Interpretation for Operator

**SANM at rank 11 is correct** — if the routing were working as intended. SANM's 365-day basket evidence (basket return +104.6%, 10th of 20 in the SMALL-ALL cross-sector replay) is strong evidence that its top-20 selection was justified over a full year of validation. The current rank-11 position reflects a legitimate claim to HIGH_CONVICTION_ANCHOR status.

The issue is not that SANM is ranked too high. The issue is that the system is assigning the right score (20 pts) via the wrong evidence (6-day window instead of 365-day window). The outcome is accidentally correct; the provenance is wrong.
