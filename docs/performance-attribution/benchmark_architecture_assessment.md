# BENCHMARK ARCHITECTURE ASSESSMENT
**Date:** 2026-06-11
**Purpose:** Define benchmark architecture for Concentrated Alpha portfolio attribution

---

## 1. Current Fidelity Benchmarks (Already Available)

Fidelity compares SIH portfolio against:
- **S&P 500** — US large cap, market-cap weighted
- **Total Market** (VTI equivalent) — US total market
- **ACWI ex-US** — International equity benchmark

These are the benchmarks Fidelity assigns to each account. The operator already receives these in the Fidelity Performance view.

**Assessment:** Adequate as baseline benchmarks but insufficient for evaluating Concentrated Alpha decisions specifically.

---

## 2. Benchmark Options for Concentrated Alpha

### Option A — S&P 500 (SPY)

**For:**
- Universally recognized
- Most comparable for US large/mid-cap blend
- Fidelity already uses it
- Free via yfinance (SPY)

**Against:**
- Portfolio includes mid-cap, international, and sector-concentrated positions
- Comparing to S&P 500 rewards international underperformance when US outperforms

**Verdict:** Appropriate as *primary benchmark* — operators expect S&P comparison.

---

### Option B — Russell 3000 (IWV)

**For:**
- Broader US equity universe (large + mid + small)
- More appropriate given portfolio's mid-cap exposure
- Free via yfinance

**Against:**
- Less intuitive to operators than S&P 500
- Small-cap exposure creates artificial drag comparisons

**Verdict:** Appropriate as *secondary benchmark* for domestic equity attribution.

---

### Option C — MSCI ACWI (ACWI)

**For:**
- Global coverage — appropriate for portfolio with international holdings (TSM, VEA, DODFX)
- Captures both US and international

**Against:**
- Makes US-outperformance sessions look worse due to international drag
- Operator intent is Concentrated Alpha — a US-dominant strategy

**Verdict:** Include as *reference benchmark* alongside S&P 500, not as primary.

---

### Option D — Custom Concentrated Alpha Benchmark

**Concept:** Blend SPY + VTI + ACWX in proportion matching the mandate's target allocation:
- ~70% S&P 500 (US large)
- ~10% Russell Mid Cap
- ~20% ACWI ex-US

**For:**
- Correctly adjusted for strategy intent
- Eliminates style bias from single-index comparison

**Against:**
- Complex to explain to operator
- Requires target allocation to be formalized
- Maintenance burden if targets change

**Verdict:** Design for Phase 2. Phase 1 should use S&P 500 as primary.

---

### Option E — Blended Strategic Benchmark

**Concept:** Weight benchmarks by current portfolio allocation:
- If portfolio is 80% US → 80% S&P 500 + 20% ACWX
- Recalculated per PAR

**For:**
- Most technically accurate
- Adjusts automatically as portfolio composition changes

**Against:**
- Creates "moving target" — operator cannot develop intuition for what constitutes outperformance
- High complexity for marginal accuracy improvement

**Verdict:** Research artifact, not operator-facing. Defer.

---

## 3. Recommended Benchmark Architecture — Phase 1

### Primary Benchmark
**S&P 500 (SPY)**
- Used in all default attribution displays
- Operator expectation baseline
- Fetchable: `yfinance.download("SPY")`

### Secondary Benchmark
**US Total Market (VTI)**
- Shown alongside S&P 500
- Better captures mid-cap exposure
- Fetchable: `yfinance.download("VTI")`

### International Reference
**MSCI ACWI (ACWI)**
- Used for international allocation attribution
- Context only — not primary performance comparison
- Fetchable: `yfinance.download("ACWI")`

### Implementation Data Requirements

```python
BENCHMARK_TICKERS = {
    "SP500":        "SPY",   # S&P 500 — primary
    "TOTAL_MARKET": "VTI",   # US Total Market — secondary
    "INTL":         "ACWI",  # MSCI ACWI — international reference
}
```

All three are free via yfinance, consistent with existing SIH data infrastructure.

---

## 4. Excess Return Calculation

```
Excess Return (Alpha) = Portfolio Return − Benchmark Return
```

Example (2026-06 observed):
```
Portfolio 1M:  -1.46%
S&P 500 1M:   -1.65%
Alpha:         +0.19%   (outperformed by 19bps)
```

Display format:
```
Portfolio    S&P 500    Alpha
  -1.46%     -1.65%    +0.19%  ▲
```

---

## 5. Phase 2 — Concentrated Alpha Custom Benchmark

To be designed in a future sprint. Requires:
1. Formal Concentrated Alpha mandate target allocation definition
2. Weighted blend calculation engine
3. Approval by operator before using as primary

Placeholder: `CONCENTRATED_ALPHA_BENCHMARK` (referenced in holdings.csv `benchmark_id` field but not yet populated with production data).
