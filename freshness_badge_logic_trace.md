# Freshness Badge Logic Trace

Repository: security-intelligence-hub  
Date: 2026-06-09

## Badge Computation Path

### Step 1: Server computes signal status

File: `scripts/run_outcome_ui.py`, `_signal_status()` function (line ~217)

```python
def _signal_status() -> dict:
    today = date.today().isoformat()
    result: dict[str, dict] = {}
    for name, path in _SIGNAL_FILES.items():
        sd = _sourced_date(path)
        result[name] = {
            "sourced_date": sd,
            "stale": sd != today,
            "exists": path.exists(),
        }
    return result
```

### Step 2: Staleness check

`_sourced_date()` returns the **maximum** `sourced_date` value found anywhere in the file. If any row has `sourced_date=today`, the function returns today.

```python
def _sourced_date(csv_path: Path) -> str | None:
    latest: str | None = None
    for row in csv.DictReader(fh):
        val = str(row.get("sourced_date", "")).strip()
        if val and (latest is None or val > latest):
            latest = val
    return latest
```

**Staleness rule:** `stale = max(sourced_date in file) != today`

### Step 3: Badge rendered

`stale = False` → badge shows **FRESH**  
`stale = True` → badge shows **STALE**

---

## Critical Answer: Q6 — What Does the Badge Reflect?

**The badge reflects: B) merely completion of a refresh attempt.**

Specifically, the badge reflects whether the signal file contains **any row** with `sourced_date = today`. It does **not** verify:
- Whether any data values were actually returned
- Whether score fields are non-empty
- Whether the provider call succeeded
- Whether field coverage is complete

---

## Badge Logic Flow Diagram

```
Refresh runs
    │
    ▼
For each symbol:
    fetch_provider_data(symbol)
        │ success → write row with score + sourced_date=today
        │ failure → write row with empty score + sourced_date=today ← KEY GAP
        ▼
latest_[provider].csv updated
    │
    ▼
max(sourced_date) in file == today?
    │
    YES → stale=False → badge=FRESH ← regardless of data quality
    NO  → stale=True  → badge=STALE
```

---

## Badge Truth Table

| Scenario | sourced_date today? | Data returned? | Badge | Correct? |
|---|---|---|---|---|
| Fetch ran, all symbols succeeded | Yes | Yes | FRESH | ✓ Yes |
| Fetch ran, some symbols returned null | Yes | Partial | FRESH | ⚠ Misleading |
| Fetch ran, ALL symbols returned null | Yes | No | FRESH | ✗ False positive |
| Fetch crashed before writing | Maybe | No | STALE | ✓ Yes |
| Fetch skipped (already fresh) | Yesterday | N/A | STALE | ✓ Yes (correct) |
| Provider timeout (row written empty) | Yes | No | FRESH | ✗ False positive |

---

## Staleness Check in refresh_signals.py

The refresh script also uses a simpler staleness check:

```python
def _is_stale(latest_csv: Path) -> bool:
    today = date.today().isoformat()
    return _latest_sourced_date(latest_csv) != today
```

This uses the **first** `sourced_date` found in the file (not maximum), introducing a subtle inconsistency with `run_outcome_ui.py`'s `_sourced_date()` which uses **maximum**. In practice this difference is inconsequential since the files are sorted with newest entries first.
