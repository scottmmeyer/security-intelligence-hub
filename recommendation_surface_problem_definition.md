# Recommendation Surface Rationalization (RSR) Problem Definition

Project: Security Intelligence Hub (SIH)  
Assessment: ISSUE-21 Recommendation Surface Rationalization  
Date: 2026-06-06

## Context

The Allocation and Portfolio Observations panel currently mixes multiple content types in one stream:
- action directives,
- observations,
- conviction context,
- explainability evidence,
- narrative framing.

This mixed stream increases interpretive load and can inflate perceived recommendation volume.

## Q1) Proper Mission of the Panel

The panel should support all of the above content categories, but not as a single undifferentiated recommendation stream.

Recommended mission:
1. Primary mission: present actionable portfolio decisions clearly.
2. Secondary mission: provide supporting observations and explainability context.
3. Tertiary mission: provide narrative synthesis where it improves operator confidence.

Operational rule:
- The main stream should be action-first.
- Non-action content should be visibly separated and not counted as recommendations.

## Core Problem Statement

Current presentation can make informational items (for example High Conviction Retain) look equivalent to action items (for example Allocation Reduction, Funding Source change).

This causes:
- recommendation inflation,
- unclear operator next steps,
- overstated workload perception,
- weaker trust in recommendation urgency labels.

## Q3) What Qualifies as a Recommendation?

A true recommendation should satisfy all required criteria:
1. It can change operator behavior in this review cycle.
2. It implies a concrete portfolio action path (buy/add/reduce/exit/reallocate).
3. It has an execution state (executable, deferred, blocked).
4. It can affect allocation, position sizing, or funding flow decisions.

If one or more of these criteria is missing, classify as observation/explainability/narrative, not recommendation.

## Design Principle

Separate semantic types at render-time, not by removing information:
- retain full intelligence context,
- classify and route to the correct panel lane,
- avoid presenting all lanes as "recommendations."

## Assessment Boundary

This document set is governance and UX architecture only.
No implementation changes, scoring changes, or methodology changes are proposed here.
