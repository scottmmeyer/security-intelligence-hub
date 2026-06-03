# Yahoo / Fidelity Signal Readiness Matrix — Phase 7.5H

**Date:** 2026-05-31  
**Reference Run:** PAR-20260529-BAF83F16  
**Scope:** Design-only assessment. No integration code written. No scoring changes.

---

## Executive Summary

| Provider | Directory | Status | Coverage (top 20) | Notes |
|----------|-----------|:------:|:-----------------:|-------|
| Yahoo Finance | `data/signals/yahoo/` | ✅ Present | 20/20 | Not yet scored; design-ready |
| Fidelity / StarMine | ESS via `EquitySummaryScores-May2026.csv` | ✅ Integrated | 20/20 | Already powers ESS signal |

**Key finding:** Fidelity is not a separate signals pipeline — it is the existing ESS provider. All top-20 candidates receive their ESS signal from `provider=FIDELITY`. No Fidelity integration work is pending for the ESS signal. Yahoo is the only unscored provider with actionable data.

---

## 1. Fidelity Signal Status

### Integration Status: COMPLETE

Fidelity delivers the StarMine Equity Summary Score via:
- **File:** `EquitySummaryScores-May2026.csv`
- **Pipeline path:** signal_snapshot.csv → analytical_universe.csv → security_overlays.csv → UCF → deployment queue
- **Provider lineage:** `provider=FIDELITY;source_file=EquitySummaryScores-May2026.csv`
- **Refresh cycle:** Monthly (current snapshot: May 2026)

There is no separate `data/signals/fidelity/` directory and none is needed. The ESS signal is the Fidelity integration. Phase 7.5G-B remediated the coverage-overwrite bug that was corrupting this signal for 251 symbols.

### What Fidelity Provides (via ESS)

| Signal | Field | Range | Used in Scoring |
|--------|-------|-------|:---------------:|
| StarMine ESS text | `starmine_ess_text` | VERY_BULLISH→BEARISH | ✅ Yes |
| StarMine ESS numeric | `starmine_ess_numeric` | 1.0–5.0 | ✅ Yes |
| Coverage domain | `coverage_domain` | STARMINE_COVERED / NON_STARMINE_ANALYST | ✅ Yes (dedup logic) |

**Additional Fidelity data fields available in the source file but not yet scored:** None identified in the current ESS import schema.

---

## 2. Yahoo Finance Signal Status

### Integration Status: AVAILABLE — NOT YET SCORED

**File:** `data/signals/yahoo/2026-05-29_yahoo_supplemental.csv`  
**Rows:** 725  
**Sourced:** 2026-05-29 (2 days old as of 2026-05-31)

**Schema:**

| Column | Description | Units | Available (top 20) |
|--------|-------------|-------|:-----------------:|
| `price_target` | Consensus analyst price target | USD | 20/20 (100%) |
| `current_price` | Market price as of sourced_date | USD | 20/20 (100%) |
| `upside_pct` | (price_target / current_price - 1) × 100 | % | 20/20 (100%) |
| `abr` | Analyst Buy Rating (consensus) | 1.0–5.0 | 12/20 (60%) |
| `eps_growth_5yr` | 5-year EPS growth estimate | % | 0/20 (0%) |
| `sourced_date` | Fetch date | date | 20/20 (100%) |

**Note:** `eps_growth_5yr` is populated in the file schema but is blank for all top-20 candidates in the 2026-05-29 snapshot. This field may have coverage gaps in the underlying Yahoo API response.

---

## 3. Per-Symbol Yahoo Readiness Matrix

| Rank | Symbol | Price Target | Current Price | Upside % | ABR | ABR Status | EPS 5yr |
|:----:|--------|:------------:|:-------------:|:--------:|:---:|:----------:|:-------:|
| 1 | VRT | $376.80 | $317.86 | +18.5% | 1.50 | ✅ Present | (blank) |
| 2 | ARW | $214.50 | $219.11 | −2.1% | (blank) | ⚠️ Missing | (blank) |
| 3 | SNX | $241.36 | $256.02 | −5.7% | 1.55 | ✅ Present | (blank) |
| 4 | ATLC | $104.00 | $84.00 | +23.8% | (blank) | ⚠️ Missing | (blank) |
| 5 | PSX | $190.58 | $176.65 | +7.9% | 2.15 | ✅ Present | (blank) |
| 6 | CBOE | $330.43 | $343.70 | −3.9% | 3.12 | ✅ Present | (blank) |
| 7 | AVT | $89.00 | $88.45 | +0.6% | (blank) | ⚠️ Missing | (blank) |
| 8 | LRCX | $313.69 | $323.97 | −3.2% | 1.53 | ✅ Present | (blank) |
| 9 | CAH | $245.27 | $199.77 | +22.8% | 1.47 | ✅ Present | (blank) |
| 10 | DELL | $220.26 | $426.35 | −48.3% | 2.00 | ✅ Present | (blank) |
| 11 | SANM | $212.25 | $265.92 | −20.2% | (blank) | ⚠️ Missing | (blank) |
| 12 | PCB | $26.00 | $24.65 | +5.5% | (blank) | ⚠️ Missing | (blank) |
| 13 | CIEN | $457.91 | $562.87 | −18.6% | 2.05 | ✅ Present | (blank) |
| 14 | NUE | $244.14 | $249.16 | −2.0% | 1.76 | ✅ Present | (blank) |
| 15 | GFF | $118.29 | $87.35 | +35.4% | (blank) | ⚠️ Missing | (blank) |
| 16 | ALNT | $73.80 | $75.06 | −1.7% | 1.60 | ✅ Present | (blank) |
| 17 | MTZ | $473.05 | $383.40 | +23.4% | 1.25 | ✅ Present | (blank) |
| 18 | CRS | $459.44 | $464.92 | −1.2% | 1.33 | ✅ Present | (blank) |
| 19 | CMCO | $26.50 | $16.04 | +65.3% | (blank) | ⚠️ Missing | (blank) |
| 20 | ANGO | $18.00 | $11.68 | +54.1% | (blank) | ⚠️ Missing | (blank) |

**ABR Coverage:** 12/20 (60%). Missing for ARW, ATLC, AVT, SANM, PCB, GFF, CMCO, ANGO.

---

## 4. Notable Observations from Yahoo Data

### 4A. Upside Distribution

Of the 20 candidates, upside distribution is bimodal:
- **Positive upside group (10 symbols):** VRT (+18.5%), ATLC (+23.8%), PSX (+7.9%), CAH (+22.8%), PCB (+5.5%), GFF (+35.4%), MTZ (+23.4%), AVT (+0.6%), CMCO (+65.3%), ANGO (+54.1%)
- **Negative upside group (10 symbols):** ARW (−2.1%), SNX (−5.7%), CBOE (−3.9%), LRCX (−3.2%), DELL (−48.3%), SANM (−20.2%), CIEN (−18.6%), NUE (−2.0%), ALNT (−1.7%), CRS (−1.2%)

The negative-upside candidates are ranked high on the CW-DAS system due to strong ESS + Zacks signals; their current market prices have run ahead of analyst consensus targets. This is not necessarily disqualifying, but is a risk signal if Yahoo upside were incorporated.

**DELL flag:** DELL shows −48.3% implied upside (price target $220 vs current $426). This is likely a stale consensus price target that has not caught up with DELL's recent stock move. This would need investigation before any Yahoo price-target scoring integration.

### 4B. ABR Analysis (where present)

ABR convention: 1.0 = Strong Buy consensus, 3.0 = Hold, 5.0 = Strong Sell.

| Symbol | ABR | Interpretation |
|--------|:---:|----------------|
| MTZ | 1.25 | Near-unanimous buy consensus |
| CRS | 1.33 | Very strong buy |
| CAH | 1.47 | Strong buy |
| VRT | 1.50 | Strong buy |
| LRCX | 1.53 | Strong buy |
| SNX | 1.55 | Strong buy |
| ALNT | 1.60 | Strong buy |
| NUE | 1.76 | Buy consensus |
| DELL | 2.00 | Moderate buy/mixed |
| CIEN | 2.05 | Moderate buy |
| PSX | 2.15 | Moderate buy |
| CBOE | 3.12 | Hold consensus (weakest in top 20) |

CBOE's ABR of 3.12 is notably weaker than its peers. Its strong CW-DAS ranking (93.04) is driven by ESS (VERY_BULLISH) and Zacks (5.0), both of which diverge from the analyst consensus captured by ABR.

---

## 5. Design Considerations for Future Yahoo Scoring

This section is design-only — no scoring changes are proposed here.

### Option A: Yahoo Upside as Modifier (low weight)
- Add `upside_pct` as a 5–10% weight modifier on top of existing composite
- Risk: stale price targets (see DELL) would corrupt scores; needs freshness gating
- Prerequisite: resolve DELL-class price lag issues before implementation

### Option B: ABR as 4th Scoring Signal
- Current scoring signals: ESS (primary), Zacks, Danelfin
- ABR is an independent analyst consensus measure, uncorrelated with Zacks in some cases (e.g., CBOE)
- Coverage gap (40% missing in top 20) would need a robust null-handling approach
- ABR scale: 1.0–5.0, aligned with Zacks inverse convention; normalization needed

### Option C: Upside as Eligibility Gate
- Exclude symbols with <−25% Yahoo upside from deployment queue
- Would affect DELL (−48.3%) at current snapshot; risk of false negatives from stale targets
- Implementation complexity: moderate; needs consensus-target freshness tracking

### Blocking Issues Before Any Yahoo Scoring Integration

| Issue | Symbol(s) Affected | Severity |
|-------|-------------------|:--------:|
| Stale analyst price targets (large negative upside) | DELL (−48.3%), SANM (−20.2%) | High |
| ABR missing for 8/20 top candidates | ARW, ATLC, AVT, SANM, PCB, GFF, CMCO, ANGO | Medium |
| `eps_growth_5yr` blank for all top 20 | All 20 | Low (field currently unused) |

---

## 6. Readiness Assessment

| Provider | Usable for Scoring Now | Blocking Issues | Readiness |
|----------|:---------------------:|-----------------|:---------:|
| Fidelity (ESS) | ✅ Already integrated | None | Fully integrated |
| Yahoo price_target / upside_pct | ⚠️ No — design only | Stale target risk (DELL) | Pre-integration design |
| Yahoo ABR | ⚠️ No — design only | 40% coverage gap in top 20 | Pre-integration design |
| Yahoo eps_growth_5yr | ❌ No | 100% blank in top 20 | Not ready |

**Conclusion:** Yahoo signals are available and structurally sound (725-row file, 2-day freshness), but require price-target freshness validation and ABR coverage improvement before they can be safely integrated into the scoring model. The DELL consensus-lag issue must be investigated and resolved before any upside-based scoring is deployed.
