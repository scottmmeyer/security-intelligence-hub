# Coverage Intent Assessment

## Observed Design Intent

The architecture mixes two universe concepts:

- `base_equity_universe.csv` is the refresh target universe for Zacks, Danelfin, Yahoo, and FMP rebuild logic.
- `analytical_universe.csv` is the denominator for the Research Universe Core Freshness metric.

## Option Assessment

The observed design is closest to Option B:

The analytical universe is broader than what some providers are expected to cover uniformly, and deployment logic operates on a provider-covered subset.

## Evidence

- Refresh rebuild targets `data/current/base_equity_universe.csv`, not `data/current/analytical_universe.csv` directly.
- Deployment-oriented candidate sets are much smaller and much fresher than the full universe.
- The freshness metric does not exclude ADRs, unknown-geography members, or non-standard instruments from the denominator.

## Assessment

The design intent is mixed:

- full-universe freshness is operationally desirable
- but the denominator includes members whose provider coverage is structurally weaker than the active deployment subset

## Verdict

This is not purely a provider-failure problem. It is partly a universe-definition and denominator-intent problem.
