# PIS-INTEGRITY-01 Forensic Audit

**Date:** 2026-06-15

---

## Q1. Where does PIS receive holdings?

**`src/pis/service.py:register_portfolio_snapshot_from_sih()`**

Called from `src/portfolio/runner.py:_register_pis_snapshot_best_effort()` at line 697:

```python
pis_result = register_portfolio_snapshot_from_sih(
    snapshot=snapshot,
    holdings=raw_holdings,   # ← unfiltered from ingest_portfolio()
)
```

`raw_holdings` is the output of `ingest_portfolio()` and contains **all** holdings regardless of `operational_state`.

---

## Q2. Where does Portfolio Analysis apply investable filtering?

**`src/portfolio/runner.py` lines 727-728:**

```python
_INVESTABLE_STATES = frozenset({"ACTIVE_POSITION", "CASH_EQUIVALENT"})
investable = [h for h in enriched if h.operational_state in _INVESTABLE_STATES]
```

This filter is applied **after** PIS registration. The call order in runner.py is:

```
1. ingest_portfolio()           → raw_holdings (all states)
2. _register_pis_snapshot_best_effort(raw_holdings)   ← PIS gets raw
3. enrich_holdings(raw_holdings)
4. investable = [h for h in enriched if h.operational_state in _INVESTABLE_STATES]
5. All recommendations use `investable`
```

**The gap:** PIS registration happens at step 2, before the investable filter at step 4.

---

## Q3. Which systems use filtered holdings?

All portfolio analytics consume `investable` (filtered):
- `compute_alignment()` — INVESTABLE only
- `compute_concentration()` — INVESTABLE only
- `generate_recommendations_*()` — INVESTABLE only
- `build_deployment_queue()` — INVESTABLE only
- CPV validator — reads `alignment` which is derived from INVESTABLE only

---

## Q4. Which systems use raw holdings?

Before this fix, PIS service received raw holdings:
- `register_portfolio_snapshot_from_sih()` — received raw (now fixed)
- `_to_pis_positions()` — received what service passes (now filtered)

After this fix: PIS receives only investable holdings.

---

## Q5. Is there one authoritative investable-state classifier?

**Before this fix:** NO. Two independent definitions existed:
1. `runner.py:_INVESTABLE_STATES = frozenset({"ACTIVE_POSITION", "CASH_EQUIVALENT"})`
2. No equivalent in `service.py` — used all holdings

**After this fix:** YES. A single constant `_PIS_INVESTABLE_STATES` in `service.py` defines the authoritative filter. Both systems now agree.

---

## Q6. Is behavior currently deterministic?

**Before fix:** Non-deterministic side effect — whether a settlement artifact appears in PIS depends on timing of the Fidelity export. `PENDING ACTIVITY` appears intermittently (settles within days), producing sporadic NEW_POSITION and EXITED_POSITION records.

**After fix:** Deterministic. Only ACTIVE_POSITION and CASH_EQUIVALENT enter PIS snapshots.

---

## Q7. What is the minimum safe correction?

**Add the investable-state filter inside `register_portfolio_snapshot_from_sih()` in `src/pis/service.py`**, before `_to_pis_positions()` is called.

This is the minimum change because:
- The filter lives in one place (single source of truth)
- No changes to runner.py, ingestion.py, storage.py, change_detection.py, lineage, attribution, or benchmark
- All test surfaces remain valid

---

## Contamination Evidence (Pre-Fix)

| Metric | Count |
|--------|-------|
| PIS snapshots (all time) | 68 |
| Position rows in all snapshots | 5,677 |
| ACTIVE_POSITION | 5,520 |
| CASH_EQUIVALENT | 57 |
| ACCOUNTING_ADJUSTMENT | 13 |
| ZERO_VALUE_LEGACY_POSITION | 30 |
| **Non-investable total** | **43** |

**Contaminating symbols:**
- `PENDING ACTIVITY` (PENDING_SETTLEMENT)
- `M26CNT069` (ACCOUNTING_ADJUSTMENT — CyberArk contra row)

**Downstream contamination:**
- 28 change records involved non-investable symbols (6 NEW_POSITION, 5 EXITED_POSITION, 17 UNCHANGED)
- 52 total lineage records; 24 unmatched (confidence=NONE); **11 of 24 (46%) caused by non-investable symbols**

---

## PENDING ACTIVITY Lifecycle (Pre-Fix)

```
Fidelity CSV export
  └── "PENDING ACTIVITY" row, mv=$29.28, type=Cash
          │
          ▼
    ingest_portfolio()
      _classify_operational_state("PENDING ACTIVITY", "PENDING ACTIVITY", 29.28)
        → "PENDING_SETTLEMENT"
          │
          ├─► raw_holdings (contains PENDING_SETTLEMENT)
          │      │
          │      ▼
          │   _register_pis_snapshot_best_effort(raw_holdings)  ← BUG: no filter
          │     register_portfolio_snapshot_from_sih(holdings=raw_holdings)
          │       _to_pis_positions(snapshot, raw_holdings)
          │         → position_snapshots.csv includes "PENDING ACTIVITY"
          │
          └─► enrich_holdings(raw_holdings)
                investable = filter(ACTIVE_POSITION, CASH_EQUIVALENT)
                  → "PENDING ACTIVITY" EXCLUDED from all portfolio analytics
```

**Result:** PIS and portfolio analytics diverge on the same snapshot.
