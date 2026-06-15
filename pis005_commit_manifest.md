# PIS-005 Commit Manifest

**Prepared:** 2026-06-14  
**Decision:** ACCEPT  
**Suggested commit message:** `PIS-005: implement derived artifact refresh orchestration`

---

## Files to Commit

### New Files (Untracked — `??` in git status)

| File | Type | Purpose |
|------|------|---------|
| `src/pis/artifact_freshness.py` | Implementation | Deterministic freshness detection for all 5 artifact layers |
| `src/pis/refresh_orchestrator.py` | Implementation | Ordered, lock-protected 5-stage refresh chain |

### Modified Files (Changed — `M` in git diff)

| File | Type | Change Description |
|------|------|-------------------|
| `scripts/run_outcome_ui.py` | Integration | Added `GET /api/pis/refresh/status`, `POST /api/pis/refresh`, startup daemon thread in `main()` |

### Documentation Files (Supporting — in workspace root)

| File | Purpose |
|------|---------|
| `artifact_dependency_graph.md` | Producer/consumer map for all 10 artifact files |
| `refresh_orchestration_design.md` | Architecture decisions, trigger evaluation, concurrency design |
| `refresh_trigger_validation.md` | Phase F scenario results (5 scenarios, Q1-Q12) |
| `refresh_orchestration_final_verdict.md` | Delivery summary and constraint compliance |

### Audit Files (This Review)

| File | Purpose |
|------|---------|
| `pis005_acceptance_audit.md` | This forensic acceptance audit |
| `pis005_commit_manifest.md` | This file |
| `pis005_regression_surface_review.md` | Regression surface analysis |
| `pis005_final_verdict.md` | Final commit decision |

---

## Files Explicitly NOT in Scope

These files changed in the working tree but belong to other work and must NOT be included in the PIS-005 commit:

| File | Reason to Exclude |
|------|------------------|
| `docs/governance/backlog/initial_issue_backlog.md` | Governance/backlog work, not PIS-005 |
| `docs/governance/backlog/roadmap_recommendation.md` | Governance/backlog work, not PIS-005 |
| `docs/governance/governance_cleanup_report.md` | Governance cleanup report, not PIS-005 |
| `docs/performance-attribution/final_verdict.md` | Attribution acceptance work, not PIS-005 |
| `final_verdict.md` | Prior forensic investigation output, not PIS-005 |
| `refresh_execution_audit.md` | Pre-existing file, separate audit scope |
| `regression_results.md` | Pre-existing test output, not PIS-005 |
| `scripts/refresh_portfolio_signals.py` | Signal refresh script, not PIS-005 |
| `scripts/refresh_signals.py` | Signal refresh script, not PIS-005 |
| `src/portfolio/cra/capital_source_builder.py` | CRA work, not PIS-005 |
| `src/portfolio/cra/models.py` | CRA work, not PIS-005 |
| `src/portfolio/cra/rotation_proposal_builder.py` | CRA work, not PIS-005 |
| `src/portfolio/models.py` | Portfolio model changes, not PIS-005 |
| `src/portfolio/recommendations.py` | Recommendation logic, not PIS-005 |
| `src/portfolio/runner.py` | Runner changes, not PIS-005 |
| `src/scoring/*.py` | Scoring fetch scripts, not PIS-005 |

---

## Suggested Git Command

```bash
git add src/pis/artifact_freshness.py
git add src/pis/refresh_orchestrator.py
git add scripts/run_outcome_ui.py
git add artifact_dependency_graph.md
git add refresh_orchestration_design.md
git add refresh_trigger_validation.md
git add refresh_orchestration_final_verdict.md
git add pis005_acceptance_audit.md
git add pis005_commit_manifest.md
git add pis005_regression_surface_review.md
git add pis005_final_verdict.md
git commit -m "PIS-005: implement derived artifact refresh orchestration

- Add artifact_freshness.py: deterministic staleness detection for all
  5 pipeline layers (canonical, change, lineage, attribution, benchmark)
- Add refresh_orchestrator.py: ordered 5-stage lock-protected refresh
  chain; each stage gates on upstream freshness before executing
- Wire GET /api/pis/refresh/status and POST /api/pis/refresh endpoints
- Add startup daemon thread to trigger self-healing refresh on server start
- Zero changes to governance, canonical selection, change detection,
  lineage matching, attribution scoring, or benchmark math
- Closes June 11 / June 14 divergence class identified by forensic audit"
```

---

## Pre-Commit Verification Checklist

- [x] `artifact_freshness.py` compiles clean: `python3 -m py_compile src/pis/artifact_freshness.py`
- [x] `refresh_orchestrator.py` compiles clean: `python3 -m py_compile src/pis/refresh_orchestrator.py`
- [x] Both modules import successfully
- [x] `artifact_freshness_report()` returns CURRENT for all layers
- [x] `refresh_derived_artifacts()` on current system: `Refreshed: []`, `Skipped: [all 5]`
- [x] No business logic files import PIS-005 modules
- [x] `GET /api/pis/refresh/status` endpoint present in run_outcome_ui.py
- [x] `POST /api/pis/refresh` endpoint present in run_outcome_ui.py
- [x] Startup trigger thread present in `main()`
