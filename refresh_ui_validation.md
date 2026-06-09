# Refresh UI Validation

Repository: security-intelligence-hub  
Issue: SI-REFRESH-02  
Date: 2026-06-09

## Before / After: Signal Pill Display

### Before (Original)

```
● Zacks    2026-06-09  (fresh)
● Danelfin 2026-06-09  (fresh)
● Yahoo    2026-06-09  (fresh)
```

No coverage detail. Yahoo eps_growth_5yr = 0% invisible.

### After (SI-REFRESH-02)

```
● Zacks    2026-06-09  (fresh)
  671/702 rows · 95.6%
  0% today: abr, price_target, eps_growth

● Danelfin 2026-06-09  (fresh)
  497/497 rows · 100%

◕ Yahoo    2026-06-09  (fresh — partial)    ← orange dot if primary field degraded
  696/697 rows · 99.9%
  0% today: eps_growth_5yr               ← advisory (non-primary field)
```

Note: Yahoo shows FRESH (not FRESH_PARTIAL) in today's run because eps_growth_5yr is a non-primary field. The advisory "0% today: eps_growth_5yr" is still visible, making the gap operator-visible.

## Test Scenarios and Expected Badge Outcomes

| Scenario | sourced_date | Row Coverage | Primary Field Coverage | badge_state |
|---|---|---|---|---|
| Full success (Danelfin) | Today | 100% | 100% | FRESH |
| Near-full success (Zacks) | Today | 95.6% | 95.6% | FRESH (above threshold) |
| Low row coverage | Today | 90% | 90% | FRESH_PARTIAL |
| All rows null (Zacks) | Today | 0% | 0% | FRESH_PARTIAL |
| Primary field 0% (Yahoo price_target) | Today | 100% rows | price_target: 0% | FRESH_PARTIAL |
| Non-primary field 0% (eps_growth_5yr) | Today | 99.9% rows | all primary: OK | FRESH + advisory |
| Empty file | — | 0 rows | — | STALE |
| Yesterday date | Yesterday | n/a | n/a | STALE |
| Mixed dates | Today + yesterday | today rows only counted | per today rows | depends |

## Regression Impact

No existing test was broken. 13 new tests added covering all scenarios above. Full suite: 1174 passed, 1 skipped, 0 failed.
