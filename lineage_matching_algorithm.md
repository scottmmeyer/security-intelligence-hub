# Lineage Matching Algorithm

## Change-to-direction mapping

Observed change classes are normalized to action direction:

- `NEW_POSITION`, `INCREASED` -> `BUY`
- `EXITED_POSITION`, `REDUCED` -> `REDUCE`

## Candidate construction

Candidates are built from PAR history:

1. `recommendations.json`
   - symbol-level candidates from `affected_symbols`
   - theme-level candidates from `drilldown.holdings` when symbol list is absent
2. `deployment_plan.json`
   - symbol-level `BUY` candidates from deployment recommendations
3. `ucf_verdicts.json`
   - `BUY` candidates for conviction/deployment labels
   - `REDUCE` candidates for trim-watch labels

## Matching window

Candidates are evaluated when recommendation date is within 0 to 90 days before the observed snapshot date.

## Confidence rules

For a change with `(symbol, direction, snapshot_date)`:

- `HIGH`
  - symbol match
  - direction match
  - recommendation within 7 days
  - no competing symbol+direction candidate within 7 days
- `MEDIUM`
  - symbol+direction match within 30 days
  - OR theme-level + direction match within 30 days
- `LOW`
  - weak timing symbol+direction match (<= 90 days)
  - OR theme-level-only signal within 90 days
- `NONE`
  - no candidate satisfies above rules

## Candidate ranking

When multiple candidates match:

1. confidence rank (`HIGH` > `MEDIUM` > `LOW`)
2. smaller `days_between`

Selected candidate becomes the lineage attribution for that observed change.

## Outputs

Per change record, persisted lineage includes:

- matched recommendation id/source/date
- confidence
- days between recommendation and observed change

Snapshot-level summary includes:

- total changes
- high/medium/low/unmatched counts
- source breakdown counts
