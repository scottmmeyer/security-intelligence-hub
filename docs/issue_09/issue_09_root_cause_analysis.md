# ISSUE-09 Root Cause Analysis

## Error
`ReferenceError: _craProposal is not defined`

Visible in the CRA panel of the Portfolio Alignment UI after a portfolio analysis is loaded.

## Root Cause

**Missing variable declaration.**

`_craProposal` was previously declared as a module-level variable (`let _craProposal = null;`) in `app.js`. During the ISSUE-07 implementation (Phase 8.0B.1C — Fundamental Conviction Modifier), the CRA section of `app.js` was refactored. In that refactoring, the `let _craProposal = null;` declaration was inadvertently removed while the variable remained referenced throughout the CRA code.

**Timeline:**
- Pre-ISSUE-07: `let _craProposal = null;` declared before `const _CRA_CATEGORIES = [...]`
- ISSUE-07 refactoring: The `_dqCompanySnapshotHtml` function block was reorganized. The `let _craProposal = null;` line was lost in the process.
- Post-ISSUE-07: All references to `_craProposal` survive (assignments in `loadCRAProposal()`, `_craLoadDraft()`, etc.) but the declaration is absent.

## Why It Causes a ReferenceError

In strict-mode JavaScript (and modern browser JS engines), accessing an undeclared variable throws `ReferenceError: _craProposal is not defined`. The assignments (`_craProposal = await resp.json()`) would have implicitly created a global variable in non-strict contexts, but accessing the variable *before* the first assignment — which happens when `renderResults()` calls `loadCRAProposal()` → which tries to `_renderCRAProposal(_craProposal)` — throws the error.

## Scope of Impact

- **CRA panel displays error** on every portfolio analysis load
- **CRA proposal generation** fails — the proposal is fetched from the API but `_craProposal` cannot be set
- **CRA save/load/export** all fail — they all check `if (!_craProposal) return;`
- **No impact on**: CW-DAS scoring, deployment queue, recommendations, PAP, STI, ESS

## Evidence

```javascript
// Line 4356 (BEFORE FIX): Assignment without prior declaration
_craProposal = await resp.json();   // ReferenceError on the line above that reads _craProposal
```
