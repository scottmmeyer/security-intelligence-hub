# Dislocation Calibration Milestone
## GitHub Milestone: Dislocation Calibration Review — December 2026

---

## Milestone Definition

**Name:** Dislocation Calibration Review  
**GitHub:** Milestone #1  
**Target date:** December 31, 2026  
**Status:** Open

---

## Purpose

The Dislocation Calibration Review is a formal, pre-specified decision gate
at which the evidence from the outcome tracking system (ISSUE-12B/12C) is
reviewed to determine whether the Dislocation Intelligence system (04A–04D)
is producing informational value.

This milestone is scheduled **before** any calibration work begins, to prevent
retrospective bias in the decision. All criteria were established in the ISSUE-12
assessment on June 5, 2026, with zero outcome data available at the time.

---

## Entry Criteria (All Required)

| Criterion | Required Value |
|-----------|---------------|
| Detection history duration | ≥ 2 full quarters (≥ 6 months from June 5, 2026) |
| Total detections recorded | ≥ 50 non-NONE detections in `dislocation_detections.csv` |
| 90-day cohorts available | ≥ 2 complete quarterly cohorts |
| Tier ordering measurable | HIGH_CONVICTION ≥ 30 detections (for statistical comparison) |
| Price data quality | SPY prices fetched without gaps for all outcome windows |

**If any criterion is not met at December 2026, the review is deferred to March 2027.**

---

## Decision Framework

### Decision 1: Are existing classes producing value?

Pass threshold: Average 90-day excess return ≥ +3% AND hit rate ≥ 55%

| Outcome | Action |
|---------|--------|
| Both criteria pass | Proceed to Decision 2 |
| Neither passes | No changes. Continue tracking. Review March 2027. |
| Mixed results | Class-level review. Consider removing underperforming classes. |

### Decision 2: Is tier ordering preserved?

Expected ordering: HIGH_CONVICTION excess return > MODERATE > WATCH

| Outcome | Action |
|---------|--------|
| Ordering preserved | Calibration eligible — adjust thresholds if needed |
| MODERATE > HIGH_CONVICTION | Recalibrate HIGH_CONVICTION thresholds (raise beat_rate cutoffs) |
| WATCH performance negative | Consider removing WATCH tier from watchlist panel |

### Decision 3: Should any class be extended or modified?

| Class | Review question |
|-------|----------------|
| A1 Fundamental Beat Divergence | Is 87.5% beat rate threshold optimal? Is INTACT-only gate too restrictive? |
| D1 Replay-Signal Lag | Is 80th percentile replay threshold optimal? |
| B2 Analyst-AI Divergence | Is analyst_count ≥ 10 gate appropriate? |
| MULTI_CLASS | Does multi-class outperform single-class? |

### Decision 4: Should dislocation influence any scoring system?

This decision requires a much higher bar (ISSUE-12 calibration criteria):
- ≥ +8% excess return (90-day) over ≥ 4 consecutive quarters
- ≥ 65% hit rate
- Formal CII philosophy review

**This threshold is extremely unlikely to be met at the December 2026 review.**
The scoring influence decision is deferred to a later milestone.

---

## Issues Assigned to Milestone

| Issue | Title | Status |
|-------|-------|--------|
| #17 | ISSUE-12D: Dislocation Outcome Review Panel | BLOCKED until Oct 2026 |

---

## Timeline

```
June 5, 2026       — Detection tracking begins (ISSUE-12B live)
July 5, 2026       — First 30-day outcomes eligible
September 3, 2026  — First 90-day outcomes eligible
October 2026       — ISSUE-12D implementation (if entry criteria met)
November 2026      — Second 90-day cohort matures
December 2026      — Calibration Review — formal decision gate
```
