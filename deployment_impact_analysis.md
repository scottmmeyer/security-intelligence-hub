# Deployment Impact Analysis

## Current Readiness Snapshot

- Research Universe: `2.1%` (`53 / 2473`)
- CW-DAS Queue: `96.9%`
- UCF Ranked: `73.7%`
- Recommendations: `80.8%`
- CRA Deployments: `96.8%`

## Finding

The low research-universe freshness score does not propagate proportionally into deployment surfaces.

## Why

CW-DAS, UCF, Recommendations, and CRA all operate on a much smaller, provider-covered subset centered on:

- active holdings
- current deployment candidates
- recommendation-eligible symbols

## Impact by System

### CW-DAS

Limited immediate impact. The queue is nearly fully core-fresh.

### UCF

Moderate impact only where ranked symbols fall outside the most recently refreshed subset.

### Recommendations

Limited immediate impact for the current portfolio review bundle.

### CRA

Limited immediate impact because deployment and source rows are mostly fresh.

### Portfolio Review

Current operator review risk is lower than the research-universe metric alone suggests.

## Conclusion

The `2.1%` research-universe figure overstates current deployment risk while still signaling a real universe-wide staleness problem.
