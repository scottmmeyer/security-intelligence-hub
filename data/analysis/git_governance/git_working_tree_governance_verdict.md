# Git Working Tree Governance Verdict — Phase GIT-001

## Verdict

**SAFE WITH CLEANUP REQUIRED**

The repository is in a coherent, tested state. No corruption, no risk of data loss, no conflicting changes. Cleanup is administrative (committing many sessions of legitimate work) rather than corrective.

---

## Q1: How many dirty files exist?

**125 entries in `git status --short`**

Breakdown:
- 13 modified tracked files (M)
- 112 untracked files/directories (??)

Note: The 125 entries represent ~200+ actual files when directory contents are expanded. An additional ~5,000+ files (FMP signals, PAR runs, other signal CSVs) are correctly gitignored and do not appear.

---

## Q2: How many are production code?

**~35–40 files**

| Type | Count |
|------|-------|
| Modified tracked src/ files | 7 |
| New untracked src/ files (cra/, scoring/) | ~9 source files |
| New untracked test files | 7 |
| New untracked scripts | 4 |
| Modified tracked config/ | 2 |
| Modified tracked UI files | 2 (app.js, index.html) |
| Modified tracked scripts | 2 (run_outcome_ui.py, refresh_signals.py) |

**Total: ~33 production code files**

---

## Q3: How many are generated artifacts?

**~90 files** (documentation, analysis reports, governance docs)

| Category | Count |
|----------|-------|
| Root-level phase_23_*.md | 68 |
| data/analysis/ phase deliverables | ~20 |
| docs/ methodology/governance/phase | ~25 |

These are **not generated at runtime** — they are intentionally produced governance and architectural documents. The term "generated" is somewhat misleading here: they are human/AI-produced documentation that belongs in source control.

True runtime-generated artifacts (excluded from git): ~5,000+ signal CSV rows, 203 PAR run directories.

---

## Q4: What should be committed?

**Everything except:**
- `data/analysis/fmp_dq_validation.json` (runtime JSON artifact)
- `data/operator/portfolio_alignment_state.json` (runtime operator state)
- Possibly: `scripts/fetch_fmp_validation_set.py` (one-time dev script — either commit or delete)

**Estimated files to commit: ~120 of 125 entries**

The backlog, methodology, CRA module, FMP integration, test suite, UI — all are legitimate, tested, and well-documented changes that should be committed.

---

## Q5: What should be ignored?

Current `.gitignore` correctly excludes:
- All signal data CSVs (`data/signals/**`)
- PAR analysis run directories
- Virtual environment, cache, secrets

**New rules to consider adding:**
```
data/analysis/fmp_dq_validation.json
data/operator/portfolio_alignment_state.json
```

No other additions are necessary. The gitignore is already well-governed.

---

## Q6: What should be reverted?

**NOTHING.**

All 13 modified tracked files represent intentional, phase-delivered, tested changes. None should be reverted. All 1,004 tests pass against the current working tree.

---

## Q7: Is the repository currently in a safe state?

**YES — SAFE, but with accumulated uncommitted work.**

State assessment:
- ✅ All tests pass (1,004 passed, 0 failed)
- ✅ No conflicting changes
- ✅ No corruption or broken state
- ✅ Generated/sensitive data is already gitignored
- ⚠️ ~120 files of legitimate work are uncommitted
- ⚠️ 68 root-level phase documents are at root rather than `docs/` (not a safety issue, aesthetics only)
- ⚠️ `data/operator/portfolio_alignment_state.json` is untracked (contains live operator decisions)

The repository represents approximately 6–8 major development phases of work that have accumulated without commits. This is the normal development pattern for this project (work-in-progress between commit sessions). It is safe to continue working or to commit.

---

## Recommended Immediate Action

The cleanup plan (`working_tree_cleanup_plan.md`) recommends committing in 7 logical groups. The minimum acceptable action is a single consolidation commit:

```bash
git add -A
git reset HEAD data/analysis/fmp_dq_validation.json data/operator/portfolio_alignment_state.json
git commit -m "feat: Multi-phase development (23.0–8.0B.1E) — PAP, CRA, FMP, Company Context, UI, Governance"
```

This creates a recoverable checkpoint before any further development.

**Authorization required for push to remote.**

---

## Classification: SAFE WITH CLEANUP REQUIRED

The codebase is healthy, tested, and coherent. The "cleanup required" is simply committing many sessions of accumulated work — not fixing any problems.
