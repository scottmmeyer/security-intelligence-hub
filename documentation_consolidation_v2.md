# Documentation Consolidation v2

**Date:** 2026-06-14  
**Scope:** Identify duplicates, superseded reports, and obsolete forensic investigations

---

## Disposition Key

| Code | Meaning |
|------|---------|
| KEEP | Commit as-is; still authoritative |
| SUPERSEDED | A newer document replaces this one; mark or archive |
| DUPLICATE | Content duplicated; one copy should be kept |
| ORPHANED | No associated code; unclear origin |

---

## Forensic Investigation Chain — KEEP (all authoritative)

The forensic investigation produced a sequential chain of reports. All are traceable and non-redundant.

| Report | Status | Reason |
|--------|--------|--------|
| `pis_attr_forensic_01_report.md` | KEEP | Primary forensic report |
| `pis_attr_forensic_final_verdict.md` | KEEP | Forensic verdict |
| `canonical_vs_lineage_alignment.md` | KEEP | Structural analysis |
| `dashboard_data_source_audit.md` | KEEP | Source audit |
| `lineage_candidate_trace.md` | KEEP | Candidate trace |
| `lineage_refresh_trigger_audit.md` | KEEP | Trigger audit |
| `par_inventory_audit.md` | KEEP | PAR inventory |
| `root_cause_verdict.md` | KEEP | Root cause |
| `attribution_refresh_trace.md` | KEEP | Attribution trace |

---

## PIS-005 Acceptance Chain — KEEP (all authoritative)

| Report | Status | Notes |
|--------|--------|-------|
| `pis005_acceptance_audit.md` | KEEP | Most recent, comprehensive |
| `pis005_commit_manifest.md` | KEEP | Active commit plan |
| `pis005_final_verdict.md` | KEEP | Decision record |
| `pis005_regression_surface_review.md` | KEEP | Surface audit |
| `refresh_orchestration_design.md` | KEEP | Architecture spec |
| `refresh_orchestration_final_verdict.md` | KEEP | Delivery record |
| `refresh_trigger_validation.md` | KEEP | Scenario validation |
| `artifact_dependency_graph.md` | KEEP | Dependency map |

---

## Two "Final Verdict" Files — POTENTIAL CONFUSION

| File | Workstream | Content | Recommendation |
|------|-----------|---------|----------------|
| `final_verdict.md` (root, modified) | PIS-FORENSIC | PIS forensic investigation final verdict | KEEP — rename to `pis_forensic_final_verdict_root.md` to avoid ambiguity, OR leave as-is with note |
| `pis_attr_forensic_final_verdict.md` | PIS-FORENSIC | Same investigation, possibly duplicate | REVIEW — verify whether content differs from final_verdict.md |
| `benchmark_final_verdict.md` | BENCH | Benchmark attribution verdict | KEEP — clearly scoped |
| `benchmark_quality_final_verdict.md` | BENCH | Benchmark quality verdict | KEEP — clearly scoped |
| `pis005_final_verdict.md` | PIS-005 | PIS-005 acceptance verdict | KEEP — clearly scoped |
| `pra_impl_02a_final_verdict.md` | PRA | PRA-02A verdict | KEEP — clearly scoped |

**Action:** Rename `final_verdict.md` → `pis_forensic_root_verdict.md` to eliminate ambiguity when browsing the root directory.

---

## Repository Stabilization Documents — Supersession Chain

A sequence of stabilization attempts has produced overlapping documents:

| File | Status | Superseded By |
|------|--------|--------------|
| `repository_stabilization_inventory.md` | SUPERSEDED | `repository_stabilization_inventory_v2.md` (this audit) |
| `repository_cleanup_plan.md` | SUPERSEDED | `workstream_commit_readiness.md` (this audit) |
| `documentation_consolidation_plan.md` | SUPERSEDED | `documentation_consolidation_v2.md` (this audit) |
| `repository_cleanliness_audit.md` | SUPERSEDED | `repository_stabilization_inventory_v2.md` (this audit) |
| `repository_stabilization_actions.md` | SUPERSEDED | This full audit |
| `workstream_isolation_plan.md` | SUPERSEDED | `repository_workstream_classification.md` |

**Recommendation:** Commit ALL of these as historical record. The v2 documents are authoritative going forward. Do not delete prior versions — they show the evolution of the stabilization effort.

---

## PRA Documents — KEEP (non-overlapping audit chain)

The pra_impl_02 and pra_impl_02a documents are sequential. No duplicates detected.

---

## Benchmark Documents — Possible Redundancy

Two quality-related verdict files:
- `benchmark_quality_final_verdict.md`
- `benchmark_final_verdict.md`

**Assessment:** `benchmark_final_verdict.md` covers the overall benchmark implementation. `benchmark_quality_final_verdict.md` covers the data quality policy specifically. These are NOT duplicates.

---

## Signal Coverage Design Documents — KEEP (sequential chain)

The coverage documents are sequential (phase 3 → 5 → 6 → 7). All KEEP.

---

## Orphaned / Unclear Origin Documents

| File | Disposition | Notes |
|------|------------|-------|
| `resume_checkpoint_repair_audit.md` | ARCHIVE | Appears to be a session continuity artifact; no active workstream reference |
| `pis_backfill_design.md` | KEEP | References PIS backfill strategy; still relevant to roadmap |
| `next_implementation_recommendation.md` | KEEP | Active roadmap guidance |
| `issue_50_rescope_recommendation.md` | KEEP | Issue management record |

---

## docs/performance-attribution/ — KEEP ALL

Four new files documenting the performance attribution design and methodology:
- `attribution_methodology_assessment.md`
- `concentrated_alpha_performance_framework.md`
- `fidelity_performance_inventory.md`
- `performance_dashboard_design.md`

Modified:
- `final_verdict.md` — updated with benchmark attribution completion status

All KEEP; no duplicates with root-level documents.

---

## Documents Not Worth Separate Attention

The following are referenced by their workstream acceptance audits and can be committed as-is:

- All `pra_impl_02*.md` files — referenced by `pra_impl_02a_final_verdict.md`
- All `benchmark_*.md` files — referenced by `benchmark_final_verdict.md`
- All `coverage_*.md` files — referenced by `signal_coverage_03_completion.md`
- All `attribution_*.md` files — referenced by `pis005_acceptance_audit.md`

---

## Summary

| Status | Count | Action |
|--------|-------|--------|
| KEEP | ~165 | Commit as-is |
| SUPERSEDED (but keep for history) | 6 | Commit; v2 equivalents are authoritative |
| ARCHIVE | 1 | `resume_checkpoint_repair_audit.md` |
| DUPLICATE | 0 | None found |
| DELETE | 0 | No safe deletes identified |

**Net recommendation:** Commit everything. Root directory clutter is acceptable while the workstream is active. Consider moving root-level workstream documents into `docs/` subdirectories as part of post-commit housekeeping.
