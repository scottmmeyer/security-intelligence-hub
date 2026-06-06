# ISSUE-07 Sector Calibration Review — Phase 8.0B.1C

## Objective
Review sectors where analyst beat-rate behavior differs materially and determine whether exclusions or special treatment are needed.

## Background
Beat rate measures how consistently a company exceeds analyst earnings estimates. In most sectors, a 62.5%+ beat rate reflects genuine execution quality. However, in certain sectors, the analyst estimation process is structurally different.

---

## Sectors Under Review

### Solar (e.g., FSLR)

**Issue:** Solar companies (particularly First Solar) have historically had below-average beat rates due to:
1. Analysts systematically over-estimate project timelines and ASP
2. Production ramp schedules create lumpy quarterly earnings
3. Tax credit impacts make quarterly estimates highly uncertain

**FSLR data:** Beat rate 43% (4/7 quarters). Revenue growth +24.1%. ROIC 15.4%.

**Without exclusion:** FSLR would receive −1.0 beat component for a 43% beat rate, resulting in a modifier of approximately −1.0 (thesis QUESTIONABLE, consistency MIXED). This would penalize FSLR for a beat rate pattern that reflects analyst inaccuracy rather than company execution.

**With exclusion:** Beat component = 0.0. Modifier applies only thesis + consistency = −0.5 + 0 = −0.5. More appropriate.

**Decision:** ✅ Solar excluded. `"Solar"` added to `_FM_BEAT_RATE_EXCLUDED_SECTORS`.

---

### Biotechnology (e.g., AGEN)

**Issue:** Pre-revenue biotech companies:
1. Have no meaningful earnings to beat (revenue is minimal or zero)
2. Beat rates are noisy and driven by minor R&D expense variances
3. Analyst estimates for clinical-stage companies are inherently uncertain

**AGEN data:** Beat rate 43% (3/7 quarters). Revenue growth +10.4%. ROIC 10.5%.

**Without exclusion:** −1.0 beat component would penalize AGEN for a noisy biotech beat rate.

**With exclusion:** Beat component = 0.0. Modifier based only on thesis + consistency.

**Decision:** ✅ Biotechnology excluded. `"Biotechnology"` added to `_FM_BEAT_RATE_EXCLUDED_SECTORS`.

---

### Energy (PSX, CVE, DVN)

**Issue considered:** Energy beat rates can be volatile due to commodity price swings affecting revenue and earnings estimates.

**Assessment:** Energy beat rates are MORE informative than most sectors, not less. An energy company that consistently beats analyst estimates is demonstrating superior hedging, cost management, and capital discipline — genuine execution quality. PSX's 71% beat rate (5/7 quarters) is a valid reflection of execution.

**Decision:** ❌ Energy NOT excluded. Beat rate applies normally.

---

### Steel / Metals (NUE, STLD, CRS)

**Issue considered:** Steel pricing volatility could make beat rates noisy.

**Assessment:** Steel companies tend to have more analyst coverage and more reliable estimates than solar/biotech. Beat rates in this sector are meaningful signals of margin management.

**Decision:** ❌ Steel NOT excluded. Beat rate applies normally.

---

### REITs (Common Stock REITs)

**Issue considered:** REITs measure earnings via FFO/AFFO which differs from GAAP EPS — potentially affecting beat rate measurement.

**Assessment:** FMP's earnings_surprises data uses reported EPS which may not perfectly reflect FFO. However, REIT beat rates are still directionally informative and no REIT is currently in the deployment queue.

**Decision:** ⚠️ Monitor. Not excluded at this time. Add to watchlist if REIT candidates appear with anomalous beat rate signals.

---

## Exclusion Registry

```python
_FM_BEAT_RATE_EXCLUDED_SECTORS = frozenset({
    "Solar",           # Systematically over-estimated; beat < 50% is normal
    "Biotechnology",   # Pre-revenue; beat rate noisy and uninformative
})
```

---

## Edge Case: FSLR Validation

| Metric | With Exclusion | Without Exclusion |
|--------|---------------|------------------|
| beat_component | 0.0 | −1.0 |
| thesis_component | −0.5 (QUESTIONABLE) | −0.5 |
| consistency_component | 0.0 (MIXED) | 0.0 |
| **Total modifier** | **−0.5** | **−1.5** |

The exclusion prevents a −1.5 penalty that would be inappropriate given FSLR's +24.1% revenue growth and 15.4% ROIC.

---

## Conclusion

Two sectors excluded from beat_rate component: Solar and Biotechnology. These are the only sectors with documented structural analyst estimation bias in the SIH universe. All other sectors receive the full beat_rate component as designed.

The exclusion list is explicitly defined in `_FM_BEAT_RATE_EXCLUDED_SECTORS` and documented here. No silent exceptions exist.
