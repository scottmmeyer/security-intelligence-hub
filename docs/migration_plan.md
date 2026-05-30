# Phase 7.3 Migration Plan

**Phase 7.3 — Architecture Design**
**Document type:** Phased migration specification
**From:** Current gap-first allocation engine
**To:** Unified Portfolio Optimizer (UPO)

---

## 0. Guiding Principles

1. **Zero regression tolerance.** Every phase must pass the full test suite before
   merging. 464/464 is the floor throughout this migration.

2. **Additive before replacement.** New logic runs in parallel with existing logic
   until it is validated. Existing recommendation output is preserved in full
   until Phase 7.3D replaces it.

3. **Audit first, produce later.** Each sub-phase produces a verification artifact
   before it changes any production output.

4. **PMI is authoritative.** Mandate interpretation is never overridden. The migration
   unifies the engine with PMI — it does not weaken PMI's authority.

5. **No UI changes until 7.3C.** The output shape of `run_analysis()` must not
   change in a breaking way for the UI server until the full recommendation tier
   model is implemented and the UI can consume it.

---

## Phase 7.3A — Parallel Scoring

**Goal:** Add PIS computation as a parallel output alongside existing recs.
No production recommendation behavior changes. PIS is computed, stored, and
auditable but does not control output order or suppression.

**Scope:**

1. **Move signal pre-computation earlier** in `runner.py`
   - `build_security_overlays()` called before `generate_recommendations()`
   - `build_strategic_profiles()` called before `generate_recommendations()`
   - Result: overlays and profiles are available as inputs to rec generation
   - **No change to recommendation output** — they are not used yet

2. **Add `compute_pis()` function** to a new module `src/portfolio/optimizer.py`
   - Inputs: candidate (holding or ETF vehicle), alignment_results, overlays,
     profiles, mandate
   - Output: float PIS score + breakdown dict (for audit)
   - Formula: as specified in `unified_optimizer_design.md` Section 4

3. **Add parallel PIS scoring pass** to runner output
   - After recs are generated: compute PIS for each rec's primary vehicle
   - Store as `pis_scores` key in result dict: `{rec_id: pis_float}`
   - Store as `pis_breakdown` key: `{rec_id: {component: value}}`

4. **Add audit script** `scripts/_generate_phase73a_pis_audit.py`
   - Runs pipeline, reads `pis_scores`, compares to PIS from Phase 7.2 audit
   - Verifies PIS ranking order matches intuition (VRT > LRCX > DELL > ... > VOO)
   - Outputs `pis_audit_report.md`

**Validation criteria:**
- [ ] All 464 tests pass
- [ ] `pis_scores` appears in `run_analysis()` result dict
- [ ] PIS for VRT ≥ 70 (Phase 7.2 computed 76.7)
- [ ] PIS for VOO ≤ 0 (fails all gates)
- [ ] PIS for REDUCE recs computed and positive

**Risk:** Low. Additive only. No existing code path is modified.

---

## Phase 7.3B — Conflict Detection

**Goal:** Implement the three conflict detection algorithms and store conflict
metadata alongside existing recommendations. Still no change to which recs are
shown or their order.

**Scope:**

1. **Add `detect_conflicts()` function** to `src/portfolio/optimizer.py`
   - Inputs: `list[PortfolioRecommendation]`, alignment_results, vehicle_exposure_map
   - Output: `list[RecommendationConflict]` dataclass
   - Implement T1, T2, T3 detection as specified in `conflict_graph_report.md` Section 6

2. **Add `RecommendationConflict` model** to `models.py`
   ```python
   @dataclass
   class RecommendationConflict:
       conflict_id: str
       conflict_type: str           # T1 | T2 | T3
       rec_a_id: str
       rec_b_id: str
       description: str
       severity: str                # HIGH | MODERATE | LOW
       resolution: str              # SUPPRESS_A | MERGE | DEMOTE | NONE
   ```

3. **Add `conflict_graph` key** to runner result dict
   - Value: list of `RecommendationConflict` dicts
   - Existing recs unchanged

4. **Add `portfolio_improvement_score` field** to `PortfolioRecommendation`
   - Populated from Phase 7.3A `pis_scores` map
   - Default: None (backward compatible)

5. **Add conflict fields** to `PortfolioRecommendation`
   - `conflict_ids: tuple[str, ...]` — populated if this rec is involved in a conflict
   - `conflict_types: tuple[str, ...]`
   - Default: empty tuple (backward compatible)

6. **Add audit script** `scripts/_generate_phase73b_conflict_audit.py`
   - Outputs `conflict_detection_report.md` with full conflict matrix
   - Verifies CF-001 through CF-005 from `conflict_graph_report.md` are detected

7. **Add tests** for T1, T2, T3 detection:
   - Test T1: mock two recs where Build vehicle leaks into OW node → expect T1 conflict
   - Test T2: mock two Build recs with shared vehicle → expect T2 conflict
   - Test T3: mock MODERATE rec + mandate INFORMATIONAL → expect T3 conflict

**Validation criteria:**
- [ ] All 464 + new tests pass
- [ ] `conflict_graph` key present in result
- [ ] CF-001 (VOO ↔ HYPER_MEGA) detected as T1 HIGH
- [ ] CF-004/CF-005 (PMI contradictions) detected as T3 HIGH
- [ ] Zero false positives on REDUCE-vs-REDUCE pairs (should be N or S, not conflict)

**Risk:** Low-Medium. New model fields are additive (default None/empty).
Existing code that reads `PortfolioRecommendation` fields is unaffected.
Test additions are net-positive.

---

## Phase 7.3C — Unified Ranking

**Goal:** The recommendation list is now sorted by PIS descending instead of
drift severity. Conflicted recs are moved to `INFORMATIONAL` tier.
The existing recommendation format is preserved — only sort order and a
new `recommendation_tier` field change.

**Scope:**

1. **Add `recommendation_tier` field** to `PortfolioRecommendation`
   - Assign from `_assign_recommendation_tier(rec, pis, conflict_ids, mandate_urgency)`
   - Tiers: `HIGH_CONVICTION_BUY` | `REPLAY_OPPORTUNITY` | `ALLOCATION_REPAIR` |
     `TRIM_RECOMMENDED` | `REBALANCE_ONLY` | `INFORMATIONAL`
   - Default `recommendation_tier = None` until this phase

2. **Add `mandate_gate_result` field** to `PortfolioRecommendation`
   - Values: `PASS` | `SOFT_PASS` | `FAIL`
   - FAIL forces `recommendation_tier = INFORMATIONAL` regardless of PIS

3. **Sort output rec list by PIS** (descending) in `generate_recommendations()`
   - INFORMATIONAL recs sorted after all action recs (consistent with current behavior
     of lower-priority recs appearing at end)

4. **Add `raw_severity` field** to `PortfolioRecommendation`
   - Preserves the original drift-based severity for audit/diagnostics
   - Existing `severity` field is RETAINED — populated from `raw_severity` for
     backward compatibility with all consumers

5. **Update `build_mandate_recommendation_overlay()`** to no longer emit the
   contradiction pattern — if `mandate_urgency = INFORMATIONAL`, the rec's
   `recommendation_tier` is set to INFORMATIONAL at generation time, and the
   `mandate_overlay` dict still contains the full interpretation for audit.

6. **Update UI server** `scripts/run_outcome_ui.py` to:
   - Read `recommendation_tier` field for display grouping
   - Show "Deploy Capital" | "Reduce Exposure" | "Balance Allocations" sections
   - Collapse INFORMATIONAL recs by default

7. **Add tests** covering:
   - `recommendation_tier` assignment logic for each tier
   - Sort order: HIGH_CONVICTION_BUY appears before REBALANCE_ONLY
   - Mandate FAIL gate sets tier to INFORMATIONAL regardless of PIS

**Validation criteria:**
- [ ] All 464 + new tests pass
- [ ] VRT, LRCX, DELL (if surfaced as recs) have tier `HIGH_CONVICTION_BUY` or `REPLAY_OPPORTUNITY`
- [ ] VOO rec has tier `INFORMATIONAL`
- [ ] Output rec list is sorted by PIS descending
- [ ] `severity` field still present and populated (backward compat)
- [ ] UI renders without errors

**Risk:** Medium. Sort order change and new fields. UI must be updated in lockstep.
This phase is the first visible change to `run_analysis()` output ordering.

---

## Phase 7.3D — Security-First Recommendation Engine

**Goal:** The recommendation engine evaluates individual portfolio securities as
Buy/Add candidates for underweight nodes before falling back to ETFs. ETFs are
only recommended when no high-conviction security alternative exists and mandate
permits it. This is the full Unified Portfolio Optimizer architecture.

**Scope:**

1. **Refactor `generate_recommendations()`** (major)
   - Currently: for each UNDERWEIGHT node → look up vehicle registry → emit rec
   - New: for each UNDERWEIGHT node → run UPO candidate evaluation
     - Build candidate set (direct securities + ETF vehicles)
     - Apply conviction gate to each candidate
     - Compute PIS for each passing candidate
     - Apply conflict detection (reuse Phase 7.3B algorithms)
     - Assign tier to top candidate(s)
     - Emit recommendation for top candidate(s) only

2. **Add `build_candidate_set()` function** to `optimizer.py`
   - For a given target node: returns all portfolio securities classified in that node
   - Plus all ETF vehicles registered for that node
   - Returns list of candidates with pre-computed PIS inputs

3. **Add `apply_conviction_gate()` function** to `optimizer.py`
   - Applies the gate logic from `unified_optimizer_design.md` Section 5
   - Returns: `(PASS | SOFT_PASS | FAIL, reason_string)`

4. **Implement Security-First Decision Logic** per `security_vs_etf_decision_framework.md`
   - Rule 1: NCS gate
   - Rule 2: Conviction availability gate
   - Rule 3: Mandate suppression bypass
   - Rule 4: Cross-node conflict gate
   - Rule 5: Net improvement minimum

5. **Cash deployment model** as a distinct output artifact
   - `cash_deployment_plan` key in result dict
   - Computed by `build_cash_deployment_plan(candidates, deployable_cash_pct, total_mv)`

6. **Retain existing rec generation as fallback**
   - If the new engine produces zero actionable recs for a node, fall back to
     the existing `_sorted_vehicles_with_suitability()` path with `tier=INFORMATIONAL`
   - This ensures backward compatibility for mandates other than CONCENTRATED_ALPHA

7. **Add comprehensive tests**
   - `test_optimizer.py`: full unit test suite for PIS scoring, conviction gate,
     conflict detection, security-first decision rules
   - Integration test: end-to-end run with CONCENTRATED_ALPHA → VOO suppressed,
     VRT/LRCX/DELL surfaced
   - Regression test: BALANCED mandate → ETF path still works correctly

**Validation criteria:**
- [ ] All 464 + new optimizer tests pass (target: ≥ 490 total)
- [ ] CONCENTRATED_ALPHA run: zero ETF Build recs with tier above INFORMATIONAL
- [ ] CONCENTRATED_ALPHA run: VRT appears in HIGH_CONVICTION_BUY tier
- [ ] BALANCED run: ETF vehicles still surface correctly (ETF path not broken)
- [ ] `cash_deployment_plan` present in result dict
- [ ] All Phase 7.2 audit report scripts still run successfully
- [ ] UI renders all sections correctly

**Risk:** High. This is the fundamental behavioral change. Requires:
- Careful testing across all mandate types
- Regression checking against archetype_validation_report patterns
- UI updates for new recommendation sections
- Possible user communication about recommendation behavior change

---

## Phase Gate Summary

| Phase | Focus | Risk | Rec Output Changes? | Tests Added |
|-------|-------|------|---------------------|-------------|
| 7.3A | Parallel PIS scoring | Low | No | ~10 |
| 7.3B | Conflict detection | Low-Medium | No (metadata only) | ~20 |
| 7.3C | Unified ranking + tiers | Medium | Sort order + new fields | ~15 |
| 7.3D | Security-first engine | High | Full behavioral change | ~40 |

---

## File / Module Map

| New/Modified | Phase | Purpose |
|---|---|---|
| `src/portfolio/optimizer.py` (NEW) | 7.3A | `compute_pis()`, `detect_conflicts()`, `build_candidate_set()`, `apply_conviction_gate()`, `build_cash_deployment_plan()` |
| `src/portfolio/models.py` | 7.3B | Add `RecommendationConflict`, new fields on `PortfolioRecommendation` |
| `src/portfolio/recommendations.py` | 7.3C/D | Refactor `generate_recommendations()` to call optimizer |
| `src/portfolio/mandate.py` | 7.3C | Move mandate evaluation earlier; integrate with rec generation |
| `src/portfolio/runner.py` | 7.3A | Move `build_security_overlays()` + `build_strategic_profiles()` earlier |
| `scripts/run_outcome_ui.py` | 7.3C | New recommendation tier UI sections |
| `tests/test_optimizer.py` (NEW) | 7.3A-D | Full optimizer test suite |
| `scripts/_generate_phase73a_pis_audit.py` (NEW) | 7.3A | Audit script |
| `scripts/_generate_phase73b_conflict_audit.py` (NEW) | 7.3B | Audit script |

---

## Compatibility Guarantees

Throughout all phases, the following contracts are maintained:

| Contract | Guarantee |
|---|---|
| `run_analysis()` return type | dict — unchanged |
| `recommendations` result key | present, same schema + new optional fields |
| `security_overlays` result key | present, unchanged |
| `strategic_profiles` result key | present, unchanged |
| `alignment` result key | present, unchanged |
| `mandate_overlay` result key | present, unchanged |
| `PortfolioRecommendation.severity` | preserved (raw_severity copy) |
| Existing test assertions | All pass throughout |
| Non-CONCENTRATED_ALPHA mandates | ETF path preserved as fallback |
