# ISSUE-13 Recommendation - Market Context Intelligence (MCI)

Project: Security Intelligence Hub (SIH)  
Date: 2026-06-06

## Q7) Minimum Viable MCI

Smallest useful implementation:

1. Deterministic run-level context snapshot
- regime label (RISK_ON/NEUTRAL/RISK_OFF)
- volatility regime flag
- rates shock flag
- breadth/sector stress flag
- scheduled macro-event window flag

2. Evidence drawer
- raw drivers and thresholds used for each label
- source and timestamp lineage

3. UI usage
- informational strip in portfolio alignment views
- no score/rank/recommendation mutation

4. Governance defaults
- explicit disclaimer: context is advisory, not causal proof
- immutable artifact storage for audit and replay

## Q8) Mature MCI Vision (Multi-Year)

Phase 1 (0-6 months):
- Option A informational-only MCI with deterministic signals and audit trails.

Phase 2 (6-18 months):
- operator-behavior analytics and attribution quality review
- introduce confidence-modifier experiments in shadow mode only (no rank impact)

Phase 3 (18+ months):
- if and only if evidence supports predictive/decision value across regimes,
  propose controlled integration pathways under formal governance review.

## Required Final Recommendation

1. Should ISSUE-13 exist?
- Yes, as a new issue concept for MCI assessment and design.
- Note: GitHub issue number 13 is already occupied historically, so create a new numbered issue for this scope.

2. What priority relative to ISSUE-12D?
- Lower than ISSUE-12D.
- ISSUE-12D is already on a defined evidence milestone and unblocks active dislocation outcome review.
- MCI should begin as a scoped design + informational pilot after ISSUE-12D readiness work is stable.

3. Should MCI begin as informational-only?
- Yes. Strong recommendation.

4. Should MCI ever influence scoring?
- Potentially, but only after outcome validation standards at least as strict as ISSUE-12 and likely stricter due to higher causality risk.
- No near-term scoring influence recommended.

5. What is the minimum implementation worth building?
- Deterministic run-level context snapshot + auditable evidence vector + read-only UI overlay.

## Final Governance Verdict

Recommendation: APPROVE MCI as a governance-scoped informational intelligence initiative (Option A), sequenced after ISSUE-12D execution gates, with explicit prohibition on narrative causal claims and no scoring/ranking influence in initial phases.
