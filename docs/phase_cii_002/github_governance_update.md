# GitHub Governance Update — Phase CII-002

## Decision: Create a Separate Issue

The methodology enhancement belongs in a dedicated issue, not ISSUE-03.

**Reasoning:**
- ISSUE-03 is a research/design phase for FMP score integration — it has nothing to do with methodology documentation
- Methodology enhancements are governance work, not scoring work
- A separate issue creates a cleaner audit trail

## New Issue Created

**Title:** `ISSUE-06: CII Methodology Enhancement — Alpha Framework and Why CII Exists`  
**GitHub Issue:** #12 (or next available number)  
**Epic:** EPIC: Company Context and Methodology (#4)  
**Labels:** `governance` `ui-ux` `priority-medium` `ready`

## Issue Description

Added Expected Sources of Alpha section, enhanced Objective text, and Why CII Exists philosophy section to the CII methodology panel. Also replaced the invisible ⓘ icon with a visible "About CII" pill button.

## Status at Phase CII-002 Completion

**Closed immediately** — all acceptance criteria met in this session:
- ✅ Four Expected Sources of Alpha documented and displayed
- ✅ Objective enhanced with "superior long-term risk-adjusted returns"  
- ✅ Why CII Exists philosophy section added
- ✅ About CII pill visible and accessible
- ✅ 1,004 tests passing

## Methodology Document Updates

The alpha framework additions in `docs/phase_cii_002/cii_alpha_framework.md` should be merged into:
- `docs/methodology/02_consensus_intelligence_framework.md` (Layer descriptions)
- `docs/methodology/03_core_beliefs.md` (Belief 1, 3, 4, 5 now have explicit alpha mechanisms)

This merge is tracked as a documentation housekeeping item, not a blocking requirement.
