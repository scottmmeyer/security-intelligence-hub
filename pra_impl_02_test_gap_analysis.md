# PRA-IMPL-02 Test Gap Analysis

## Scope

Independent review of `tests/test_pra_impl_02_funding_policy.py` against the full
behavioral surface of PRA-IMPL-02. Evidence from code inspection.

---

## Q21. What behavior is actually covered?

The test file contains 6 tests:

| Test | Coverage |
|---|---|
| `test_reduction_candidates_rank_deterministically` | Category ranking order (SIGNAL_DETERIORATION > OVERWEIGHT_REDUCTION > LOW_CONVICTION), conviction penalty active, reason/alignment fields present |
| `test_reduction_tie_breaks_by_symbol` | Lexicographic tie-break when score and category are identical |
| `test_deployment_annotations_include_primary_and_alternatives` | `annotate_deployments_with_funding_plan` populates primary source, reason, and alternatives on deployment targets |
| `test_cash_first_policy_when_available` | `identify_funding_sources` selects EXCESS_CASH as primary when deployable cash > floor |
| `test_no_cash_scenario_uses_non_cash_sources` | Cash at 1% (below 2% reserve floor) → no EXCESS_CASH source → first source is non-cash |
| `test_explainability_extracts_funding_and_alternatives_drivers` | AI-003 correctly extracts all 3 new driver types from post-PRA rationale format |

**Summary: Core happy-path scenarios are covered.**

---

## Q22. What behavior is NOT covered?

### Missing CRA-level coverage

1. **`score_reduction_candidates` with blocked source**
   - Sources with `blocked_by_policy=True` should score 0.0 and rank last
   - Not tested

2. **`score_reduction_candidates` with DO_NOT_SELL policy**
   - `policy_penalty("DO_NOT_SELL") = -100` effectively zeros the score
   - Not tested explicitly (test_pra only uses `blocked=False`)

3. **`annotate_deployments_with_funding_plan` with no eligible sources**
   - All sources blocked → deployments returned unmodified (funding fields remain empty)
   - Not tested

4. **`annotate_deployments_with_funding_plan` with self-funding exclusion**
   - Candidates exclude `s.symbol == target.symbol` to prevent self-funding
   - Not tested with overlapping symbols

5. **Capital source builder → score_reduction_candidates integration**
   - `build_capital_sources(...)` → `score_reduction_candidates(...)` path is
     tested only via CRA phase tests (`test_cra_phase_23_6a.py`) but without
     asserting the new `reduction_score` / `reduction_reason` fields on output

6. **RotationProposal serialization of new fields**
   - No test verifies `rotation_proposal.to_dict()` includes `reduction_score`,
     `reduction_reason`, `policy_alignment_reason` on source records or
     `funding_source_*` fields on target records

### Missing PAP-level coverage

7. **`identify_funding_sources` with multiple overweight nodes**
   - Live trace shows 2 OVERWEIGHT_REDUCTION sources for the same portfolio
   - Test only creates 1 alignment node; multi-node ordering not verified

8. **`identify_funding_sources` with SELL_LAST policy source**
   - `policy_penalty("SELL_LAST") = -5` should lower ranking of a SELL_LAST source
   - Not tested

9. **`_funding_policy_alignment(entry)` for unknown source_type**
   - Falls back to "Policy-aware funding source." — not tested

10. **PAP recommendation rationale clause construction**
    - No test verifies the actual full rationale string emitted by
      `generate_recommendations(...)` contains the Why/Alternatives/Policy clauses
    - `test_pra` only verifies the parser, not the generator

### Missing explainability coverage

11. **Pre-PRA rationale (no Why/Alternatives/Policy clauses)**
    - `build_recommendation_explanation` with old-style rationale should return
      only `funding_source` driver, not alternatives or policy
    - Not tested

12. **Rationale with no funding clause at all**
    - REDUCE_OVERWEIGHT recommendations have no funding clause
    - Should return empty `funding_drivers` list
    - Not tested

### Missing API/UI coverage

13. **`/api/cra/proposal` payload fields**
    - No test calls the API endpoint and asserts `reduction_score`,
      `reduction_reason`, `policy_alignment_reason` in the JSON response

14. **UI rendering**
    - No test verifies the `_craBuildSourceCard` or `_craBuildTargetCard` functions
      render the new HTML blocks (no DOM/HTML rendering test exists)

---

## Q23. Are there missing edge cases?

Yes, several:

1. **Exactly at reserve floor** (deployable_cash = 0.0 exactly)
   - `max(0.0, total - floor) = 0.0` → condition `> 0.1` fails → no source
   - Not tested; could be important for portfolios at exact target cash level

2. **All sources blocked**
   - `pool_sources` becomes empty in `rotation_proposal_builder`
   - `annotate_deployments_with_funding_plan` receives no actionable sources
   - Deployment targets returned unmodified → correct behavior, but not asserted

3. **Deployment target is also a reduction source** (circular conflict)
   - `annotate_deployments_with_funding_plan` excludes `s.symbol == target.symbol`
   - But `score_reduction_candidates` does NOT exclude deployment targets from scoring
   - The conviction penalty (-2 to -22) is the mechanism, not hard exclusion
   - Not tested: what happens when the only source is also the only target

4. **DEFERRED sources**
   - `filtered_sources` excludes `priority == "DEFER"`
   - Not tested in PRA tests (covered in CRA phase tests)

5. **Tie at score 0.0** (two blocked sources)
   - Both score 0.0; tie-break by proceeds then symbol
   - Not tested

---

## Q24. Are there missing serialization/API/UI tests?

**Yes — this is the largest gap.**

| Missing Test | Severity | Rationale |
|---|---|---|
| CRA proposal API payload contains new fields | HIGH | Operators rely on API payload; serialization could break without detection |
| `RotationProposal.to_dict()` includes `reduction_score` on sources | HIGH | Direct contract verification |
| `RotationDeploymentTarget.to_dict()` includes `funding_source_alternatives` | HIGH | Direct contract verification |
| `_craBuildSourceCard` renders reduction score/reason HTML | MEDIUM | UI regression could go undetected |
| `_craBuildTargetCard` renders funding source HTML | MEDIUM | UI regression could go undetected |
| PAP rationale includes all 3 new clauses | MEDIUM | Generator correctness |
| Pre-PRA rationale produces only `funding_source` driver | LOW | Backward compat |

**Recommended next action:** Add a serialization test that:
1. Builds a `CapitalSourceRecord` with `reduction_score=95.0`, `reduction_reason="test"`, `policy_alignment_reason="test"`
2. Calls `.to_dict()` (or the `to_api_payload_dict` equivalent in models)
3. Asserts the new keys are present in the output dict

And a `RotationDeploymentTarget` equivalent for `funding_source_alternatives`.
