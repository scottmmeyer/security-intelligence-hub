# ISSUE-12C — Math Validation

**Date:** June 5, 2026

---

## Return Formulas

All returns use simple (arithmetic) return, not log return. This matches the
standard used in the ISSUE-12 metrics framework.

### Symbol Return

$$R_{sym} = \frac{P_{t+n} - P_{t_0}}{P_{t_0}} \times 100$$

Where:
- $P_{t_0}$ = `price_at_detection` (stored at run time from Yahoo supplemental `current_price`)
- $P_{t+n}$ = `price_at_outcome` (adjusted close fetched via yfinance at outcome date)
- $n$ = holding_period_days (30, 90, or 180)

### SPY Return

$$R_{SPY} = \frac{P^{SPY}_{t+n} - P^{SPY}_{t_0}}{P^{SPY}_{t_0}} \times 100$$

Uses the same dates as the symbol return. `auto_adjust=True` ensures dividend-
adjusted prices for SPY (SPY pays quarterly dividends; ignoring them would
understate SPY returns and inflate apparent excess returns).

### Excess Return

$$R_{excess} = R_{sym} - R_{SPY}$$

### Outcome Status

| Condition | Status |
|-----------|--------|
| $R_{excess} > +0.25\%$ | WIN |
| $R_{excess} < -0.25\%$ | LOSS |
| $-0.25\% \leq R_{excess} \leq +0.25\%$ | FLAT |

The ±0.25% FLAT band accounts for execution bid-ask spread. A detection with
+0.10% excess return is not meaningfully predictive.

---

## Verified Test Case

**Setup:**
- Symbol: DELL
- `price_at_detection` = $100.00 (stored)
- `price_at_outcome` = $110.00 (90 days later)
- `spy_price_at_detection` = $500.00
- `spy_price_at_outcome` = $525.00

**Calculation:**
$$R_{DELL} = \frac{110 - 100}{100} \times 100 = +10.00\%$$
$$R_{SPY} = \frac{525 - 500}{500} \times 100 = +5.00\%$$
$$R_{excess} = 10.00 - 5.00 = +5.00\% \rightarrow \text{WIN}$$

**Test `test_excess_return_math` confirms:**
- `symbol_return_pct` = 10.00 ± 0.01 ✅
- `spy_return_pct` = 5.00 ± 0.01 ✅
- `excess_return_pct` = 5.00 ± 0.01 ✅
- `outcome_status` = "WIN" ✅

---

## Edge Cases Handled

| Case | Behavior |
|------|---------|
| Weekend/holiday outcome date | Falls back to nearest prior trading day (up to 5 days) |
| Missing SPY price | Row excluded (not imputed) |
| Missing symbol price | Row excluded (not imputed) |
| Empty `price_at_detection` | Row excluded |
| Zero or negative entry price | Row excluded |
| NaN from yfinance | Filtered by `math.isnan()` check |

---

## Adjusted vs. Unadjusted Prices

`yf.Ticker().history(auto_adjust=True)` returns dividend-adjusted close prices.
This is the correct choice because:
1. SPY pays quarterly dividends (~1.3% annual yield); unadjusted prices would
   understate SPY's total return by ~0.3% per quarter
2. Many held securities also pay dividends; adjusted prices capture total return
3. Using the same adjustment for both symbol and benchmark maintains comparability

The `price_at_detection` stored from Yahoo supplemental is `current_price`
(regularMarketPrice, unadjusted). For consistency, the yfinance history call
uses adjusted close for both entry date and outcome date prices. However, the
entry price is stored at run time from Yahoo supplemental (unadjusted).

**This creates a small bias:** the entry price is unadjusted but the outcome
price comparison uses adjusted close. The effect is small for 90-day windows
(typically < 0.3% bias per dividend payment) but should be noted for future
calibration. A future improvement (ISSUE-12D or 12E) could store adjusted
prices at detection time.
