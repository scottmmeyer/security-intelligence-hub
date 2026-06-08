# Implementation Readiness Review

Project: Security Intelligence Hub (SIH)  
Scope: Transition readiness from assessment to implementation  
Date: 2026-06-08

## Q1) Per-Assessment Readiness Verdict

### ISSUE-19 — Fund Vehicle Intelligence (FVI)

Assessment complete: Yes  
Ready for implementation: Yes, phase-1 advisory only  
Blocked: No for advisory overlay; yes for scoring influence  
Missing design elements: Data source contract and peer-group configuration schema  

Readiness detail:
- The advisory quality label (LOW/MEDIUM/HIGH/ELITE) from three percentile inputs is fully specified.
- Peer group category assignment for common holdings (DODFX -> Foreign Large Value) is documented.
- Load/switching economics framework is defined.
- Missing element before implementation: explicit data ingestion contract for whichever provider (Morningstar-class or fallback) will supply category rank, expense ratio, and risk-adjusted return percentile at runtime.
- Scoring influence path remains blocked by evidence burden; not relevant to phase-1 implementation.

Recommended status: Transition to implementation with phase-1 scope (advisory overlay only).

---

### ISSUE-20 — Policy-Aware Recommendation Engine

Assessment complete: Yes  
Ready for implementation: Yes  
Blocked: No  
Missing design elements: Explicit unit-test scope for cross-surface execution_state assertions  

Readiness detail:
- DO_NOT_SELL and SELL_LAST behaviors across all six surfaces are fully tabulated.
- Canonical execution state outputs (BLOCKED_BY_POLICY, DEFERRED_BY_POLICY, MONITOR_ONLY, REDUCE_SELL_LAST) are defined.
- Precedence hierarchy is explicit (policy > allocation > vehicle quality > signal rank).
- Implementation requires extending existing policy execution gate logic to Funding Sources and Allocation Reduction output layers; no score mutations required.
- Missing element: explicit test scenarios for each surface combination (six surfaces × two policy types = twelve baseline test assertions).

Recommended status: Transition to implementation immediately as the highest-priority delivery in the PRA stream.

---

### ISSUE-21 — Recommendation Surface Rationalization

Assessment complete: Yes  
Ready for implementation: Yes  
Blocked: No  
Missing design elements: Typed card schema wire format and card_type field placement in the JSON payload  

Readiness detail:
- Five semantic classes (ACTION, OBSERVATION, NARRATIVE, EXPLAINABILITY, DIAGNOSTIC) are defined.
- Placement model for each card type is documented.
- Typed count replacement policy is fully specified.
- Missing element before full implementation: decision on where `card_type` metadata field lives in the JSON response structure (`recommendations.json`, `deployment_queue.json`, or both).
- High Conviction Retain reclassification is fully specified and has no scoring dependency.

Recommended status: Transition to implementation in tandem with ISSUE-20. UI surface work can proceed once policy execution state fields are stable.

---

### ISSUE-22 — Portfolio Recommendation Architecture

Assessment complete: Yes  
Ready for implementation: Yes, as contracts; implementation work is delivered via child issues  
Blocked: No  
Missing design elements: Formal typed-output schema definition  

Readiness detail:
- Recommendation class hierarchy, lifecycle states, and precedence model are fully documented.
- Mature-state 2027 architecture is articulated.
- This issue does not map to a single bounded implementation unit. Its value is as the governing contract document for PRA-IMPL-01 through PRA-IMPL-05.
- Missing element: a formal schema file (JSON Schema or equivalent) for card_type, execution_state, effective_action, and evidence_link contract fields.

Recommended status: Transition by creating the typed-output schema as a concrete deliverable of PRA-IMPL-01, then treating ISSUE-22 as archival.

---

## Summary Table

| Issue | Complete | Ready | Blocked | Missing | Recommended Status |
|---|---|---|---|---|---|
| ISSUE-19 FVI | Yes | Phase-1 yes | Phase-2 scoring path | Data ingestion contract | Transition to phase-1 implementation |
| ISSUE-20 Policy Engine | Yes | Yes | No | Cross-surface test scope | Transition to implementation immediately |
| ISSUE-21 Surface Rationalization | Yes | Yes | No | card_type JSON placement | Transition in tandem with ISSUE-20 |
| ISSUE-22 PRA Architecture | Yes | As contracts | No | Typed schema definition | Transition by creating PRA-IMPL-01 |

## Governance Notes

No code changes are proposed in this document.  
No issues are created or closed in this document.  
These are readiness assessments and planning recommendations only.
