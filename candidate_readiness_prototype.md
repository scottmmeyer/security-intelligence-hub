# Candidate Readiness Prototype

Display-only prototype, computed from current data and existing symbol sets.

## Proposed Metrics

1. Research Universe Core Freshness Percent

- Definition: percent of research universe symbols that are fresh on Zacks, Danelfin, and Yahoo together.

2. CW-DAS Queue Core Freshness Percent

- Definition: percent of queue symbols fresh on Zacks, Danelfin, and Yahoo together.

3. UCF Ranked Core Freshness Percent

- Definition: percent of UCF-ranked symbols fresh on Zacks, Danelfin, and Yahoo together.

4. Recommendation Candidate Core Freshness Percent

- Definition: percent of primary recommendation symbols fresh on Zacks, Danelfin, and Yahoo together.

5. CRA Deployment Core Freshness Percent

- Definition: percent of CRA deployment symbols fresh on Zacks, Danelfin, and Yahoo together.

6. Stale or Missing Candidate Count

- Definition: count of symbols in each candidate set with any stale or missing core provider state.

## Current Demonstration Values

| Metric | Value |
| --- | ---: |
| Research universe core freshness | 10.1% (251 / 2473) |
| CW-DAS queue core freshness | 96.9% (31 / 32) |
| UCF ranked core freshness | 73.7% (56 / 76) |
| Recommendation primary symbols core freshness | 80.8% (21 / 26) |
| CRA deployment core freshness | 96.8% (30 / 31) |

## Candidate Readiness Display State (Prototype)

Proposed simple status logic:

- HIGH: candidate set core freshness >= 95% and stale_or_missing_count <= 1
- MEDIUM: candidate set core freshness between 80% and 94.9%
- LOW: candidate set core freshness < 80%

Using current values:

- CW-DAS queue: HIGH
- CRA deployments: HIGH
- Recommendation primary: MEDIUM
- UCF ranked: LOW to MEDIUM boundary (73.7%)
- Research universe: LOW

## Why This Helps

This separates holdings-readiness from candidate-readiness and tells the operator whether new-capital candidate quality is improving as rebuild progresses.
