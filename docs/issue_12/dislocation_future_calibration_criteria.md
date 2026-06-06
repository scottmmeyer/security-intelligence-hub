# Dislocation Future Calibration Criteria
## ISSUE-12 Assessment — June 5, 2026

---

## 1. Purpose

This document defines the objective, pre-specified criteria that would justify
future modifications to the Dislocation Intelligence system. These criteria
are established before outcome data is collected to prevent retrospective
bias in the calibration decision.

---

## 2. Q7 — Evidence Thresholds

### Tier to authorize: Adding new dislocation classes (D2, C1, etc.)

| Criterion | Threshold | Measurement |
|-----------|-----------|-------------|
| Existing class average excess return | ≥ +3% (90-day, vs. SPY) | Rolling cohort median |
| Existing class hit rate | ≥ 55% | 90-day, all non-NONE detections |
| Tier ordering preserved | HIGH_CONVICTION > MODERATE > WATCH excess return | 90-day |
| Cohort size | ≥ 50 detections per class | Total since tracking started |
| Data duration | ≥ 2 full quarters | ~6 months of detection history |

**All criteria must pass.** Passing any single criterion alone is insufficient.

---

### Tier to authorize: Adjusting tier thresholds (e.g., changing beat_rate cutoff)

| Criterion | Threshold |
|-----------|-----------|
| Current threshold demonstrates opposite tier ordering | e.g., MODERATE consistently outperforms HIGH_CONVICTION |
| Cohort size | ≥ 30 detections in the affected tier |
| Observation window | ≥ 3 consecutive quarterly cohorts showing the anomaly |

**Single-quarter anomalies do not justify recalibration.** Regime effects
(market corrections, earnings surprises) can cause any signal to look poor
in a single quarter.

---

### Tier to authorize: Allowing dislocation to influence scoring (composite, CW-DAS, etc.)

**This is a governance escalation. The bar is much higher.**

| Criterion | Threshold |
|-----------|-----------|
| Excess return (90-day) | ≥ +8% vs. SPY, consistently over ≥ 4 quarters |
| Hit rate | ≥ 65% over the same period |
| Information Coefficient (IC) | > 0.10 (moderate positive IC is notable) |
| Independent validation | At least one out-of-sample cohort confirmed |
| CII philosophy review | Formal assessment that scoring influence doesn't introduce reverse circularity |
| No tier reversal in any single quarter | HIGH_CONVICTION must never underperform WATCH in any cohort |

**Current governance: NO scoring influence.** This threshold is intentionally
high because incorporating an unvalidated signal into scoring could corrupt
composite_score, CW-DAS, and all downstream systems. The risk of a false positive
(incorporating a signal that appears to work but doesn't) is substantially higher
than the risk of a false negative (missing an opportunity to improve scoring).

---

## 3. What Would NOT Justify Changes

| Observation | Conclusion | Reason |
|-------------|-----------|--------|
| 1 quarter of positive results | Insufficient | Single-period bias |
| HIGH_CONVICTION outperforms SPY in one cohort | Insufficient | Could be index-level beta |
| Operator feedback that watchlist names "felt right" | Insufficient | Subjective, recall bias |
| A specific famous stock appeared on the watchlist before rallying | Insufficient | Hindsight selection |
| 2 quarters of results with cohort < 30 | Insufficient | Under-powered |

---

## 4. Current Status: No Outcomes Yet

**Detection start date:** June 5, 2026 (ISSUE-04B shipped)

**Earliest 30-day outcome:** July 5, 2026  
**Earliest 90-day outcome:** September 3, 2026  
**Earliest meaningful statistical analysis:** September–October 2026  
**Earliest calibration decision:** December 2026 (after 2 full quarters)

Until September 2026, no outcome data will be available. The correct action is:

1. Implement detection persistence (ISSUE-12B)
2. Continue running PAR analyses as normal
3. Do not modify dislocation thresholds
4. Do not add new classes
5. Do not expand the watchlist UI
6. Review in September 2026

---

## 5. Governance Chain for Future Enhancements

```
Collect outcomes (ISSUE-12B/12C) — ongoing
  ↓
Review at 90 days (September 2026)
  ↓
Does any class meet excess-return + hit-rate criteria?
  ├── NO: Continue tracking. Do not modify. Review again at 6 months.
  └── YES: Does the improvement justify adding new classes?
        ├── YES: Design new class with pre-specified thresholds (new ISSUE-04E)
        └── NO: Recalibrate existing thresholds (new ISSUE-04E)

Does any class meet the scoring-influence threshold?
  ├── NO: Maintain informational-only status. Document.
  └── YES: Formal CII philosophy review before any scoring change.
```

---

## 6. What the System Should NOT Do Before Outcomes Are Validated

1. Use dislocation tier as a deployment priority boost
2. Include dislocation in the composite score
3. Use dislocation as a CRA capital-source suppression signal
4. Promote HIGH_CONVICTION names to higher CW-DAS positions
5. Automatically exclude DETERIORATING names from deployment queue
   (the thesis integrity classification already handles this in the Fundamental Modifier)
6. Generate operator alerts or notifications based on tier alone

All of the above would constitute pre-validated scoring influence — exactly what
the governance model is designed to prevent until outcomes are confirmed.
