# ISSUE-12 — Final Recommendation
## Dislocation Outcome Tracking Framework Assessment — June 5, 2026

---

## Q1: Should SIH Begin Tracking Dislocation Outcomes?

**YES — immediately, via ISSUE-12B.**

The dislocation intelligence capability (04A–04D) is complete and operational.
It is producing informational classifications in every PAR run. Without outcome
tracking, there is no mechanism to validate whether these classifications have
predictive value.

The marginal cost of adding detection persistence is low (~30 lines in
`runner.py` that append to a CSV). The marginal benefit is the ability to
answer "is this working?" in 90 days, with evidence. Not tracking outcomes now
means a 90-day delay for every additional week of delay.

---

## Q2: What Exact Fields Should Be Recorded?

**Minimum required snapshot per detection:**

```csv
detection_date, run_id, symbol, tier, dislocation_class, active_classes,
ess_at_detection, danelfin_at_detection, replay_percentile_at_detection,
replay_supported_at_detection, composite_score_at_detection,
cw_das_score_at_detection, thesis_integrity_at_detection,
fundamental_modifier_at_detection, dislocation_version,
price_at_detection
```

All fields except `price_at_detection` are available in existing run artifacts.
`price_at_detection` requires `current_price` from `latest_yahoo_supplemental.csv`
at run time.

De-duplicate: only record a detection when a symbol enters a non-NONE tier for
the first time at that tier level. Persistent detections across consecutive dates
are tracked via resolution date, not re-logged as new events.

---

## Q3: What Benchmark Should Be Used?

**Primary: SPY Total Return (same holding period window)**

Excess return = symbol total return − SPY total return over identical dates.

Secondary (after 3+ cohorts): cap-matched benchmark (SPY/MDY/IJR based on
market cap bucket from holdings enrichment).

Defer sector benchmarks until primary analysis is established.

---

## Q4: What Holding Periods Should Be Tracked?

**Primary: 90 days** (one calendar quarter — full earnings cycle)

Secondary: 30 days (quick-reversion check), 180 days (persistence check)

Defer 365-day outcomes until 18 months of tracking history exists.

**First 90-day outcomes computable: September 3, 2026.**

---

## Q5: How Should A1, D1, B2, and MULTI_CLASS Be Evaluated?

**All classes independently, plus MULTI_CLASS as a separate category.**

Class A1 tests: does fundamental execution lift market signals?  
Class D1 tests: does historical replay predict signal recovery?  
Class B2 tests: does analyst consensus outperform AI models when they diverge?  
MULTI_CLASS tests: do co-occurring signals produce higher excess returns?

Required per class: cohort size, hit rate (90d), median excess return (90d).

If MULTI_CLASS does not outperform single-class at 90 days, the multi-signal
framework is adding correlated noise rather than independent evidence. This
would be a significant finding — it would justify streamlining the classifier
to only report the highest-tier single class rather than MULTI_CLASS.

---

## Q6: What Level of Evidence Would Justify Future Enhancements?

**Gate for adding new dislocation classes:**
- ≥ +3% average 90-day excess return vs. SPY
- ≥ 55% hit rate
- Tier ordering preserved (HIGH > MODERATE > WATCH)
- ≥ 50 detections per class
- ≥ 2 full quarters of data

**Gate for scoring influence (composite, CW-DAS, etc.):**
- ≥ +8% 90-day excess return over ≥ 4 consecutive quarters
- ≥ 65% hit rate
- IC > 0.10
- Formal CII philosophy review
- Full governance approval

**No outcome data currently exists. The earliest calibration decision is
December 2026.** Until then, all dislocation classifications remain strictly
informational.

---

## Q7: What Implementation Phases Should Follow?

### ISSUE-12B — Detection Persistence (XS, ~1–2 hrs)
**Recommended: Next priority after this assessment.**

Add `_persist_dislocation_detections()` to `runner.py`:
- Append to `data/derived/dislocation_detections.csv`
- Record minimum snapshot fields including `price_at_detection`
- De-duplicate on (date, symbol, tier)
- No UI changes. No scoring changes.

### ISSUE-12C — Outcome Computation Script (S, ~3–5 hrs)
**Target: September 2026 (after first 90-day window closes)**

Batch script: reads `dislocation_detections.csv`, fetches historical prices
via yfinance, computes excess return vs. SPY, writes `dislocation_outcomes.csv`.

### ISSUE-12D — Outcome Review Panel (S, ~3–5 hrs)
**Target: October 2026 (after first outcomes are computed)**

Simple read-only panel in the Dislocation Watchlist page showing:
- Detection count by tier and class
- 30-day and 90-day hit rates
- Median excess return by tier

Gate: only render if `dislocation_outcomes.csv` exists with ≥ 20 records.

### ISSUE-12E — Calibration Decision (deferred)
**Target: December 2026**

Based on outcomes data, decide whether to:
- Recalibrate tier thresholds
- Add new dislocation classes
- Expand to scoring influence (requires very high bar — see Q6)

---

## Summary: Current State and Priorities

| Completed | Status |
|-----------|--------|
| 04A Methodology | ✅ |
| 04B Class A1 | ✅ |
| 04C Watchlist UI | ✅ |
| 04D Classes D1 + B2 | ✅ |
| 12 Outcome Framework Design | ✅ (this document) |

| Next steps | Priority |
|------------|---------|
| ISSUE-12B: Detection Persistence | **Immediate — XS effort** |
| Run analyses monthly (maintain history) | Ongoing |
| ISSUE-12C: Outcome computation | September 2026 |
| ISSUE-12D: Outcome panel | October 2026 |
| ISSUE-12E: Calibration decision | December 2026 |

---

## Governance Commitment

Until outcomes are validated (December 2026 at earliest):

- Dislocation tier does NOT influence CW-DAS scores
- Dislocation tier does NOT influence composite scores
- Dislocation tier does NOT influence CRA rotation logic
- Dislocation tier does NOT influence deployment queue ordering
- Dislocation is an operator advisory surface only

This commitment is unconditional and does not depend on outcome results. If
outcomes are positive, the scoring-influence proposal goes through formal CII
philosophy review before any implementation.

---

## Deliverables Written

1. `docs/issue_12/dislocation_outcome_tracking_design.md` ✅
2. `docs/issue_12/dislocation_benchmark_assessment.md` ✅
3. `docs/issue_12/dislocation_metrics_framework.md` ✅
4. `docs/issue_12/dislocation_future_calibration_criteria.md` ✅
5. `docs/issue_12/issue_12_final_recommendation.md` ✅ (this document)
