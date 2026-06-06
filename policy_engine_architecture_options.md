# Policy Engine Architecture Options

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-20 Architecture Options  
Date: 2026-06-06

## Architectural Goal

Make policy behavior deterministic and consistent across recommendation systems without mutating scoring logic.

## Option A: Surface-Local Policy Handling

Description:
- Each surface (CRA, PAP, Funding Sources, Allocation Reduction, Strategic Exit) applies its own policy rules.

Pros:
- Minimal immediate refactor
- Fast local iteration

Cons:
- High divergence risk
- Duplicate logic and inconsistent explanations
- Poor auditability

Assessment:
- Not recommended as target model.

## Option B: Central Policy Decision Layer (Recommended)

Description:
- Introduce a canonical policy decision contract shared across surfaces.
- Inputs: symbol, base recommendation, opportunity flag, policy state.
- Outputs: execution_state, effective_action, priority_adjustment, explanation payload.

Pros:
- Single source of policy truth
- Consistent behavior and explainability
- Better governance and testability

Cons:
- Requires coordination across all recommendation outputs

Assessment:
- Recommended minimum architecture for ISSUE-20.

## Option C: Full Policy Rules Engine with Extensible DSL

Description:
- Generalized rules framework for many policy types and contexts.

Pros:
- Long-term flexibility
- Rich policy composition

Cons:
- Higher complexity than currently required
- Overhead before governance semantics are stable

Assessment:
- Long-term possibility only after Option B maturity.

## Q5) Future Policy Types

SIH should support additional policy types, but phased and governance-gated.

Candidate additions:
- CONVICTION_ANCHOR
- TAX_SENSITIVE
- LEGACY_POSITION
- FOUNDER_CONVICTION
- INCOME_POSITION

Recommendation:
1. Keep DO_NOT_SELL and SELL_LAST as current hard scope.
2. Add new policies only when each has:
- explicit trigger semantics,
- precedence rule,
- conflict matrix entry,
- explanation template,
- audit fields.

## Minimum Data Contract for Policy-Aware Recommendations

Every policy-affected recommendation should carry:
- policy_type
- policy_execution_gate
- execution_state
- effective_action
- original_recommendation
- policy_adjusted_priority
- policy_explanation

This contract should be consistent across CRA, PAP, Strategic Exit, Funding Sources, and Allocation Reduction outputs.
