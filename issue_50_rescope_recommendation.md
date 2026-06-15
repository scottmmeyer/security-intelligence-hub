# Issue #50 Re-Scope Recommendation

## Goal

Preserve completed attribution work without incorrectly closing the benchmark-attribution issue.

## Constraint

This workspace does not provide direct issue-tracker mutation in the current task flow, so this document supplies issue-ready titles, status recommendations, and body text for manual issue updates.

## Phase 1 — Recommendation Attribution Completion Record

### New Issue

**Title:** `PERFORMANCE-ATTRIBUTION-01A — Recommendation Outcome Attribution`

**Status:** `CLOSED`

### Summary

Implemented:
- canonical-governed attribution
- recommendation lineage integration
- outcome classification
- attribution persistence
- attribution APIs
- attribution dashboard sections
- deterministic tests

### Evidence Link

- [performance_attribution_acceptance_audit.md](performance_attribution_acceptance_audit.md)

### Recommended Issue Body

This issue records completion of the recommendation outcome attribution layer.

Delivered scope:
- canonical-governed change attribution
- recommendation lineage integration
- deterministic outcome classification
- attribution persistence under `data/history/pis/attribution/`
- PIS attribution APIs
- dashboard attribution sections
- deterministic tests and regression coverage

This issue is complete and should be closed independently of benchmark attribution.

## Phase 2 — Re-Scope Existing Issue #50

### Updated Title

**Title:** `PERFORMANCE-ATTRIBUTION-01B — Portfolio Return and Benchmark Attribution`

### Updated Status

- `OPEN`
- `priority-medium`
- `needs-design`

### Required Body Update

Not yet implemented:
- benchmark return series
- SPY comparison
- excess return
- alpha
- benchmark APIs
- benchmark dashboard

Current state:
- Recommendation Outcome Attribution is complete and tracked separately as PERFORMANCE-ATTRIBUTION-01A.
- Benchmark Attribution remains open and should continue under Issue #50 as PERFORMANCE-ATTRIBUTION-01B.

### Recommended Issue Body

Issue #50 is re-scoped to cover benchmark-relative attribution only.

In scope:
- portfolio return
- SPY return
- excess return / alpha
- recommendation excess return
- source-level excess return
- benchmark attribution persistence, APIs, and dashboard sections

Out of scope for this issue:
- recommendation outcome attribution already completed under PERFORMANCE-ATTRIBUTION-01A

Status:
- OPEN
- priority-medium
- needs-design

## Phase 3 — Benchmark Attribution Stream

Recommended supporting design/audit artifact:
- [benchmark_engine_reuse_assessment.md](benchmark_engine_reuse_assessment.md)

## Final Recommendation

### Q9. Should Recommendation Outcome Attribution be considered complete?

Yes.

The completed work should be preserved as PERFORMANCE-ATTRIBUTION-01A and considered closed.

### Q10. Should Issue #50 remain open?

Yes.

The benchmark-attribution portion is not implemented and should remain open.

### Q11. Should benchmark attribution become its own tracked implementation stream?

Yes.

It should be tracked as PERFORMANCE-ATTRIBUTION-01B with its own design, scope, and validation gates.

### Q12. What is the recommended next feature to build?

Recommended next feature: AI-003 — Allocation Philosophy Explainability.

Reasoning:
- higher trust and operator clarity payoff now
- lower implementation risk than benchmark attribution
- benchmark attribution can proceed cleanly after design is finalized
