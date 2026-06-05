# Commit Manifest — Phase GOV-001

## Overview

7 logical commit groups covering all ~125 dirty entries.  
All groups assume tests pass before each commit.

---

## Group 1 — FMP Foundation
**Covers:** Phases 8.0B.0 through 8.0B.1B (data infrastructure, no scoring changes)

**Files:**
```
src/scoring/fetch_fmp_signals.py
src/scoring/fmp_universe_enrichment.py
scripts/refresh_signals.py  (M — FMP provider added)
scripts/fmp_bulk_fetch_universe.py
scripts/fetch_fmp_validation_set.py
scripts/fmp_dq_analyze.py
scripts/fmp_dq_validate.py
tests/test_fmp_phase_8_0b1a.py
docs/phase_8_0b0/
docs/phase_8_0b0a/
docs/phase_8_0b1a/
docs/phase_8_0b1a1/
data/analysis/phase_8_0b1b/
data/analysis/issue_01_fmp_bulk/
docs/governance/fmp_integration_philosophy.md  (if exists as separate file)
```

**Rationale:** Self-contained FMP data layer. No UI or scoring changes. Foundation for all FMP display work.

**Commit message:**
```
feat: FMP Integration Foundation — signal intake, universe enrichment, bulk fetch

Phases 8.0B.0 through ISSUE-01 (completed June 5, 2026).
- fetch_fmp_signals.py: 4-dataset FMP fetcher with URL param auth
- fmp_universe_enrichment.py: coverage classifier, FULL/PARTIAL/ETF_NA/NO_DATA
- fmp_bulk_fetch_universe.py: resumable per-symbol fetcher, smart-resume
- refresh_signals.py: FMP provider integration
- Coverage: 98.7% FULL (2,442/2,475 symbols)
- 50 new tests in test_fmp_phase_8_0b1a.py
- No scoring changes. No CW-DAS changes.

Closes ISSUE-01.
```

---

## Group 2 — FMP Diagnostic Overlay
**Covers:** Phase 8.0B.1B.5 and 8.0B.X.1/X.2/X.3/X.4 — display enrichment

**Files:**
```
src/scoring/fetch_company_profile.py
docs/phase_8_0bx/
data/analysis/phase_8_0b_x1/
```

**Rationale:** Builds on Group 1. Company profile fetcher and CW-DAS drift audit documentation.

**Commit message:**
```
feat: FMP Diagnostic Overlay and Company Context — Phases 8.0B.X through 8.0B.1B.5

- fetch_company_profile.py: Yahoo Finance company profile fetcher
- Thesis Integrity, Fundamental Consistency, Dislocation Detection (JS-side)
- CW-DAS allocation drift audit (audit only, no formula changes)
- Display-only: no scoring, ranking, or recommendation changes
```

---

## Group 3 — Company Context UI Enhancements
**Covers:** UI changes from Company Snapshot through Fundamental Snapshot

**Files:**
```
ui/portfolio_alignment/app.js  (M — major additions)
ui/portfolio_alignment/index.html  (M — major additions)
```

Note: These two files contain changes from multiple phases (CRA panel, Company Snapshot, Fundamental Snapshot, Why SIH Likes It, CII modal). They are committed together as the UI checkpoint.

**Rationale:** All UI changes are additive and display-only. Committing together as a UI checkpoint is cleaner than attempting to separate by feature.

**Commit message:**
```
feat: UI enhancements — Company Snapshot, Fundamental Snapshot, Why SIH Likes It, CII modal (v17)

- Company Snapshot: company name, HQ, sector, industry, business description
- Fundamental Snapshot: FMP data display with Thesis Integrity / Consistency / Dislocation badges
- Why SIH Likes It: signal-derived operator rationale bullets
- CII Methodology Panel: ⓘ button opens 4-layer framework modal
- CSS additions: dq-company-snapshot, dq-fundamental-snapshot, dq-why-sih, cii-modal
- No scoring changes. app.js v17.
```

---

## Group 4 — Consensus Intelligence Methodology
**Covers:** Phase 8.0B.1E — CII methodology documentation

**Files:**
```
docs/methodology/
data/analysis/phase_8_0b1e/
```

**Rationale:** Self-contained governance documentation. No code changes.

**Commit message:**
```
docs: Consensus Intelligence Investing (CII) methodology — Phase 8.0B.1E

- Official CII methodology classification and 4-layer framework
- Core beliefs, dislocation philosophy, branding, taglines
- UI integration recommendations
- Governance: docs/methodology/ is the canonical methodology reference
```

---

## Group 5 — Portfolio Action Pipeline and CRA
**Covers:** Phases 23.x PAP + Phase 23.6 CRA

**Files:**
```
src/portfolio/deployment_queue.py  (M)
src/portfolio/enrichment.py  (M)
src/portfolio/ingestion.py  (M)
src/portfolio/optimizer.py  (M)
src/portfolio/reconciliation.py  (M)
src/portfolio/runner.py  (M)
src/portfolio/operator_policy.py  (??)
src/portfolio/cra/  (?? — entire module)
config/allocation_dimensions.yaml  (M)
config/etf_exposure_decomposition.yaml  (M)
scripts/run_outcome_ui.py  (M)
tests/test_reconciliation.py  (M)
tests/test_operator_policy.py  (??)
tests/test_policy_api.py  (??)
tests/test_23_5_block_diagnostics.py  (??)
tests/test_apply_policy_to_queue.py  (??)
tests/test_compute_execution_state.py  (??)
tests/test_cra_phase_23_6a.py  (??)
docs/phase_23_6/  through  docs/phase_23_6b5/
phase_23_*.md  (68 root-level files)
portfolio_alignment_tax_columns.md
tax_aware_action_framework.md
tax_position_panel.md
tax_state_persistence.md
sih_rehydration_baseline_post_22d10.md
data/analysis/phase_22d11/
```

**Rationale:** The largest group, covering all PAP and CRA work. Grouping together keeps the delivery context intact (PAP enables CRA; CRA depends on deployment_queue). All 1,004 tests pass against this group.

**Commit message:**
```
feat: Portfolio Action Pipeline (PAP) and Capital Rotation Advisor (CRA) — Phases 23.x through 23.6B.5

PAP:
- deployment_queue.py: policy rank boost, allocation_node, Phase 23.5
- operator_policy.py: DO_NOT_SELL, SELL_LAST, PREFERRED_ACCUMULATION registry
- enrichment/ingestion/optimizer/reconciliation/runner: PAP pipeline extensions
- 89 tests in test_cra_phase_23_6a.py; 6 additional policy/execution test files

CRA:
- src/portfolio/cra/: capital_source_builder, rotation_proposal_builder, models, impact_estimator
- CRA API endpoints in run_outcome_ui.py
- Tier-aware allocation, circular conflict resolution, strategic exit override

Configuration:
- allocation_dimensions.yaml: extended node hierarchy
- etf_exposure_decomposition.yaml: registry updates

Documentation:
- docs/phase_23_6/ through docs/phase_23_6b5/
- 68 root-level phase_23_*.md analysis documents
```

---

## Group 6 — GitHub Governance Framework
**Covers:** Phase 8.0B.1D backlog establishment + GIT-001 audit

**Files:**
```
docs/governance/
data/analysis/git_governance/
.gitignore  (M — 2 new rules added)
```

**Rationale:** Governance-only. No code changes. Documents the backlog system and repo cleanup.

**Commit message:**
```
docs: GitHub backlog governance and repository audit — Phases 8.0B.1D and GIT-001

- Backlog inventory (46 items), issue taxonomy (24 labels), epic structure (6 epics)
- Initial issue backlog, roadmap recommendation, execution standard
- GIT-001 repository audit: dirty file inventory, commit strategy, cleanup plan
- .gitignore: added data/operator/portfolio_alignment_state.json and fmp_dq_validation.json
- GitHub Issues: 10 open (6 epics + 4 issues), ISSUE-01 closed
```

---

## Group 7 — Remaining Documentation and Governance
**Covers:** Any remaining untracked docs not in above groups

**Files:**
```
(anything remaining in git status after Groups 1-6)
```

**Commit message:**
```
docs: Remaining phase documentation and governance artifacts
```

---

## Commit Order

```
Group 5 (PAP/CRA — largest, test-dependent) → first
Group 1 (FMP foundation) → second
Group 2 (FMP overlay) → third
Group 3 (UI) → fourth (depends on Groups 1+2 for FMP data)
Group 4 (Methodology) → fifth (independent)
Group 6 (Governance) → sixth (includes .gitignore)
Group 7 (Remaining) → last
```

Or: use the single consolidation commit if per-group commits are too time-consuming.
