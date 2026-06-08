# Backlog Priority Recommendation

Project: Security Intelligence Hub (SIH)  
Scope: Priority ordering and implementation sequence recommendation  
Date: 2026-06-07

## Priority Recommendation Across Requested Streams

Requested priority set:
- ISSUE-12D
- FVI implementation
- Policy Engine implementation
- Recommendation Surface Rationalization
- Portfolio Recommendation Architecture
- MCI

Recommended order:
1. ISSUE-12D (existing evidence/milestone track)
2. Portfolio Recommendation Architecture implementation (from ISSUE-22)
3. Policy Engine implementation (from ISSUE-20)
4. Recommendation Surface Rationalization implementation (from ISSUE-21)
5. FVI implementation phase-1 advisory integration (from ISSUE-19)
6. MCI implementation follow-on

## Priority Rationale

1. ISSUE-12D remains a fixed governance gate with explicit milestone timeline.
2. PRA (ISSUE-22) is the architecture contract needed to unify semantics and counting.
3. Policy implementation (ISSUE-20) establishes execution truth and precedence.
4. Surface rationalization (ISSUE-21) translates contract truth into operator-facing UX.
5. FVI implementation (ISSUE-19) should land on top of policy-aware, rationalized surfaces.
6. MCI is strategically valuable but lower immediate execution integrity impact.

## Q6 Summary: What Can Be Parallelized

Parallelizable:
- ISSUE-12D evidence work with PRA implementation stream.
- UX design exploration for surface rationalization while policy normalization is underway.

Sequential dependencies:
- Policy and surface contracts before FVI integration.
- Architecture contract before large cross-surface UI/counting migrations.

## Final Backlog Governance Recommendation

1. Keep assessment issues (19-22) as design records and close them after linking implementation-track issues.
2. Create implementation-track child issues with explicit dependencies and typed acceptance criteria.
3. Maintain one architecture umbrella to prevent fragmented recommendation semantics.
4. Report progress using typed action metrics (actions vs non-action intelligence), not aggregate recommendation totals.

## Explicit Non-Changes

This package performs no code changes, no test changes, no scoring changes, and no direct GitHub mutations.
