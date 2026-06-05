# Production Code Audit — Phase GIT-001

## Scope
13 modified tracked files + ~25 new untracked source files.

---

## Modified Tracked Files

### src/portfolio/deployment_queue.py
**Change type:** Feature enhancement  
**Phase:** 23.5 / 7.5B — CW-DAS policy rank boost, allocation_node field  
**Purpose:** Added `policy_rank_boost`, `original_rank`, `allocation_node` to DeploymentCandidate; policy-aware ranking  
**Classification: COMMIT**

### src/portfolio/enrichment.py
**Change type:** Feature addition  
**Phase:** Multiple (PAP pipeline extensions)  
**Purpose:** Additional enrichment fields for analyst consensus, fidelity signals  
**Classification: COMMIT**

### src/portfolio/ingestion.py
**Change type:** Feature enhancement  
**Phase:** PAP portfolio parsing improvements  
**Purpose:** V2 Fidelity format support, improved column handling  
**Classification: COMMIT**

### src/portfolio/optimizer.py
**Change type:** Feature enhancement  
**Phase:** PAP optimizer extensions  
**Purpose:** Optimizer improvements for deployment planning  
**Classification: COMMIT**

### src/portfolio/reconciliation.py
**Change type:** Bug fix + enhancement  
**Phase:** Phase 22D / 23.x reconciliation fixes  
**Purpose:** Zero-value position handling, M26CNT069 classification  
**Classification: COMMIT**

### src/portfolio/runner.py
**Change type:** Feature addition (+65 lines)  
**Phase:** PAP runner extensions  
**Purpose:** FMP integration hooks, deployment queue pipeline additions  
**Classification: COMMIT**

### config/allocation_dimensions.yaml
**Change type:** Configuration update  
**Phase:** Phase 23.5 allocation node hierarchy  
**Purpose:** Extended allocation node definitions  
**Classification: COMMIT**

### config/etf_exposure_decomposition.yaml
**Change type:** Registry update  
**Phase:** Phase 22D / 23.x  
**Purpose:** ETF decomposition registry updates (SPAXX cleanup is technical debt but still valid)  
**Classification: COMMIT** (technical debt item tracked as ISSUE-08)

### scripts/refresh_signals.py
**Change type:** Feature addition  
**Phase:** 8.0B.1A — FMP provider integration  
**Purpose:** Added `fmp` as a provider; `_refresh_fmp()` function  
**Classification: COMMIT**

### scripts/run_outcome_ui.py
**Change type:** Major feature addition (+322 lines)  
**Phase:** Multiple (CRA API, security-metadata API, FMP enrichment)  
**Purpose:** New endpoints: `/api/cra/proposal`, `/api/security-metadata` (FMP-enriched)  
**Classification: COMMIT**

### ui/portfolio_alignment/app.js
**Change type:** Major feature addition (+2,013 lines)  
**Phase:** Phases 23.6, 8.0B.X, 8.0B.1B.5, 8.0B.1E, CII-001  
**Purpose:** CRA panel, Company Snapshot, Fundamental Snapshot, Why SIH Likes It, CII modal  
**Classification: COMMIT**

### ui/portfolio_alignment/index.html
**Change type:** Major feature addition (+899 lines)  
**Phase:** Multiple UI phases  
**Purpose:** CRA panel HTML, Company/Fundamental Snapshot CSS, CII modal HTML/CSS, v17  
**Classification: COMMIT**

### tests/test_reconciliation.py
**Change type:** Feature addition (+222 lines)  
**Phase:** Phase 22D/23.x reconciliation improvements  
**Purpose:** Extended test coverage for reconciliation fixes  
**Classification: COMMIT**

---

## New Untracked Production Code

### src/portfolio/cra/ (6 files)
**Phase:** 23.6A through 23.6B.5  
**Purpose:** Capital Rotation Advisor — complete new module  
Files: `__init__.py`, `capital_source_builder.py`, `rotation_proposal_builder.py`, `models.py`, `impact_estimator.py`  
**Classification: COMMIT** — core production feature, 1,004 tests pass

### src/portfolio/operator_policy.py
**Phase:** 23.1/23.2 — Operator Policy Registry  
**Purpose:** Operator policy types, registry, DO_NOT_SELL/SELL_LAST/PREFERRED_ACCUMULATION  
**Classification: COMMIT**

### src/scoring/fetch_fmp_signals.py
**Phase:** 8.0B.1A — FMP signal intake  
**Purpose:** FMP API fetcher for 4 datasets  
**Classification: COMMIT**

### src/scoring/fetch_company_profile.py
**Phase:** 8.0B.X.1 — Company snapshot  
**Purpose:** Yahoo Finance company profile fetcher  
**Classification: COMMIT**

### src/scoring/fmp_universe_enrichment.py
**Phase:** 8.0B.1B — FMP universe enrichment  
**Purpose:** Enrichment module, coverage classifier, load/save functions  
**Classification: COMMIT**

---

## New Untracked Tests

All 7 new test files: **COMMIT**
- `test_cra_phase_23_6a.py` — 89 tests covering all CRA phases
- `test_fmp_phase_8_0b1a.py` — 50 tests for FMP signal intake
- `test_operator_policy.py`, `test_policy_api.py`, `test_23_5_block_diagnostics.py`, `test_apply_policy_to_queue.py`, `test_compute_execution_state.py`

All pass in the current 1,004-test suite.

---

## New Untracked Scripts

### scripts/fmp_bulk_fetch_universe.py
**Phase:** ISSUE-01  
**Purpose:** Production bulk fetcher for FMP full-universe coverage  
**Classification: COMMIT** — operational tool, used for weekly refresh

### scripts/fetch_fmp_validation_set.py
**Phase:** 8.0B.1B development  
**Purpose:** One-time 12-symbol validation fetch  
**Classification: REVIEW** — one-time dev helper; could be committed for historical traceability or deleted

### scripts/fmp_dq_analyze.py, scripts/fmp_dq_validate.py
**Phase:** FMP data quality investigation  
**Purpose:** FMP data quality analysis scripts  
**Classification: REVIEW** — determine if these have ongoing operational value

---

## Summary

| Decision | Count |
|----------|-------|
| COMMIT | ~30 files |
| REVIEW | 3–4 files |
| REVERT | 0 |

**Zero production files should be reverted.** All modifications represent intentional, tested, phase-delivered changes.
