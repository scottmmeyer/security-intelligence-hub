# Phase 8.0B.0 — Final Verdict

**Date:** 2026-06-04  
**Classification: FMP INTEGRATION JUSTIFIED**

---

## The Seven Questions

### Q1: Is FMP Worth Integrating?

**Yes — unambiguously.**

SIH currently has strong signal intelligence (ESS, Zacks, Danelfin, Replay) but **zero fundamental context**. The system knows whether analysts like a stock. It does not know whether the underlying business justifies that opinion. It cannot distinguish a buying opportunity from a deteriorating thesis. FMP fills every major gap.

The FMP API key is already present in `.env`. The infrastructure is ready. The gap is data, not architecture.

---

### Q2: Which Metrics Should Be Integrated First?

**Phase 8.0B.1 Tier 1 (highest ROI, 4 integrations):**

1. **Earnings Surprise History** — `/earnings?symbol=X` (last 8 quarters)
   - Enables dislocation vs deterioration classification
   - Prevents false sell signals after temporary earnings reactions

2. **Revenue and EPS Growth (Quarterly)** — `/income-statement-growth?symbol=X`
   - Core growth trajectory signal
   - 3-quarter deceleration = thesis break signal

3. **Key Metrics TTM Bulk** — `/key-metrics-ttm-bulk`
   - Single API call for P/E, EV/EBITDA, FCF yield for all 689 symbols
   - Enables valuation gate in CW-DAS and dislocation framework

4. **Estimate Revisions** — `/upgrades-downgrades-consensus-bulk`
   - Net analyst revision direction = leading indicator for ESS changes
   - Captures analyst sentiment before ESS updates

**These four endpoints are sufficient to build the Dislocation Framework and materially improve CW-DAS.**

---

### Q3: Which Metrics Should Never Be Integrated?

| Metric | Reason |
|--------|--------|
| FMP DCF Valuation | Model-dependent, too many assumptions to be deterministic |
| FMP internal composite ratings | Redundant with ESS + Danelfin; would create scoring circularity |
| Technical indicators | SIH philosophy uses replay-based validity, not TA; introducing TA would be architectural drift |
| News APIs | No NLP infrastructure; would require new processing layer |
| Crypto/Forex/Commodities | Out of scope for equity portfolio |

---

### Q4: What Would Most Improve CW-DAS?

**Earnings Surprise History + Revenue Growth → CW-DAS Earnings Momentum Component**

CW-DAS currently has 7 components. The weakest is the **momentum component (10 points)** which only uses ESS direction and signal_direction. ESS lags actual earnings by days to weeks. Replacing the momentum component with:

```
earnings_momentum = f(
    earnings_surprise_streak,   # consecutive beats
    revenue_growth_trend,       # accelerating/decelerating
    estimate_revision_direction # net upgrades/downgrades
)
```

This would make the momentum component the most forward-looking element of CW-DAS, replacing a lagged signal (ESS direction) with actual fundamental velocity.

**Expected impact:** The biggest beneficiaries would be:
- Securities with recent earnings beats where ESS hasn't fully updated → rank correctly elevated
- Securities with earnings misses where ESS is still showing BULLISH → rank correctly depressed

---

### Q5: What Would Most Improve CRA?

**Earnings surprise history + growth trajectory → CRA SIGNAL_DETERIORATION quality filter**

Currently, CRA's most impactful failure mode is the **false sell signal**: it identifies AVGO or DELL after an earnings-driven dip as SIGNAL_DETERIORATION (when ESS temporarily shifts), when in fact the business is intact or improving.

FMP would let CRA apply a **thesis integrity check** before generating a sell source:

```
If ESS = BEARISH but:
  - Earnings surprise (last quarter) > 0%
  - Revenue growth positive and stable
  - Net analyst revisions neutral or positive
  → Reclassify as WATCH_DISLOCATION, not SIGNAL_DETERIORATION
  → Suppress from capital pool
```

This directly prevents the "sell the dip on a good company" error.

---

### Q6: What Would Most Improve Conviction Scoring?

**Persistent earnings beat pattern → conviction tier amplifier**

Currently, conviction tier (CCL vs HCA) is driven by narrative_tier from STI, which uses replay + composite. Replay is backward-looking (did this signal historically work?). FMP enables a **forward conviction signal**:

```
conviction_amplifier:
  STRONG: ≥ 6 of last 8 quarters beat EPS estimates + revenue growth > 15%
  MODERATE: ≥ 5 of 8 beats, growth > 8%
  WEAK: ≤ 3 of 8 beats or revenue growth decelerating
```

A security with STRONG conviction_amplifier + existing CCL tier = highest deployment priority. A security with WEAK conviction_amplifier + current HCA tier = candidate for demotion.

This would make conviction scoring **forward-validated** rather than purely backward-looking.

---

### Q7: Can SIH Support a "Stocks on Sale" Framework After FMP Integration?

**Yes — with 4 FMP integrations and no new algorithms.**

The Dislocation Framework (see phase_8_0b0_dislocation_framework.md) requires:
- Earnings surprise history (rank 1)
- Revenue growth trend (rank 2)
- Key metrics TTM bulk / current P/E (rank 3)
- Estimate revisions (rank 4)

These are exactly the same 4 integrations recommended for CW-DAS improvement. The dislocation framework is not a separate project — it emerges naturally from the fundamental data layer.

**The Dislocation Framework would be the most operationally distinctive capability SIH could build.** No existing portfolio intelligence tool in the operator's workflow (based on the system architecture) can classify "high-conviction dislocation" vs "thesis break" automatically. This is a genuine competitive advantage.

---

## Recommended Phase 8.0B.1 Scope

### Bounded Deliverables

**8.0B.1A — FMP Signal Intake Pipeline**
- Implement FMP data fetch for earnings_surprises (per symbol, last 8Q)
- Implement FMP data fetch for income_statement_growth (quarterly, last 4Q)
- Implement FMP key_metrics_ttm bulk (entire universe, single call)
- Implement FMP upgrades_downgrades_consensus_bulk (entire universe)
- Store in `data/signals/fmp/` with daily refresh
- No scoring changes — data ingestion only

**8.0B.1B — FMP Signal Integration into Analytical Universe**
- Add FMP-derived fields to analytical_universe.csv:
  - `earnings_beat_rate_8q` (beats / 8 quarters)
  - `revenue_growth_yoy_q1` (most recent quarter)
  - `revenue_growth_acceleration` (QoQ slope)
  - `forward_pe_ttm` (from key_metrics)
  - `fcf_yield_ttm` (from key_metrics)
  - `ev_ebitda_ttm` (from key_metrics)
  - `net_analyst_revision_90d` (upgrades - downgrades / total)
- No modifications to existing scoring formulas

**8.0B.1C — CW-DAS Momentum Enhancement** (deferred to 8.0B.2)
- Replace ESS-based momentum component with earnings_momentum composite
- Requires design review and governance approval
- Phase 8.0B.1 keeps existing scoring unchanged

---

## Final Classification

**FMP INTEGRATION JUSTIFIED**

- FMP API key is already present
- Infrastructure is ready for data integration
- Four high-value endpoints provide most of the benefit
- No new ML, no new algorithms, no architectural changes
- Enables the most important new SIH capability: Dislocation vs Deterioration classification
- Estimated Phase 8.0B.1A/B scope: moderate implementation effort, very high value

The question is not whether to integrate FMP. The question is how to sequence it to maximize value while respecting implementation discipline.

**Recommended first step: Phase 8.0B.1A — FMP Signal Intake Pipeline.**
