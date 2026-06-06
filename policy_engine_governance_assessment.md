# Policy Engine Governance Assessment

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-20 Governance and Explainability Controls  
Date: 2026-06-06

## Governance Principles

1. Preserve intelligence truth.
- Never hide or rewrite the original recommendation signal.

2. Apply policy as explicit execution governance.
- Policy modifies actionability/ordering, not scoring evidence.

3. Keep operator intent auditable.
- Every policy-affected recommendation must include machine-readable and human-readable rationale.

4. Maintain deterministic precedence.
- Same inputs must always produce same policy-adjusted outputs.

## Q6) Explanation Requirements

Every policy-affected recommendation must include:
1. Base recommendation and reason
2. Active policy and policy rationale
3. Policy effect on actionability/rank
4. Effective action after policy
5. Audit timestamp and decision snapshot id

### Example 1: DO_NOT_SELL vs SELL

Input:
- Symbol: TSLA
- Base recommendation: TRIM
- Policy: DO_NOT_SELL

Required explanation:
- "TRIM signal detected from allocation/score evidence. Execution blocked by active DO_NOT_SELL policy. Action changed to MONITOR_ONLY."

### Example 2: SELL_LAST vs Reduce Candidate

Input:
- Symbol: DODFX
- Base recommendation: REDUCE_CANDIDATE
- Policy: SELL_LAST

Required explanation:
- "Reduction signal detected. SELL_LAST policy keeps symbol executable but moves it behind non-SELL_LAST candidates in liquidation priority."

## Q7) Interaction with ISSUE-19 FVI

Policy and FVI should be compositional, not substitutive.

Decision order recommendation:
1. Determine sleeve action (for example International overweight -> reduce sleeve)
2. Determine vehicle quality from FVI (for example DODFX = ELITE)
3. Apply operator policy constraints (for example SELL_LAST)
4. Emit final action plan with separate sleeve and vehicle lanes

### DODFX Example

Given:
- FVI: ELITE
- Policy: SELL_LAST
- Sleeve: International overweight

Recommended output:
- Sleeve action: reduce International exposure
- Vehicle action: retain DODFX as preferred/last-to-sell implementation vehicle
- Execution action: seek alternative reduction sources first; DODFX only as last resort if reduction target unmet

This avoids false replacement and preserves high-quality vehicles while honoring policy intent.

## Required Controls

1. Policy-affected action log in run artifacts
2. Policy conflict validation (hard reject for contradictory pairs)
3. Cross-surface consistency checks for execution_state/effective_action mapping
4. Periodic governance audit of blocked/deferred recommendations and outcome impact

## Risk Assessment

Primary risks if not governed:
- inconsistent recommendations across surfaces
- hidden policy overrides without clear explanation
- operator distrust from opaque action changes

Mitigation:
- central policy decision contract,
- deterministic precedence,
- mandatory explanation payload,
- explicit audit trail.
