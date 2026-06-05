# Generated Artifact Audit — Phase GIT-001

## Definitions

**Generated artifacts** = files produced at runtime or analysis time that are deterministic, regeneratable, or operational data (not architectural source code).

---

## Artifacts Already Correctly Gitignored

These appear in no git status output — correctly excluded:

| Path | Size | Ignore Rule | Notes |
|------|------|------------|-------|
| `data/signals/**` | ~5 dirs, ~30 CSV files | `.gitignore:95` | Signal cache files (FMP, Yahoo, Zacks, Danelfin, company profile) |
| `data/portfolio_ingestion/analysis_runs/` | 203 run directories | `.gitignore:125` | PAR run artifacts |
| `data/portfolio_ingestion/manifest.json` | 1 file | `.gitignore` | Run manifest |
| Various auto-generated `.md` reports | ~20 files | Listed in `.gitignore` | archetype_validation_report.md etc. |

**Assessment: Correctly governed. No action needed.**

---

## Generated Artifacts Currently Untracked (Appear in git status ??)

### data/analysis/phase_8_0b_x1/ — Phase 8.0B.X.1 Deliverables
**Files:** 11 markdown files  
**Content:** company_snapshot_data_inventory.md, company_snapshot_source_review.md, etc.  
**Type:** Phase analysis deliverables — intentionally produced governance documents  
**Intended for source control:** YES — these are architectural documentation, not runtime artifacts  
**Classification: COMMIT**

### data/analysis/phase_8_0b1b/ — Phase 8.0B.1B Deliverables
**Files:** 7 markdown files  
**Content:** universe_schema_review.md, field_mapping.md, coverage_report.md, etc.  
**Type:** Phase analysis deliverables  
**Classification: COMMIT**

### data/analysis/phase_8_0b1e/ — Phase 8.0B.1E Deliverables
**Files:** 3 markdown files  
**Content:** CII methodology panel design/validation/verdict  
**Type:** Phase analysis deliverables  
**Classification: COMMIT**

### data/analysis/issue_01_fmp_bulk/ — ISSUE-01 Deliverables
**Files:** 3 markdown files  
**Content:** coverage_report.md, enrichment_validation.md, fmp_bulk_fetch_final_verdict.md  
**Type:** Issue certification deliverables  
**Classification: COMMIT**

### data/analysis/git_governance/ — This Audit
**Files:** 6 markdown files  
**Content:** This audit and related files  
**Type:** GIT-001 governance deliverables  
**Classification: COMMIT**

### data/analysis/phase_22d11/ — Phase 22D.11 Certification
**Files:** 2 markdown files  
**Type:** Phase certification  
**Classification: COMMIT**

### data/analysis/fmp_dq_validation.json
**Content:** FMP data quality validation results  
**Type:** Generated JSON artifact from dq validation scripts  
**Intended for source control:** UNCERTAIN — regeneratable, but may be useful as a baseline snapshot  
**Classification: REVIEW** — Could add to .gitignore under `data/analysis/*.json` pattern, or commit as a point-in-time baseline

---

## Root-Level Phase Deliverable Reports (68 files)

All `phase_23_*.md` files at repository root.

**Assessment:** These are architectural documentation from Phases 23.0A through 23.5, produced before the `docs/phase_*/` convention was established. They are NOT gitignored and NOT runtime artifacts.

**Examples:**
- `phase_23_2_operator_policy_requirements.md` — design document
- `phase_23_4a_ui_design.md` — UI specification
- `phase_23_5_certification_report.md` — certification record

**Options:**
1. **Commit as-is** (recommended) — they are valid documentation, just located at root
2. Move to `docs/` structure (requires authorized refactor, not this phase)
3. Add to .gitignore (NOT recommended — architectural documentation)

**Classification: COMMIT as-is** — not runtime artifacts, document the system's development history

**Also at root:** `tax_aware_action_framework.md`, `tax_position_panel.md`, `tax_state_persistence.md`, `sih_rehydration_baseline_post_22d10.md`, `portfolio_alignment_tax_columns.md`

---

## Operator Runtime State

### data/operator/portfolio_alignment_state.json
**Content:** `strategic_exit_symbols`, `active_policies` (TSLA DO_NOT_SELL, DODFX SELL_LAST)  
**Type:** Runtime operational data — stores operator decisions  
**Intended for source control:** UNCERTAIN

Arguments for committing:
- Contains initialized policy defaults
- Reproducibility: new environments start with correct policy baseline

Arguments against committing:
- Contains operator decisions that evolve during use
- Future: may contain sensitive position data
- Better managed as a seeded template (committed as `portfolio_alignment_state.default.json`, excluded as `portfolio_alignment_state.json`)

**Classification: REVIEW** — Recommend committing a sanitized default, then adding the live file to `.gitignore`

---

## Summary

| Category | Count | Decision |
|----------|-------|---------|
| Phase analysis deliverables (data/analysis/) | ~25 docs | COMMIT |
| Root phase_23_*.md | 68 docs | COMMIT |
| docs/methodology/ docs/governance/ | ~25 docs | COMMIT |
| data/analysis/fmp_dq_validation.json | 1 | REVIEW |
| data/operator/portfolio_alignment_state.json | 1 | REVIEW |
| Already correctly gitignored | thousands | NO ACTION |
