# PIS Navigation and UI Model
**Date:** 2026-06-12

## Navigation Principle

PIS should be reachable from SIH decision surfaces, and SIH should be able to deep-link into PIS outcomes.

## Navigation Hierarchy

### From SIH to PIS
Examples:
- Deployment Candidate -> View Outcome History
- Reduction Candidate -> View Prior Trade Outcome
- Recommendation Card -> View Portfolio Change Lineage

### From PIS to SIH
Examples:
- VEA Exit -> View Original Recommendation
- Unresolved Cash Increase -> View Related Deployment Context
- New Position -> View Recommendation History

## URL Strategy

Use stable, descriptive routes that encode the portfolio outcome object being viewed.

Recommended pattern:
- `/pis/snapshots/{snapshot_id}`
- `/pis/changes/{event_id}`
- `/pis/lineage/{lineage_id}`
- `/pis/reconciliation/{queue_id}`
- `/pis/outcomes/{symbol}`

Cross-links back to SIH should use the matching SIH run or recommendation identifier.

Examples:
- `/sih/recommendations/{recommendation_id}`
- `/sih/deployment-queue/{run_id}`
- `/sih/reduction-queue/{run_id}`

## Cross-Link Strategy

Each PIS record should retain:
- source recommendation id
- SIH run id
- portfolio snapshot id
- lineage confidence
- resolution state

This allows navigation in both directions without duplicating business logic.

## User Workflow

1. User sees a portfolio change in PIS.
2. User opens the matched SIH recommendation.
3. User checks whether the change was expected.
4. If no match exists, user resolves the missing-information prompt.
5. The resolution becomes part of the PIS lineage record.

## UI Principle

PIS UI should explain outcomes, not recreate SIH decision tools.

The two systems should feel connected, but visually and functionally distinct:
- SIH = decision surface
- PIS = outcome surface
