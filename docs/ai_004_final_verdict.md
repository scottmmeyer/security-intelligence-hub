# AI-004 — Final Verdict: Allocation Policy Version Diff Visibility

**Status:** COMPLETE — CERTIFIED OPERATIONALLY READY  
**Date:** 2026-06-15

---

## Required Questions — Final Answers

| # | Question | Answer |
|---|----------|--------|
| Q1 | Can policy history be reconstructed from existing artifacts? | **YES** — PAR `alignment.csv` embeds `target_pct` and `tactical_target_pct` per node per run. PAR `run_metadata.json` embeds `recalculation_id`. Both are present in all 19 canonical runs. Full policy fingerprinting reconstructed from existing data. |
| Q2 | Are schema changes required? | **NO** |
| Q3 | Does this modify allocation policy? | **NO** |
| Q4 | Does this modify CRA? | **NO** |
| Q5 | Does this modify CW-DAS? | **NO** |
| Q6 | Does this modify DIL? | **NO** |
| Q7 | Does this preserve SIH/PIS separation? | **YES** — reads config and PAR artifacts, writes only to `data/history/pis/policy/`. Zero feedback path. |
| Q8 | Does this provide meaningful governance intelligence? | **YES** — Documents baseline V1 policy with full structural constraints. Infrastructure ready to detect any future policy change. |
| Q9 | Does this explain recommendation evolution? | **YES** — When policy changes occur, every target change is attributed to the specific recalculation event. Operators can answer "why did the CRA recommendation change?" by examining which node's target shifted. |
| Q10 | Does this improve auditability and traceability? | **YES** — Every PAR run is now linked to a policy fingerprint ID. Regulatory question "which policy was active when this recommendation was generated?" is now answerable. |

---

## Implementation Summary

### Files Created
| File | Description |
|------|-------------|
| `src/pis/policy_version_diff.py` | Core engine + 3 API functions |
| `tests/test_policy_version_diff.py` | 35-test validation suite |
| `docs/ai_004_policy_version_diff_design.md` | Design document |
| `docs/ai_004_algorithm_specification.md` | Algorithm specification |
| `docs/ai_004_validation_plan.md` | Validation plan |

### Files Modified
| File | Change |
|------|--------|
| `scripts/run_outcome_ui.py` | Added 3 new elif branches |
| `ui/pis_dashboard/app.js` | Added 4 section definitions, 1 subsystem, 4 render functions, 4 runSectionTask calls |
| `ui/pis_dashboard/index.html` | Added 4 new section panels |

---

## Test Results

| Suite | Result |
|-------|--------|
| AI-004 new tests (35) | **35 passed, 0 failed** |
| Pre-existing failures | 5 in unrelated test files (unchanged) |

---

## Live Endpoint Verification (2026-06-15)

All three endpoints verified against live data:

| Endpoint | Status | Key Data |
|----------|--------|---------|
| `GET /api/pis/policy/current` | ✓ LIVE | policy_id=ALLOCATION_POLICY_V1, methodology_id=v1_2026_05, effective_date=2026-05-20, config_hash=8f7195b655f3, run_count=19, node_count=39 |
| `GET /api/pis/policy/history` | ✓ LIVE | 1 version, SEED_20260520_D9E58D7F, 2026-05-21 to 2026-06-15 |
| `GET /api/pis/policy/diff` | ✓ LIVE | has_changes=False — correctly reports single-version state |

### Current Policy State (Live)
- **Active policy:** `ALLOCATION_POLICY_V1` (effective 2026-05-20)
- **Recalculation ID:** `SEED_20260520_D9E58D7F` (single version across all 19 runs)
- **Fingerprint:** `SEED_20260520_D9E58D7F:b6506ae7`
- **Structural constraints documented:** cash floor 2%, max mega-cap 50%, min international 10%, etc.
- **39 allocation nodes** with target percentages captured

---

## Does This Answer "Why Did The System Change Its Mind?"

**YES — with one important calibration.**

In the current observation window, the system has *not* changed its mind — there has been exactly one policy version active since May 20, 2026. This is the correct answer and the system correctly reports it.

When a policy recalculation *does* occur (triggered by evidence accumulation or operator action), the diff engine will automatically:
1. Detect the new `recalculation_id`
2. Compute target changes per node (delta in pp, direction)
3. Identify added/removed nodes
4. Generate governance observations: "Policy transition SEED_A → SEED_B: EQUITIES.US.MID reduced from 20% to 15%"
5. Link the policy change timestamp to the PAR runs that generated recommendations under the new policy

The answer to "why did the system change its mind?" becomes: "Policy SEED_B took effect on 2026-07-01. EQUITIES.US.MID target decreased from 20.0% to 15.0% (−5.0pp). This caused 3 CRA recommendations to shift from REDUCE_OVERWEIGHT to MAINTAIN."

---

## Final Recommendation

### **HIGH VALUE**

**Rationale:** AI-004 establishes the allocation policy audit trail — the infrastructure that allows operators and governance reviewers to answer the most important forward-looking question: "why did the guidance change?"

**Key architectural value:**

1. **Every PAR run is now policy-stamped.** The fingerprint_id links each analysis run to an exact, reproducible policy state. Audit question: "which policy version generated this recommendation?" — now answerable.

2. **Policy changes will be self-documenting.** When the allocation policy is next recalculated, the diff engine will automatically capture what changed, when, and to what extent. No manual documentation required.

3. **Structural constraints are visible.** Operators can see the governance constraints (cash floor, mega-cap ceiling, international minimum) at a glance, without opening YAML files.

4. **The diff infrastructure is future-proof.** The engine handles N versions, not just 2. As the policy evolves over months and years, the full history is maintained.

**Does this preserve "SIH decides. PIS observes."?**

**YES — by design.** The policy governance panel has zero feedback path to SIH. It reads, documents, diffs, and reports. It never modifies. It is governance infrastructure, not a control mechanism.
