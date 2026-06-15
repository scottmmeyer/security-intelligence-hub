# Decision Lineage Framework
**Project:** PIS-001
**Date:** 2026-06-12

## Purpose

Associate portfolio changes with the SIH recommendation or action path that likely produced them.

## Lineage Chain

Recommendation -> Trade -> Outcome

Example:
- SIH deployment candidate: VRT
- trade executed: buy
- outcome: positive contribution after the trade

## Primary SIH Sources

PIS should search these SIH artifacts first:
- PAP outputs
- CRA deployment queue
- reduction queue
- DIL explanations
- recommendation history
- run metadata and portfolio snapshots

## Matching Methodology

### 1) Symbol match
The detected portfolio change must match the recommendation symbol or affected symbol set.

### 2) Direction match
- NEW_POSITION / POSITION_INCREASE should prefer buy or add recommendations.
- POSITION_REDUCTION / POSITION_EXIT should prefer reduction, trim, or exit recommendations.

### 3) Temporal match
The change date should fall after the recommendation date and within a configurable lineage window.

### 4) Context match
Use shared metadata where available:
- conviction tier
- recommendation type
- deployment queue rank
- CW-DAS or other SIH explanation fields
- node or mandate context

## Confidence Scoring

Suggested confidence bands:
- 90-100: strong exact match
- 70-89: likely match with minor ambiguity
- 40-69: partial match, needs user confirmation
- below 40: unresolved

Suggested scoring inputs:
- exact symbol overlap
- exact direction alignment
- close date proximity
- matching recommendation type
- matching portfolio node or outcome context

## Example Matches

### VRT added
- symbol: VRT
- recommendation source: deployment queue
- direction: buy
- confidence: 96%
- classification: matched deployment recommendation

### VEA sold
- symbol: VEA
- recommendation source: reduction queue
- direction: sell
- confidence: 92%
- classification: matched reduction recommendation

## Lineage Record Fields

- lineage_id
- event_id
- recommendation_id
- recommendation_source
- recommendation_type
- matched_symbol
- matched_direction
- match_confidence
- evidence_summary
- resolution_status
- user_override_reason

## Governance Rule

Lineage matching must be additive and non-destructive.
It may annotate outcomes, but it must not change SIH recommendation history or scoring outputs.
