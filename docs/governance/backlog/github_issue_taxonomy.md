# GitHub Issue Taxonomy — Phase 8.0B.1D

## Label System

### Type Labels

| Label | Color | Description |
|-------|-------|-------------|
| `epic` | #8B5CF6 purple | Top-level initiative grouping multiple issues |
| `enhancement` | #3B82F6 blue | New feature or capability |
| `bug` | #EF4444 red | Defect or incorrect behavior |
| `governance` | #6B7280 gray | Process, documentation, standards work |
| `technical-debt` | #F97316 orange | Known cleanup with no behavioral change |
| `research` | #14B8A6 teal | Investigation, audit, validation |
| `ui-ux` | #EC4899 pink | Frontend/display work |
| `data-quality` | #FBBF24 yellow | Data validation, null handling, coverage |

### Component Labels

| Label | Color | Description |
|-------|-------|-------------|
| `fmp` | #0EA5E9 light blue | Financial Modeling Prep integration |
| `cra` | #7C3AED purple | Capital Rotation Advisor |
| `pap` | #1D4ED8 dark blue | Portfolio Action Pipeline |
| `cwdas` | #065F46 green | CW-DAS scoring formula |
| `sti` | #92400E brown | Strategic Intelligence (STI/UCF) |
| `ess` | #BE185D pink | ESS signal pipeline |
| `replay` | #115E59 teal | Replay scoring system |
| `ui` | #6D28D9 violet | UI-specific (combined with ui-ux for clarity) |
| `provider` | #1E3A5F navy | External data provider (Yahoo, Zacks, FMP, etc.) |

### Priority Labels

| Label | Color | Description | SLA |
|-------|-------|-------------|-----|
| `priority-critical` | #DC2626 red | Blocking operator use or data integrity | Immediate |
| `priority-high` | #EA580C orange | High operator value, near-term roadmap | Next 1–2 sessions |
| `priority-medium` | #D97706 amber | Meaningful improvement, not urgent | Next 5–10 sessions |
| `priority-low` | #4B5563 gray | Nice-to-have, low urgency | Deferred |

### Status Labels

| Label | Color | Description |
|-------|-------|-------------|
| `ready` | #16A34A green | Fully scoped, can be implemented immediately |
| `needs-design` | #9333EA purple | Requires design phase before implementation |
| `blocked` | #DC2626 red | Blocked by a dependency or authorization gate |
| `deferred` | #6B7280 gray | Explicitly deferred to a future milestone |
| `in-progress` | #3B82F6 blue | Currently being worked |

---

## Milestone Structure

GitHub Milestones map to roadmap phases:

| Milestone | Scope |
|-----------|-------|
| `FMP Integration Track` | 8.0B.1A through 8.0B.2 |
| `CRA Track v2` | 23.6C through 23.6D |
| `Company Context Track` | 8.0B.X through 8.0B.X.3 |
| `Governance & Backlog` | 8.0B.1D, standards, tooling |
| `Scoring Evolution` | 8.0B.1C, CW-DAS enhancements |
| `Technical Debt Cleanup` | TD items, registry cleanup |
| `UI Enhancement Track` | Dislocation Watchlist, filters, exports |

---

## Issue Template

```markdown
## Summary
One sentence describing the change.

## Context
Why this matters. Link to relevant design documents or phase verdicts.

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Regression suite passes (n tests, 0 failures)
- [ ] No scoring/ranking/recommendation changes (if display-only)

## Design Documents
- Link to relevant .md files in docs/

## Phase Reference
Phase X.Y.Z

## Non-Negotiables
List any constraints (e.g., "NO scoring changes")

## Estimated Effort
XS / S / M / L / XL
```

---

## Label Usage Examples

| Issue | Type | Component | Priority | Status |
|-------|------|-----------|----------|--------|
| FMP Bulk Fetch | enhancement | fmp, provider | priority-high | ready |
| Graduated Drift Penalty | enhancement | cwdas | priority-medium | needs-design |
| YAML Registry Cleanup | technical-debt | pap | priority-low | ready |
| CRA Draft Persistence | enhancement | cra, ui-ux | priority-high | ready |
| FMP Score Integration Assessment | research | fmp, cwdas | priority-high | needs-design |
| Dislocation Watchlist | enhancement | ui-ux | priority-medium | needs-design |
