# STALE-PAR-01: Architecture Assessment

**Date:** 2026-06-09  
**Issue:** #42  
**Status:** Resolved via Option A (Policy Replay on Load) — implemented

---

## Problem Statement

PAR artifacts persist to disk at generation time. The policy execution state of recommendation dicts (`execution_state`, `effective_action`, `card_lifecycle_state`) is computed once during `run_analysis()` and frozen into `recommendations.json`.

If operator policies change after a PAR is generated:
- `security_overlays.csv` reflects the annotation correctly (per-symbol, trivially re-derivable)
- `recommendations.json` does NOT update — it retains the stale execution_state from generation time

This creates split-brain UI behavior: PAP shows EXECUTABLE/TRIM for a symbol that CRA correctly shows as BLOCKED by DO_NOT_SELL.

---

## Phase 1 — Policy Lineage Trace

```
Portfolio CSV
    ↓
run_analysis()
    ↓ generates
PortfolioRecommendation objects
    ↓ serialized via
dataclasses.asdict() → recs_with_drilldown (list of dicts)
    ↓ policy applied via
_apply_policy_to_recs(recs_with_drilldown, _policy_registry)      ← MUTATION
    ↓ frozen to disk
recommendations.json  ← STALE POINT

UI load (load_analysis_run)
    ↓ reads
recommendations.json  (stale execution_state if policy changed)
    ↓ serves to
app.js renderRecommendations()
    ↓ displays
PAP Actions lane  ← SHOWS STALE STATE
```

**Staleness Vector:** Any operator policy added, revoked, or modified between PAR generation and UI load creates a mismatch.

**Staleness in security_overlays.csv:** NOT affected. Each row is per-symbol and policy is re-annotated during generation. However overlays have no multi-symbol rec-level semantics — a REDUCE_OVERWEIGHT rec with 4 affected symbols cannot be blocked from the overlay alone.

---

## Phase 2 — Version Model Design

Four approaches were evaluated for detecting and resolving stale policy state:

### Option A: Policy Replay on Load (RECOMMENDED)

Re-apply `apply_policy_to_recommendations()` on every call to `load_analysis_run()` using the **current** policy registry.

**Policy version tracking fields added:**
- `policy_replay_applied: bool` — whether replay was applied
- `policy_replay_timestamp: str` — ISO 8601 UTC timestamp of replay
- `current_policy_snapshot: dict` — current policy state at time of load
- `policy_is_stale: bool` — True if PAR-time snapshot differs from current snapshot
  - Computed by comparing `run_metadata.policy_snapshot` vs `current_policy_snapshot`

### Option B: Policy Version Validation

Store a `policy_version` hash in the PAR. On load, compare against current hash and raise a staleness warning.

**Detection fields (not yet implemented):**
- `policy_snapshot_hash: str` — SHA256 of serialized policy registry at generation time
- `policy_last_modified: str` — timestamp of last policy change

**Limitation:** Detects staleness but does not fix it. UI still shows incorrect state.

### Option C: PAR Staleness Warning Only

Display a banner in the UI when `policy_is_stale=True`. Do not auto-correct.

**Limitation:** Operator must manually re-run to get correct state. Doesn't prevent misinformed decisions.

### Option D: Hybrid (Option A + Option C)

Apply policy replay automatically (Option A) AND show a disclosure banner when a stale PAR was corrected (Option C).

---

## Phase 3 — Option Comparison

| Option | Complexity | Risk | Operator Experience | Performance Impact | Governance |
|---|---|---|---|---|---|
| A: Policy Replay | **Low** — 10-line addition to load_analysis_run | **Low** — mutation is output-layer only; scoring untouched | **Best** — always shows correct state | Negligible (~0ms, no I/O) | Clean — on-disk file unchanged; replay is live-view transform |
| B: Version Validation | Medium — needs hash computation, storage, comparison | Medium — still shows wrong state if not auto-corrected | Poor — operator must re-run | Low | Adds hash audit trail |
| C: Warning Only | Low | Medium — operator may act on stale state | Moderate — visible warning, but still wrong data | None | Transparent but doesn't fix |
| D: Hybrid A+C | Low | **Lowest** — auto-corrects AND discloses | **Best** — correct state + honest disclosure | Negligible | Best of all worlds |

---

## Governance Implications

**Option A / D (implemented):**
- The on-disk `recommendations.json` is NOT modified. The live-view transform is ephemeral and exists only in the server response.
- Pre-existing audit trail (on-disk PAR) is preserved as a historical record.
- The `policy_replay_applied` and `policy_is_stale` flags provide full governance transparency.
- Scoring, signal generation, ESS, STI, CW-DAS, and recommendation content are **never modified**. Only the output-layer annotation fields are updated.

**Backward compatibility:** All pre-upgrade PARs lacking `policy_snapshot` in `run_metadata` will have `policy_is_stale=True` as a conservative default (empty vs non-empty comparison). This is acceptable — they get replayed with current policy, which is correct behavior.

---

## Selected Architecture: Option D (Hybrid A+C)

Policy replay on load (Option A) with staleness disclosure (Option C):
- `load_analysis_run()` always re-applies current policy to recommendations
- `policy_is_stale: bool` returned in result
- UI `renderNarrativeSummary()` shows a disclosure badge when `policy_is_stale=True`
