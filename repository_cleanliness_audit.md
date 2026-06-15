# Repository Cleanliness Audit

## Phase 4 Commands

```bash
git status
git status --porcelain=v1 -uall
git status --porcelain=v1 -uall | wc -l
```

## Q1. Remaining dirty files count?

- Remaining dirty files: `94`

## Q2. Remaining categories?

Remaining classification counts:
- `Signal Coverage / Refresh`: 28
- `Generated Artifact`: 12
- `Documentation Draft`: 19
- `PIS Foundation`: 35
- `Temporary / Ignore`: 0

## Q3. Any unintended leftovers?

Yes.

Remaining `PIS Foundation` leftovers are still present and uncommitted, including:
- `scripts/backfill_pis_snapshots.py`
- `src/pis/__init__.py`
- `src/pis/ingestion.py`
- `tests/test_pis_backfill_01.py`
- `tests/test_pis_phase1.py`
- `ui/pis_dashboard/README.md`
- multiple `docs/pis-001/*`, `docs/pis-001a/*`, `docs/pis-planning/*` files

These are outside the strict four-commit execution scope but relevant to full foundation repository closure.

## Q4. Any generated artifacts still present?

Yes.

Examples include:
- `refresh_execution_audit.md`
- `refresh_button_trace.md`
- `refresh_execution_trace.md`
- `refresh_runtime_evidence.md`
- `regression_results.md`
- `ui_refresh_state_assessment.md`
- `ui_refresh_truthfulness_assessment.md`
- `final_verdict.md`
- `docs/performance-attribution/final_verdict.md`
- `docs/pis-001/final_verdict.md`

## Q5. Any refresh/coverage work still uncommitted?

Yes.

Examples include:
- `scripts/refresh_signals.py`
- `scripts/refresh_portfolio_signals.py`
- `src/scoring/fetch_danelfin_scores.py`
- `src/scoring/fetch_yahoo_supplemental.py`
- `src/scoring/fetch_zacks_scores.py`
- `src/portfolio/runner.py`
- `src/portfolio/holdings_coverage.py`
- `tests/test_signal_coverage_phase3.py`
- `tests/test_signal_coverage_phase5.py`
- `tests/test_signal_coverage_phase6.py`
- `tests/test_signal_coverage_phase7.py`

## Cleanliness Outcome

Working tree is **not clean**.

Current state is acceptable only if interpreted as:
- four required PIS milestone commits completed,
- plus intentionally deferred non-PIS streams still present,
- plus unresolved PIS leftover files requiring follow-up closure commit(s).
