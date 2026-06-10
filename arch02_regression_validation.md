# ARCH-02: Regression Validation

**Date:** 2026-06-09

---

## Regression Outcome

| Suite | Passed | Skipped | Failed |
|---|---|---|---|
| Full test suite (pytest) | 1192 | 1 | **0** |

No regressions introduced.

---

## Change Scope

| Component | Changed? | Notes |
|---|---|---|
| `src/portfolio/deployment_queue.py` | No | CW-DAS unchanged |
| `src/portfolio/cra/capital_source_builder.py` | No | CRA logic unchanged |
| `src/portfolio/cra/rotation_proposal_builder.py` | No | CRA logic unchanged |
| `src/portfolio/recommendations.py` | No | RPS unchanged |
| `src/portfolio/operator_policy.py` | No | Policy engine unchanged |
| `src/portfolio/runner.py` | No | No backend changes |
| `ui/portfolio_alignment/app.js` | **Yes** | ARCH-01 label + ARCH-02 render functions + hook |
| `ui/portfolio_alignment/index.html` | **Yes** | New HTML section + CSS |

All changes are display-only UI additions.

---

## Detailed Change Log

### `app.js`

1. **ARCH-01:** `"Recommended Actions — Top 10"` → `"Deployment Candidates — Top 10"` (1 line)
2. **ARCH-02:** Added `renderReductionQueuePlaceholder()` — shows loading state
3. **ARCH-02:** Added `renderReductionQueue(sources, totalPool, fviData)` — full render
4. **ARCH-02:** Added `_RQ_PRIORITY_ORDER` constant and `_RQ_CATEGORY_LABELS` constant
5. **ARCH-02:** Hook in `loadCRAProposal()` — calls `renderReductionQueue` after CRA loads
6. **ARCH-02:** Hook in `renderResults()` — calls `renderReductionQueuePlaceholder`

### `index.html`

1. **ARCH-02:** New `<div id="reductionQueueContainer" class="rq-section"></div>` after `deploymentQueueContainer`
2. **ARCH-02:** ~60 lines of new CSS for `.rq-*` classes
