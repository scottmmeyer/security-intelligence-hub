# SIH DECISION-CONFIDENCE-01 - UI Wireframe Candidate Confidence

## UX Goal

The operator should not have to leave the action surface to understand trust.

The current refresh-health view is useful, but the trust label should sit next to the buy, rank, reduce, or rotate decision itself.

## 1. Deployment Queue Row

```text
ARW
CW-DAS: 102.9
Data Confidence: HIGH

ESS      Fresh   2026-06-22
Zacks    Fresh   2026-06-22
Danelfin Fresh   2026-06-22
Yahoo    Stale   2026-06-18
FMP      Stale   2026-06-04
```

Alternative compact row:

```text
ARW   CW-DAS 102.9   CCL   Data Confidence: MEDIUM
```

Expanded detail on click:

```text
Freshness Issues
- Yahoo stale by 4d
- FMP stale by 18d
```

## 2. Recommendation Card

```text
#4 Reduce EQUITIES.US.MEGA.ULTRA_MEGA allocation

Action Confidence: HIGH
Data Confidence: MEDIUM

Freshness Issues
- MU FMP stale
- TSLA Danelfin stale
```

Single-symbol card:

```text
TSLA
Action Confidence: HIGH
Data Confidence: LOW

Issues
- ESS stale
- Yahoo stale
- Danelfin missing
```

## 3. UCF Ranked Candidate

```text
ARW
UCF Label: CORE_CONVICTION_LEADER
UCF Score: 95.4
Data Confidence: HIGH
```

If degraded:

```text
VRT
UCF Label: CORE_CONVICTION_LEADER
UCF Score: 84.3
Data Confidence: MEDIUM

Reason
- FMP stale
```

## 4. CRA Deployment Candidate

```text
Deploy To: ARW
Target Capital: $2,500
Data Confidence: HIGH
```

## 5. CRA Capital Source Candidate

```text
Source: TSLA
Intent: Thesis Trim
Data Confidence: LOW

Freshness Issues
- ESS stale
- Danelfin missing
```

## 6. Portfolio Action Pipeline / Reduction Candidate

```text
Signal Deterioration
TSLA
Priority: HIGH
Data Confidence: LOW
```

```text
Funding Source
XYZ
Priority: MEDIUM
Data Confidence: MEDIUM

Freshness Issues
- Danelfin stale
- FMP stale
```

## 7. Summary Strip Above Action Surfaces

Recommended compact aggregate block:

```text
Candidate Confidence Summary
HIGH 12   MEDIUM 14   LOW 6
```

Use one summary per action surface:

- Deployment Queue summary
- Recommendation summary
- CRA summary

## Badge Semantics

Recommended visual language:

- `HIGH`: green, current enough to trust operationally
- `MEDIUM`: amber, usable with caution and refresh awareness
- `LOW`: red, stale or missing enough that the operator should verify before acting

## Placement Recommendation

Best placement order:

1. beside score or label on row-level candidate surfaces
2. expanded provider freshness block on hover, expand, or row drilldown
3. aggregate summary above each candidate table or card lane

Worst placement:

- only in global refresh panel
- only in symbol drilldown
- only at the bottom of a recommendation card

That would preserve the current discoverability problem instead of solving it.