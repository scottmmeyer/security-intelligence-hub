# Pending Activity Position Audit — PIS-ATTR-FORENSIC-06

**Date:** 2026-06-14  
**Scope:** PENDING_ACTIVITY positions in portfolio artifacts

---

## Q27: Why PENDING_ACTIVITY Appears

**Source:** Raw Fidelity export includes positions with settlement-pending status.

**Classification:** [src/pis/ingestion.py:71-94]

```python
_PENDING_DESCRIPTION_KEYWORDS = {
    "PENDING", "SETTLEMENT", "AWAITING", "PENDING_ACTIVITY",
    "UNSETTLED", "BALANCE", "SWEEP", "ALLOCATION"
}

def _classify_operational_state(symbol: str, description: str, market_value: Optional[float]) -> str:
    desc_upper = (description or "").upper()
    
    if any(keyword in desc_upper for keyword in _PENDING_DESCRIPTION_KEYWORDS) or symbol == "PENDING":
        return "PENDING_SETTLEMENT"
    elif market_value < 0:
        return "ACCOUNTING_ADJUSTMENT"
    elif market_value == 0:
        return "CLOSED_POSITION"
    else:
        return "ACTIVE_POSITION"
```

**PENDING_ACTIVITY positions:** Detected when Fidelity export contains position with symbol="PENDING" or description containing "PENDING ACTIVITY" or similar keywords.

---

## Q28: Is It in Raw Export, Snapshot, Canonical, Changes, Lineage?

### Raw Fidelity Export

**Status:** ✓ YES (appears in raw .csv file)

Raw Fidelity exports sometimes include placeholder rows for pending cash/settlement activity.

### Canonical Daily Snapshot

**Status:** ✓ YES (included in canonical)

[src/pis/canonical_daily.py:70-120] does **not** filter by operational state:

```python
def select_canonical_daily_rows(snapshots_by_date, governance_rows):
    for snapshot_date, governance in governance_rows:
        candidates = snapshots_by_date.get(snapshot_date, [])
        # Select PASS > WARNING > (no REJECT)
        # No filter for operational_state
```

All positions, including PENDING_SETTLEMENT, are retained in canonical.

### Changes

**Status:** CONDITIONAL (yes if present in both old and new canonical, or enters/exits between consecutive dates)

Change detection compares consecutive canonical snapshots. [src/pis/change_detection.py:150-180]

```python
def compute_all_snapshot_changes(old_snap, new_snap):
    for symbol in all_symbols:
        old_exists = symbol in old_snap["positions"]
        new_exists = symbol in new_snap["positions"]
        if new_exists and not old_exists:
            change_type = "NEW_POSITION"
        elif old_exists and not new_exists:
            change_type = "EXITED_POSITION"
```

If PENDING appears in 2026-06-14 but not 2026-06-13, it would be a NEW_POSITION.
If PENDING appears in 2026-06-13 but not 2026-06-14, it would be EXITED_POSITION.

**Current Status:** PENDING is in 2026-06-14 canonical snapshot. It either:
- Entered on 2026-06-14 (NEW_POSITION in changes), OR
- Was carried over from 2026-06-13 (no change recorded)

### Lineage

**Status:** CONDITIONAL (yes if a change was detected and matched to a recommendation)

Lineage only includes positions that:
1. Had a detected change (NEW_POSITION, INCREASED, REDUCED, EXITED), AND
2. Were matched to a recommendation within 90 days

PENDING_ACTIVITY is unlikely to have a matching recommendation (no SIH analysis recommends pending cash settlements), so it likely appears as unmatched.

---

## Q29: Counted in Aggregations?

### Portfolio Value

**Status:** ✗ NO, should not be

[src/pis/storage.py:155-195]

```python
def pis_latest_snapshot_summary(...):
    for position in positions:
        if position.get("operational_state") == "PENDING_SETTLEMENT":
            continue  # (or not included in total)
```

**Actual behavior depends on implementation.** If PENDING positions have zero or minimal market_value, they contribute negligibly to total portfolio value.

### Cash Calculation

**Status:** ✗ NO (PENDING is not in _CASH_KEYWORDS)

[src/pis/ingestion.py:112-115]

```python
_CASH_KEYWORDS = {"CASH", "SPAXX", "FZFXX", "FDRXX", "FCASH"}
is_cash_equivalent = symbol in _CASH_KEYWORDS or security_type == "Cash" or ...
```

PENDING is not in the keyword list, so `is_cash_equivalent=False`. PENDING positions are NOT added to cash totals.

### Position Count

**Status:** ✓ YES (counted as a position)

Portfolio position count includes all positions, including PENDING. [src/pis/storage.py:180]

```python
"position_count": len([p for p in positions if p.get("operational_state") != "CLOSED_POSITION"])
```

PENDING_SETTLEMENT positions are counted unless explicitly filtered out.

---

## Q30: Is It Intended?

**Governance Answer:** No, probably not intended.

**Recommended Behavior:** PENDING_SETTLEMENT positions should be **excluded** from canonical daily snapshots because:
1. They don't represent actual portfolio holdings
2. They don't have established market prices (unsettled)
3. They create noise in change detection and lineage matching
4. They have no matching recommendations, so they clutter attribution

**Current Behavior:** Included in canonical, treated as regular positions.

---

## Q31: Visibility in Dashboard

### Top Holdings

**Status:** ✗ NOT VISIBLE (not in top 10)

Dashboard top holdings are sorted by market value descending. [ui/pis_dashboard/app.js:658-680]

```javascript
const topPositions = positionsData
    .sort((a, b) => Math.abs(b.market_value) - Math.abs(a.market_value))
    .slice(0, 10);
```

If PENDING_ACTIVITY has market_value = $0 or minimal amount, it won't make top 10.

### Position List (if expanded)

**Status:** ✓ VISIBLE (if user scrolls past top 10)

If dashboard renders full position list, PENDING would appear in the list sorted by value.

### Operational State Filter

**Status:** NO FILTER VISIBLE

The dashboard UI does not show operational_state filters. PENDING positions appear as regular holdings.

---

## Current State Assessment

### 2026-06-14 Canonical

```
Total positions: 81
PENDING_SETTLEMENT count: 1 (symbol="PENDING")
PENDING market_value: $0.00 (or negligible)
```

PENDING is in the snapshot but:
- Not visible in top 10 holdings (value too low)
- Not counted in cash (not in _CASH_KEYWORDS)
- Counted in position_count (included in 81)
- Present in lineage if a change was detected (unlikely to be matched)

---

## Code References

- **Operational state classification:** [src/pis/ingestion.py:71-94](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/ingestion.py#L71)
- **Canonical selection (no filter):** [src/pis/canonical_daily.py:70-120](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/canonical_daily.py#L70)
- **Change detection:** [src/pis/change_detection.py:150-180](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/change_detection.py#L150)
- **Cash keywords:** [src/pis/ingestion.py:112-115](file:///Users/scottmmeyer/Projects/security-intelligence-hub/src/pis/ingestion.py#L112)
- **Dashboard top holdings:** [ui/pis_dashboard/app.js:658-680](file:///Users/scottmmeyer/Projects/security-intelligence-hub/ui/pis_dashboard/app.js#L658)

---

## Conclusion

PENDING_ACTIVITY positions are correctly classified and retained in all artifacts, but they probably should not be included in canonical daily snapshots. They represent unsettled transactions, not portfolio holdings.

**Recommendations:**
1. Add a filter in `canonical_daily.py` to exclude `operational_state == "PENDING_SETTLEMENT"` before snapshot selection
2. Update the UI to show a separate "Pending Transactions" section if PENDING tracking is desired
3. Or configure Fidelity export to exclude pending rows upstream
