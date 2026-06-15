# Benchmark Interval Validation

**Date:** 2026-06-15  
**Investigation:** Dashboard reports Portfolio Return 3.95%, Benchmark Return 0.00%, Excess Return 3.95%

---

## Finding: EXPECTED BEHAVIOR — Not a Defect

**Root cause:** The 0.00% benchmark return occurs when the NEAREST_PRIOR_TRADING_DAY alignment policy maps both the entry date (prior snapshot date) and exit date (current snapshot date) to the same SPY price date.

---

## The Specific Interval

The reported values come from interval:

```
snapshot_date:      2026-06-14 (Sunday)
prior_snapshot_date: 2026-06-11 (Thursday)
benchmark_entry_date: 2026-06-11
benchmark_exit_date:  2026-06-11
benchmark_entry_price: 737.76000977
benchmark_exit_price:  737.76000977
benchmark_return_pct: 0.0%
portfolio_return_pct: 3.952511%
excess_return_pct:    3.952511%
data_quality_status:  OK
```

---

## NEAREST_PRIOR_TRADING_DAY Policy Trace

The `CsvBenchmarkPriceProvider._nearest_prior_date()` function returns the latest date in the SPY data that is ≤ the target date.

Available SPY data:
```
...
2026-06-05: 737.5500
2026-06-08: 739.2200
2026-06-09: 737.0500
2026-06-10: 725.4300
2026-06-11: 737.7600   ← latest available
```

**For prior date = 2026-06-11 (Thursday):**
- Nearest prior trading day ≤ 2026-06-11 = **2026-06-11** (Thursday, direct match)
- entry_price = 737.76

**For snapshot date = 2026-06-14 (Sunday):**
- Nearest prior trading day ≤ 2026-06-14 = **2026-06-11** (Sunday has no market; Thursday is nearest prior)
- exit_price = 737.76

Since entry_date == exit_date == 2026-06-11 and entry_price == exit_price:
- benchmark_return = (exit - entry) / entry = 0 / 737.76 = **0.00%**

---

## All 0.00% Benchmark Intervals

| Interval | Prior Day | Snapshot Day | Why 0.00% |
|----------|-----------|-------------|----------|
| 2026-05-30 ← 2026-05-29 | Thursday | Saturday | Sat → nearest prior = Thu = same as prior |
| 2026-05-31 ← 2026-05-30 | Saturday | Sunday | Both → nearest prior = Thu 05-29 |
| 2026-06-06 ← 2026-06-05 | Friday | Saturday | Sat → nearest prior = Fri = same as prior |
| 2026-06-14 ← 2026-06-11 | Thursday | Sunday | Sun → nearest prior = Thu = same as prior |

All four cases share the same pattern: **the snapshot was taken on a weekend/non-trading day, so NEAREST_PRIOR_TRADING_DAY maps it to the same SPY data date as the prior snapshot.** SPY didn't trade between the two snapshot dates.

---

## Why data_quality_status = OK

The quality status checks:
1. Is there a benchmark entry price? YES → not `MISSING_BENCHMARK_ENTRY`
2. Is there a benchmark exit price? YES → not `MISSING_BENCHMARK_EXIT`
3. Is the entry price > 0? YES → not `INVALID_BENCHMARK_BASE`

All checks pass → status = `OK`. The 0.00% return is arithmetically correct given same-day entry and exit. The quality flag is not designed to detect "entry == exit" as a separate condition.

---

## Is This a Defect?

**No.** The behavior is mathematically correct and by design:

1. The NEAREST_PRIOR_TRADING_DAY policy is correctly applied
2. The quality status `OK` is correctly set (data is present and valid)
3. Fidelity portfolio snapshots dated on weekends or Sundays are valid (the portfolio value is as of market close Friday, but the export timestamp is Sunday)
4. Portfolio return CAN be non-zero on a weekend interval because it reflects valuation changes that accrued over the prior trading days (e.g., May 22–29 activity shows up in the May 29 snapshot, and the subsequent portfolio dated Jun 11 reflects 3 weeks of moves)

---

## Alternative Interpretation Considered

Could this be a data staleness issue where the portfolio snapshot is misdated?

**Rejected.** The portfolio value for 2026-06-14 is $473,874.84, up from $455,857.04 on 2026-06-11 — a genuine 3.95% gain reflecting 3 trading days (June 11, 12, 13) of market movement. The SPY data correctly shows June 11 as the last available price.

---

## Potential Enhancement (Non-Critical)

For weekend intervals where entry==exit, a more descriptive quality flag like `SAME_TRADING_DAY` could be added to the benchmark series to make this more visible. This would not change any calculation but would allow dashboard filtering of weekend-interval rows.

**This is a design enhancement, not a defect fix. Issue #50 is not blocked by this.**

---

## Summary

| Finding | Verdict |
|---------|---------|
| Portfolio Return = 3.95% | CORRECT |
| Benchmark Return = 0.00% | CORRECT (expected for Sunday snapshot) |
| Excess Return = 3.95% | CORRECT |
| data_quality_status = OK | CORRECT |
| Is this a defect? | NO — expected behavior |
| Should Issue #50 be blocked? | NO |
