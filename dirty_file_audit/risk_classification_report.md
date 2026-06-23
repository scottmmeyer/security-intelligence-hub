# Risk Classification Report
# DIRTY-FILE-AUDIT-01 — 2026-06-22

## Risk Level Summary

| Risk | Count | Files |
|---|---|---|
| **HIGH** | **2** | src/portfolio/cra/capital_source_builder.py, src/portfolio/cra/models.py |
| **MEDIUM** | **7** | scripts/refresh_signals.py, scripts/run_outcome_ui.py, src/models/provider_health_models.py, src/pipeline/stages/ess_intake_stage.py, src/portfolio/ess_coverage.py, config/allocation_policy.yaml, scripts/prepare_portfolio_review.py |
| **LOW** | **40** | All UI files, documentation, new source modules, validation files, test files |

---

## HIGH RISK Files — Detailed Analysis

### src/portfolio/cra/capital_source_builder.py
**Risk classification**: HIGH (touches CRA allocation logic)
**Actual change**: Adds `_compute_source_intent()` — a pure display function deriving human-readable intent labels from existing category/ESS/signal data. Does NOT modify capital source ranking, sizing, ordering, or filtering logic.
**Net scoring/ranking impact**: NONE
**Confirmed safe**: Yes — CRA-EXPLAIN-02 per repo memory notes; all existing test suite passed (89 tests)
**Governance note**: HIGH classification is correct by topology (touches CRA), but actual risk is display-only.

### src/portfolio/cra/models.py
**Risk classification**: HIGH (touches CRA models)
**Actual change**: Adds `SOURCE_INTENT_*` string constants and `source_intent` field to `CapitalSourceRecord`. This is a backward-compatible model extension.
**Net scoring/ranking impact**: NONE
**Confirmed safe**: Yes — additive model extension, no existing field changes
**Governance note**: As above — HIGH by topology, display-only in practice.

---

## MEDIUM RISK Files — Detailed Analysis

### scripts/refresh_signals.py
**Risk classification**: MEDIUM (touches refresh orchestration)
**Actual change**: Adds refresh mode routing constants (`REFRESH_MODE_STALE_ONLY`, `REFRESH_MODE_PORTFOLIO_SIGNALS`, `REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE`) and mode normalization helper. Extends `_refresh_zacks/danelfin/yahoo()` signatures to accept `refresh_mode` parameter. Does not change the underlying fetch logic, stale detection, or coverage rules.
**Net scoring/ranking impact**: NONE — controls which symbols get refreshed, not how they are scored

### scripts/run_outcome_ui.py
**Risk classification**: MEDIUM (large server-side change)
**Actual change**: +1239 lines adding new API endpoints: `/api/signal-refresh`, `/api/signal-refresh/status`, `/api/refresh-transparency`, `/api/signal-status` coverage data, drift/intelligence summaries. All new endpoints are read-only data providers. No scoring, ranking, or allocation logic added.
**Net scoring/ranking impact**: NONE

### src/models/provider_health_models.py
**Risk classification**: MEDIUM (touches data models used by ESS pipeline)
**Actual change**: Adds `gap_type`, `true_missing_count`, `stale_coverage_count`, `no_fresh_starmine_count` fields to `EssCoverageGapWarning`. Backward-compatible with defaults. Changes `summary_message` property format.
**Net scoring/ranking impact**: NONE — diagnostic model only

### src/pipeline/stages/ess_intake_stage.py
**Risk classification**: MEDIUM (ESS intake pipeline)
**Actual change**: ESS-INTAKE-ORDERING-01 — merge logic for same-day provider partitions. Affects how ESS data is ingested and stored, not how it is scored or ranked.
**Net scoring/ranking impact**: LOW — could affect data availability but not scoring logic

### src/portfolio/ess_coverage.py
**Risk classification**: MEDIUM (ESS coverage diagnostics)
**Actual change**: New helper functions for StarMine freshness detection (`_load_signal_rows_by_symbol`, `_has_fresh_starmine`, `_load_latest_historical_signals`). These populate the coverage warning model — diagnostic only.
**Net scoring/ranking impact**: NONE

### config/allocation_policy.yaml
**Risk classification**: MEDIUM (configuration file)
**Actual change**: Adds `signal_conflict` section with two advisory badge thresholds. Inline comment explicitly states: "Changes here affect badge classification only — no scoring or ranking impact."
**Net scoring/ranking impact**: NONE

### scripts/prepare_portfolio_review.py
**Risk classification**: MEDIUM (new script, untested state unknown)
**Actual change**: New untracked script — purpose is portfolio review artifact generation. Needs review to confirm it does not mutate scoring data.
**Assessment**: Likely safe based on naming convention but requires human review before commit.

---

## LOW RISK Files

All remaining files fall into these categories — all confirmed LOW risk:
- UI files (JavaScript, HTML) — display-only changes
- New PIS/SIH analytics modules — all confirmed read-only per repo memory notes
- Test files — additive coverage
- Documentation — no runtime impact
- Validation utilities — input validators, not scoring logic
- Signal conflict classifier — advisory display per SIGNAL-GOV-02A

---

## Summary Verdict

**The 2 HIGH-classified files are HIGH by topology only.** Both implement display-only extensions (intent labeling) and carry zero scoring/ranking risk. No file in the working tree modifies ESS scoring, CW-DAS ranking, UCF ranking, recommendation generation, or replay computation.
