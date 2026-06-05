# Phase 23.6A — Final Verdict

**Date:** 2026-06-04
**Classification: CERTIFIED COMPLETE — READY FOR PHASE 23.6B**

---

## Success Criteria Checklist

| # | Criterion | Status |
|---|-----------|--------|
| 1 | `GET /api/cra/proposal` returns a valid RotationProposal | ✅ Verified against real PAR run (`CRA-20260604-2844185D`) |
| 2 | Capital sources detected correctly across all 5 categories | ✅ 63-test suite covers all categories |
| 3 | Policies function correctly (DO_NOT_SELL, SELL_LAST, CORE_ANCHOR) | ✅ 5 policy tests pass; TSLA correctly blocked in real data |
| 4 | Tax modifiers function correctly (Bucket A, D) | ✅ 4 tax modifier tests pass; FIS correctly assigned Bucket A in real data |
| 5 | Capital pool builds correctly (blocked sources excluded) | ✅ `test_total_capital_pool_excludes_blocked` passes |
| 6 | Deployment targets preserve CW-DAS ordering | ✅ `test_deployments_preserve_cw_das_rank_order` passes |
| 7 | Impact estimates generate successfully | ✅ 7 impact estimator tests pass |
| 8 | All tests pass | ✅ 63/63 CRA tests pass; 928/928 full suite passes |
| 9 | No scoring models were modified | ✅ Governance review confirms; `test_cw_das_scores_unchanged` passes |
| 10 | No upstream portfolio intelligence behavior changed | ✅ Zero regressions in full suite |

---

## Live Smoke Test Results (real portfolio, 2026-06-04)

```
Proposal ID:    CRA-20260604-2844185D
Run ID:         PAR-20260604-3565A7CD (latest COMPLETE)
Status:         OPERATOR_REVIEW_REQUIRED
Portfolio MV:   $472,454
Capital Pool:   $99,011  (39 sources, 28 unblocked)
Deployments:    VRT (rank 1, DAS 95.1, $49,506)
                ARW (rank 2, DAS 93.9, $49,506)

Alignment:      0.4142 → 0.5542  (+0.14 estimated)
Review flags:   Capital pool 20.7% > 10% threshold

Notable:
  TSLA — URGENT/SIGNAL_DETERIORATION — blocked=True (DO_NOT_SELL active) ✅
  FIS  — HIGH/SIGNAL_DETERIORATION   — tax_bucket=A (loss ~$12,594) ✅
  FIS  — also in strategic_exit_symbols → evidence merged ✅
```

---

## Implementation Questions (from design phase)

### Q1: Were any design changes required?
**Yes** — four implementation adaptations (see implementation summary §Design Changes):
1. `allocation_node` derived from holdings when absent from queue entry
2. Tax buckets derived from cost_basis comparison (no per-symbol bucket table)
3. `market_value` joined from holdings.csv (not present on overlay rows)
4. `strategic_profiles.json` fallback to `strategic_exit_symbols` + TRIM flags

### Q2: Did any assumptions prove invalid?
**Yes** — three assumptions were invalid (same items as Q1). All resolved gracefully without design deviation.

### Q3: Did strategic profiles contain all required fields?
**Not applicable** — `strategic_profiles.json` is not yet produced by the PAR pipeline. The CRA degrades gracefully: Category 2 uses operator-designated `strategic_exit_symbols` and existing overlay TRIM flags. When the PAR pipeline begins producing `strategic_profiles.json`, the CRA will automatically use it with no code changes required.

### Q4: Did tax integration require any additional inputs?
**Partially** — Bucket B and E require `holding_days` data not available in PAR artifacts. Bucket E (approaching LT threshold) cannot be assigned. This is documented as an open question. Bucket A and D detection works correctly from cost_basis vs market_value.

### Q5: Were any governance boundaries challenged?
**No** — all non-negotiable constraints satisfied. The impact estimator's heuristic coefficients are the closest edge case; they are clearly labeled `is_estimate=True` and explicitly documented as approximations requiring calibration.

---

## Open Questions for Phase 23.6B

1. **Bucket E detection** — holding_days needed; could be derived from portfolio CSV if `acquisition_date` field is added
2. **Impact estimator calibration** — coefficients (+4.0 OW resolved, +3.0 UW funded, etc.) should be validated against historical PAR run deltas before labeling as "guidance"
3. **allocation_node persistence** — Phase 23.6B UI can trigger a PAR re-run to populate allocation_node in fresh queue entries
4. **Draft persistence API** — `POST /api/cra/proposal/draft` is in scope for Phase 23.6C; the data model is ready

---

## Phase 23.6B Readiness

The backend is complete and functional. Phase 23.6B (UI) can proceed immediately with:
- `GET /api/cra/proposal` as the data source
- `RotationProposal.to_dict()` as the wire format
- All source/target fields available for card rendering
- `proposal_status` and `review_flags` for status badges
- `impact.is_estimate = True` label for the impact column

No backend changes required to begin Phase 23.6B.
