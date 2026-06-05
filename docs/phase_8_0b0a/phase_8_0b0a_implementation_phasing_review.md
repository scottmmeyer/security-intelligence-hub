# Phase 8.0B.0A — Implementation Phasing Review

**Date:** 2026-06-04  

---

## Proposed Roadmap Review

| Phase | Proposed Scope | Assessment |
|-------|---------------|-----------|
| **8.0B.1A** — Signal Intake | FMP data fetch + storage | ✅ Correct — establish data before touching scores |
| **8.0B.1B** — Analytical Universe | Join FMP into analytical_universe.csv | ✅ Correct — visibility before scoring |
| **8.0B.1C** — CW-DAS Integration | Scoring changes | ⚠️ Recommend inserting diagnostic phase first |

---

## Recommended Insertion: Phase 8.0B.1B.5 — FMP Diagnostic Overlay

### Why Insert This Phase?

Before modifying any scoring formula, the operator needs to:

1. **See FMP data alongside existing signals** without changing any scores
2. **Validate FMP data quality** against expected values (is DELL's P/E plausible?)
3. **Identify coverage gaps** empirically (which symbols return null?)
4. **Calibrate intuitions** about what FMP signals look like for known holdings
5. **Build operator trust** before trusting FMP to influence deployments

This is the same reason Phase 23.6B.3 (CRA forensic validation) was inserted before Phase 23.6B.4 (trust remediation). Data visibility before scoring impact is a structural principle.

---

## Full Recommended Phasing

### Phase 8.0B.1A — FMP Signal Intake Pipeline
**Scope:** Data ingestion only. No scoring changes. No analytical universe changes.

Deliverables:
- `scripts/refresh_fmp_signals.py` — fetch + store FMP signals
- `data/signals/fmp/` directory structure established
- `latest_fmp_*.csv` files populated
- Staleness detection integrated with `refresh_signals.py --providers fmp`
- FMP refresh as optional step in `/api/signal-refresh`

**Gate:** FMP data is flowing and storing correctly for 689 symbols.

**Duration estimate:** 1–2 sessions

---

### Phase 8.0B.1B — Analytical Universe Extension (Read-Only Pass-Through)
**Scope:** Add FMP fields to analytical_universe.csv as new columns. No existing columns changed. No scoring changes.

Deliverables:
- Analytical universe rebuild reads `latest_fmp_key_metrics.csv`
- New columns added (nullable): `fmp_pe_ttm`, `fmp_ev_ebitda_ttm`, `fmp_fcf_yield`, `fmp_revenue_growth_q1_yoy`, `fmp_beat_rate_8q`, `fmp_net_revision_90d`
- Existing `composite_score`, `ess_score_text`, CW-DAS — **unchanged**
- FMP columns visible in analytical_universe.csv for operator inspection

**Gate:** FMP columns appear in analytical_universe. All null for international symbols (expected). Values look plausible for US symbols.

**Duration estimate:** 1 session

---

### Phase 8.0B.1B.5 — FMP Diagnostic Overlay (NEW — Recommended)
**Scope:** UI panel showing FMP data alongside existing intelligence. Read-only. No scoring changes.

Deliverables:
- New "Fundamental Context" column in Security Intelligence Overlay table
- Shows: P/E TTM, Revenue Growth, Earnings Beat Rate, Net Revisions for each held symbol
- Color-coded: green = positive, red = negative, grey = no data
- Clearly labeled "Informational — not used in scoring"
- Operator can visually cross-reference FMP with ESS/Zacks/Danelfin signals

**Gate:** Operator has reviewed FMP data for held positions. Validated it looks correct. Identified any anomalies. Given sign-off to proceed to scoring integration.

**This phase is the trust checkpoint.** An operator who can see that DELL has 8/8 earnings beats and 31% revenue growth will understand and trust the upcoming scoring changes.

**Duration estimate:** 1–2 sessions (UI work)

---

### Phase 8.0B.1C — CW-DAS Momentum Enhancement
**Scope:** Replace/augment CW-DAS momentum component using FMP signals.

Deliverables:
- `earnings_momentum` derived field (earnings_beat_rate × revenue_growth_direction × revision_direction)
- CW-DAS momentum component (currently 10pts ESS-direction-based) supplemented with earnings_momentum
- Governance review and test suite for scoring changes
- Backward compatibility: if FMP data is null, fall back to current ESS-direction behavior

**Gate:** Full regression suite passes. CW-DAS scores plausibly reflect fundamental context. No surprise rank reversals for well-known holdings.

**Duration estimate:** 2–3 sessions

---

### Phase 8.0B.2 — Dislocation Framework
**Scope:** Implement the SIGNAL_DETERIORATION quality filter in CRA (prevent false sell signals on dislocated stocks) and new HIGH_CONVICTION_DISLOCATION classification.

Deliverables:
- CRA capital source builder checks FMP earnings beat rate + revenue growth before generating SIGNAL_DETERIORATION record
- New `dislocation_score` field in analytical_universe
- CRA surfaces dislocation context on source cards in UI

**Gate:** AVGO scenario correctly classified as DISLOCATION (not DETERIORATION) when thesis is intact.

---

## Summary: Recommended Phase Sequence

```
8.0B.0  — Capability Audit           ✅ COMPLETE
8.0B.0A — Architecture Review        ✅ COMPLETE (this phase)
8.0B.1A — Signal Intake              → Implementation
8.0B.1B — Analytical Universe        → Implementation
8.0B.1B.5 — Diagnostic Overlay      → Trust checkpoint (NEW)
8.0B.1C — CW-DAS Integration        → Scoring changes
8.0B.2  — Dislocation Framework     → CRA integration
```

**The diagnostic overlay (8.0B.1B.5) is not optional.** It is the architecture principle that has governed every phase of SIH development: visibility before trust, trust before authority.
