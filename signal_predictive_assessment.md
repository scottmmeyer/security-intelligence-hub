# Signal Predictive Assessment
**Phase 7.6C — Signal Authority and Confidence Framework**
**Run Reference:** PAR-20260601-9CFD7C63
**Date:** 2026-06-01

---

## Methodology Statement

This assessment evaluates the predictive quality of each signal source used in the Security Intelligence Hub. It is based solely on structural properties observable in the current system — coverage, freshness, data lineage, and architectural role. **No per-signal historical accuracy data or backtest results exist in this system.** Forward accuracy rankings are inferred from signal design characteristics and institutional pedigree, not from measured hit rates.

---

## Signal Inventory and Structural Assessment

### 1. ESS — StarMine Earnings Surprise Score (via Fidelity)

| Property | Value |
|---|---|
| Provider | StarMine / Fidelity (licensed) |
| Signal type | Quantitative — earnings surprise momentum model |
| Coverage (universe) | 2,498 / 2,831 = 88.2% |
| Freshness | Same-day (2026-06-01) |
| Update frequency | Daily at market open |
| CW-DAS influence | Signal component (0–30) + Momentum component (0–10) = max 40 pts of 103 |
| Composite weight | 61.1% |

**Structural strengths:**
- Forward-looking earnings surprise momentum is one of the most academically validated predictive factors in equity analysis (Earnings Quality, Post-Earnings Announcement Drift)
- StarMine is an institutional-grade quantitative model used by professional portfolio managers globally
- Daily updates provide maximum signal freshness; VERY_BULLISH on 2026-06-01 reflects latest earnings data
- Double-counts into CW-DAS by design: the architects made an intentional choice that ESS quality justifies dual representation (composite + momentum)

**Structural weaknesses:**
- No internal backtest measures ESS accuracy for this specific portfolio universe
- Earnings surprise momentum can reverse rapidly after actual earnings announcements
- Missing for ~12% of universe (micro-cap, international); creates systematic blind spots
- ESS is the Fidelity-provided signal; "Fidelity Analyst Opinion" and "ESS" are the same data — operators may perceive them as independent confirmations when they are not

**Predictive evidence tier:** HIGH (by design and institutional pedigree; not verified in this system)

---

### 2. Replay Support (Historical Backtest Gate)

| Property | Value |
|---|---|
| Provider | Internal — historical replay engine |
| Signal type | Binary gate: was this holding selected in past replay runs? |
| Coverage | Sector/cap-bucket level (applies to 100% of portfolio holdings) |
| Freshness | 2026-05-15 (17 days stale at run date) |
| Historical window | 365 days (2025-05-14 to 2026-05-14) |
| CW-DAS influence | Replay gate: 0 or 20 pts (binary) |
| Composite weight | 0% (not in composite_score; standalone in CW-DAS) |

**Structural strengths:**
- The ONLY signal in the system with direct 1-year forward price performance validation
- Replay validates that historical position selections in a sector/cap bucket performed within acceptable return ranges over a 12-month window
- 365-day window provides meaningful trend validation (vs. momentum signals that can be noisy over short periods)
- Not subject to analyst bias or consensus lag

**Structural weaknesses:**
- Binary flag — no depth gradient. A holding supported by one marginal replay appearance is treated identically to one with 12 consecutive appearances
- Operates at sector/cap-bucket level only; individual stock selection within a bucket is not evaluated
- 17-day staleness at run date (last replay: 2026-05-14); short-window replay data (2026-05-20 to 2026-05-26, 6 days) exists but is a different, narrower signal
- Replay confirms past bucket-level performance, not forward-looking earnings momentum

**Predictive evidence tier:** HIGH for bucket-level deployment confidence; MODERATE for individual stock selection

---

### 3. Zacks Rating

| Property | Value |
|---|---|
| Provider | Zacks Investment Research |
| Signal type | Earnings estimate revision model (analyst consensus) |
| Coverage (universe) | ~2,601 / 2,831 = 91.9% |
| Freshness | ~2026-05-30 (2-day lag) |
| Update frequency | ~Weekly per symbol |
| CW-DAS influence | Via composite_score → signal component (0–30); Zacks weight = 27.8% of composite |
| Composite weight | 27.8% |

**Structural strengths:**
- Highest universe coverage of the three composite signals (91.9% vs ESS 88.2%)
- Zacks earnings estimate revision model is a well-tested, academically validated approach (closely related to SUE factors)
- Provides meaningful independent estimate revision signal distinct from StarMine methodology
- Zacks=5 (Strong Buy) is a meaningful positive signal with documented historical predictive value

**Structural weaknesses:**
- Structurally outweighed by ESS: Zacks contributes 27.8% to composite vs ESS 61.1%; a Zacks=5.0 Strong Buy cannot overcome ESS=BEARISH in composite scoring (see AEIS case: composite=3.06 despite Zacks=5.0)
- Weekly update frequency may lag intra-week earnings developments
- No internal backtest in this system

**Predictive evidence tier:** MODERATE-HIGH (by institutional reputation; weight insufficient to override ESS)

---

### 4. Danelfin AI Score

| Property | Value |
|---|---|
| Provider | Danelfin AI |
| Signal type | AI-based technical + fundamental composite model |
| Coverage (universe) | ~954 / 2,831 = 33.7% |
| Freshness | ~2026-05-30 (2-day lag) |
| Update frequency | ~Monthly |
| CW-DAS influence | Via composite_score → signal component; Danelfin weight = 11.1% of composite |
| Composite weight | 11.1% |

**Structural strengths:**
- AI/ML model may capture non-linear relationships that traditional factor models miss
- Score 1–5 (high=bullish) is interpretable and comparable to other signals
- Provides a third independent signal, reducing the risk of single-source over-reliance when ESS and Zacks agree

**Structural weaknesses:**
- Lowest coverage in the system (33.7%); absent for 66.3% of analytical universe
- Lowest composite weight (11.1%); a Danelfin=5.0 maximum score cannot overcome ESS=BEARISH alone (see KGC: Danelfin=5.0, composite=2.61 due to ESS=BEARISH)
- Monthly update frequency is slowest of all signals; may be stale during volatile periods
- Danelfin AI methodology is proprietary and not independently verifiable; signal design is a black box
- No internal backtest in this system

**Predictive evidence tier:** MODERATE (useful corroboration only; structurally incapable of overriding ESS in current system)

---

### 5. Yahoo Analyst Buy/Sell Rating (ABR)

| Property | Value |
|---|---|
| Provider | Yahoo Finance (aggregating Wall Street analyst ratings) |
| Signal type | Analyst consensus buy/sell rating aggregate; analyst price target implied upside |
| Coverage (universe) | ~954 / 2,831 = 33.7% |
| Freshness | 2026-05-21 (10 days stale at run date) |
| CW-DAS influence | **ZERO** — not included in composite_score v1 |
| Composite weight | 0% (composite_v2_yahoo field exists but is NULL for all current holdings) |

**Structural strengths:**
- ABR aggregates many analyst opinions, reducing individual analyst bias
- Yahoo upside_pct (implied upside to price target) is a distinct forward-valuation signal not captured by earnings momentum models (ESS, Zacks)
- Can detect overvaluation scenarios where ESS is positive but analysts' price targets are below current price (see CIEN, DELL, CBOE)

**Structural weaknesses:**
- **Not in the scoring path** — Yahoo ABR has ZERO influence on composite_score, CW-DAS, or UCF labels in current system (v1)
- 10-day staleness is the worst of all signals; consensus ratings change slowly but can miss recent news
- Analyst consensus is a lagging indicator; analysts are documented to have herding bias and slow to downgrade
- ABR available only for 33.7% of universe; same coverage gap as Danelfin
- `composite_v2_yahoo` column exists in analytical_universe.csv but is populated with NULL for all current holdings — v2 activation would be a system change

**Predictive evidence tier:** LOW in current system (no scoring path); MODERATE as independent valuation sanity check when consulted manually

---

## Signal Agreement Distribution (PAR-20260601-9CFD7C63)

Of 37 portfolio holdings analyzed:

| Disagreement Level | Count | Examples |
|---|---|---|
| ALIGNED (0 gap) | ~18 | ARW, SNX, ATLC, PSX, AVT, LRCX, CAH, NUE |
| MINOR (1 tier gap) | ~12 | VRT, CBOE, CIEN, DELL, SANM, NVDA |
| MATERIAL (2 tier gap) | 3 | TSM, PCB, PLTR |
| MAJOR (3+ tier gap) | 2 | AEIS, KGC |

**AEIS** is the canonical MAJOR disagreement case: ESS=BEARISH(2) vs Zacks=5.0(Strong Buy) + Danelfin=4.0(Bullish). The 3-tier ESS/Zacks gap is the widest observed. UCF correctly flags `COMPOSITE_ESS_DIVERGE`.

**KGC** shows the ESS vs Danelfin MAJOR case: ESS=BEARISH vs Danelfin=5.0 (maximum bullish). No UCF conflict flag is raised for this type of disagreement (current flags only catch ESS vs composite direction, not ESS vs individual signals).

---

## Key Structural Finding: ESS Double-Counting

ESS influences CW-DAS in two separate components:
1. **Signal component** (0–30): composite_score is 61.1% ESS → ESS contributes up to ~18.3 pts of 30
2. **Momentum component** (0–10): ESS direction directly sets momentum_c; only VERY_BULLISH/BULLISH ESS earns 7.5–10 pts; NEUTRAL or worse earns 0

This means a stock with ESS=NEUTRAL loses 10 pts from momentum_c regardless of Zacks, Danelfin, or Yahoo signals. A stock with ESS=BEARISH loses ~9 pts from signal component AND the full 10 pts from momentum — losing ~19 pts that no other signal can recover, even with Zacks=5.0 + Danelfin=5.0.

This double-counting is architecturally intentional (ESS is the highest-quality signal in the system) but creates operator blind spots when ESS is wrong.

---

## Evidence Ranking Summary

| Rank | Signal | Basis | System Role |
|---|---|---|---|
| 1 | ESS (StarMine/Fidelity) | Institutional-grade, forward-looking, daily, 88.2% coverage, academically validated factor | Dominant (61.1% composite + full momentum component) |
| 2 | Replay Support | Only forward-validated evidence in system (365-day bucket backtest) | Binary gate (20 pts in CW-DAS) |
| 3 | Zacks | High coverage (91.9%), earnings revision model, strong independent signal | Secondary composite input (27.8%) |
| 4 | Composite Direction (aggregate) | Multi-signal convergence of ESS+Zacks+Danelfin reduces single-source risk | Output (feeds signal component) |
| 5 | Danelfin | AI model, orthogonal methodology, but narrow coverage and low weight | Marginal composite input (11.1%) |
| 6 | Yahoo ABR | Useful valuation sanity check; aggregates analyst consensus | Not in scoring path (informational only) |
