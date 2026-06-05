# Dirty File Inventory — Phase GIT-001

## Summary

**Total dirty entries in `git status --short`:** 125  
**Modified tracked files (M):** 13  
**Untracked files/directories (??):** 112  

Note: Many untracked entries are directory placeholders — the actual file count within those directories is significantly higher. The 203 PAR analysis run directories and 4 FMP signal CSVs are gitignored and do not appear in `git status --short`.

---

## Breakdown by Category

### Category 1 — Production Code (Modified — tracked files)
**Count: 13 files**

| File | Change Type | Notes |
|------|------------|-------|
| `src/portfolio/deployment_queue.py` | Modified | CW-DAS Phase 23.5/7.5B changes |
| `src/portfolio/enrichment.py` | Modified | Enrichment pipeline extensions |
| `src/portfolio/ingestion.py` | Modified | Ingestion parser additions |
| `src/portfolio/optimizer.py` | Modified | Portfolio optimizer changes |
| `src/portfolio/reconciliation.py` | Modified | Reconciliation fixes |
| `src/portfolio/runner.py` | Modified | PAR runner additions |
| `config/allocation_dimensions.yaml` | Modified | Allocation node configuration |
| `config/etf_exposure_decomposition.yaml` | Modified | ETF decomposition registry |
| `scripts/refresh_signals.py` | Modified | FMP provider added |
| `scripts/run_outcome_ui.py` | Modified | New API endpoints (+322 lines) |
| `ui/portfolio_alignment/app.js` | Modified | Major additions (+2,013 lines) |
| `ui/portfolio_alignment/index.html` | Modified | CSS + modal additions (+899 lines) |
| `tests/test_reconciliation.py` | Modified | Reconciliation test extensions (+222 lines) |

### Category 2 — New Production Code (Untracked)
**Count: ~25 files across directories**

| Path | Contents | Notes |
|------|---------|-------|
| `src/portfolio/cra/` | 6 files: `__init__.py`, `capital_source_builder.py`, `rotation_proposal_builder.py`, `models.py`, `impact_estimator.py`, `__pycache__` | Capital Rotation Advisor module |
| `src/portfolio/operator_policy.py` | 1 file | Operator Policy Registry |
| `src/scoring/fetch_fmp_signals.py` | 1 file | FMP signal fetcher |
| `src/scoring/fetch_company_profile.py` | 1 file | Company profile fetcher |
| `src/scoring/fmp_universe_enrichment.py` | 1 file | FMP enrichment module |

### Category 3 — New Tests (Untracked)
**Count: 7 files**

| File | Associated Phase |
|------|----------------|
| `tests/test_cra_phase_23_6a.py` | CRA Phase 23.6A |
| `tests/test_fmp_phase_8_0b1a.py` | FMP Phase 8.0B.1A |
| `tests/test_operator_policy.py` | Operator Policy |
| `tests/test_policy_api.py` | Policy API |
| `tests/test_23_5_block_diagnostics.py` | Phase 23.5 block diagnostics |
| `tests/test_apply_policy_to_queue.py` | Policy queue application |
| `tests/test_compute_execution_state.py` | Execution state computation |

### Category 4 — New Scripts (Untracked)
**Count: 4 files**

| File | Purpose | Commit? |
|------|---------|---------|
| `scripts/fmp_bulk_fetch_universe.py` | Production FMP bulk fetcher | YES |
| `scripts/fetch_fmp_validation_set.py` | One-time validation helper | REVIEW |
| `scripts/fmp_dq_analyze.py` | FMP data quality analysis | REVIEW |
| `scripts/fmp_dq_validate.py` | FMP data quality validation | REVIEW |

### Category 5 — Governance / Documentation (Untracked)
**Count: ~50 files across directories**

| Directory | Contents | Commit? |
|-----------|---------|---------|
| `docs/methodology/` | 9 CII methodology docs | YES |
| `docs/governance/` | Backlog, taxonomy, epics, roadmap, standards | YES |
| `docs/phase_23_6/` through `docs/phase_23_6b5/` | Phase 23.6 documentation | YES |
| `docs/phase_8_0b0/` through `docs/phase_8_0bx/` | Phase 8.0B documentation | YES |
| `data/analysis/phase_8_0b_x1/` | Phase 8.0B.X analysis deliverables | YES |
| `data/analysis/phase_8_0b1b/` | Phase 8.0B.1B analysis deliverables | YES |
| `data/analysis/phase_8_0b1e/` | Phase 8.0B.1E analysis deliverables | YES |
| `data/analysis/issue_01_fmp_bulk/` | ISSUE-01 deliverables | YES |
| `data/analysis/phase_22d11/` | Phase 22D.11 certification | YES |
| `data/analysis/git_governance/` | This audit (GIT-001) | YES |
| `data/analysis/fmp_dq_validation.json` | FMP data quality validation artifact | REVIEW |

### Category 6 — Root-Level Analysis Reports (Untracked)
**Count: 68 files**

All are `phase_23_*.md` files at the repository root.

**Examples:** `phase_23_0a1_final_verdict.md`, `phase_23_2_operator_policy_requirements.md`, `phase_23_4a_ui_design.md`, etc.

These are phase deliverables that were created before the `docs/phase_*/` directory convention was established. They are not gitignored and are candidates for either:
- Committing as-is (historical record)
- Moving to `docs/` structure (if cleanup is authorized)
- Ignoring (not recommended — they are architectural documentation)

Also included: `portfolio_alignment_tax_columns.md`, `tax_aware_action_framework.md`, `tax_position_panel.md`, `tax_state_persistence.md`, `sih_rehydration_baseline_post_22d10.md`

### Category 7 — Operator Runtime State (Untracked)
**Count: 1 file**

| File | Contents | Commit? |
|------|---------|---------|
| `data/operator/portfolio_alignment_state.json` | Strategic exits, active policies, operator preferences | REVIEW — contains runtime operator decisions |

**Note:** Not gitignored. Contains operator policy state (strategic exit symbols, policy types). This is runtime operational data, not architectural source. Should likely be gitignored or committed as a seeded default with sensitive data removed.

### Category 8 — Generated Signal Data (Gitignored)
**Count: N/A — already ignored**

The following are gitignored per `data/signals/**` rule and do NOT appear in git status:
- `data/signals/fmp/latest/` — 5 CSV files (2,467+ rows each)
- `data/signals/company_profile/` — 2 CSV files
- `data/signals/security_metadata/`
- `data/signals/yahoo/`
- `data/signals/zacks/`
- `data/signals/danelfin/`

### Category 9 — PAR Analysis Runs (Gitignored)
**Count: N/A — already ignored**

`data/portfolio_ingestion/analysis_runs/` — 203 run directories — gitignored per `.gitignore:125`.

---

## True Untracked Count by Commit Decision

| Decision | Approximate Count | Category |
|----------|------------------|---------|
| COMMIT — production code | 30 | New src/, scripts/, tests/ |
| COMMIT — documentation | 55+ | docs/, data/analysis/, root .md |
| REVIEW before commit | 5 | operator state, one-time scripts, dq artifacts |
| ALREADY IGNORED | ~5,000+ | signals, analysis runs |
| ADD TO .gitignore | 1–2 | data/operator/, possibly fmp_dq validation |
