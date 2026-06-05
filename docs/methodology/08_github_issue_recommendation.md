# 08 — GitHub Issue Recommendation

## Recommended Issue

---

### Title
`[METHODOLOGY] Establish and Publish Consensus Intelligence Investing Framework`

### Labels
`governance` `documentation` `priority-medium` `ready`

### Epic
EPIC-06: Governance & Tooling

### Milestone
Governance & Backlog

### Description

The Security Intelligence Hub has developed a coherent, multi-layer investment methodology through Phases 23.x through 8.0B.1D. This methodology is currently distributed across dozens of phase deliverable documents but is not formally documented in a single canonical reference.

This issue establishes and publishes the official SIH investment philosophy as:

**Consensus Intelligence Investing (CII)**

A four-layer framework:
1. Analyst Consensus (ESS, Zacks, Danelfin)
2. Fundamental Validation (FMP data)
3. Historical Validation (Replay)
4. Portfolio Discipline (CW-DAS, CRA)

### Deliverables

Phase 8.0B.1E produces 9 methodology documents in `docs/methodology/`:

- `01_methodology_classification.md`
- `02_consensus_intelligence_framework.md`
- `03_core_beliefs.md`
- `04_dislocation_philosophy.md`
- `05_branding_and_naming.md`
- `06_tagline_recommendations.md`
- `07_ui_integration_recommendation.md`
- `08_github_issue_recommendation.md`
- `09_final_verdict.md`

### Acceptance Criteria
- [ ] 9 methodology documents written and committed to `docs/methodology/`
- [ ] Primary name established: "Consensus Intelligence Investing (CII)"
- [ ] Primary tagline established: "Where Analyst Consensus Meets Portfolio Discipline"
- [ ] Dislocation philosophy documented (INTACT + CONSISTENT = opportunity; DETERIORATING + CONTRADICTORY = value trap)
- [ ] Core beliefs documented (10 beliefs)
- [ ] UI integration recommendation produced
- [ ] GitHub Issue created with this specification
- [ ] No code changes, no scoring changes

### Related Issues (created from this phase)

**Spawned actionable issue:**

`[UI] Add methodology tagline to Portfolio Alignment header subtitle`

Labels: `ui-ux` `governance` `priority-low` `ready`  
Effort: XS  
Description: Update `<p class="subtitle">` in `index.html` to include "Where Analyst Consensus Meets Portfolio Discipline". Single-line text change. No functional impact.

Acceptance Criteria:
- [ ] Header subtitle updated per `docs/methodology/07_ui_integration_recommendation.md` Option A
- [ ] All other UI functionality unchanged
- [ ] No regressions

**Spawned future issue:**

`[UI] Build Methodology About Dialog (CII framework reference panel)`

Labels: `ui-ux` `governance` `priority-low` `needs-design`  
Effort: S  
Description: Add a `ⓘ` icon to the SIH header that opens a brief methodology panel explaining the four-layer framework. Informational only.

---

## Should This Become an Official Backlog Item?

**YES.**

The methodology documentation is not just historical record — it is a governance anchor. When future changes are proposed, they should be evaluated against the stated beliefs and framework layers. A change that violates Core Belief 9 (operator authority is final) or bypasses a framework layer (e.g., removing the Replay gate) should be flagged against this document.

**The methodology document is also the single best answer to:**
- "What does SIH do?"
- "How is this different from just following analyst ratings?"
- "Why can't I just look up the Zacks rating myself?"

It is appropriate to track this as a closed backlog item once Phase 8.0B.1E deliverables are complete, with the spawned UI issue (`tagline update`) as an open actionable item.
