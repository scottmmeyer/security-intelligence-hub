# Regression Results

## PRA-IMPL-02 Regression

Command:

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_pra_impl_02_funding_policy.py tests/test_cash_semantics.py tests/test_cra_phase_23_6a.py
```

Result:

- `126 passed`

Coverage highlights:

1. deterministic reduction candidate ranking with stable tie-break behavior
2. deployment funding annotations expose primary + alternatives
3. cash-first funding behavior remains intact when excess cash exists
4. non-cash fallback behavior works when cash reserve is insufficient
5. explainability extracts funding source, alternatives, and policy alignment drivers
6. existing CRA and cash semantics regressions remain green

## PIS-UI-03 Regression

Focused command:

```bash
/Users/scottmmeyer/Projects/security-intelligence-hub/.venv/bin/python -m pytest -q tests/test_pis_ui_phase1_dashboard.py
```

Result:

- `11 passed`

Broad command:

```bash
/Users/scottmmeyer/Projects/security-intelligence-hub/.venv/bin/python -m pytest -q tests/test_pis_governance_stage_a.py tests/test_pis_canonical_daily_004b.py tests/test_pis_change_detection_phase1.py tests/test_pis_recommendation_lineage_01.py tests/test_pis_ui_phase1_dashboard.py
```

Result:

- `36 passed`

Coverage highlights:

1. Executive KPI header and all summary card anchors are present.
2. System status banner now exposes an explicit overall health label.
3. Inventory/governance/canonical/change-summary/lineage detail tables are collapsible.
4. Progressive loading and lineage timeout/degraded contracts remain in place.

## PIS-UI-02 Regression

Command:

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_pis_ui_phase1_dashboard.py
```

Result:

- `9 passed`

Runtime validation highlights:

- loading banner visible at startup
- section placeholders visible immediately
- healthy sections render before lineage completes
- lineage transitions through `LOADING -> SLOW -> FAILED`
- dashboard remains usable during lineage timeout

## Focused Governance Regression

Command:

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_signal_coverage_phase1.py tests/test_signal_coverage_phase3.py tests/test_signal_coverage_phase5.py tests/test_si_refresh_02_coverage.py
```

Result:

- `26 passed`

## Adjacent Refresh Regression

Command:

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_signal_fetch_resume.py
```

Result:

- `3 passed`

## Coverage-Aware Enforcement Regression (Phase 6)

Command:

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_signal_coverage_phase6.py tests/test_signal_coverage_phase1.py tests/test_signal_coverage_phase3.py tests/test_signal_coverage_phase5.py tests/test_si_refresh_02_coverage.py
```

Result:

- `31 passed`

Additional command:

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_signal_fetch_resume.py
```

Result:

- `3 passed`

## Coverage Repair Retry Regression (Phase 7)

Command:

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_signal_coverage_phase7.py tests/test_signal_fetch_resume.py tests/test_signal_coverage_phase6.py
```

Result:

- `15 passed`

Full command:

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_signal_coverage_phase1.py tests/test_signal_coverage_phase3.py tests/test_signal_coverage_phase5.py tests/test_si_refresh_02_coverage.py tests/test_signal_fetch_resume.py tests/test_signal_coverage_phase6.py tests/test_signal_coverage_phase7.py
```

Result:

- `41 passed`

Live validation command:

```bash
PYTHONPATH=. .venv/bin/python scripts/refresh_signals.py --smart --providers danelfin yahoo --report-path data/current/last_signal_refresh_report.json
```

Live result summary:

- Yahoo retried `19` failed checkpoints; `19` refreshed; coverage `DEGRADED -> COMPLIANT`
- Danelfin retried `2` failed checkpoints; `2` refreshed; coverage `DEGRADED -> COMPLIANT`

## New Coverage Enforced by Tests

Added coverage proves:

1. latest holdings baseline uses the same mtime-based source everywhere
2. applicable holdings are submitted for Zacks refresh
3. applicable holdings are submitted for Danelfin refresh
4. applicable holdings are submitted for Yahoo refresh
5. non-applicable holdings are classified explicitly
6. research-universe health and holdings coverage remain separate metrics
7. research `FRESH` can coexist with holdings `DEGRADED`, but the contract is explicit and tested
8. provider fresh + holdings degraded triggers targeted `coverage_repair` refresh
9. provider fresh + holdings compliant skips refresh with explicit `skip_compliant` mode
10. stale/missing applicable holdings are the targeted submission set during coverage-repair
11. refresh reporting surfaces provider activity and coverage before/after for UI truthfulness
12. same-day successful checkpoints are skipped in coverage-repair
13. same-day failed/empty checkpoints are retried in coverage-repair
14. stale same-day checkpoints are retried in coverage-repair
15. research-refresh resume behavior remains unchanged
16. reporting now distinguishes `skipped_already_covered` and `retried_failed_checkpoint`

## PIS-UI-01 Regression (Phase 1 Read-Only Dashboard)

Command:

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_pis_phase1.py tests/test_pis_ui_phase1_dashboard.py
```

Result:

- `14 passed`

Coverage highlights:

1. snapshot inventory contract returns expected fields
2. latest snapshot summary returns totals and top holdings
3. timeline change-vs-prior calculation is deterministic
4. empty-state defaults are explicit and non-crashing
5. multi-account same-day snapshots aggregate correctly
6. SIH <-> PIS navigation links and required `/api/pis/*` calls are present

## PIS-BACKFILL-01 Regression (Historical PAR -> PIS)

Command:

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_pis_backfill_01.py tests/test_pis_phase1.py tests/test_pis_ui_phase1_dashboard.py
```

Result:

- `19 passed`

Backfill execution command:

```bash
PYTHONPATH=. .venv/bin/python3 scripts/backfill_pis_snapshots.py --all
```

Initial run result summary:

- `eligible_runs=235`
- `registered_snapshots=67`
- `skipped_duplicates=166`
- `skipped_invalid_runs=0`
- `failures=2`

Post-fix idempotency re-run summary:

- `eligible_runs=235`
- `registered_snapshots=0`
- `skipped_duplicates=233`
- `skipped_invalid_runs=2`
- `failures=0`

Live API evidence after backfill:

- `/api/pis/health` -> `snapshot_count=67`
- `/api/pis/status` -> `snapshot_count=67`
- `/api/pis/snapshots` -> populated snapshot inventory rows
- `/api/pis/latest` -> populated summary and top holdings

## PIS-002 Regression (Portfolio Change Detection Engine)

Command:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_pis_change_detection_phase1.py tests/test_pis_backfill_01.py tests/test_pis_ui_phase1_dashboard.py -q
```

Result:

- `17 passed`

Coverage highlights:

1. New, exited, increased, reduced/unchanged semantics are validated against deterministic fixtures.
2. Cash delta is validated via `is_cash_equivalent` rows.
3. Multi-account same-day aggregation is validated.
4. Snapshot ordering is validated (latest date compares only to immediate prior date).
5. Empty-history behavior returns explicit non-crashing payloads.
6. API read-model payload keys are validated for latest/detail/summary responses.
7. Route wiring for `/api/pis/changes/latest`, `/api/pis/changes/{snapshot_id}`, and `/api/pis/change-summary` is validated.
8. Dashboard HTML/JS contract now validates all six change-detection sections and endpoint wiring.

## PIS-003 Regression (Recommendation Lineage Matching)

Command:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_pis_recommendation_lineage_01.py tests/test_pis_change_detection_phase1.py tests/test_pis_backfill_01.py tests/test_pis_ui_phase1_dashboard.py -q
```

Result:

- `24 passed`

Coverage highlights:

1. High-confidence direct symbol/direction/timing lineage matching is validated.
2. Medium-confidence delayed symbol match behavior is validated.
3. Low-confidence theme-level lineage behavior is validated.
4. Unmatched (`NONE`) changes are explicitly validated.
5. Multiple-candidate ranking and tie-break selection are validated.
6. High-confidence demotion under competing recommendations is validated.
7. API payload contracts for latest/detail/summary lineage endpoints are validated.
8. Empty-history behavior persists headers and returns explicit empty payloads.
9. Server route presence and dashboard section/API wiring are validated.

## PERFORMANCE-ATTRIBUTION-01 Regression

Focused command:

```bash
/Users/scottmmeyer/Projects/security-intelligence-hub/.venv/bin/python -m pytest -q tests/test_pis_performance_attribution_01.py tests/test_pis_ui_phase1_dashboard.py
```

Result:


Broad command:

```bash
/Users/scottmmeyer/Projects/security-intelligence-hub/.venv/bin/python -m pytest -q tests/test_pis_governance_stage_a.py tests/test_pis_canonical_daily_004b.py tests/test_pis_change_detection_phase1.py tests/test_pis_recommendation_lineage_01.py tests/test_pis_performance_attribution_01.py tests/test_pis_ui_phase1_dashboard.py
```

Result:


Coverage highlights:

1. Deterministic winner/neutral/loser threshold classification is validated.
2. Record-level attribution joins lineage matches to canonical-governed change rows deterministically.
3. Snapshot-level attribution summary aggregation is validated.
4. Latest/history/aggregate attribution payload contracts are validated.
5. New server routes for `/api/pis/attribution/latest`, `/api/pis/attribution/history`, and `/api/pis/attribution-summary` are validated.
6. Dashboard attribution sections and endpoint wiring contracts are validated.

## PERFORMANCE-ATTRIBUTION-01B-A Regression (Benchmark Source and Return-Series Foundation)

Command:

```bash
.venv/bin/python -m pytest -q tests/test_pis_benchmark_attribution_01a.py
```

Result:

- `5 passed`

Extended slice:

```bash
.venv/bin/python -m pytest -q tests/test_pis_performance_attribution_01.py tests/test_pis_ui_phase1_dashboard.py tests/test_pis_benchmark_attribution_01a.py
```

Result:

- `21 passed`

Coverage highlights:

1. SPY benchmark source abstraction is deterministic via provider interface.
2. Canonical interval return-series calculation is validated.
3. Nearest-prior-trading-day alignment is validated for non-trading canonical dates.
4. Benchmark return, portfolio return, and excess return math are validated.
5. Missing benchmark-data behavior is deterministic and explicit in `data_quality_status`.
6. CSV persistence contract for `data/history/pis/benchmark_attribution/benchmark_return_series.csv` is validated.
7. Benchmark attribution API route contracts are validated for returns/latest/summary endpoints.

## PERFORMANCE-ATTRIBUTION-01B-B Regression (Recommendation and Source-Level Benchmark Alpha)

Command:

```bash
.venv/bin/python -m pytest -q tests/test_pis_benchmark_attribution_01a.py tests/test_pis_benchmark_attribution_01b.py
```

Result:

- `10 passed`

Extended slice:

```bash
.venv/bin/python -m pytest -q tests/test_pis_performance_attribution_01.py tests/test_pis_ui_phase1_dashboard.py tests/test_pis_benchmark_attribution_01a.py tests/test_pis_benchmark_attribution_01b.py
```

Result:

- `26 passed`

Coverage highlights:

1. Recommendation attribution rows join benchmark intervals by `snapshot_date` + `prior_snapshot_date`.
2. Recommendation excess return math is deterministic.
3. Source-level alpha aggregation metrics are deterministic.
4. Positive/negative alpha classification is deterministic.
5. Non-OK benchmark rows are excluded from headline source alpha metrics.
6. Non-OK benchmark rows are preserved in detail records for audit.
7. Benchmark recommendation/source/latest API contracts are validated.

## PERFORMANCE-ATTRIBUTION-01B-C Regression (Benchmark Attribution Dashboard Integration)

Command:

```bash
.venv/bin/python -m pytest -q tests/test_pis_ui_phase1_dashboard.py tests/test_pis_benchmark_attribution_01a.py tests/test_pis_benchmark_attribution_01b.py tests/test_pis_performance_attribution_01.py
```

Result:

- `26 passed`

Coverage highlights:

1. Benchmark Attribution section anchors exist in PIS dashboard HTML.
2. Benchmark API calls wired in app.js.
3. Quality badge helper exists in app.js.
4. Benchmark summary card exists in HTML.
5. Source alpha table target exists in HTML.
6. Progressive loading section attributes exist for benchmark sections.
7. No regressions in prior attribution or lineage dashboard contracts.

## AI-003 Regression (Allocation Explainability)

Focused command:

```bash
/Users/scottmmeyer/Projects/security-intelligence-hub/.venv/bin/python -m pytest -q tests/test_allocation_explainability_01.py tests/test_wp04_1_ui_prototype.py
```

Result:

- `12 passed`

Broad command:

```bash
/Users/scottmmeyer/Projects/security-intelligence-hub/.venv/bin/python -m pytest -q tests/test_allocation_explainability_01.py tests/test_wp04_1_ui_prototype.py tests/test_pis_performance_attribution_01.py tests/test_pis_ui_phase1_dashboard.py
```

Result:

- `28 passed`

Coverage highlights:

1. Deterministic explanation generation from persisted recommendation artifacts is validated.
2. Policy, signal, funding, and philosophy driver mapping are validated.
3. Missing-driver handling is explicit and non-crashing.
4. Explanation persistence CSV contract headers are validated.
5. New `/api/explanations/*` routes are validated for presence.
6. Portfolio Alignment UI contract for Recommendation Explanation rendering is validated.

## PIS-004A Regression (Account Scope Governance Stage A)

Command:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_pis_governance_stage_a.py tests/test_pis_ui_phase1_dashboard.py -q
```

Result:

- `14 passed`

Adjacent command:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_pis_change_detection_phase1.py tests/test_pis_recommendation_lineage_01.py -q
```

Result:

- `13 passed`

Coverage highlights:

1. Expected account scope evaluates to PASS deterministically.
2. Contaminated scope with 401(k)/BrokerageLink evaluates to REJECT.
3. Value warning band behavior is deterministic.
4. Value reject threshold behavior is deterministic.
5. Source artifact warnings are deterministic.
6. Combined rule evaluation preserves REJECT precedence.
7. Threshold configurability is validated with custom config.
8. Governance latest/summary API payload contracts are validated.
9. Dashboard contract validates governance endpoints and section wiring.

## PIS-004B Regression (Canonical Daily Snapshot Selection Stage B)

Command:

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_pis_canonical_daily_004b.py tests/test_pis_change_detection_phase1.py tests/test_pis_recommendation_lineage_01.py tests/test_pis_ui_phase1_dashboard.py
```

Result:

- `23 passed`

Coverage highlights:

1. PASS is preferred over WARNING during canonical daily selection.
2. REJECT candidates are excluded from canonical selection.
3. WARNING is selected only when no PASS candidate exists.
4. Latest-ingested PASS candidate is selected deterministically.
5. Snapshot ID lexical tie-break is deterministic.
6. Canonical persistence to `data/history/pis/canonical/canonical_daily_snapshots.csv` is validated.
7. Canonical API payloads (`latest/history/summary`) are validated.
8. Dashboard contract now validates canonical section and canonical API wiring.
9. Change detection tests run on governance-compliant canonical fixtures.
10. Lineage tests remain deterministic under canonical recompute flow.

Runtime endpoint verification:

- `/api/pis/canonical/latest` -> HTTP 200
- `/api/pis/canonical/history` -> HTTP 200
- `/api/pis/canonical-summary` -> HTTP 200
- `/api/pis/summary` -> HTTP 200 with canonical timeline values
- `/api/pis/changes/latest` -> HTTP 200 with canonical snapshot IDs
- `/api/pis/lineage/latest` -> HTTP 200 with canonical-derived lineage