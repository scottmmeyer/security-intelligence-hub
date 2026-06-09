# STALE-PAR-01: Recommended Implementation

**Date:** 2026-06-09  
**Status:** IMPLEMENTED  
**Architecture:** Option D (Hybrid A+C — Policy Replay on Load + Staleness Disclosure)

---

## Implementation

### Backend: `src/portfolio/runner.py` — `load_analysis_run()`

Added policy replay block at the end of `load_analysis_run()`:

```python
# STALE-PAR-01: Policy replay on load
_load_registry = OperatorPolicyRegistry.load(_OPERATOR_STATE)
if recs_list:
    _apply_policy_to_recs(recs_list, _load_registry)
    result["policy_replay_applied"] = True
    result["policy_replay_timestamp"] = datetime.now(timezone.utc).isoformat()
else:
    result["policy_replay_applied"] = False

result["current_policy_snapshot"] = _load_registry.policy_snapshot()
par_policy_snap = (result.get("run_metadata") or {}).get("policy_snapshot", {})
result["policy_is_stale"] = (par_policy_snap != result["current_policy_snapshot"])
```

Also added reconciliation checks exposure:
```python
recon_path = run_dir / "reconciliation.json"
if recon_path.exists():
    result["reconciliation_checks"] = recon_data.get("checks", [])
    ...
```

### Backend: `src/portfolio/runner.py` — `run_analysis()` result dict

Added `reconciliation_checks_warned` and `reconciliation_checks` (full array) to the fresh-run result dict.

### Frontend: `ui/portfolio_alignment/app.js`

- `renderNarrativeSummary(data)` — shows staleness badge when `data.policy_is_stale === true`
- `renderReconciliationPanel(data)` — uses `data.reconciliation_checks` for explainability (UX-PA-02)

---

## Final Q&A

### Q1: What is the preferred STALE-PAR-01 architecture?

**Option D: Hybrid (Policy Replay on Load + Staleness Disclosure)**

Policy is re-applied on every `load_analysis_run()` call using the current operator policy registry. The on-disk PAR is preserved as-is. The UI displays a staleness advisory when the PAR was generated under different policy state.

### Q2: Can historical PARs now safely coexist with evolving policies?

**Yes.** With Option D:
- Historical PARs retain their original on-disk state (full audit trail preserved)
- On load, execution_state and effective_action are updated to reflect current policy
- The UI shows a disclosure badge when a stale PAR was corrected
- Operators always see policy-consistent recommendation states, regardless of when the PAR was generated

### Q3: What reconciliation check is currently failing?

**RC-02 — Allocation Total Reconciliation (FAIL)**

3 holdings have `asset_class=UNKNOWN` and non-zero market value:
- BSVN: $2,697.60 (0.58% of portfolio)
- STNG: $2,283.60 (0.49%)
- SIMO: $1,316.05 (0.28%)

Root cause: Missing asset class mapping for these symbols. L1 node sum is 98.65% (gap = −1.35pp vs 100.00% target).

**RC-06 — Security Classification Audit (WARN)**

SPAXX is present in the ETF decomposition registry as `CASH_DECOMPOSABLE`. Advisory only — zero hard violations.

### Q4: Does the failure affect recommendations?

**No direct effect on recommendations.** RC-02 FAIL means the 3 unclassified holdings (~1.35% of portfolio) are excluded from allocation scoring. Their absence may cause slight understatement of overweight drift in affected tiers, but recommendation generation is not blocked. The reconciliation panel (UX-PA-02) now shows this with explicit `affects_recommendations = false` label.

### Q5: Is Portfolio Alignment now demo-ready?

**Yes — with qualifications:**

Ready:
- Policy enforcement: TSLA correctly shows BLOCKED everywhere (after STALE-PAR-01 fix)
- UX: Narrative summary, score definitions, allocation drivers, reconciliation explainability
- Trust layer: Stale PAR advisory badge visible when applicable
- Capital pool: Clean (no protected assets)

Known open items (not blocking demo):
- RC-02 FAIL: BSVN/STNG/SIMO need asset class mapping — existing holdings, not a new regression
- SI-REFRESH-03: Historical coverage tracking (LOW priority backlog)

### Q6: What is the next highest-priority implementation item after Sprint 2?

Based on current state:

1. **BSVN/STNG/SIMO classification** — fix the 3 UNKNOWN asset class mappings to resolve RC-02 FAIL. Small config change; resolves persistent reconciliation failure.
2. **STALE-PAR-01 Option B complement** — add policy_snapshot_hash to PAR for deeper audit trail.
3. **UX-PA-10 and beyond** — remaining backlog items from the UX audit (13 total identified, 5 implemented).
4. **SI-REFRESH-03** — historical coverage tracking (LOW priority).
