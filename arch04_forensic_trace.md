# ARCH-04: Forensic Trace

**Date:** 2026-06-09

---

## Policy State Propagation — Before ARCH-04

```
OperatorPolicyRegistry
  (TSLA → DO_NOT_SELL, DODFX → SELL_LAST)
        ↓
apply_policy_to_recommendations()              src/portfolio/operator_policy.py
  for each sell-context rec:
    for each affected_symbol:
      compute_execution_state(sym, flag, registry) → (state, action)
    TAKE MOST RESTRICTIVE across all symbols
    rd["execution_state"] = best_state         ← rec-level, propagated
    rd["effective_action"] = best_action
        ↓
recommendations.json                           (on disk, stale PAR)
  REC-5DD333BD: execution_state = "DEFERRED_BY_POLICY"   ← KGC inherited
  REC-F129627C: execution_state = "BLOCKED_BY_POLICY"    ← MU inherited
        ↓
load_analysis_run() / STALE-PAR-01 replay
  _apply_policy_to_recs(recs_list, _load_registry)       ← same function
        ↓
UI renderRecommendations()                     app.js
  buildCard(): r.execution_state drives lane placement
  → DEFERRED rec → Blocked lane (KGC invisible as executable)
  → BLOCKED rec → Blocked lane (MU invisible as executable)
        ↓
PAP Blocked Lane:
  [BLOCKED] REDUCE EQUITIES.INTERNATIONAL — all 12 symbols appear blocked
  [BLOCKED] REDUCE EQUITIES.US.MEGA.ULTRA_MEGA — TSLA and MU both appear blocked
```

---

## Locations Where "Most Restrictive Wins" Was Applied

| Location | File | Line (approx) | Effect |
|---|---|---|---|
| `apply_policy_to_recommendations()` | `src/portfolio/operator_policy.py` | ~411–460 | Sets rec-level `execution_state` via most-restrictive loop |
| STALE-PAR-01 replay | `src/portfolio/runner.py` — `load_analysis_run()` | ~1465 | Calls same function; same propagation |

No other locations propagated policy at the rec level. Per-symbol policy already existed correctly in:
- `security_overlays.csv` (per-symbol, always correct)
- PAP Cat 1, Cat 3, Cat 4 computing in `_computePortfolioActions()` (uses `ov.policy_type` directly from overlays)
- CRA `capital_source_builder.py` (per-symbol independent evaluation)

The root cause was exclusively in `apply_policy_to_recommendations()`.

---

## After ARCH-04

```
apply_policy_to_recommendations()  (ARCH-04 semantics)
  for each sell-context rec:
    all_syms = affected_symbols ∪ drilldown.holdings.symbol (deduped)
    for each sym in all_syms:
      compute_execution_state(sym, flag, registry) → (state, action)
      store in sym_states[sym]
    rd["symbol_execution_states"] = sym_states       ← NEW: per-symbol dict
    annotate drilldown.holdings with per-symbol states ← NEW: holdings annotated
    REC-LEVEL state = EXECUTABLE if any affected_symbol is EXECUTABLE
                    = DEFERRED_BY_POLICY if all are DEFERRED (no executable)
                    = BLOCKED_BY_POLICY if all are BLOCKED
```
