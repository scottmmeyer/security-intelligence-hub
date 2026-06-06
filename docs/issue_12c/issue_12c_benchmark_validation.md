# ISSUE-12C — Benchmark Validation

**Date:** June 5, 2026

---

## SPY as Primary Benchmark

Per the ISSUE-12 benchmark assessment, SPY (S&P 500 Total Return) is the
approved primary benchmark. This document validates that the implementation
correctly fetches and uses SPY prices.

---

## Implementation Details

### SPY Price Fetch

```python
spy_prices = fetch_price_history("SPY", spy_start_buf, spy_end_buf)
```

Uses `yf.Ticker("SPY").history(start=..., end=..., auto_adjust=True)`. The
`auto_adjust=True` parameter ensures dividend-reinvested total return prices.

### Date Range Coverage

SPY is fetched once for the entire batch using the min/max of all detection
and outcome dates, plus a ±5-day buffer:

```
spy_start = min(all detection_dates) - 5 days
spy_end   = max(all outcome_dates)   + 5 days
```

This ensures a single SPY fetch covers all detection windows without multiple
network round-trips.

### Benchmark Application

For each detection:
- `spy_price_at_detection`: SPY adjusted close on `detection_date` (or nearest prior trading day)
- `spy_price_at_outcome`: SPY adjusted close on `detection_date + holding_period_days` (or nearest prior)

The same nearest-prior-day fallback logic applies to both symbol and SPY prices,
ensuring temporal alignment.

---

## Test Validation

`test_missing_spy_price_excludes_row` confirms that if SPY prices are not
available for a given detection window, the row is excluded rather than
computing an incomplete excess return. ✅

`test_excess_return_math` confirms that SPY return = (525-500)/500*100 = 5.0%
when SPY moves from 500 to 525. ✅

`test_negative_excess_return_is_loss` confirms LOSS when symbol underperforms
SPY. ✅

---

## Benchmark Limitations

Per the ISSUE-12 benchmark assessment, the following limitations are documented:

1. **Beta mismatch:** SIH holds concentrated positions in large-cap US tech and
   industrials. SPY includes sectors and sizes not represented in the detection
   universe. A detection that simply matches S&P 500 sector momentum would show
   positive excess return even without providing alpha.

2. **Dividend adjustment note:** As described in `issue_12c_math_validation.md`,
   the entry price (from Yahoo supplemental) is unadjusted while outcome prices
   use adjusted close. For SPY, this is consistently applied on both sides of
   the comparison, so the benchmark is internally consistent.

3. **Cap-matched benchmark (deferred):** Using SPY for large-caps, MDY for
   mid-caps, and IJR for small-caps would improve precision. This is deferred
   until the primary analysis is established (ISSUE-12E roadmap).

---

## Scope: No Live SPY Data Yet

As of June 5, 2026, no outcomes are mature (first 30-day window closes July 5,
2026). The SPY benchmark is architecturally validated and ready. Live SPY data
will be fetched when `compute_outcomes()` is first called with mature detections.
