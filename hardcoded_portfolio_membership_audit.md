# SIGNAL-COVERAGE-03 Hardcoded Portfolio Membership Audit

Date: 2026-06-12

## Scope

Audit objective: identify all hardcoded portfolio-membership definitions and usages, then confirm dynamic holdings architecture.

Search terms used:
- `_PORTFOLIO_SYMBOLS`
- `PORTFOLIO_SYMBOLS`
- `hardcoded holdings arrays`
- `symbol allowlists`
- `manual portfolio membership lists`

Primary search surfaces:
- `scripts/**/*.py`
- `src/**/*.py`
- `tests/**/*.py`
- `docs/**/*.md` (historical references)

## Findings

### 1) `_PORTFOLIO_SYMBOLS` definition and usage

Found in production code before remediation:
- `scripts/refresh_portfolio_signals.py`
  - Definition: static ticker list (`_PORTFOLIO_SYMBOLS = [...]`)
  - Usage A: Danelfin missing-symbol selection
  - Usage B: Yahoo missing-symbol selection

After remediation:
- No `_PORTFOLIO_SYMBOLS` variable remains in production code.
- `scripts/refresh_portfolio_signals.py` now resolves membership dynamically from canonical holdings loader.

### 2) Other hardcoded portfolio membership lists

No additional production portfolio-membership list was found in active refresh/scoring paths.

Additional symbol arrays found during grep were classified as:
- Ad-hoc analysis scripts in `scripts/_*.py` used for one-off diagnostics/report generation.
- Not used by daily provider refresh orchestration.
- Not used by CW-DAS scoring, recommendation generation, DIL/PAP/CRA pipelines.

Examples (non-governance operational path):
- `scripts/_phase_7_8a_ts.py` (`SYMS = [...]`)
- `scripts/_dil_validate.py` (`for sym in [...]`)
- `scripts/phase_7_8a_persistence.py` (operator quick-reference subset)

## Remediation Outcome

- Replaced static membership source in `scripts/refresh_portfolio_signals.py` with:
  - `sorted(_load_portfolio_equity_holdings())`
- Canonical source of truth remains latest PAR holdings:
  - `data/portfolio_ingestion/analysis_runs/PAR-*/holdings.csv` (equities only)
- Portfolio membership is no longer manually maintained in source for this workflow.

## Verification

- Targeted tests: `tests/test_signal_coverage_phase3.py` (4 passed)
- Full regression: `1181 passed, 32 skipped, 50 warnings`

## Final Audit Verdict

Hardcoded portfolio membership has been removed from operational refresh workflows.

Any remaining hardcoded symbol arrays are confined to non-production/ad-hoc analysis scripts and do not govern provider coverage decisions.
