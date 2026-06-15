# Branch Strategy Recommendation

**Date:** 2026-06-14

---

## Current State

| Field | Value |
|-------|-------|
| Current branch | `stream/benchmark-attribution-01b` |
| HEAD commit | `18fbbd8` (AI-003: implement deterministic allocation philosophy explainability) |
| Last merge point | `main` at `18fbbd8` (HEAD and main are at same commit) |
| Dirty files | 174 |
| Active workstreams | 5 (PIS-005, BENCH, PRA, SIG-COV, PIS-FORENSIC) |

---

## Branch Assessment

`stream/benchmark-attribution-01b` is the active feature branch. Because `main` and `HEAD` are at the same commit (`18fbbd8`), this branch is effectively at parity with main. All 174 dirty files are uncommitted work on top of the AI-003 commit.

---

## Cross-Stream Contamination Assessment

| File | Workstreams Mixed | Risk Level |
|------|------------------|-----------|
| `scripts/run_outcome_ui.py` | PIS-005 + BENCH | LOW — additions are in separate `elif` blocks |
| `ui/pis_dashboard/app.js` | BENCH + PIS-005 visibility | LOW — PIS-005 visibility is API-level, not JS |
| `tests/test_pis_ui_phase1_dashboard.py` | BENCH (expanded) | LOW — additive only |

**Verdict:** No hard contamination. Multiple workstreams can be committed on the current branch in sequence without isolation branches.

---

## Recommended Branch Strategy

### Option A: Sequential Commits on Current Branch (RECOMMENDED)

Keep `stream/benchmark-attribution-01b`. Commit each workstream in the recommended order on this single branch. Then merge to main.

**Advantages:**
- Simplest approach
- No rebasing required
- All history stays linear
- Avoids branch proliferation

**Commit sequence:**

```
stream/benchmark-attribution-01b
  ├── REPO-GOV: .gitignore, backlog, roadmap updates
  ├── PRA-IMPL-02A: funding policy, depletion model, API contract
  ├── SIG-COV-03: holdings coverage detection and targeted refresh  ← HOLD until 3 tests fixed
  ├── PIS-FORENSIC-01: forensic investigation reports
  ├── PIS-005: derived artifact refresh orchestration
  └── BENCH-01B: benchmark attribution pipeline and dashboard
```

After all commits:
```bash
git checkout main
git merge --no-ff stream/benchmark-attribution-01b
git tag bench-01b-v1
```

### Option B: Isolation Branches Per Workstream

Create separate branches per workstream and merge them in order.

**Not recommended** because:
- No hard contamination exists that requires isolation
- `run_outcome_ui.py` is modified by two workstreams — splitting would require cherry-picking or manual split
- Adds overhead with no material benefit

---

## Recommended Next Branch

For work that begins after the current stabilization commit sequence is complete:

**If next target is SIG-COV test fix:**  
Stay on `stream/benchmark-attribution-01b` and fix before committing SIG-COV.

**If next target is a new feature:**  
```bash
git checkout -b stream/<next-feature-name>
```
Examples:
- `stream/pis-006-post-ingestion-trigger` (post-ingestion refresh trigger)
- `stream/pis-benchmark-dashboard-panel` (frontend refresh health UI)
- `stream/sig-cov-phase8` (next signal coverage phase)

---

## Recommended Commit Order (Detailed)

### Commit 1: REPO-GOV

```bash
git add .gitignore
git add docs/governance/backlog/
git add docs/governance/governance_cleanup_report.md
git add documentation_consolidation_plan.md foundation_release_tag_report.md
git add generated_artifact_archive_report.md next_implementation_recommendation.md
git add repository_cleanliness_audit.md repository_cleanup_plan.md
git add repository_stabilization_actions.md repository_stabilization_inventory.md
git add workstream_isolation_plan.md issue_50_rescope_recommendation.md
git add migration_feasibility_assessment.md recommended_migration_strategy.md
git commit -m "REPO-GOV: governance cleanup, backlog updates, gitignore additions"
```

### Commit 2: PRA-IMPL-02A

```bash
git add src/portfolio/cra/ src/portfolio/models.py src/portfolio/recommendations.py src/portfolio/runner.py
git add tests/test_pra_impl_02*.py
git add pra_impl_02*.md allocation_reduction_model.md funding_*.md regression_results.md refresh_execution_audit.md
git commit -m "PRA-IMPL-02A: funding policy, depletion model, and API contract"
```

### Commit 3: SIG-COV-03 (after fixing 3 failing tests)

```bash
git add src/portfolio/holdings_coverage.py scripts/refresh_signals.py scripts/refresh_portfolio_signals.py
git add src/scoring/ tests/test_signal_coverage*.py
git add coverage_*.md historical_coverage_analysis.md holdings_*.md operational_refresh_enforcement.md
git add provider_*.md refresh_button_trace.md refresh_eligibility_model.md refresh_execution_trace.md
git add refresh_runtime_evidence.md refresh_status_api_design.md signal_*.md spy_coverage_audit.md
git add targeted_refresh_strategy.md ui_refresh_*.md
git commit -m "SIG-COV-03: holdings coverage detection and targeted refresh"
```

### Commit 4: PIS-005 + PIS-FORENSIC

```bash
git add src/pis/artifact_freshness.py src/pis/refresh_orchestrator.py
git add scripts/run_outcome_ui.py  # PIS-005 additions only (will also include BENCH additions)
git add artifact_dependency_graph.md refresh_orchestration*.md refresh_trigger_validation.md
git add pis005_*.md attribution_refresh_trace.md canonical_vs_lineage_alignment.md
git add dashboard_data_source_audit.md lineage_candidate_trace.md lineage_refresh_trigger_audit.md par_inventory_audit.md
git add PIS_FORENSIC_INVESTIGATION_INDEX.md attribution_freshness_audit.md attribution_readiness_assessment.md
git add attribution_start_gate.md attribution_validation.md cash_vs_spaxx_audit.md final_verdict.md
git add lineage_freshness_audit.md pis_attr_forensic*.md pis_closure_01_report.md
git add pis_foundation*.md portfolio_manager*.md recommendation_return_trace.md
git add reproducibility_validation.md root_cause_verdict.md snapshot_comparison_model.md
git add pis_backfill_design.md
git commit -m "PIS-005: derived artifact refresh orchestration + forensic investigation records"
```

### Commit 5: BENCH-01B

```bash
git add src/pis/benchmark_attribution.py src/pis/performance_attribution.py
git add ui/pis_dashboard/ ui/outcome_visualization/ 
git add tests/test_pis_benchmark_attribution*.py tests/test_pis_performance_attribution_01.py tests/test_pis_ui_phase1_dashboard.py
git add docs/performance-attribution/ docs/pis-001/ docs/pis-001a/ docs/pis-planning/
git add benchmark_*.md performance_attribution_*.md recommendation_outcome_framework.md
git add outcome_classification_model.md post_attribution_roadmap.md source_alpha_validation.md
git commit -m "BENCH-01B: benchmark attribution pipeline and dashboard"
```

### Commit 6: THIS AUDIT

```bash
git add repository_stabilization_inventory_v2.md repository_workstream_classification.md
git add workstream_commit_readiness.md generated_artifact_disposition.md
git add documentation_consolidation_v2.md branch_strategy_recommendation.md
git add repository_stabilization_final_verdict.md
git commit -m "REPO-STAB-02: repository stabilization audit and workstream classification"
```

---

## Post-Commit Merge

```bash
git checkout main
git merge --no-ff stream/benchmark-attribution-01b -m "Merge stream/benchmark-attribution-01b: PRA-02A, SIG-COV-03, PIS-005, BENCH-01B"
git tag -a bench-01b-complete -m "Benchmark attribution 01B + PIS-005 orchestration complete"
```

---

## SIG-COV Test Blocker

Before committing SIG-COV-03, resolve the 3 failing tests in `tests/test_signal_coverage_phase6.py`. The failure is a mode routing mismatch in `_refresh_zacks()` — `mode` returns `"research_refresh"` where tests expect `"coverage_repair"`. This is a contained fix in `scripts/refresh_signals.py`.
