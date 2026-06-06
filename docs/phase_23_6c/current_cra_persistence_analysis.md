# CRA Current Persistence Analysis — Phase 23.6C

## What Currently Exists

### API
- `GET /api/cra/proposal` — builds a fresh `RotationProposal` from the latest COMPLETE PAR run on every request. Stateless; no storage.

### Data Model
`RotationProposal.to_dict()` produces a complete JSON-serializable dict containing:
- `proposal_id`, `run_id`, `as_of_date`, `cra_version`
- `sources` (list of CapitalSourceRecord dicts)
- `deployments` (list of RotationDeploymentTarget dicts)
- `impact` (PortfolioImpactEstimate dict)
- `proposal_status`, `review_flags`, `created_at_utc`
- `suppressed_sources`, `suppressed_source_count`

### UI
- `loadCRAProposal()` — fetches fresh proposal on every analysis load
- `_renderCRAProposal()` — renders sources, rotation map, impact columns
- Include/Skip checkboxes (`_craUpdatePool()`, `_craSkipToggle()`)
- No save, load, export, or clipboard buttons exist

## What Is Transient (Lost on Refresh)

| Data | Lost on? | Notes |
|------|---------|-------|
| Include/Skip checkbox state | Page refresh | Operator selections not persisted |
| Proposal JSON | Page refresh | Re-fetched from PAR run each time |
| Capital pool calculation | Page refresh | Derived from checkbox state |
| Proposal metadata | Page refresh | Created_at_utc changes each fetch |

## What Is Lost on New Portfolio Analysis

| Data | Status |
|------|--------|
| Previous CRA proposal | Replaced by new PAR run |
| Operator Include/Skip selections | Lost |
| Export history | None exists |

## What Needs Persistence

1. **Last generated proposal** — JSON saved to `data/operator/cra_draft.json`
2. **Operator Include/Skip state** — embedded in saved proposal as `operator_include_map`
3. **Export capability** — CSV, Markdown, clipboard summary

## What Must NOT Be Saved

- Raw portfolio CSV file
- Account numbers or holder names
- API keys or credentials
- Portfolio file content

## Storage Decision

`data/operator/cra_draft.json` — single file, latest proposal only. Versioned by `proposal_id` and `created_at_utc`. Simple, low-maintenance, consistent with `portfolio_alignment_state.json` convention.

gitignore: `data/operator/` is NOT gitignored at the directory level — but `portfolio_alignment_state.json` was individually added. CRA draft should be added individually too: `data/operator/cra_draft.json` (will be added to .gitignore as it is runtime operational data).
