# UX Sprint 1 — Navigation Design (UX-PA-04)

## Design: Multi-Dim Score to Section Navigation

### Problem

The 4 multi-dimensional scores at the top of the Portfolio Alignment page (Allocation Alignment, Portfolio Quality, Implementation Quality, Replay Alignment) each correspond to a detailed section elsewhere on the page. Users who see a "Needs attention" score have no obvious way to jump to the relevant detail.

### Solution

Added a "↓ View" link to each multi-dim score card. Clicking scrolls smoothly to the target section.

### Mapping

| Score Card | Anchor Target | Section Name |
|---|---|---|
| Allocation Alignment | `#allocationPanel` | Allocation Map |
| Portfolio Quality | `#deploymentQueueContainer` | Deployment Queue |
| Implementation Quality | `#portfolioActionPipelineSection` | Portfolio Action Pipeline |
| Replay Alignment | `#replayPanel` | Replay Alignment & Geography |

### Implementation

- Navigation uses `element.scrollIntoView({behavior:'smooth', block:'start'})`.
- Added `anchor` property to each dim definition object.
- The `navHtml` is generated inline in the card template.
- No dependencies on router or history API — pure DOM scroll.

### CSS

```css
.multidim-nav   { margin-top: 6px; font-size: 0.7rem; color: var(--accent-2); cursor: pointer; text-decoration: underline; text-align: center; }
.multidim-nav:hover { color: var(--primary); }
```

### Rationale

- "↓ View" is a convention used widely in analytics dashboards.
- Color accent-2 (non-primary) communicates "navigation" without distracting from the score itself.
- Smooth scroll maintains context orientation.
