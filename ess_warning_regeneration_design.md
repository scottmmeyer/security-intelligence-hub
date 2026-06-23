# ESS-COVERAGE-03 Part C - Warning Regeneration Design (No Algorithm Changes)

Date: 2026-06-17
Constraint: Design only; do not implement until root cause confirmation complete.

## Design Goal

Guarantee that data/current/ess_coverage_warning.json freshness is coupled to current merged signal state whenever signal_snapshot.csv changes.

Non-goals:
- No scoring changes
- No recommendation logic changes
- No ESS warning classification model changes

## Root-Cause Target

Current issue:
- Warning write is gated behind persistence success branch.
- Merge update can happen earlier in stage.
- Early return on persistence errors skips warning regeneration.

Design intent:
- Move warning regeneration trigger to a lifecycle point that always executes after merge update succeeds, independent of non-fatal persistence validation results.

## Minimal Safe Remediation Options

### Option A (preferred): Post-merge finally-style regeneration in ESS intake stage

Placement:
- After append_signal_snapshots returns successfully and current signal_snapshot.csv is updated.
- Execute warning build/write in a guaranteed cleanup/finalization section for this stage path.

Behavior:
- Regenerate warning artifact once per successful merge write.
- If persistence validator fails, stage status can remain FAILED/DEGRADED per current policy, but warning file still reflects latest merged state.

Why preferred:
- Smallest change surface.
- Maintains single ownership in ESS intake stage.
- Avoids introducing secondary owner in API/UI/portfolio runner.

### Option B: Regenerate warning at read-time fallback in API/runner

Placement:
- In scripts/run_outcome_ui.py or src/portfolio/runner.py before consuming warning file.

Behavior:
- If warning missing/stale relative to signal_snapshot.csv mtime, recompute and rewrite.

Tradeoffs:
- Introduces write side effects in read paths.
- Duplicates ownership and increases coupling.
- Harder to reason about idempotency and race behavior.

Recommendation:
- Not preferred for this repo architecture.

## Required Guardrails

1. Single write per run
- Ensure warning write happens at most once for each stage execution.

2. Source-of-truth coupling
- Use merged current signal_snapshot.csv as the computation base.

3. Failure semantics preserved
- Do not modify persistence verification pass/fail policy.
- Only decouple warning write from that gate.

4. Artifact observability
- Add lineage/meta field for warning artifact write time and source snapshot date.
- Keep stage metadata fields (counts/examples) aligned with regenerated file.

## Validation Plan (for implementation phase)

1. Unit test: persistence validator error after successful merge
- Expect warning file mtime to advance and contents to reflect new merge.
- Stage may still report failure/degraded per existing policy.

2. Integration test: stale-warning reproduction
- Recreate historical sequence where merge updates but warning previously remained old.
- Verify warning now updates in same run.

3. API/UI truthfulness test
- /api/signal-status returns new warning payload immediately after run.
- UI warning pill and alignment warning match regenerated artifact.

4. Non-regression
- Existing ESS-COVERAGE-02 tests remain green.
- No changes in scoring outputs or recommendation tiers.

## Q1-Q6 Answers

Q1. Why was warning not regenerated?
- Because warning build/write executes only after persistence validation passes; an early return on persistence errors bypasses that step.

Q2. Is warning generation attached to wrong lifecycle event?
- Yes. It is attached to stage-success completion, not directly to merge completion.

Q3. Relation to ESS-COVERAGE-02 changes?
- ESS-COVERAGE-02 introduced warning generation in stage success path. Recent semantic updates improved warning classification but did not remove lifecycle gate causing skip risk.

Q4. Smallest safe fix?
- Keep ownership in ESS intake stage and guarantee warning regeneration after merge success regardless of persistence warning/errors branch outcomes.

Q5. Need algorithm/scoring/model changes?
- No. Root cause is orchestration timing, not warning classification math.

Q6. How to prevent recurrence?
- Enforce artifact freshness invariant: warning artifact timestamp/data must be >= merged snapshot update for same run; add tests for merge-success + persistence-error path.

## Part C Conclusion

A minimal orchestration change, not a scoring change, resolves the regeneration gap. Tie warning rewrite to post-merge lifecycle completion and keep existing validation/scoring behavior intact.