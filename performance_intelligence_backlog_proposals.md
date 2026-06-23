# Performance Intelligence Backlog Proposals
## SIH-BACKLOG-REALIGNMENT-01 — Part C

Date: 2026-06-17

## Proposed New Issues

### PERF-VAL-01 — Performance Calculation Validation
Priority: High

Objective:
Validate SIH can independently reproduce Fidelity performance reporting.

Validation Questions:
- Q1: Can SIH reproduce Fidelity TWRR?
- Q2: Can SIH reproduce benchmark returns?
- Q3: Can SIH explain return variance?
- Q4: Can SIH independently calculate alpha?

Expected Deliverable Format:

Fidelity Return:
48.73%

SIH Return:
48.5x%

Variance:
+/- 0.xx pp

Benchmark Return:
xx.xx%

SIH Alpha:
xx.xx pp

Variance Explanation:
- Methodology deltas
- Cash-flow timing assumptions
- Price source timing differences
- Rounding conventions

Acceptance Criteria:
1. SIH return and benchmark calculations are reproducible from immutable artifacts.
2. Variance to Fidelity is quantified and explained to a documented tolerance band.
3. Alpha decomposition is auditable and traceable to source artifacts.
4. Output is exposed via API and summarized in dashboard panel.

Suggested Deliverables:
- src/pis/performance_validation.py
- data/analysis/performance/performance_validation_report.json
- UI section: "Performance Validation"
- Tests: deterministic fixtures for TWRR and benchmark calculations

---

### PERF-VAL-02 — Benchmark Methodology Reconciliation
Priority: Medium

Objective:
Document and reconcile benchmark methodology differences between Fidelity and SIH (constituent set, weighting, rebalance cadence, holidays, and stale-price handling).

Acceptance Criteria:
1. Methodology matrix identifies all meaningful differences.
2. Each difference has quantified return impact on a known date range.
3. Final benchmark-reconciliation note is published and linked from PERF-VAL-01.

---

### PERF-VAL-03 — Variance Attribution Engine
Priority: Medium

Objective:
Build deterministic attribution of performance variance components: data-source timing, pricing source, cash treatment, and rounding.

Acceptance Criteria:
1. Variance is decomposed into additive components that sum to total variance.
2. Component-level attribution is reproducible across reruns.
3. Exposed through API for audit and dashboard rendering.

## Ready-to-Create GitHub Issue Body (PERF-VAL-01)

Title:
PERF-VAL-01: Performance Calculation Validation (Fidelity vs SIH)

Body:
Validate SIH can independently reproduce Fidelity portfolio return, benchmark return, and alpha calculations.

Questions:
- Can SIH reproduce Fidelity TWRR?
- Can SIH reproduce benchmark returns?
- Can SIH explain variance?
- Can SIH independently calculate alpha?

Deliverable format:
- Fidelity Return: xx.xx%
- SIH Return: xx.xx%
- Variance: +/- x.xx pp
- Benchmark Return: xx.xx%
- SIH Alpha: xx.xx pp
- Variance explanation with methodology deltas

Governance:
- Deterministic and auditable calculations only
- No silent assumptions
- Source lineage required for all performance inputs
