# Phase 8.0B.0A — Final Verdict

**Date:** 2026-06-04  
**Classification: FMP IMPLEMENTATION APPROVED — WITH ONE PREREQUISITE ACTION**

---

## Prerequisite (Blocking)

**The current FMP API key is on the FREE plan (250 calls/day).**

All fundamental endpoints (earnings, income statements, key metrics, analyst estimates, growth, grades) return **HTTP 402** on the free plan. Only the `profile` endpoint is accessible.

**Action required before Phase 8.0B.1A can begin:**
> Upgrade the FMP subscription to at least the **Starter plan ($19/month)**.

This is the only prerequisite. Nothing else blocks implementation.

---

## The Eight Questions

### Q1: Is FMP Operationally Feasible at Current Scale (689 Symbols)?

**Yes — on Starter plan ($19/mo).**

- 689 symbols × 4 daily endpoints = 689 calls/day (within Starter's 300/min capacity)
- Daily refresh completes in ~12 minutes per-symbol or < 5 minutes with bulk
- Pre-market availability confirmed: refresh window 03:30–04:00 fits comfortably
- Failure modes handled with fail-open pattern matching existing SIH behavior

---

### Q2: Is FMP Operationally Feasible at 5,000 Symbols?

**Yes — on Ultimate plan ($99/mo) with bulk endpoints.**

- Bulk endpoints: 4–6 calls total for any universe size
- Per-symbol on Starter: 5,000 calls @ 240/min = ~21 minutes (still pre-market viable)
- Upgrade trigger: when universe exceeds 2,500 symbols OR operational efficiency requires it
- No code redesign needed to switch from per-symbol to bulk — same output format

---

### Q3: Which Endpoints Should Be Implemented First?

**Priority order (Starter plan):**

1. `/key-metrics-ttm?symbol=X` — P/E, EV/EBITDA, FCF yield (daily; highest value)
2. `/earnings?symbol=X&limit=8` — earnings surprise history (quarterly; dislocation framework critical)
3. `/income-statement-growth?symbol=X&limit=4` — revenue/EPS growth (quarterly; thesis validation)
4. `/grades-consensus?symbol=X` — net analyst revision direction (daily/weekly)

When upgrading to Ultimate: replace per-symbol with bulk equivalents.

---

### Q4: Which Endpoints Should Be Deferred?

| Endpoint | Reason to Defer |
|----------|----------------|
| `/financial-scores` (Piotroski) | Annual update; low urgency for v1 |
| `/analyst-estimates` (forward estimates) | Useful but covered partially by grades-consensus |
| `/ratios-ttm` (margins) | Nice to have; not critical for dislocation framework |
| Bulk endpoints (Ultimate plan) | Defer until scale requires them or budget allows |

---

### Q5: What Is the Optimal Ingestion Architecture?

**Per-symbol CSV refresh on Starter plan, following the existing refresh_signals.py pattern:**

```
scripts/refresh_signals.py (extended)
  --providers fmp  (new provider alongside zacks, danelfin, yahoo)

data/signals/fmp/
  daily/fmp_key_metrics_{date}.csv
  quarterly/fmp_earnings_surprises_{year}_{q}.csv
  quarterly/fmp_income_growth_{year}_{q}.csv
  daily/fmp_grades_consensus_{date}.csv
  latest/ (symlinked/copied current files)
```

No new pipeline stages. FMP plugs into the existing refresh + analytical_universe rebuild flow.

---

### Q6: What Is the Optimal Refresh Cadence?

| Data | Cadence |
|------|---------|
| Valuation (P/E, EV/EBITDA, FCF yield) | **Daily** (pre-market 03:30–03:55) |
| Estimate revisions (grades consensus) | **Daily** (same window) |
| Earnings surprise history | **Quarterly** + event-triggered for symbols reporting this week |
| Revenue/EPS growth | **Quarterly** (after each earnings season) |
| Financial quality ratios | **Daily TTM** (same as valuation) |

---

### Q7: Should a Diagnostic Overlay Be Inserted Before Scoring Integration?

**Yes — strongly recommended.**

Phase 8.0B.1B.5 — FMP Diagnostic Overlay:
- Adds FMP columns to the Security Intelligence Overlay UI table
- Shows P/E TTM, Revenue Growth, Earnings Beat Rate, Net Revisions alongside existing signals
- No scoring changes; clearly labeled informational
- Operator validates data quality and builds intuitions before trusting FMP to influence deployments

This is the same "visibility before trust, trust before authority" principle that has governed all SIH phases.

---

### Q8: What Should Phase 8.0B.1 Actually Implement?

**Recommended breakdown:**

**8.0B.1A — FMP Signal Intake** (implement first)
- Extend `refresh_signals.py` with FMP provider
- Fetch + store key_metrics, earnings_surprises, income_growth, grades_consensus
- data/signals/fmp/ directory and file structure
- Staleness detection and fail-open behavior
- No scoring changes

**8.0B.1B — Analytical Universe Extension**
- Add FMP columns (nullable) to analytical_universe.csv
- Join pattern mirrors existing Zacks/Danelfin/Yahoo joins
- All FMP columns null for uncovered symbols (graceful degradation)
- No scoring changes

**8.0B.1B.5 — Diagnostic Overlay** (recommended addition)
- FMP Fundamental Context panel in Security Intelligence Overlay
- Informational; read-only; not used in scoring
- Operator trust checkpoint before 8.0B.1C

**8.0B.1C — CW-DAS Momentum Integration** (deferred to after 8.0B.1B.5 sign-off)
- Replace/augment CW-DAS momentum component
- Earnings beat history + revenue growth + revision direction → earnings_momentum score
- Governance review and full regression suite required

---

## Recommended Implementation Plan

```
PREREQUISITE (blocking):
  → Upgrade FMP API key to Starter plan ($19/mo)
  → Verify: profile endpoint + key_metrics_ttm return HTTP 200 for VRT

Phase 8.0B.1A — FMP Signal Intake
  Effort: 1–2 sessions
  Output: FMP data flowing into data/signals/fmp/

Phase 8.0B.1B — Analytical Universe Extension  
  Effort: 1 session
  Output: FMP columns in analytical_universe.csv (nullable)

Phase 8.0B.1B.5 — FMP Diagnostic Overlay
  Effort: 1–2 sessions (UI)
  Output: FMP data visible in Portfolio Alignment UI
  Gate: Operator reviews and validates FMP data for held positions

Phase 8.0B.1C — CW-DAS Momentum Integration
  Effort: 2–3 sessions
  Output: Earnings momentum in CW-DAS; dislocation thesis in CRA sources
  Gate: Full regression suite; governance sign-off

Phase 8.0B.2 — Dislocation Framework
  Effort: 2–3 sessions
  Output: SIGNAL_DETERIORATION quality filter; HIGH_CONVICTION_DISLOCATION classification
```

---

## Classification

**FMP IMPLEMENTATION APPROVED**

Pending: upgrade FMP subscription from FREE ($0) to Starter ($19/mo).

Without the plan upgrade, no fundamental endpoints are accessible and Phase 8.0B.1A cannot begin.

With the plan upgrade: all critical endpoints (earnings, growth, key metrics, grades) become available and the implementation roadmap proceeds as specified.
