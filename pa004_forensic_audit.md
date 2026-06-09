# PA-004 Forensic Audit

Repository: security-intelligence-hub  
Date: 2026-06-09  
Issue: PA-004 Policy Consistency Failure Across Advisory Surfaces (#36)

## Q1 — Why Does PAP Still Show TSLA?

**Root cause:** Cat 3 (Allocation Reduction) and Cat 4 (Funding Sources) in `_computePortfolioActions()` do not check `policy_type` or `execution_state` before including symbols. They pull symbols directly from `REDUCE_OVERWEIGHT` `affected_symbols` (Cat 3) and from overlays (Cat 4), without applying any policy gate.

Cat 1 (Signal Deterioration) already correctly routes `BLOCKED_BY_POLICY` symbols to cat5 (Policy-Suppressed). This was implemented correctly. But Cat 3 and Cat 4 are unguarded.

## Q2 — Where Is Policy Normalization Missing?

| Surface | Policy Checked | Gap |
|---|---|---|
| Deployment Queue | Yes (apply_policy_to_queue) | None |
| security_overlays.csv | Yes (compute_execution_state per flag) | Partial* |
| recommendations.json | Yes (apply_policy_to_recommendations) | None |
| PAP Cat 1 | Yes (checks execState === BLOCKED_BY_POLICY) | None |
| PAP Cat 3 Allocation Reduction | **No** | **BUG** |
| PAP Cat 4 Funding Sources | **No** | **BUG** |

*Partial: DODFX's overlay execution_state is EXECUTABLE because its current opportunity_flag is HOLD (not a sell flag). `compute_execution_state("DODFX", "HOLD", registry)` returns EXECUTABLE correctly — SELL_LAST only activates on sell-context flags. But Cat 3 puts DODFX in a reduction context, so the policy must be re-evaluated there using `ov.policy_type` directly.

## Q3 — Is PAP Bypassing apply_policy_to_recommendations()?

**Not exactly.** PAP is not driven by `recommendations.json` — it builds its own data pipeline via `_computePortfolioActions()` using `security_overlays` and `deployment_queue` directly. `apply_policy_to_recommendations()` only affects the `recs_with_drilldown` list, which is the Allocation & Portfolio Observations panel. PAP's Cat 3 and Cat 4 use overlay data, not the already-normalized recommendation dicts.

## Q4 — Other Symbols Affected

Any symbol with DO_NOT_SELL that has a BEARISH overlay flag AND appears in a REDUCE_OVERWEIGHT node would be inconsistently shown in Cat 3/4.

In the current run, TSLA is the only DO_NOT_SELL symbol. DODFX (SELL_LAST) is affected in Cat 3 — it appears as an unrestricted reduction candidate when it should be marked DEFERRED_BY_POLICY.

## Q5 — Additional Policy Inconsistencies

**DODFX in Cat 3 (Allocation Reduction):** Appears without deferral annotation. Its overlay `execution_state` is EXECUTABLE because `compute_execution_state("DODFX", "HOLD", registry)` returns EXECUTABLE — HOLD is not a sell-context flag. But in Cat 3, DODFX is being presented as a reduction candidate, which IS a sell-context. The policy check must use `ov.policy_type` directly for Cat 3 and Cat 4.

**Cat 4 (Funding Sources):** No policy check exists. Any DO_NOT_SELL symbol that passes the other Cat 4 filters (size, score, not protected tier) would appear as a funding candidate.

## Evidence

```
TSLA security_overlay:
  opportunity_flag: TRIM
  execution_state: BLOCKED_BY_POLICY
  policy_type: DO_NOT_SELL

DODFX security_overlay:
  opportunity_flag: HOLD
  execution_state: EXECUTABLE   ← correct for HOLD context
  policy_type: SELL_LAST

REDUCE_OVERWEIGHT (ULTRA_MEGA):
  affected_symbols: ['MU', 'VOO', 'TSLA', 'FXAIX']
  execution_state: BLOCKED_BY_POLICY  ← recommendation is correctly blocked
  
PAP Cat 3 (before fix):
  Includes TSLA from REDUCE_OVERWEIGHT symbols — no policy check
  
PAP Cat 4 (before fix):
  No policy_type check — any symbol passing other filters appears
```

## Conclusion

The fix is entirely within `_computePortfolioActions()` in `app.js`. No backend changes required. The `policy_type` field is already present on every overlay object.

Fix strategy:
- Cat 3: Check `ov.policy_type === "DO_NOT_SELL"` → move to cat5. Check `ov.policy_type === "SELL_LAST"` → include with DEFERRED_BY_POLICY annotation and tail-rank.
- Cat 4: Check `ov.policy_type === "DO_NOT_SELL"` → exclude entirely. Check `ov.policy_type === "SELL_LAST"` → include but assign lowest priority (last-resort).
