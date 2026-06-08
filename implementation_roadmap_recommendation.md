# Implementation Roadmap Recommendation

Project: Security Intelligence Hub (SIH)  
Scope: Full implementation planning recommendation  
Date: 2026-06-08

## Q3) Recommended Structure

Recommended structure: parent/child implementation issues.

Rationale:
- Three independent issues risks fragmented contract semantics.
- One umbrella issue creates an oversized unmanageable scope.
- Parent/child gives architecture coherence with independently completable units.

---

## Recommended Implementation Issues to Create

### Parent: PRA-IMPL-00 — Portfolio Recommendation Architecture Implementation

Purpose: Umbrella tracking issue. Contains typed recommendation schema, lifecycle contract, and architecture decisions required before children proceed.

Labels: epic, governance, recommendation-engine, priority-high
Dependencies: ISSUE-22 (design basis)
Status at creation: in-progress (scope definition complete)

---

### Child 1: PRA-IMPL-01 — Typed Recommendation Contract and Card Schema

Purpose: Define and publish the formal typed-output schema for recommendation cards across all surfaces.

Deliverables:
- card_type field in JSON response payload
- execution_state canonical value set
- effective_action canonical value set
- evidence_link field specification
- card lifecycle state machine (OBSERVED → ACTION_QUALIFIED → POLICY_ADJUSTED → DECISION_PENDING → EXECUTED)

Labels: enhancement, governance, recommendation-engine, priority-high, ready
Dependencies: None
Recommended first implementation target: Yes

---

### Child 2: PRA-IMPL-02 — Policy-Aware Funding Sources and Allocation Reduction

Purpose: Apply ISSUE-20 canonical execution states to Funding Sources and Allocation Reduction surfaces.

Deliverables:
- DO_NOT_SELL: exclusion from executable funding source candidates
- DO_NOT_SELL: BLOCKED_BY_POLICY state on Allocation Reduction cards
- SELL_LAST: tail-ranking in funding cohort with badge
- SELL_LAST: DEFERRED_BY_POLICY on Allocation Reduction cards
- Explanation text referencing active policy
- 12 baseline cross-surface acceptance test assertions

Labels: enhancement, governance, ui-ux, policy-engine, priority-high, ready
Dependencies: PRA-IMPL-01 (card schema)

---

### Child 3: PRA-IMPL-03 — Recommendation Surface Lane Separation and Typed Counts

Purpose: Replace single aggregate recommendation count with typed lanes and typed counts.

Deliverables:
- Four UI lanes: Action Queue, Observation Monitor, Conviction Anchors, Explainability Workspace
- Typed count header: Actions N, Observations N, Conviction Anchors N, Explainability N
- card_type-driven lane routing
- "Total Cards" label replaces "Total Recommendations" on aggregate display

Labels: enhancement, ui-ux, governance, recommendation-surface, priority-medium, ready
Dependencies: PRA-IMPL-01, PRA-IMPL-02 preferred

---

### Child 4: PRA-IMPL-04 — Conviction Anchors Section Extraction

Purpose: Move High Conviction Retain, Conviction Anchor, and Strategic Retain Signal cards out of the main Action Queue into the Conviction Anchors lane.

Deliverables:
- Conviction Anchors section with UCF tier and conviction evidence context
- Cross-link from Conviction Anchor entry to related deployment or reduction action if applicable
- Removal of these card types from Actions count

Labels: enhancement, ui-ux, sti, recommendation-surface, priority-medium, ready
Dependencies: PRA-IMPL-03

---

### Child 5: PRA-IMPL-05 — FVI Advisory Overlay

Purpose: Phase-1 advisory fund quality labels integrated into allocation reduction and replacement review surfaces.

Deliverables:
- Fund quality label (LOW/MEDIUM/HIGH/ELITE) on fund-type holdings in Allocation Reduction surface
- Peer group configuration for held mutual funds
- Advisory-only display; no score modification
- "Reduce sleeve, retain quality vehicle" language where label is HIGH or ELITE
- Policy × FVI combined display (SELL_LAST + ELITE renders as separate concerns)

Labels: enhancement, governance, fvi, recommendation-engine, priority-medium, needs-data
Dependencies: PRA-IMPL-01, PRA-IMPL-02, PRA-IMPL-03

---

## Q4) Recommended Labels

| Label | Apply to |
|---|---|
| enhancement | All PRA-IMPL issues |
| governance | All PRA-IMPL issues |
| ui-ux | PRA-IMPL-02, 03, 04, 05 |
| policy-engine | PRA-IMPL-02 |
| recommendation-engine | PRA-IMPL-00, 01, 05 |
| recommendation-surface | PRA-IMPL-03, 04 |
| sti | PRA-IMPL-04 |
| fvi | PRA-IMPL-05 |
| epic | PRA-IMPL-00 (parent) |
| priority-high | PRA-IMPL-00, 01, 02 |
| priority-medium | PRA-IMPL-03, 04, 05 |
| ready | PRA-IMPL-01, 02, 03, 04 |
| needs-data | PRA-IMPL-05 |

---

## Q5) Recommended Sequencing

| Step | Issue | Status | Can Parallelize With |
|---|---|---|---|
| 1 | ISSUE-12D | Open, milestone-gated | All PRA-IMPL |
| 2 | PRA-IMPL-01 (typed schema) | Ready | ISSUE-12D |
| 3 | PRA-IMPL-02 (policy normalization) | Ready after PRA-IMPL-01 | — |
| 4 | PRA-IMPL-03 (surface lanes + counts) | Ready after PRA-IMPL-01/02 | Early UX design during step 3 |
| 5 | PRA-IMPL-04 (conviction anchors) | Ready after PRA-IMPL-03 | — |
| 6 | PRA-IMPL-05 (FVI advisory overlay) | Needs-data; after PRA-IMPL-01/02/03 | Data config during step 4 |
| 7 | MCI implementation | Post current architecture stabilization | — |

---

## Q6) Recommended First Implementation Target

PRA-IMPL-01: Typed Recommendation Contract and Card Schema

Why:
1. Zero scoring risk; purely additive JSON schema fields.
2. Enables all downstream children.
3. Fastest path to unblocking policy normalization and surface rationalization.
4. Concrete, bounded deliverable with clear acceptance criteria.
5. No data dependencies.

---

## Q7) Recommended Roadmap Timeline View

```
June 2026
  └── ISSUE-12D: evidence collection underway (milestone: Dec 2026)
  └── PRA-IMPL-01: typed recommendation schema → start

July 2026
  └── PRA-IMPL-02: policy-aware Funding Sources + Allocation Reduction

August 2026
  └── PRA-IMPL-03: surface lane separation + typed counts
  └── PRA-IMPL-04: conviction anchors extraction (in tandem with 03)

Q4 2026
  └── PRA-IMPL-05: FVI advisory overlay (after data config completed)
  └── ISSUE-12D: evidence milestone approach (Dec 2026)

2027
  └── MCI implementation planning begins
  └── ISSUE-12D outcome review (milestone: Dec 2026, results in Q1 2027)
  └── FVI phase-2 policy-gated replacement (evidence-dependent)
```

---

## Assessment Issues: Recommended Final Status

| Issue | Recommended Action After Implementation Issues Created |
|---|---|
| ISSUE-19 FVI Assessment | Close with comment linking PRA-IMPL-05; retain as design record |
| ISSUE-20 Policy Engine Assessment | Close with comment linking PRA-IMPL-02; retain as design record |
| ISSUE-21 RSR Assessment | Close with comment linking PRA-IMPL-03/04; retain as design record |
| ISSUE-22 PRA Assessment | Close with comment linking PRA-IMPL-00; retain as design record |
