# Workstream Commit Readiness

**Date:** 2026-06-14  
**Branch:** stream/benchmark-attribution-01b

---

## Summary

| Workstream | Code Complete | Tests Present | Tests Pass | Docs Present | Commit Ready |
|-----------|:---:|:---:|:---:|:---:|:---:|
| PIS-005 Refresh Orchestration | ✓ | — | n/a | ✓ | **YES** |
| Benchmark Attribution (BENCH) | ✓ | ✓ | ✓ | ✓ | **YES** |
| PRA-IMPL-02 / 02A | ✓ | ✓ | ✓ | ✓ | **YES** |
| Signal Coverage (SIG-COV) | ✓ | ✓ | ⚠ 3 fail | ✓ | **CONDITIONAL** |
| PIS Forensic Investigation | — | — | n/a | ✓ | **YES** (docs only) |
| Repository Governance | — | — | n/a | ✓ | **YES** (docs only) |

---

## PIS-005 — COMMIT READY

**Code complete:** YES — `artifact_freshness.py`, `refresh_orchestrator.py`, `run_outcome_ui.py` additions  
**Tests present:** NO — No unit test file for orchestrator yet (identified as non-blocker in acceptance audit)  
**Tests pass:** n/a  
**Acceptance audit:** PASSED — all 6 phases, all 14 questions YES  
**Regression surface:** ZERO — no business logic modified  
**Runtime validation:** All layers CURRENT at 2026-06-14  

**Commit ready: YES**  
**Suggested commit message:** `PIS-005: implement derived artifact refresh orchestration`

---

## BENCH — Benchmark Attribution — COMMIT READY

**Code complete:** YES — `benchmark_attribution.py`, `performance_attribution.py`  
**Tests present:** YES — 3 test files  
**Tests pass:** YES — 15 tests pass (test_pis_performance_attribution_01.py, test_pis_benchmark_attribution_01a.py, test_pis_benchmark_attribution_01b.py)  
**Docs present:** YES — 26+ benchmark design documents, acceptance audit  
**UI present:** YES — pis_dashboard app.js (+339 lines), index.html (+60 lines), outcome_visualization additions  
**Outstanding issue:** performance_attribution_acceptance_audit.md notes that the open issue title ("Portfolio Return and Benchmark Attribution") is only partially satisfied — benchmark attribution is implemented; the recommendation outcome portion is separate.

**Commit ready: YES**  
**Suggested commit message:** `BENCH-01B: implement benchmark attribution pipeline and dashboard`

---

## PRA-IMPL-02 / 02A — COMMIT READY

**Code complete:** YES — `funding_policy.py` (new), 6 modified source files  
**Tests present:** YES — 4 new test files  
**Tests pass:** YES — 11 tests pass (test_pra_impl_02_funding_policy.py, test_pra_impl_02a_api_contract.py pass cleanly)  
**Docs present:** YES — 16 pra_impl_02* documents, acceptance verdicts  
**Notes:** `regression_results.md` and `refresh_execution_audit.md` are audit output documents belonging to this workstream.

**Commit ready: YES**  
**Suggested commit message:** `PRA-IMPL-02A: funding policy, depletion model, and API contract`

---

## SIG-COV — Signal Coverage / Refresh — CONDITIONAL

**Code complete:** YES — `holdings_coverage.py` (new), 5 modified files  
**Tests present:** YES — 4 test files  
**Tests pass:** PARTIAL

| Test File | Pass | Fail | Status |
|-----------|------|------|--------|
| test_signal_coverage_phase3.py | 11 | 0 | ✓ |
| test_signal_coverage_phase5.py | Included in above | — | ✓ |
| test_signal_coverage_phase7.py | 7 | 0 | ✓ |
| test_signal_coverage_phase6.py | 2 | **3** | ✗ FAILING |

**Failing tests in test_signal_coverage_phase6.py:**
1. `test_provider_fresh_but_coverage_degraded_triggers_targeted_refresh` — asserts `mode == "coverage_repair"` but gets `"research_refresh"`
2. `test_provider_fresh_and_coverage_compliant_skips` — asserts fetch should not run, but it does
3. `test_provider_fresh_with_missing_applicable_symbol_submits_missing` — same mode mismatch

**Root cause:** The `_refresh_zacks()` function in `scripts/refresh_signals.py` is returning `mode="research_refresh"` in coverage-degraded scenarios where the test expects `mode="coverage_repair"`. The mode routing logic between coverage-triggered and research-triggered refresh is not aligned with the test contracts.

**Commit ready: CONDITIONAL** — resolve 3 failing tests before commit  
**Suggested commit message (when fixed):** `SIG-COV-03: holdings coverage detection and targeted refresh`

---

## PIS-FORENSIC — COMMIT READY (docs only)

**Nature:** Read-only investigation documents generated during forensic audit of PIS lineage/attribution staleness  
**Code:** None  
**Tests:** None  
**Docs present:** YES — 18 investigation reports  
**Commit concern:** These are analysis artifacts. Should be committed to preserve investigation history alongside the PIS-005 code that resolves the findings.

**Commit ready: YES** (as documentation bundle)  
**Suggested grouping:** Include with PIS-005 commit or as standalone `PIS-FORENSIC-01: forensic investigation reports and root cause analysis`

---

## REPO-GOV — COMMIT READY (docs + config)

**Nature:** Governance documents, backlog updates, .gitignore additions, repository planning  
**Code:** `.gitignore` modification only  
**Tests:** None  
**Notes:** .gitignore adds PRA scratch artifact exclusion patterns  

**Commit ready: YES**  
**Suggested grouping:** Can bundle with any workstream commit or as `REPO-GOV: backlog, roadmap, and gitignore updates`

---

## Recommended Commit Order

1. **REPO-GOV** — `.gitignore` first (cleanest to commit independently)
2. **PRA-IMPL-02A** — code complete, tests pass
3. **SIG-COV** — after 3 failing tests are resolved
4. **PIS-005** — code complete, acceptance audit passed
5. **BENCH-01B** — largest workstream, tests pass
6. **PIS-FORENSIC** — document bundle, can go with PIS-005

---

## Blocker Summary

| Blocker | Workstream | Severity | Action |
|---------|-----------|----------|--------|
| 3 failing tests in test_signal_coverage_phase6.py | SIG-COV | MEDIUM | Fix mode routing in `_refresh_zacks()` or fix test expectations |
| No unit tests for PIS-005 orchestrator | PIS-005 | LOW (non-blocker per acceptance audit) | Follow-on task |
