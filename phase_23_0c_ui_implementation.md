# Phase 23.0C — C5: UI Implementation

**Status**: COMPLETE  
**Date**: 2026-06-03

## Files Modified

| File | Changes |
|------|---------|
| `ui/portfolio_alignment/app.js` | Phase 23.0C block added; Phase 23.0A Tax-Aware Action block removed |
| `ui/portfolio_alignment/index.html` | CSS replaced, HTML section replaced, script bumped to v7 |
| `scripts/run_outcome_ui.py` | Two new API endpoints added |
| `data/operator/portfolio_alignment_state.json` | Created with FIS seed |

## Architecture

### Section Layout

The Portfolio Action Pipeline section is:
- `id="portfolioActionPipelineSection"` — outer container, `display:none` until analysis loads
- `id="portfolioActionPipelineContent"` — populated by `renderPortfolioActionPipeline(data)`
- Header badges: `id="pipelineActionCount"` + `id="pipelineCategoryCount"`

### Category Accordion

Each category is a `.pap-category` div with:
- `.pap-cat-header` — click to toggle, contains number badge + label + count + chevron
- `.pap-cat-body` — hidden by default, shown when `.pap-expanded` class present
- `pap-auto-expand` class: added to HIGH-priority categories for auto-expand on render

### Script Version

`app.js?v=7` — cache-busted from v6.

## Behavior

- Pipeline section hidden until `renderResults()` is called
- `clearAll()` also hides `portfolioActionPipelineSection`
- `saveTaxState()` re-renders pipeline on success (in case tax state affects display)
- `addStrategicExit()` / `removeStrategicExit()` re-render pipeline live
- `loadStrategicExits()` called at `DOMContentLoaded` (persistent state loaded on boot)

## CSS Classes Added

`.pap-section`, `.pap-panel`, `.pap-panel-header`, `.pap-panel-title`, `.pap-summary-badge`,  
`.pap-empty`, `.pap-category`, `.pap-cat-header`, `.pap-cat-num`, `.pap-cat-label`,  
`.pap-cat-count`, `.pap-cat-chevron`, `.pap-cat-body`, `.pap-cat-empty`, `.pap-tbl`,  
`.pap-sym`, `.pap-protected-badge`, `.pap-pri`, `.pap-pri-HIGH/MEDIUM/LOW`,  
`.pap-row-high`, `.pap-row-med`, `.pap-drift`, `.pap-xref`, `.pap-xref-SIGNAL_DETERIORATION`,  
`.pap-xref-ALLOCATION_REDUCTION`, `.pap-se-manager`, `.pap-se-manager-label`,  
`.pap-se-chips`, `.se-chip`, `.se-chip-sym`, `.se-chip-rm`, `.pap-se-add-row`,  
`.pap-se-input`, `.pap-se-btn`, `.se-status`, `.se-status-ok/warn/error`
