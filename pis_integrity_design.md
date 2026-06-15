# PIS-INTEGRITY-01 Design

**Date:** 2026-06-15

---

## Design Goals

- Single source of truth for investable-state classification
- Deterministic behavior (no state-dependent outcomes)
- Auditability (filter is explicit, named, testable)
- Fail-closed governance (ambiguous states excluded)
- No recommendation changes
- No benchmark changes

---

## Option A: Filter at PIS Registration (SELECTED)

**Location:** `src/pis/service.py:register_portfolio_snapshot_from_sih()`

**Mechanism:**

```python
_PIS_INVESTABLE_STATES = frozenset({"ACTIVE_POSITION", "CASH_EQUIVALENT"})

# Before calling _to_pis_positions:
investable_holdings = [
    h for h in holdings
    if h.operational_state in _PIS_INVESTABLE_STATES
]
pis_positions = _to_pis_positions(snapshot, investable_holdings)
```

**Properties:**
- Filter is in service.py — the canonical registration boundary
- One constant to maintain
- All downstream (change detection, lineage, attribution) automatically clean
- `raw_holdings` from runner.py preserved as-is (no runner.py change)
- Existing duplicate protection, immutability, and index contracts unchanged
- Testable in isolation

**Justification for selection:**
The right place to enforce the invariant is at the boundary where SIH hands data to PIS. `register_portfolio_snapshot_from_sih` is that boundary. The filter belongs there, not in runner.py (which should remain agnostic), not in change_detection.py (too late), not in storage.py (wrong layer).

---

## Option B: Filter at Change Detection

**Location:** `src/pis/change_detection.py:_aggregate_positions()`

**Mechanism:** Read `operational_state` from position file and skip non-investable rows.

**Rejected because:**
- Requires reading `operational_state` from position_snapshots.csv in change detection (currently not read)
- Non-investable rows would still contaminate snapshot partitions (storage wrong)
- Position count in index would mismatch actual positions used for change detection
- Three separate layers would need coordinated changes

---

## Option C: Post-Hoc Filtering via Allowlist (Alternative)

**Mechanism:** Maintain an explicit denylist of symbols to exclude from PIS (e.g., "PENDING ACTIVITY").

**Rejected because:**
- Symbol-based denylist is brittle (new settlement symbols would bypass it)
- `operational_state` is already the authoritative classification
- Denylist would be incomplete as Fidelity adds new accounting symbols

---

## Integrity Rules

The following operational states are **NON-INVESTABLE** and must never produce change detection records:

| State | Description | Example |
|-------|-------------|---------|
| `PENDING_SETTLEMENT` | Unsettled trade / Fidelity "PENDING ACTIVITY" row | PENDING ACTIVITY |
| `ACCOUNTING_ADJUSTMENT` | Correction or contra entry (may have negative MV) | M26CNT069 |
| `ZERO_VALUE_LEGACY_POSITION` | Zero-value legacy position, no economic substance | Various |
| Any future unrecognized state | Default-to-exclude for fail-closed governance | N/A |

The following operational states are **INVESTABLE**:

| State | Description |
|-------|-------------|
| `ACTIVE_POSITION` | Normal investable holding |
| `CASH_EQUIVALENT` | Assigned by enrichment for cash positions |

---

## Backward Compatibility

- Existing PIS snapshot partitions are **not retroactively rewritten** (immutability contracts preserved)
- Existing change_records.csv and lineage_records.csv are **not retroactively cleaned** 
- On the next portfolio upload, new snapshots will only contain investable positions
- The PIS-005 refresh chain will recompute change detection and lineage from the corrected snapshot forward
- Historical contaminated records will naturally cycle out as older snapshots age out of the change detection window

This is the correct approach: retroactive modification would violate immutability contracts.
