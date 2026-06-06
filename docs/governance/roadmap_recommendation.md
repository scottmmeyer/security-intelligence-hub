# Roadmap Recommendation
## June 5, 2026 — Governance Realignment

---

## Q1: What should be the next active issue?

**No active implementation issues are recommended for June–August 2026.**

All planned features are complete. The single open implementation issue
(ISSUE-12D) is blocked until September 2026 by design.

The correct posture for the next 90 days is:

1. Run portfolio analyses regularly to accumulate detection history
2. Monitor `data/derived/dislocation_detections.csv` growth
3. Run the outcome engine in September 2026 when first cohort matures
4. Review results before opening new implementation issues

---

## Q2: Should new signal development pause?

**YES — enter an observation phase.**

This is not stagnation. It is the responsible engineering response to having
built a complete, validated intelligence system that now needs empirical
evidence to determine its next evolution.

Specifically, the following should NOT be started before December 2026:

- New dislocation classes (D2, C1, co-occurrence classes)
- Threshold recalibration of existing classes
- Any feature that uses dislocation tier as a scoring input
- New analyst signal integrations (beyond the completed pipeline)
- New FMP signal dimensions (beyond the active Fundamental Modifier)

**What is appropriate during the observation phase:**

- Signal refresh pipeline maintenance (keep data current)
- Bug fixes (any severity)
- UI polish (minor UX improvements that don't change intelligence)
- Governance documentation
- Portfolio analysis runs to accumulate detection history

---

## Q3: What evidence thresholds must be reached before dislocation influences any system?

As established in the ISSUE-12 Final Recommendation (June 5, 2026):

**Gate for adding new dislocation classes:**
- ≥ +3% average 90-day excess return vs. SPY
- ≥ 55% hit rate
- Tier ordering preserved (HIGH > MODERATE > WATCH excess returns)
- ≥ 50 detections per class
- ≥ 2 full quarters of data

**Gate for any scoring influence (composite, CW-DAS, CRA):**
- ≥ +8% 90-day excess return over ≥ 4 consecutive quarters
- ≥ 65% hit rate
- Information Coefficient > 0.10
- Formal CII philosophy review
- Approval at the December 2026 milestone

These thresholds are unconditional and do not change based on individual
impressive cases.

---

## Q4: Should SIH now enter an observation phase?

**YES — effective immediately.**

The observation phase is defined as:

| Property | Value |
|----------|-------|
| Duration | June 5 – September 2026 (until first cohort) |
| Active development | Bug fixes and pipeline maintenance only |
| New features | None |
| Data collection | Every PAR run accumulates detection data |
| Review trigger | September 3, 2026 (first 90-day cohort matures) |

The observation phase ends when the first outcome review (ISSUE-12D) is
implemented and reviewed. The December 2026 milestone is the formal
decision point for what comes next.

---

## Q5: What should the development focus be between June–September 2026?

### High Priority: Data Accumulation

Run portfolio analyses regularly. Every run:
- Generates a dislocation detection snapshot
- Appends to `data/derived/dislocation_detections.csv`
- Accumulates the evidence base for September review

More frequent runs = larger cohort = more statistical power.

### Medium Priority: Signal Refresh Quality

Ensure the signal refresh pipeline (ESS, Danelfin, Zacks, Yahoo, FMP) runs
reliably on a regular cadence. Fresh signals are required for:
- Accurate dislocation classification
- Correct detection persistence (price_at_detection must reflect current price)

### Low Priority: Technical Debt

Review and address any technical debt accumulated during rapid feature
development (May–June 2026). Candidates:

- `_fmpDislocationType()` in `app.js` — legacy heuristic still present; can
  be removed now that backend payload is authoritative
- Confirm `coverage_history.csv` is maintained correctly
- Review any pending `# TODO` or `# FIXME` comments in `src/portfolio/`

### Defer Until September Review

Everything else. The feature backlog is empty by design. The correct action
is to let the observation phase run.

---

## Summary Timeline

```
June 5, 2026         — Observation phase begins
                       All open implementation issues closed
                       Detection tracking active (ISSUE-12B/12C)
                       Dislocation Calibration Milestone created (Dec 2026)

July 5, 2026         — First 30-day outcomes eligible
                       Run compute_outcomes(30) to spot-check data quality

September 3, 2026    — First 90-day cohort matures
                       Run compute_outcomes(90)
                       Implement ISSUE-12D (Outcome Review Panel)
                       Review tier ordering, hit rates, excess returns

October 2026         — ISSUE-12D implementation (if entry criteria met)
                       First public outcome data visible in UI

November 2026        — Second 90-day cohort matures
                       Preliminary calibration analysis

December 2026        — FORMAL CALIBRATION REVIEW
                       Decide: new classes? threshold changes? scoring influence?
                       This is the next major decision gate.
```
