# SIG-COV-03 Commit Report

**Date:** 2026-06-14  
**Commit:** 6e1c40c  
**Message:** SIG-COV-03: holdings coverage detection and targeted refresh

## Test Validation (Pre-Commit)

```
tests/test_signal_coverage_phase3.py   PASS
tests/test_signal_coverage_phase5.py   PASS
tests/test_signal_coverage_phase6.py   5/5 PASS (was 2/5 before fix)
tests/test_signal_coverage_phase7.py   PASS
Total: 23 passed, 0 failed
```

## Files Committed: 34

**Source (7):** holdings_coverage.py (new), refresh_signals.py (fixed _is_stale), refresh_portfolio_signals.py, fetch_danelfin_scores.py, fetch_yahoo_supplemental.py, fetch_zacks_scores.py  
**Tests (4):** test_signal_coverage_phase3/5/6/7.py  
**Docs + Fix (23):** coverage_*.md, holdings_*.md, signal_*.md, refresh_*.md, provider_*.md, spy_coverage_audit.md, ui_refresh_*.md, sig_cov_03_fix_report.md

## Fix Summary

`_is_stale()` changed from strict same-day equality to 2-day tolerance window. Data sourced ≤2 days ago is now research-fresh (enables coverage_repair mode). Data >2 days old triggers full research_refresh.

## Status: COMMITTED ✓
