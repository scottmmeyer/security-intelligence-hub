# Copilot Execution Standard — Phase 8.0B.1D

## Overview

This standard defines how all future SIH development work is executed when using GitHub Copilot as the implementation agent.

The goal: ensure every change is scoped, governed, traceable, and reversible.

---

## Workflow

```
GitHub Issue
  → Design Phase (for M/L/XL issues)
  → Implementation
  → Validation
  → Certification Report
  → Issue Closure
  → Roadmap Update
```

---

## Step 1: GitHub Issue Creation

Every non-trivial change starts with a GitHub Issue.

**Required fields:**
- Title (action-oriented, e.g., "Add Graduated Drift Penalty to CW-DAS")
- Description (context, why it matters)
- Acceptance Criteria (checkboxes)
- Labels (type + component + priority + status)
- Epic reference
- Non-Negotiables section (explicit constraints)

**Non-Negotiables template:**
```
## Non-Negotiables
- NO scoring changes (if display-only)
- NO ranking changes
- NO recommendation changes
- Regression suite must pass (n tests, 0 failures)
```

---

## Step 2: Design Phase

Required for all issues labeled `needs-design`. Skip for `ready` issues with XS/S effort.

**Design phase produces:**
- Design document in `docs/` or `data/analysis/phase_X/`
- Field mapping (if data is involved)
- Risk assessment
- Counterfactual analysis (if scoring change)
- Governance verdict document

**Design phase ends with a classification:**
- `APPROVED` — proceed to implementation
- `APPROVED WITH ADVISORIES` — proceed with noted constraints
- `BLOCKED` — do not implement; document reason

---

## Step 3: Implementation

**Before starting:**
- Mark issue `in-progress`
- Confirm design document is approved
- Read target files before editing
- Confirm test count before changes

**During implementation:**
- One logical change per commit / session block
- Prefer `multi_replace_string_in_file` for multi-file changes
- Check `node --check` for JS changes
- Run `pytest -q` after every meaningful change

**Constraints:**
- Never modify scoring formulas without explicit authorization
- Never bypass safety checks (`--no-verify`, `--force`)
- Never delete files without confirmation
- Never push to remote without user instruction

---

## Step 4: Validation

Every implementation must include:

| Check | Required |
|-------|---------|
| `node --check app.js` | Always (for JS changes) |
| `pytest -q` with test count | Always |
| Browser smoke test (if UI) | For UI changes |
| Live API validation (if backend) | For API changes |
| Regression: 0 test failures | Always |
| Score/ranking unchanged (if display-only) | Display-only phases |

---

## Step 5: Certification Report

For phases M and above, produce a certification document:

**Template:**
```markdown
# Phase X.Y.Z Certification

## Verdict: APPROVED / APPROVED WITH ADVISORIES / BLOCKED

## Changes Made
- File: description of change
- File: description of change

## Validation Results
- Test count: N passed, 0 failed
- JS syntax: SYNTAX OK
- API validation: [results]
- Score/ranking impact: NONE

## Governance Compliance
- Non-Negotiables: all respected
- Acceptance Criteria: all met

## Next Authorized Phase
Phase X.Y.(Z+1) — [title] — AUTHORIZED
```

---

## Step 6: Issue Closure

Checklist before closing:
- [ ] All Acceptance Criteria checked
- [ ] Certification report created or referenced
- [ ] No regressions
- [ ] Issue linked to relevant commit or deliverable

Close issue with reference to deliverable:
> "Closed by Phase X.Y.Z — [certification document path]"

---

## Step 7: Roadmap Update

After issue closure:
1. Update `docs/governance/backlog/roadmap_recommendation.md`
2. Update relevant epic in `epic_structure.md`
3. Note next authorized phase in next session startup

---

## Phasing Conventions

### Phase numbering
- Major phases: `23.6`, `8.0B.1`
- Sub-phases: `23.6B.4`, `8.0B.1A.1`
- Micro-phases: `8.0B.X.2`, `8.0B.1B.5`

### Governance language
- `AUTHORIZED` — approved to execute, dependencies met
- `DEFERRED` — intentionally postponed, reason documented
- `BLOCKED` — cannot proceed, dependency unmet
- `COMPLETE` — delivered and certified

---

## Communication Standard

When reporting phase completion, always state:
1. What was built / what changed
2. What was NOT changed (non-negotiables confirmation)
3. Test count
4. Next authorized phase

**Example:**
> "Phase 8.0B.1B.5 complete. APPROVED. Added Fundamental Snapshot UI section with Thesis Integrity, Fundamental Consistency, and Dislocation classification. No scoring, ranking, or recommendation changes. 1,004 tests passing. Phase 8.0B.1C is authorized."

---

## Anti-Patterns to Avoid

| Anti-Pattern | Correct Behavior |
|-------------|-----------------|
| Implementing without reading target files | Read before editing |
| Multiple unrelated changes in one session | One logical change per session block |
| Undocumented deferred work | All deferred work logged in GitHub Issues |
| "Improvements" beyond scope | Implement exactly what was asked |
| Running `git push` without user instruction | Never push without explicit request |
| Skipping regression check | Always run `pytest -q` before marking done |
| Creating markdown files without being asked | Only create docs when explicitly requested |
