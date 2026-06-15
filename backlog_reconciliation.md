# Backlog Reconciliation

**Date:** 2026-06-15  
**Branch:** stream/pis-006-post-ingestion-trigger  
**Source:** GitHub Issues (open) vs repository artifacts

---

## Open Issues

11 open issues identified via GitHub API:

```
#50: PERFORMANCE-ATTRIBUTION-01: Portfolio Return and Benchmark Attribution [priority-high]
#40: AI-001-OPTION-B: Actual Portfolio Compliance Validator (CPV Rules) [priority-medium, ready]
#38: PA-006: Allocation Drift Trend Visibility [priority-medium, needs-design]
#32: AI-004: Allocation Policy Version Diff Visibility [priority-medium]
#31: AI-003: Allocation Philosophy Explainability Gap [priority-high]
#25: PRA-IMPL-02: Policy-Aware Funding Sources and Allocation Reduction [priority-high, ready]
#17: ISSUE-12D: Dislocation Outcome Review Panel [needs-design]
 #6: EPIC: Governance and Tooling [epic]
 #5: EPIC: Signal Intelligence Evolution [epic]
 #3: EPIC: Portfolio Action Pipeline (PAP) [epic]
 #2: EPIC: Capital Rotation Advisor (CRA) [epic]
```

---

## Issue-by-Issue Assessment

### Issue #50 — PERFORMANCE-ATTRIBUTION-01

**Repository evidence:**
- `src/pis/performance_attribution.py` — 503 lines, full implementation
- `src/pis/benchmark_attribution.py` — 832 lines, full implementation
- `data/history/pis/attribution/attribution_records.csv` — 14 records, date through 2026-06-14
- `data/history/pis/benchmark_attribution/benchmark_return_series.csv` — 17 intervals, all OK quality
- `data/history/pis/benchmark_attribution/recommendation_benchmark_records.csv` — 28 records
- `data/history/pis/benchmark_attribution/source_benchmark_summary.csv` — active
- Tests: `tests/test_pis_performance_attribution_01.py`, `test_pis_benchmark_attribution_01a.py`, `test_pis_benchmark_attribution_01b.py` — all pass
- Dashboard: benchmark attribution panel populated; 17 intervals; 28 included rows; 0 excluded

**Determination:** COMPLETE (with one known behavioral characteristic — see Issue #50 forensic analysis below)

---

### Issue #31 — AI-003: Allocation Philosophy Explainability

**Repository evidence:**
- `src/sih/allocation_explainability.py` — implemented (modified in AI-003 commit `18fbbd8`)
- Commit `18fbbd8`: "AI-003: implement deterministic allocation philosophy explainability"
- `scripts/run_outcome_ui.py`: `/api/explanations/latest`, `/api/explanations/summary`, `/api/explanations/{id}` endpoints all wired
- `data/history/explanations/` — exists with generated explanation artifacts
- Policy drivers, signal drivers, funding drivers, philosophy mapping implemented

**Determination:** COMPLETE — can be closed

---

### Issue #25 — PRA-IMPL-02: Policy-Aware Funding Sources and Allocation Reduction

**Repository evidence:**
- `src/portfolio/cra/funding_policy.py` — implemented (new file in PRA-IMPL-02A commit)
- `src/portfolio/cra/capital_source_builder.py` — modified
- `src/portfolio/cra/models.py` — modified
- `src/portfolio/recommendations.py` — modified
- Tests: `test_pra_impl_02_funding_policy.py`, `test_pra_impl_02a_api_contract.py`, `test_pra_impl_02a_pap_rationale.py`, `test_pra_impl_02a_serialization_contracts.py` — 16 passed
- Acceptance audit: `pra_impl_02a_final_verdict.md` — ACCEPT

**Determination:** COMPLETE — can be closed

---

### Issue #40 — AI-001-OPTION-B: Portfolio Compliance Validator

**Repository evidence:** No `compliance_validator.py` or CPV implementation found in codebase. No test files matching CPV. No acceptance artifact.

**Determination:** OPEN — not implemented

---

### Issue #38 — PA-006: Allocation Drift Trend Visibility

**Repository evidence:** Label says `needs-design`. No implementation artifacts found.

**Determination:** OPEN (needs design)

---

### Issue #32 — AI-004: Allocation Policy Version Diff Visibility

**Repository evidence:** No implementation found. No acceptance artifacts.

**Determination:** OPEN — not implemented

---

### Issue #17 — ISSUE-12D: Dislocation Outcome Review Panel

**Repository evidence:** Label says `needs-design`. Some preliminary design files in `docs/issue_12c/` but no implementation.

**Determination:** OPEN (needs design)

---

### EPICs (#2, #3, #5, #6)

**Determination:** OPEN — epics by design; remain open until all child issues complete

---

## Issue Closure Candidates

| Issue | Status | Evidence | Recommend Close? |
|-------|--------|---------|-----------------|
| #50 | COMPLETE | Full implementation + tests + dashboard | YES (see forensic review) |
| #31 (AI-003) | COMPLETE | Commit 18fbbd8 + API endpoints + artifacts | YES |
| #25 (PRA-IMPL-02) | COMPLETE | Commit 8791ee9 + 16 tests + verdict | YES |
| #40 | OPEN | No implementation | NO |
| #38 | OPEN | Needs design | NO |
| #32 | OPEN | Not implemented | NO |
| #17 | OPEN | Needs design | NO |

---

## Recommended Next Implementation

After closing #50, #31, #25, the highest-priority remaining open issue is:

**#40 — AI-001-OPTION-B: Portfolio Compliance Validator (CPV)**  
Label: `priority-medium, ready`

This is a discrete, well-scoped compliance validation feature that complements the existing portfolio analysis pipeline.
