# Benchmark Attribution Gap Review

## Scope Context

This review is for PERFORMANCE-ATTRIBUTION-01B completion readiness prior to implementing additional benchmark logic.

## Explicit Missing Gaps

1. SPY benchmark source
- Missing a dedicated, PIS-owned benchmark source definition and retrieval contract for SPY.

2. Benchmark return series
- Missing persisted benchmark return history aligned to canonical daily dates.

3. Canonical portfolio return series
- Missing canonical portfolio return series output explicitly normalized to the same date windows used for benchmark comparison.

4. Portfolio vs SPY excess return
- Missing deterministic excess-return computation: portfolio return minus benchmark return per aligned interval.

5. Recommendation excess return
- Missing recommendation-level excess-return metric built on benchmark-relative outcomes.

6. Source-level alpha ranking
- Missing aggregated benchmark-relative alpha ranking by recommendation source.

7. Benchmark attribution APIs
- Missing dedicated benchmark endpoints in the PIS API surface for latest/history/summary benchmark views.

8. Benchmark dashboard sections
- Missing benchmark-focused UI sections for portfolio vs SPY, top alpha recommendations, worst relative recommendations, and source alpha ranking.

9. Deterministic benchmark alignment tests
- Missing test suite for date alignment, return-window consistency, excess-return math, and summary aggregation determinism.

## Pre-Implementation Requirements

- Freeze benchmark data ownership contract.
- Define canonical alignment rules for weekends/holidays/missing dates.
- Lock API response schemas before UI integration.
- Add deterministic fixtures for benchmark and portfolio windows.

## Readiness Conclusion

The stream is prepared for implementation planning and execution sequencing, but benchmark logic is not yet complete; the above nine gaps are the mandatory completion set for 01B.
