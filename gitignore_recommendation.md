# .gitignore Recommendation
## June 5, 2026

---

## Current Coverage for `data/` (existing .gitignore)

```
data/current/
data/history/**
data/signals/**
data/portfolio_ingestion/analysis_runs/
data/portfolio_ingestion/archive/
data/portfolio_ingestion/incoming/
data/portfolio_ingestion/normalized/
data/portfolio_ingestion/rejected/
data/portfolio_ingestion/manifest.json
data/allocation/
data/derived/
data/operator/portfolio_alignment_state.json
data/operator/cra_draft.json
data/analysis/fmp_dq_validation.json   ← only this one file is excluded
```

**Gap:** `data/analysis/` subdirectories are not ignored except for one specific file.

---

## Q1: Are these generated working artifacts?

**YES.** All files under `data/analysis/` are working analysis outputs, intermediate
research documents, and generated data CSVs produced during development phases.
They are not source code, not tests, not architecture definitions, and not
final deliverables. The finalized versions of this work are captured in `docs/`.

---

## Q2: Do they contain unique information not captured in docs?

**NO.** For the 8 currently untracked files:
- Narrative conclusions are superseded by `docs/phase_cii005/` deliverables
- CSV data is regeneratable from live Yahoo supplemental + FMP feeds
- The checkpoint execution report has no corresponding code artifact

For previously committed `data/analysis/` content (e.g., `phase_22d*/`):
- Those were committed in earlier sessions under the assumption they should be versioned
- They follow the same pattern as untracked content and could reasonably be ignored going forward

---

## Q3: Should they live in the repository permanently?

**NO — for new content going forward.** The `docs/` directory is the appropriate
permanent home for research conclusions, assessments, and certifications. The
`data/analysis/` directory is a working scratchpad whose outputs graduate to `docs/`
when finalized. Versioning the scratchpad creates noise in the commit history.

**Note on previously committed `data/analysis/` content:** Those files are already
in the repo history. Adding `data/analysis/` to `.gitignore` will not remove them
from the repo — it will only prevent new analysis files from being tracked. The
right cleanup for existing committed analysis files is a future `git rm --cached`
operation if desired, but this is NOT part of the current commit.

---

## Q4: Recommended .gitignore Additions

Add the following block to `.gitignore` after the existing `data/analysis/fmp_dq_validation.json` entry:

```gitignore
# Analysis working artifacts — intermediate research outputs.
# Finalized conclusions graduate to docs/.
# Do not version working analysis scratchpad.
data/analysis/phase_*/
data/analysis/git_governance/
```

This is a **narrow** pattern that:
- Only ignores phase-prefixed subdirectories and git_governance
- Does NOT ignore the top-level `data/analysis/` directory
- Does NOT affect the already-ignored `data/analysis/fmp_dq_validation.json`
- Does NOT affect other `data/analysis/` files that may legitimately be committed

A broader alternative `data/analysis/` would also work but would require explicit
`git add -f` for any analysis file someone wanted to commit.

**Recommendation: Use the narrow pattern.** It is more surgical and self-documenting.

---

## No changes made. Recommendation only.
