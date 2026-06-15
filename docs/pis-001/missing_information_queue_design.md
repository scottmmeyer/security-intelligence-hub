# Missing Information Queue Design
**Project:** PIS-001
**Date:** 2026-06-12

## Purpose

Capture portfolio changes that cannot be classified automatically and route them to the operator for reconciliation.

## When an Event Becomes Unresolved

An event becomes unresolved when:
- no SIH recommendation match is found
- the change is not explained by known portfolio state transitions
- cash moves are visible but the funding source is unknown
- a new position has no clear SIH lineage

## Queue Record Fields

- unresolved_event_id
- event_id
- snapshot_date_from
- snapshot_date_to
- account_id
- symbol
- event_type
- magnitude
- auto_classification_attempt
- auto_classification_confidence
- missing_reason_code
- prompt_group
- status
- created_at_utc
- resolved_at_utc
- operator_resolution
- operator_notes

## Prompt Groups

### Cash change prompts
For unexplained cash increases, prompt the user with:
- Deposit
- Transfer
- Dividend
- Sale Proceeds
- Other

### New position prompts
For positions without a recommendation match, prompt the user with:
- Personal Research
- Advisor Recommendation
- External Service
- Other

### Exit prompts
For sales or exits without lineage, prompt the user with:
- Planned Reduction
- Risk Management
- Reallocation
- Unclear
- Other

## Workflow

1. PIS detects an unresolved event.
2. PIS records the event in the queue with the best available confidence score.
3. The operator reviews the prompt and chooses the most accurate explanation.
4. The resolution is stored as lineage metadata for future analysis.
5. Future matching logic may learn from prior resolution patterns, but Phase 1 should remain rule-based.

## Status Lifecycle

- OPEN
- NEEDS_REVIEW
- RESOLVED
- SUPPRESSED

## Design Principle

This queue is not a failure state. It is the mechanism that makes the otherwise invisible portfolio state observable and auditable.
