# Dashboard KPI Model (PIS-UI-03)

## KPI Set

1. `Snapshots`
- Source: `/api/pis/snapshots`
- Metric: `snapshots.length`

2. `Canonical Days`
- Source: `/api/pis/canonical-summary`
- Metric: `selected_dates`

3. `PASS`
- Source: `/api/pis/governance-summary`
- Metric: `status_counts.PASS`

4. `WARNING`
- Source: `/api/pis/governance-summary`
- Metric: `status_counts.WARNING`

5. `REJECT`
- Source: `/api/pis/governance-summary`
- Metric: `status_counts.REJECT`

6. `Latest Portfolio Value`
- Source: `/api/pis/latest`
- Metric: `total_value`
- Format: currency

7. `Latest Change`
- Source: `/api/pis/changes/latest`
- Metric: `summary.portfolio_value_change`
- Format: signed currency

8. `Lineage Matches`
- Source: `/api/pis/lineage/latest`
- Metric: `matches.length`

## Formatting Rules

- Integer-like values: localized integer formatting.
- Currency: USD compact with sign for deltas.
- Missing/unknown values: `-`.

## Update Strategy

- KPI strip initializes with loading shell.
- KPI strip recomputes after each relevant payload completion.
- No polling; update is tied to existing progressive load cycle.

## Error Handling

- If a contributing endpoint fails, unaffected KPIs still render from available payloads.
- Failed-source KPI values remain `-` or `0` depending on semantic default.
