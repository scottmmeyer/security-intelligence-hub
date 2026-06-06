# ISSUE-12D — Dislocation Outcome Review Panel (Proposal)
## June 5, 2026

**GitHub:** #17  
**Status:** BLOCKED  
**Target:** October 2026  
**Milestone:** Dislocation Calibration Review (December 2026)

---

## Purpose

Add a read-only outcome research panel to the Dislocation Watchlist section
of the Portfolio Alignment UI. The panel will display realized outcomes for
mature dislocation detections as computed by ISSUE-12C.

---

## Entry Requirements (All Must Pass)

| Requirement | Target Date | Notes |
|-------------|------------|-------|
| First 90-day cohort mature | September 3, 2026 | detection_date ≤ June 5, 2026 → matured |
| `dislocation_outcomes.csv` populated | September 2026 | ≥ 20 rows required |
| `dislocation_outcome_summary.json` generated | September 2026 | `build_outcome_summary()` run |
| Statistical review completed | September–October 2026 | Confirm tier ordering, hit rates |
| No data quality issues | September 2026 | Verify SPY prices fetched correctly |

**Implementation is blocked until ALL criteria are met.** Partial data would
produce misleading conclusions.

---

## Planned Features

### Outcome Summary Strip

```
DISLOCATION OUTCOMES  [90d]  [As of YYYY-MM-DD]

HIGH CONVICTION    N detections   Hit Rate XX%   Median Excess +X.X%
MODERATE           N detections   Hit Rate XX%   Median Excess +X.X%
WATCH              N detections   Hit Rate XX%   Median Excess +X.X%
```

### Class Attribution Summary

```
CLASS BREAKDOWN

A1 Fundamental Beat Divergence    N    XX% hit rate    +X.X% median
D1 Replay-Signal Lag              N    XX% hit rate    +X.X% median
B2 Analyst-AI Divergence          N    XX% hit rate    +X.X% median
MULTI_CLASS                       N    XX% hit rate    +X.X% median
```

### Outcome History Table

| Detection Date | Symbol | Tier | Classes | Symbol Return | SPY Return | Excess | Status |
|---|---|---|---|---|---|---|---|
| YYYY-MM-DD | DELL | MODERATE | A1,D1 | +X.X% | +X.X% | +X.X% | WIN |

### Governance Advisory

All panels must display:
> ⚠ Research only — past performance does not guarantee future results.
> Outcomes are informational. No action implied.

---

## What This Panel Must NOT Do

1. Change CW-DAS scores based on outcome data
2. Promote HIGH_CONVICTION detections in the deployment queue
3. Suppress LOSS-class detections from the watchlist
4. Generate operator alerts or notifications
5. Influence CRA rotation logic
6. Claim predictive certainty

---

## Implementation Scope

| Component | Estimated Size |
|-----------|--------------|
| New `/api/dislocation/outcomes` endpoint in `run_outcome_ui.py` | XS |
| New `renderDislocationOutcomes(data)` function in `app.js` | S |
| CSS for outcome panels | XS |
| Version bump app.js v25 → v26 | trivial |

**Total estimated effort:** S (3–4 hours)

---

## Data Sources

- `data/derived/dislocation_outcomes.csv` (ISSUE-12C)
- `data/derived/dislocation_outcome_summary.json` (ISSUE-12C)

These files are read-only by the UI. No new computation at UI time.
