# Generated Artifact Audit — Phase SC-H1

**Generated:** 2026-05-30  
**Scope:** All generated, derived, or temporary files in the working tree that are not intentional source code.

---

## Classification Key

| Recommendation | Meaning |
|---|---|
| KEEP | Retain as part of the committed artifact set (useful, intentional, stable) |
| ARCHIVE | Move to an archive folder or data/history partition before committing |
| DELETE | Remove entirely — no value, accidental, or redundant |
| GITIGNORE | Do not commit; add pattern to `.gitignore` and exclude from source control |

---

## Category 1 — Root-Level Generated Reports (23 files)

These `.md` files at the project root are outputs from report-generation scripts. They are not documentation authored by hand and will drift as analysis runs change.

| File | Phase | Recommendation | Rationale |
|---|---|---|---|
| `archetype_validation_report.md` | 7.2 | GITIGNORE | Point-in-time audit output; regeneratable from script |
| `cash_deployment_report.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `cash_reconciliation_report.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `conviction_deployment_report.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `conviction_model_quality_report.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `conviction_ranking_report.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `coverage_denominator_report.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `coverage_gap_report.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `coverage_reconciliation_report.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `l1_allocation_gap_report.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `optimizer_ui_validation_report.md` | 7.3B | KEEP | Phase 7.3B deliverable; documents live optimizer behavior; not regenerated automatically |
| `overlap_analysis_report.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `portfolio_philosophy_validation_report.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `portfolio_reconciliation_report.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `recommendation_conflict_report.md` | 7.2 | GITIGNORE | Point-in-time audit output; regeneratable |
| `recommendation_explainability_report.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `replay_alignment_audit.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `security_vs_etf_report.md` | 7.1 | GITIGNORE | Point-in-time audit output; regeneratable |
| `strategic_narrative_audit.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `strategic_narrative_validation_report.md` | 7.x | GITIGNORE | Point-in-time audit output; regeneratable |
| `taxonomy_clean_run_report.md` | 7.2 | GITIGNORE | Point-in-time audit output; regeneratable |
| `taxonomy_reconciliation_report.md` | 7.2 | GITIGNORE | Point-in-time audit output; regeneratable |
| `ui_archetype_consistency_report.md` | 7.2 | GITIGNORE | Point-in-time audit output; regeneratable |

**Recommended `.gitignore` pattern:** `*_report.md` at root OR explicit per-file list  
**Exception:** `optimizer_ui_validation_report.md` — keep (phase deliverable with unique live-run content)

---

## Category 2 — `docs/` Generated Artifact

| File | Phase | Recommendation | Rationale |
|---|---|---|---|
| `docs/conflict_graph_report.md` | 7.2 | ARCHIVE | Generated conflict graph; move to `docs/archive/` or `data/exports/`; not a persistent doc |

---

## Category 3 — `data/` Generated Outputs

| File / Directory | Phase | Recommendation | Rationale |
|---|---|---|---|
| `data/allocation/` (6 files) | 6.2 | GITIGNORE | Runtime allocation run outputs; regeneratable; belongs in `.gitignore` with other data/ outputs |
| `data/derived/coverage_history.csv` | 7.x | GITIGNORE | Derived data; regeneratable from signals + run history |
| `data/derived/phase7_audit_data.json` | 7.x | GITIGNORE | Temporary Phase 7 audit data; regeneratable |
| `data/exports/optimizer_candidate_report.md` | 7.3A | ARCHIVE | Useful point-in-time snapshot; move to `data/exports/archive/` |
| `data/exports/optimizer_vs_legacy_report.md` | 7.3A | ARCHIVE | Useful point-in-time snapshot; move to `data/exports/archive/` |

---

## Category 4 — `navigation_state.yaml`

| File | Recommendation | Rationale |
|---|---|---|
| `navigation_state.yaml` | GITIGNORE | Auto-updated UI session state; changes on every navigation; not meaningful to track |

---

## Category 5 — Diagnostic / Debug Scripts (30 files, `scripts/_*.py`)

All scripts prefixed with `_` in the `scripts/` directory are temporary diagnostics or report-generation one-shots created during development.

| Pattern | Count | Recommendation | Rationale |
|---|---|---|---|
| `scripts/_debug_*.py` | 3 | DELETE | Pure debug output scripts; no production value; created to inspect live state during development |
| `scripts/_fi_before_after.py` | 1 | DELETE | Before/after comparison diagnostic; no longer relevant |
| `scripts/_pmi_audit*.py` (4 files) | 4 | DELETE | PMI audit investigation scripts; findings already incorporated into test suite |
| `scripts/_check_alignment.py` | 1 | DELETE | Temporary alignment check; superseded by test suite |
| `scripts/_phase7_*.py` (4 files) | 4 | DELETE | Phase 7 data exploration scripts; no longer needed |
| `scripts/_test_pipeline.py` | 1 | DELETE | Temporary pipeline test script; superseded by tests/ |
| `scripts/_archetype_validation.py` | 1 | DELETE | Superseded by `tests/test_archetype.py` |
| `scripts/_portfolio_philosophy_validation.py` | 1 | DELETE | Superseded by test suite |
| `scripts/_ui_archetype_consistency_report.py` | 1 | DELETE | One-shot; no longer needed |
| `scripts/_generate_*.py` (10 files) | 10 | ARCHIVE | Report generators; not test infrastructure, not operational tools; archive to `scripts/archive/` if evidence needed |

**Recommended `.gitignore` pattern:** `scripts/_*.py`

---

## Category 6 — `data/portfolio_ingestion/analysis_runs/`

Not shown in `git status` (already gitignored or not checked). Per `.gitignore` conventions established in this repo, all `data/portfolio_ingestion/` outputs should be excluded. **Verify `.gitignore` covers this path.**

---

## Summary

| Recommendation | Count (files) | Primary Location |
|---|---|---|
| KEEP | 1 | `optimizer_ui_validation_report.md` |
| ARCHIVE | 7 | `data/exports/`, `docs/conflict_graph_report.md` + `_generate_*.py` scripts |
| DELETE | 16 | `scripts/_debug_*.py`, `_pmi_audit*.py`, `_phase7_*.py`, `_check_alignment.py`, `_fi_before_after.py`, `_test_pipeline.py`, `_archetype_validation.py`, `_portfolio_philosophy_validation.py`, `_ui_archetype_consistency_report.py` |
| GITIGNORE | 32 | `*_report.md` (root), `data/allocation/`, `data/derived/`, `navigation_state.yaml`, `scripts/_*.py` |

---

## Recommended `.gitignore` Additions

```gitignore
# Auto-generated root-level audit reports (regeneratable)
archetype_validation_report.md
cash_deployment_report.md
cash_reconciliation_report.md
conviction_deployment_report.md
conviction_model_quality_report.md
conviction_ranking_report.md
coverage_denominator_report.md
coverage_gap_report.md
coverage_reconciliation_report.md
l1_allocation_gap_report.md
overlap_analysis_report.md
portfolio_philosophy_validation_report.md
portfolio_reconciliation_report.md
recommendation_conflict_report.md
recommendation_explainability_report.md
replay_alignment_audit.md
security_vs_etf_report.md
strategic_narrative_audit.md
strategic_narrative_validation_report.md
taxonomy_clean_run_report.md
taxonomy_reconciliation_report.md
ui_archetype_consistency_report.md

# UI session state
navigation_state.yaml

# Derived data outputs
data/allocation/
data/derived/

# Diagnostic scripts (prefix convention)
scripts/_*.py
```
