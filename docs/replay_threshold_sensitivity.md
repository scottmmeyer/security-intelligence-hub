# Replay Threshold Sensitivity Study

**Date:** 2026-06-16  
**Scope:** Analysis of replay top-N threshold impact on portfolio coverage.  
**Status:** INFORMATIONAL — No changes recommended at this time.

---

## Current Configuration

| Parameter | Current Value |
|-----------|--------------|
| Top-N per industry cohort | 20 |
| Top-N all-industry cohorts | 20 |
| Snapshot date | 2025-05-14 (single) |
| Total cohorts | 120 (all AVAILABLE) |
| Symbols in any cohort | 856 unique |
| Portfolio holdings with replay | 44 / 77 (57%) |

---

## Sensitivity Analysis

### Scenario 1: Expand top-N from 20 → 25

**Estimated new coverage:** ~3 additional positions  
**Positions likely to qualify:** CIEN, MKSI, MCB (highest composite scores in RC-02 category)  
**Confidence impact:** Low risk. These are the next-ranking securities in their cohorts. Their historical performance data would be genuine.  
**UCF impact:** CIEN (4.89) most likely to elevate to DEPLOYMENT_CANDIDATE if replay percentile is strong.

| Position | Composite | Cohort | Expected UCF change |
|----------|-----------|--------|---------------------|
| CIEN | 4.89 | US/LARGE/TECHNOLOGY | TACTICAL_GROWTH → possible DEPLOYMENT_CANDIDATE |
| MKSI | 4.78 | US/MID/TECHNOLOGY | TACTICAL_GROWTH → possible DEPLOYMENT_CANDIDATE |
| MCB | 4.77 | US/SMALL/ALL | TACTICAL_GROWTH → possible DEPLOYMENT_CANDIDATE |

### Scenario 2: Expand top-N from 20 → 30

**Estimated new coverage:** ~7–10 additional positions  
**Positions likely to qualify:** Above plus PRG, PLTR, HCI, LMAT, NVS  
**Confidence impact:** Moderate risk. Symbols ranked 21–30 historically had lower conviction scores. Replay evidence may not be as strong.  
**UCF impact for LMAT:** If replay percentile is 50th–70th, adds ~10–14 CW-DAS points. Likely stays TACTICAL_GROWTH due to REPLAY_LOSS/SIGNAL_TIER_MISMATCH conflict flags.

### Scenario 3: Multiple historical snapshot dates

**Current limitation:** One snapshot (2025-05-14). Securities that ranked high at other dates get no replay evidence.  
**Benefit:** Would give securities like LMAT multiple chances to qualify as cohort conditions change.  
**Requirements:** Archived signal snapshots for multiple historical dates. Currently only 2025-05-14 is supported.

### Scenario 4: Expand EMERGING_MARKETS cohorts

**Addresses:** VWO (RC-01 — no cohort for EMERGING_MARKETS/LARGE)  
**Impact:** One additional position, moderate improvement to international allocation analytics.

---

## Recommendation Matrix

| Action | Benefit | Risk | Recommendation |
|--------|---------|------|----------------|
| Expand top-N to 25 | 3 more positions, CIEN likely promoted | Low | Consider for next replay run |
| Expand top-N to 30 | 7–10 more positions | Moderate (dilution) | Not recommended |
| Add snapshot dates | Gradual improvement over time | Low | Passive — will happen as signal archive grows |
| Add EMERGING_MARKETS cohorts | VWO covered | Low | Low priority |
| Change replay matching logic | Major engineering | Medium | Not recommended |

---

## Conclusion

The current top-N=20 threshold is appropriate and well-calibrated. It ensures replay evidence is only granted to securities with demonstrated high conviction at the selection date. The trade-off between coverage breadth and signal quality is currently tilted correctly toward quality.

The most valuable near-term action: when running the next annual replay cycle (May 2026), the top-N threshold for specific high-composite securities (CIEN, MKSI) should be reviewed to determine if expansion to 25 is warranted.
