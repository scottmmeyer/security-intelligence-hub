# Phase 23.6A — Implementation Summary

**Date:** 2026-06-04
**Status:** COMPLETE

---

## Files Created

| File | Lines | Role |
|------|-------|------|
| `src/portfolio/cra/__init__.py` | 19 | Package init, public exports |
| `src/portfolio/cra/models.py` | 183 | Data contracts: CapitalSourceRecord, RotationDeploymentTarget, PortfolioImpactEstimate, RotationProposal |
| `src/portfolio/cra/capital_source_builder.py` | 354 | 5-category source detection, policy gating, tax modifier application, deduplication |
| `src/portfolio/cra/impact_estimator.py` | 149 | Simplified alignment/concentration delta estimation |
| `src/portfolio/cra/rotation_proposal_builder.py` | 264 | Full proposal assembly, capital allocation, manifest-based run resolution |
| `tests/test_cra_phase_23_6a.py` | 543 | 63-test suite covering all 5 categories, policy handling, tax modifiers, allocation, impact, integration |

## Files Modified

| File | Change |
|------|--------|
| `scripts/run_outcome_ui.py` | Added `GET /api/cra/proposal` endpoint (~45 lines) |

**Total lines added:** ~1,557

---

## Design Changes Required

### Change 1: `allocation_node` not in serialized queue entries
- **Design assumed:** `allocation_node` field present in `deployment_queue.json`
- **Reality:** Phase 23.5 added `allocation_node` to the Python model but existing serialized PAR runs pre-date this field
- **Resolution:** `_derive_allocation_node()` in `rotation_proposal_builder.py` derives the node from `holdings.csv` geography + market_cap_bucket when the persisted field is absent. Future PAR runs that serialize `allocation_node` will use it directly.

### Change 2: No per-symbol tax buckets in tax state
- **Design assumed:** Per-symbol A–E bucket assignments in `portfolio_alignment_state.json`
- **Reality:** Tax state has `strategic_exit_symbols` and `operator_policies` but no per-symbol bucket table
- **Resolution:** Bucket derived from `cost_basis` vs `market_value` comparison:
  - `cost_basis > market_value` → Bucket A (loss harvest)
  - Small gain (≤$5,000) → Bucket C
  - Large gain (>$5,000) → Bucket D (operator review)
  - Bucket B and E require `holding_days` data not available in PAR artifacts; not assigned
- **Impact:** Bucket E (approaching LT threshold) cannot be detected without holding_days; documented in open questions

### Change 3: `security_overlays.csv` missing `market_value` and `weight_vs_target`
- **Design assumed:** `market_value` and `weight_vs_target` fields on overlay rows
- **Reality:** These fields are not in `security_overlays.csv`; market_value is in `holdings.csv`
- **Resolution:** `capital_source_builder.py` joins overlays with holdings by symbol for market_value. `weight_vs_target` is replaced by `drift_pct` from `alignment.csv` joined via derived allocation_node.

### Change 4: `strategic_profiles.json` does not exist in current PAR runs
- **Reality:** The file is not produced by the current PAR pipeline
- **Resolution:** Category 2 (Strategic Exit) gracefully falls back to:
  1. Operator-designated `strategic_exit_symbols` from tax state
  2. TRIM/WATCH flags from overlays (already covered by Category 1)
  - When strategic_profiles are passed explicitly (future support), full STI classification is used

---

## Implementation Notes

- The `_CandidateRecord` mutable staging class is used internally to enable priority merging during deduplication before converting to frozen `CapitalSourceRecord`
- Tax modifier application (`_apply_tax_modifier`) operates on the mutable candidate in-place; this is the only internal mutation — external contracts remain immutable
- Bucket D downgrade rule only applies to HIGH priority (not URGENT); this is intentional: if a thesis is completely broken (URGENT), the operator still sees the signal clearly with review required
- The `build_proposal_from_manifest()` convenience function automatically excludes CONCENTRATED_ALPHA runs from the "active run" selection; this mirrors the existing portfolio alignment UI behavior
