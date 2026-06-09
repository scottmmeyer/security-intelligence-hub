# UX Sprint 2 — Validation

**Date:** 2026-06-09

---

## Regression Outcome

| Suite | Passed | Skipped | Failed |
|---|---|---|---|
| Full test suite (pytest) | 1192 | 1 | **0** |

No regressions introduced.

---

## STALE-PAR-01 Validation

### Policy Replay Logic Test

From CRA-POOL-AUDIT live test:
- Before policy replay: `execution_state=EXECUTABLE`, `effective_action=''` (stale PAR)
- After `apply_policy_to_recommendations()` called with current registry: `execution_state=BLOCKED_BY_POLICY`, `effective_action=MONITOR_ONLY`
- Confirmed for REDUCE_OVERWEIGHT rec containing TSLA in affected_symbols

### Staleness Detection

- `par_policy_snap = run_metadata.policy_snapshot` (set at generation time)
- `current_policy_snapshot = registry.policy_snapshot()` (computed at load time)
- `policy_is_stale = (par_policy_snap != current_policy_snapshot)`
- Fresh PAR (5C476C55): `policy_is_stale = False` (generated today, same policy state)
- Pre-PA-004 PARs: `policy_is_stale = True` (no policy_snapshot in metadata → empty dict ≠ current)

### Governance

- On-disk `recommendations.json` is NOT modified
- No scoring changes: `_apply_policy_to_recs` only modifies `execution_state`, `effective_action`, `card_lifecycle_state`
- Output is ephemeral (lives in HTTP response only)
- `policy_replay_applied: True` / `policy_replay_timestamp` in result provide full transparency

---

## UX-PA-02 Validation

- `renderReconciliationPanel()` called only when `reconciliation_checks` array is populated
- Panel hidden (returns empty `el.innerHTML`) when all checks PASS — tested: no phantom panel on clean PARs
- `escHtml()` applied to all dynamic content (check names, sub-check symbols, guidance text)
- Collapsible toggle works: initial state = visible, toggle button text updates
- RC-02 FAIL: sub-checks show BSVN / STNG / SIMO with root cause `A: missing_asset_class_mapping`
- `affects_recommendations` defaults to "Recommendations unaffected" when field is null/undefined (safe default)
- **Validated.**

---

## UX-PA-05 Validation

- L1 rows filtered: `depthOf(node_key) === 1 && node_key !== "CASH"` — excludes CASH from overweight/underweight display (CASH is a separate mandate constraint)
- Threshold: overweights show drift > 0.5pp, underweights show drift < −0.5pp
- Gap column shows top 3 by absolute drift regardless of direction
- `escHtml()` applied to node labels
- Empty state per column: "None above threshold" / "No gaps"
- **Validated.**

---

## UX-PA-08 Validation

- 4 `defn` strings added, each <120 characters, plain English, no acronyms
- `multidim-defn` CSS: small italic muted text — visually subordinate to score and label
- Removed unused `navEl` variable (dead code from prior sprint)
- Definitions do not repeat the label or tooltip — each adds new information
- **Validated.**

---

## UX-PA-09 Validation

- `renderNarrativeSummary()` called before `renderMultiDimScores()` in `renderResults()` — consistent with HTML section order
- `escHtml()` applied to all recommendation-derived text
- Two-column layout uses CSS grid with single-column fallback at ≤700px
- Stale PAR badge: only shown when `data.policy_is_stale === true`
- Observation list capped at 3; action list capped at 3
- Fallback action item when no EXECUTABLE ACTION recs exist
- **Validated.**

---

## Behavioral Validation

| Concern | Verified |
|---|---|
| No scoring changes | ✓ — policy_replay only mutates 3 annotation fields |
| No recommendation generation changes | ✓ — recs generated same way, only output-layer updated |
| No policy logic changes | ✓ — existing apply_policy_to_recommendations(), unchanged |
| No CW-DAS changes | ✓ — no changes to deployment_queue.py |
| No ESS changes | ✓ — no changes to ess.py or signal pipeline |
| No STI changes | ✓ — no changes to trim intelligence |
| All new CSS uses existing variable names | ✓ |
| No inline JS event handlers using unescaped user data | ✓ |
