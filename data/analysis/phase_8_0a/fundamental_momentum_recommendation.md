# Fundamental Momentum Recommendation
**Phase 8.0A | Q8: How should Fundamental Momentum Intelligence (FMI) be integrated into SIH?**

Generated: 2026-06-02

---

## Executive Recommendation

**Recommended Integration Path: B. OPERATOR OVERLAY (Phase 8.0B) → E. STANDALONE INTELLIGENCE LAYER (Phase 8.0C)**

Do not integrate FMI into the CW-DAS scoring engine or UCF weighting until:
1. An automated FMI data pipeline exists covering 80%+ of the analytical universe
2. FMS scores have been validated for at least one full quarter against actual signal performance
3. The operator has reviewed FMI display data and confirmed it reflects expected business reality

---

## Integration Stage Definitions

| Stage | Label | FMI Role |
|-------|-------|----------|
| **A** | Passive Archive | FMI data collected but not displayed |
| **B** | Operator Overlay | FMI displayed as informational layer alongside composite signal; no scoring impact |
| **C** | UCF Factor | FMI incorporated as a weighted factor in Universe Coverage Framework scoring (e.g., 10–15%) |
| **D** | CW-DAS Weighting | FMI affects Conviction-Weighted Deployment Allocation System output |
| **E** | Standalone Intelligence | FMI produces independent deployment recommendations with conviction weighting |

---

## Current State Assessment

**SIH is ready for Stage A → B transition** based on Phase 8.0A findings:

| Criterion | Status |
|-----------|--------|
| Signal quality validated | ✅ Phase 7.8A — 290 persistent leaders confirmed |
| Fundamental data gap identified | ✅ Phase 8.0A — 8 specific gaps documented |
| FMS design complete | ✅ Phase 8.0A — 6-component 0–100 score |
| Data source identified | ✅ FMP Starter ($19/month) |
| Operator symbol alignment verified | ✅ 4/5 operator symbols fundamentally confirmed |
| Automated pipeline built | ❌ Not built — Phase 8.0B work |

---

## Recommended Integration Path Detail

### Phase 8.0B: Operator Overlay (Next Phase)

**Trigger to begin**: Operator decision to invest $19/month in FMP Starter tier.

**Scope**:
- Build `scripts/fetch_fmi_data.py` — calls FMP API for revenue, EPS, forward estimates, FCF, and forward PE for top 200 symbols by composite score
- Add FMI fields to `data/analysis/fmi_scores.csv` and update weekly
- Display FMS alongside composite score in operator UI (read-only, no scoring impact)
- Generate FMI alert when FMS < 30 for a symbol with composite score > 4.5 (potential divergence warning)

**What operator gains**:
- Instant visibility into PSX-type situations: signal strong, fundamentals diverging
- Context for position sizing: VRT at 47x PE vs ARW at 12x PE on similar signals
- Early warning on cyclical bounce-backs vs structural compounders

**What does NOT change**:
- CW-DAS scoring logic
- UCF weighting
- ESS/Zacks/Danelfin ingestion
- Any existing deployment queue output

---

### Phase 8.0C: UCF Factor (Future Phase)

**Trigger to begin**: FMS covers 80%+ of analytical universe with weekly+ update cadence AND 1 full quarter of FMI validation completed.

**Proposed UCF weight**:
- FMS contributes 10% weight to Universe Coverage Framework scoring
- Existing signal composite retains 90% weight
- FMS applied as a **confidence modifier**, not a primary driver:
  - FMS 70–100: confidence multiplier +1.05x
  - FMS 40–70: neutral
  - FMS 0–40: confidence multiplier 0.90x (caution)

**Rationale**: The signal composite is already signal-complete. FMS adds a quality filter. A 10% weight reflects that fundamentals are confirmatory, not leading.

---

### Phase 8.0D: CW-DAS Factor (Long-Term)

**Trigger to begin**: 6+ months of FMI validation data showing FMS-high symbols outperform FMS-low symbols within the same composite score tier.

**Scope**:
- Incorporate FMS as a deployment sizing modifier — higher FMS = larger initial deployment tranche
- Create FMI-adjusted conviction bands (VERY_HIGH, HIGH, MODERATE, etc.) by crossing composite score with FMS

**Note**: This phase requires performance data that doesn't yet exist. Do not advance to Phase 8.0D without empirical validation.

---

## Why Not Integrate FMI into Scoring Now?

1. **Coverage gap is too large**: Only 5 of 2,416 universe symbols have FMI data today. Scoring 5 symbols differently than 2,411 would introduce systematic bias.

2. **No validation data**: The FMS design is theoretical. It has not been backtested against actual signal performance. Integrating an unvalidated score into the CW-DAS risks degrading an already-validated system.

3. **PSX case is instructive, not definitive**: PSX's FMI divergence was confirmed by this research. But PSX might still outperform if the refining cycle recovers sharply. Signals can be right for reasons that don't show in backward-looking fundamentals.

4. **Operator override exists**: The operator already has the ability to manually adjust allocation sizes in the deployment queue. FMI as an operator overlay (Stage B) gives the operator the information they need to exercise this authority — without requiring a scoring system change.

---

## Operator Action Items (Recommended)

| Priority | Action | Estimated Effort | Phase |
|----------|--------|-----------------|-------|
| P1 | Subscribe to FMP Starter ($19/month) | 1 hour | 8.0B |
| P1 | Build `fetch_fmi_data.py` — revenue, EPS, FCF, forward estimates for top 200 | 4–6 hours | 8.0B |
| P2 | Add FMI columns to operator UI display (read-only informational row) | 2–3 hours | 8.0B |
| P2 | Define FMI divergence alert: composite > 4.5 AND FMS < 30 | 1 hour | 8.0B |
| P3 | Backfill FMS for operator symbols (VRT, ARW, SNX, PSX, ATLC, SANM) with FMP data | 2 hours | 8.0B |
| P4 | Validate FMS vs 1Q signal performance before UCF integration | Ongoing | 8.0C |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| FMP API changes/pricing | Low | Medium | EDGAR XBRL fallback for actuals |
| FMS mis-scores commodity cycle | Medium | Low | Stage B display-only limits impact |
| FMI adds noise to high-scoring signals | Low | Medium | 10% UCF weight cap in Stage C |
| Operator ignores FMI divergence warnings | Medium | Medium | Design alert prominence carefully |
| PSX-type divergence causes missed winner | Low | Medium | Signal system retains primary authority |

---

## Summary

The recommended integration path is **conservative and additive**:

1. **Now (Phase 8.0A)**: Evidence gathered, framework designed — complete
2. **Next (Phase 8.0B)**: Build automated FMI pipeline, display as operator overlay — no scoring changes
3. **Later (Phase 8.0C)**: Add FMS as 10% UCF factor after validation
4. **Future (Phase 8.0D)**: CW-DAS integration only after performance data confirms FMS predictive value

The fundamental momentum layer should serve the operator's decision authority — providing context, surfacing divergences, and adding confidence to high-quality signal leaders — without disrupting a signal system that already works.
