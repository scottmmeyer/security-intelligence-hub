# Typed Recommendation Counts Validation

Repository: security-intelligence-hub  
PAR: PAR-20260529-76C900C3 (fresh run with June 9 ESS)  
Date: 2026-06-09

## Validation Method

A fresh `run_analysis()` call was executed against the May-29 portfolio with June 9 ESS signals. The typed counts were extracted directly from the result dict to confirm server-side computation matches the audit predictions.

## Live PAR Output

```
recommendation_count:   33
action_count:            3
blocked_action_count:    3
conviction_anchor_count: 25
narrative_count:         1
explainability_count:    1
observation_count:       0
sum of typed counts:    33  ✓ (matches recommendation_count exactly)
```

## Audit Prediction vs Actual

| Lane | Audit Prediction | Actual | Match |
|---|---|---|---|
| action_count | 3 | 3 | ✓ |
| blocked_action_count | 3 | 3 | ✓ |
| conviction_anchor_count | 25 | 25 | ✓ |
| narrative_count | 1 | 1 | ✓ |
| explainability_count | 1 | 1 | ✓ |
| observation_count | 0 | 0 | ✓ |
| TOTAL | 33 | 33 | ✓ |

## Implementation Method

Typed counts are computed both:

1. **Server-side** (in `runner.py`) — `_compute_typed_rec_counts()` injects additive fields into the run_analysis result and run_metadata:
   - `action_count`, `blocked_action_count`, `conviction_anchor_count`, `narrative_count`, `explainability_count`, `observation_count`
   - Backwards-compatible with existing `recommendation_count` field

2. **Client-side** (in `app.js`) — `computeLaneCounts(recs)` recomputes from the recommendations array at render time for the KPI strip. This ensures the typed count header always reflects the current recommendation set, even in cached views.

## Consistency Rule

`action_count + blocked_action_count + conviction_anchor_count + narrative_count + explainability_count + observation_count === recommendation_count`

This invariant holds for all tested runs.

## Before/After Operator Experience

| Metric | Before | After |
|---|---|---|
| KPI headline | "33 Recommendations" | "3 Actions · 3 Blocked · 25 Anchors · 1 Narratives · 1 Explain" |
| Primary decision count | 33 (overstatement) | 3 (accurate) |
| Workload overstatement factor | ~11× | 1× |
