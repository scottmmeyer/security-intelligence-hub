# Portfolio Recommendation Architecture (PRA)

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-22 Portfolio Recommendation Architecture  
Date: 2026-06-06

## Q1) Definition of Recommendation Classes

SIH should formalize five distinct output classes.

## 1. Recommendation

Definition:
- A portfolio guidance unit that can trigger an operator decision with an executable path.

Required attributes:
1. Action verb (ADD, REDUCE, EXIT, FUND_FROM, REBALANCE)
2. Target scope (symbol, sleeve, node, or basket)
3. Execution state (EXECUTABLE, DEFERRED, BLOCKED)
4. Decision horizon (now, near-term, deferred)

## 2. Observation

Definition:
- A materially relevant state that may influence decisions but does not itself prescribe immediate execution.

Examples:
- High Conviction Retain
- Strategic Retain Signal
- Dislocation state context

## 3. Narrative

Definition:
- Human-readable synthesis of portfolio posture across multiple signals.

Examples:
- Conviction anchors summary
- Portfolio concentration narrative

## 4. Explainability

Definition:
- Evidence trace that explains why a recommendation or observation exists.

Examples:
- STI classification trace
- Replay alignment evidence
- Policy adjustment rationale

## 5. Diagnostic

Definition:
- System integrity and model-behavior metadata used to validate trustworthiness.

Examples:
- Gate failures
- Coverage sufficiency indicators
- Data quality warnings

## Architecture Principle

All five classes should be displayed, but only Recommendation class items should be counted as recommendations.

## Q4) Operator-Facing Architecture

Recommended operator workspace lanes:
1. Action Queue (Recommendation class only)
2. Observation Monitor (state and context)
3. Conviction and Narrative Summary
4. Explainability Workspace
5. Diagnostic Integrity Panel

Display rule:
- Action Queue is primary.
- All other lanes are supporting.
- Cross-links connect action cards to supporting evidence.

## Q7) 2027 Mature-State PRA

Target-state flow:
1. Multi-source signal intake (CRA, PAP, STI, Dislocation, FVI, Policy)
2. Typed classification of outputs
3. Policy precedence pass
4. Recommendation normalization and deduplication
5. Action queue prioritization
6. Decision capture and execution logging
7. Outcome feedback into evidence cycle

Key mature-state properties:
- Action truthfulness (no inflation)
- Deterministic precedence
- Evidence-linked explainability
- Auditable decision-to-outcome chain
- Extensible integration for new intelligence sources
