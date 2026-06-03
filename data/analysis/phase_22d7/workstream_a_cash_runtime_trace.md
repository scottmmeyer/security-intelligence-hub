# Phase 22D.7 — Workstream A: Cash Governance Runtime Trace

**Generated:** Phase 22D.7 Production Trust Remediation  
**Status:** RESOLVED ✅  
**Run Audited:** PAR-20260602-F734F626 (defective) → PAR-20260602-4A83D5BD (corrected)

---

## Root Cause Summary

The artifact `PAR-20260602-F734F626` was generated on **2026-06-02T13:16 UTC** by
a server process (PID 43740) that was started on **2026-06-01T19:43 UTC** — before
the Phase 22D.6 code changes were written to disk at **2026-06-02T06:45 UTC**.

The running server had an in-memory code image pre-dating Phase 22D.6. Because
`deployment_queue.py` is an untracked new file and `runner.py` modifications were
uncommitted, the old process had no knowledge of `compute_deployable_cash()`. The
old runner generated `cash_context` with an inline 5-field structure using the
2.0% governance hard minimum as the floor rather than the 7.0% mandate target.

---

## Layer-by-Layer Trace

### Layer 1: Mandate Configuration

| Item | Value |
|------|-------|
| Active mandate | `CONCENTRATED_ALPHA` |
| Mandate YAML | `config/allocation_models/concentrated_alpha_profile.yaml` |
| `CASH` node target | **7.0%** |
| `load_archetype_targets("CONCENTRATED_ALPHA")["CASH"]` | **7.0** ✅ |

### Layer 2: `compute_deployable_cash()` (deployment_queue.py)

```python
# Correct logic — Phase 22D.6 implementation
effective_floor_pct = max(MIN_CASH_PCT, float(mandate_cash_target_pct))
# = max(2.0, 7.0) = 7.0  ← CORRECT
floor_mv = total_market_value * effective_floor_pct / 100.0
# = 479,347.59 * 7.0 / 100 = $33,554.33  ← CORRECT
deployable_mv = max(0.0, cash_mv - floor_mv)
# = max(0, 41,279.15 - 33,554.33) = $7,724.82  ← CORRECT
```

### Layer 3: runner.py call site (line 721)

```python
_cash_target_pct = archetype_targets.get("CASH")  # → 7.0
cash_context = compute_deployable_cash(
    holdings=investable,
    total_market_value=snapshot.total_market_value,
    mandate_cash_target_pct=_cash_target_pct,  # 7.0 ← passed correctly
)
```

The runner code is correct. The defect was stale process memory — not a code bug.

### Layer 4: Artifact Serialization

`cash_context` dict returned from `compute_deployable_cash()` is assigned directly
into `dq_payload["cash_context"]` and written to `deployment_queue.json`. No
transformation or field filtering occurs.

### Layer 5: UI Binding (app.js)

```javascript
const cashCtx = dq.cash_context || {};
const _cashTargetPct = cashCtx.mandate_cash_target_pct != null
    ? parseFloat(cashCtx.mandate_cash_target_pct).toFixed(1) : "—";
// Line 2083:
formatMV(cashCtx.deployable_mv)   // renders deployable cash
```

UI correctly reads `cash_context.deployable_mv` and `cash_context.mandate_cash_target_pct`.
When loaded with run `PAR-20260602-4A83D5BD`, UI will display **$7,724.82** and **7.0%**.

---

## Before / After Comparison

| Field | PAR-20260602-F734F626 (defective) | PAR-20260602-4A83D5BD (corrected) |
|-------|----------------------------------|----------------------------------|
| `field_count` | 5 | 9 |
| `mandate_cash_target_pct` | *(absent)* | **7.0** |
| `effective_floor_pct` | *(absent)* | **7.0** |
| `floor_mv` | $9,586.95 (2% of $479K) | $33,554.33 (7% of $479K) |
| `excess_mv` | *(absent)* | $7,724.82 |
| `deployable_mv` | **$31,692.20** ❌ | **$7,724.82** ✅ |
| `deployable_pct` | 6.61% | 1.61% |

---

## Fix Applied

1. Killed stale server process (PID 43740, started 2026-06-01T19:43)
2. Restarted server: `PYTHONPATH=. .venv/bin/python3 scripts/run_outcome_ui.py --port 8765`
3. Regenerated run using same portfolio CSV (Jun 02 2026 extract, CONCENTRATED_ALPHA mandate)
4. New run `PAR-20260602-4A83D5BD` confirmed correct: `deployable_mv=$7,724.82`, 9 fields

**Status: CLOSED**
