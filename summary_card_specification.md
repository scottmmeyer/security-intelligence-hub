# Summary Card Specification (PIS-UI-03)

## Card 1: Governance Summary

Fields:
- PASS count
- WARNING count
- REJECT count
- top rejection reason
- top warning reason

Data sources:
- `/api/pis/governance-summary`
- `/api/pis/governance/latest`

Reason extraction:
- parse uppercase reason tokens from `reasons`
- count frequency within matching governance status
- choose highest-frequency token or `-`

## Card 2: Canonical Selection Summary

Fields:
- selected dates
- selection policy
- rejected snapshots excluded
- warning snapshots ignored

Data sources:
- `/api/pis/canonical-summary`
- `/api/pis/canonical/latest`
- `/api/pis/governance-summary`

## Card 3: Portfolio Trend

Fields:
- latest value
- prior value
- change
- change %

Data source:
- `/api/pis/summary` (`timeline`)

Computation:
- latest = `timeline[0].portfolio_value`
- prior = `timeline[1].portfolio_value`
- change = `latest - prior`
- change% = `(change / prior) * 100`

## Card 4: Latest Change Detection

Fields:
- new positions
- exited positions
- increased positions
- reduced positions

Data source:
- `/api/pis/changes/latest` (`summary`)

## Card 5: Lineage Summary

Fields:
- matched high
- matched medium
- matched low
- unmatched
- match rate %

Data source:
- `/api/pis/lineage/latest` (`summary`)

Computation:
- matched = `total_changes - unmatched`
- match rate = `matched / total_changes`

## Rendering and Failure Policy

- Cards are visible by default.
- Cards update incrementally as payloads resolve.
- Partial data is allowed; unavailable fields render `-`.
- No card blocks the rest of the dashboard.
