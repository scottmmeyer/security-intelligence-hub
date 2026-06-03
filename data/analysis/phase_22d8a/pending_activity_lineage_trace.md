# Phase 22D.8A — Pending Activity Lineage Trace

**Run Audited:** PAR-20260602-8CF1CB84  
**Source File:** Portfolio_Positions_Jun-02-2026 (2).csv  
**Audit Scope:** How PENDING ACTIVITY ($-3,566.55) flows through the analysis pipeline

---

## 1. Raw Source CSV Entry

From `Portfolio_Positions_Jun-02-2026 (2).csv`:

```
Account,Account Name,Symbol,Description,...,Current Value,...
Z35123695,Individual - TOD,Pending activity,,,,,-$3566.55,,,,,,,,,
```

Key observations:
- Symbol field is blank (empty string in CSV)
- Description is "Pending activity" (mixed case)
- Quantity is blank
- Market value is **-$3,566.55** (negative)
- No security type, sector, or industry information

Fidelity also exported SPAXX at the **pre-settlement balance** in the same account:
```
Z35123695,Individual - TOD,SPAXX**,HELD IN MONEY MARKET,,,,$41209.64,...
```

SPAXX has **not been reduced** for the pending settlement. The -$3,566.55 is Fidelity's
indicator that this amount will be debited from SPAXX upon settlement.

---

## 2. Ingestion Layer: `_parse_fidelity()` → `_classify_operational_state()`

**File:** `src/portfolio/ingestion.py`

The operational state classifier logic:
```python
def _classify_operational_state(sym: str, desc: str, mv: Optional[float]) -> str:
    desc_upper = desc.upper()
    if any(kw in desc_upper for kw in _PENDING_DESCRIPTION_KEYWORDS) or sym == "PENDING":
        return "PENDING_SETTLEMENT"
    if mv is not None and mv < 0:
        return "ACCOUNTING_ADJUSTMENT"
    ...
```

For the PENDING ACTIVITY row:
- `sym = ""` (blank — empty string from CSV)
- `desc = ""` (blank — Fidelity description field was also blank in this row)

**Critical path decision:**
- `_PENDING_DESCRIPTION_KEYWORDS` check: `desc_upper = ""` → no match
- `sym == "PENDING"` check: `sym = ""` → no match
- `mv < 0` check: `-3566.55 < 0` → **YES → returns `ACCOUNTING_ADJUSTMENT`**

**Verdict:** PENDING ACTIVITY is classified as `ACCOUNTING_ADJUSTMENT` (not `PENDING_SETTLEMENT`)
due to blank symbol and description in that row's parsed fields. The negative market value
sentinel catches it.

---

## 3. Holdings.csv Representation

After ingestion and enrichment, the row in `holdings.csv`:
```
symbol="PENDING ACTIVITY"  market_value=-3566.55  operational_state=ACCOUNTING_ADJUSTMENT  is_cash_equivalent=False  security_type="Common Stock"
```

Note: The `symbol` field in holdings.csv reads "PENDING ACTIVITY" — this is derived from
the CSV row identifier or fallback logic in the parser, not from the raw symbol column.

---

## 4. Investable Filter: `runner.py` line 558–559

```python
_INVESTABLE_STATES = frozenset({"ACTIVE_POSITION", "CASH_EQUIVALENT"})
investable = [h for h in enriched if h.operational_state in _INVESTABLE_STATES]
```

PENDING ACTIVITY `operational_state = "ACCOUNTING_ADJUSTMENT"` is **NOT in `_INVESTABLE_STATES`**.

→ PENDING ACTIVITY is **excluded from the `investable` list entirely**.

---

## 5. Cash Computation: `compute_deployable_cash()` in `deployment_queue.py`

```python
cash_context = compute_deployable_cash(
    holdings=investable,           # ← does NOT contain PENDING ACTIVITY
    total_market_value=snapshot.total_market_value,   # ← DOES include PENDING
    mandate_cash_target_pct=_cash_target_pct,
)
```

Inside `compute_deployable_cash`:
```python
cash_mv = sum(h.market_value for h in holdings if h.is_cash_equivalent)
```

- `holdings` = `investable` list = no PENDING ACTIVITY
- SPAXX has `is_cash_equivalent=True` → included: $41,279.15
- Result: `cash_mv = $41,279.15`

---

## 6. Total Market Value: `ingestion.py` line 416

```python
total_mv = sum(r["market_value"] for r in raw_rows)
```

This is an **unconditioned sum** over ALL raw rows including PENDING ACTIVITY:
- Sum = $480,298.55 (includes PENDING ACTIVITY at -$3,566.55)
- Without PENDING ACTIVITY: $483,865.10

`snapshot.total_market_value = $480,298.55` → passed directly to `compute_deployable_cash`

---

## 7. Asymmetry Summary

| Component | PENDING ACTIVITY (-$3,566.55) included? |
|-----------|----------------------------------------|
| `cash_mv` numerator | **NO** (excluded via investable filter) |
| `total_market_value` denominator | **YES** (unconditioned sum at ingestion) |
| `floor_mv` (7% × total_mv) | Effectively YES (uses total_mv) |
| `deployable_mv` = max(0, cash_mv - floor_mv) | Uses overstated cash_mv |

This asymmetry causes `cash_mv` to be overstated by exactly $3,566.55 relative to
the true post-settlement cash balance.

---

## 8. Settlement Context

PENDING ACTIVITY in a Fidelity export represents a **T+1 settlement debit**.
When PRG (PROG HOLDINGS, $3,622.00 at MV) was purchased, Fidelity:
1. Immediately showed the PRG position in the holdings at current MV ($3,622.00)
2. Did NOT reduce SPAXX by the purchase price ($3,566.55 cost basis)
3. Added PENDING ACTIVITY = -$3,566.55 as a future-dated cash debit

After settlement (T+1): PENDING ACTIVITY row disappears, SPAXX is debited by $3,566.55.

During the settlement window, the system operates on pre-settlement SPAXX balance.
