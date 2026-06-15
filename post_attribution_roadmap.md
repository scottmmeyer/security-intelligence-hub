# Post-Attribution Roadmap

## Scope

This roadmap evaluates the next recommended implementation order after Recommendation Outcome Attribution is complete.

Candidates reviewed:
- AI-003 — Allocation Philosophy Explainability
- PRA-IMPL-02 — Policy-Aware Funding Sources
- PERFORMANCE-ATTRIBUTION-01B — Benchmark Attribution
- AI-004 — Allocation Policy Version Diff Visibility
- PA-006 — Allocation Drift Trend Visibility

Reviewed sources:
- [docs/backlog/allocation_intelligence/AI-003-allocation-philosophy-explainability.md](docs/backlog/allocation_intelligence/AI-003-allocation-philosophy-explainability.md)
- [docs/backlog/allocation_intelligence/AI-004-allocation-policy-version-diff.md](docs/backlog/allocation_intelligence/AI-004-allocation-policy-version-diff.md)
- [docs/backlog/portfolio_alignment/PA-006-allocation-drift-trend-visibility.md](docs/backlog/portfolio_alignment/PA-006-allocation-drift-trend-visibility.md)
- [docs/backlog/implementation_recommendations.md](docs/backlog/implementation_recommendations.md)
- [pra_impl_02_certification.md](pra_impl_02_certification.md)

## Current Status Notes

- Recommendation Outcome Attribution is complete.
- Benchmark Attribution remains open.
- PRA-IMPL-02 appears already certified complete for its original scope in [pra_impl_02_certification.md](pra_impl_02_certification.md).
- AI-003 is high priority but content-dependent.
- AI-004 is medium priority and depends on versioning infrastructure.
- PA-006 is medium priority and requires new historical aggregation infrastructure.

## Q6. Which should be next?

Recommended next feature: **AI-003 — Allocation Philosophy Explainability**.

Reasoning:
- already identified as high-priority governance enrichment
- medium complexity rather than large infrastructure work
- benefits immediately from the system’s growing recommendation/outcome explainability story
- does not depend on benchmark attribution
- improves operator trust sooner than a deeper benchmark build

If the team wants an analytics-heavy next stream instead of a governance/explainability stream, then PERFORMANCE-ATTRIBUTION-01B is the best separate implementation stream, but it should not displace the clearer and lower-risk AI-003 follow-up unless benchmark comparison is suddenly business-critical.

## Q7. Which depends on benchmark attribution?

Direct dependency among the listed candidates: none.

Observations:
- AI-003 does not require benchmark attribution.
- AI-004 does not require benchmark attribution.
- PA-006 does not require benchmark attribution.
- PRA-IMPL-02 is already complete and does not depend on benchmark attribution.

However, PERFORMANCE-ATTRIBUTION-01B itself depends on:
- benchmark data readiness
- canonical portfolio return construction
- benchmark-aligned interval logic

## Q8. Which benefits from recommendation outcome attribution already completed?

Most direct beneficiary: **PERFORMANCE-ATTRIBUTION-01B**.

Secondary beneficiary: **AI-003**.

Why:
- Benchmark Attribution can build directly on the existing recommendation attribution records, source grouping, and dashboard patterns.
- AI-003 benefits indirectly because the system now has a stronger explainability narrative around "why recommendations existed" and "what happened after they were acted on."

## Recommended Order

1. AI-003 — Allocation Philosophy Explainability
2. PERFORMANCE-ATTRIBUTION-01B — Portfolio Return and Benchmark Attribution
3. AI-004 — Allocation Policy Version Diff Visibility
4. PA-006 — Allocation Drift Trend Visibility

PRA-IMPL-02 should not be scheduled as next work because the repo already records it as complete for its certified scope.

## Rationale Summary

- AI-003 is the best next feature because it is high-priority, bounded, and trust-enhancing.
- PERFORMANCE-ATTRIBUTION-01B should remain open as its own implementation stream and move after AI-003 unless external pressure makes benchmark comparison urgent.
- AI-004 comes after AI-003 because version-diff visibility depends on stronger governance/versioning support.
- PA-006 remains later because it requires new infrastructure and is larger in scope.
