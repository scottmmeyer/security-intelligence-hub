# Phase Final Verdict

## Q1. Why is Research Universe Core Freshness only 10.1%?

On the current live data it is actually `2.1%` (`53 / 2473`).
The metric is low because it requires Zacks, Danelfin, and Yahoo all to be fresh for every symbol in the full analytical universe, and only 53 symbols currently satisfy that three-provider intersection.

## Q2. Is the root cause coverage, freshness, or universe construction?

All three matter, but the immediate dominant cause is provider staleness. Universe construction and denominator choice make the figure look worse operationally.

## Q3. Does rebuild_research_universe actually process the full universe?

It is intended to process the full base-equity universe for Zacks, Danelfin, and Yahoo.

## Q4. Which provider contributes most to the freshness deficit?

Yahoo has the largest stale count, but Zacks, Danelfin, and Yahoo all contribute almost equally to the core-fresh intersection failure because each has only 53 fresh symbols today.

## Q5. Is FMP the dominant bottleneck?

For Data Confidence on deployment surfaces: yes, one of the dominant bottlenecks.
For the Research Universe Core Freshness metric itself: no.

## Q6. Does the 10.1% metric represent a real operational risk?

It represents a real research-cache breadth problem, but not a proportional current portfolio-review risk.

## Q7. Is candidate-readiness overstating or understating deployment risk?

The research-universe metric overstates current deployment risk. Candidate-readiness is closer to actual operator decision risk.

## Q8. Should operators be concerned about the 10.1% value?

Yes, as a universe-health signal. No, as a direct signal that current queue, recommendation, and CRA surfaces are equally unsafe.

## Q9. Is the metric itself flawed?

Not mathematically flawed, but semantically misleading without denominator and provider-context explanation.

## Q10. What is the single most important root cause discovered?

The metric is a full analytical-universe intersection of fresh Zacks, Danelfin, and Yahoo data, while deployment surfaces operate on a much smaller, recently refreshed subset. That denominator mismatch is the most important interpretive issue.

