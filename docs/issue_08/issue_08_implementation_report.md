# ISSUE-08 — Implementation Report
## Fix analyst_count Fetch Pipeline

**Date:** June 5, 2026  
**Status:** COMPLETE  
**Scope:** Data pipeline fix — no UI changes, no scoring changes

---

## 1. Summary

Completed the analyst_count data flow from Yahoo Finance through the fetch pipeline, CSV storage, model loading, and API payload. The `numberOfAnalystOpinions` field was available in yfinance but was never requested. The `AnalystConsensus.analyst_count` model field existed but was always `None`. This fix completes the pipeline.

---

## 2. Root Cause

`fetch_yahoo_supplemental.py` called `yf.Ticker(sym).info` but did not include `info.get("numberOfAnalystOpinions")` in the result dict. All downstream consumers (`analyst_consensus.py`, `runner.py`, `app.js`) had the plumbing in place — only the source fetch was missing.

---

## 3. Files Changed

### `src/scoring/fetch_yahoo_supplemental.py`

Three additive changes:

**1. `_OUTPUT_HEADERS` — added `analyst_count`:**
```python
_OUTPUT_HEADERS = [
    "symbol",
    "price_target",
    "abr",
    "analyst_count",    # ISSUE-08: new field
    "eps_growth_5yr",
    "current_price",
    "upside_pct",
    "sourced_date",
]
```

**2. `fetch_yahoo_supplemental()` result dict — initialized field:**
```python
result: dict[str, float | int | None] = {
    "price_target": None,
    "abr": None,
    "analyst_count": None,    # ISSUE-08
    ...
}
```

**3. Fetch + row construction — read and emit field:**
```python
# Fetch
_raw_count = info.get("numberOfAnalystOpinions")
result["analyst_count"] = int(_raw_count) if _raw_count else None

# Row write
"analyst_count": str(data.get("analyst_count")) if data.get("analyst_count") is not None else "",
```

Note: used `.get()` instead of `["analyst_count"]` to maintain backward compatibility with test mocks that don't include the new field.

### `src/portfolio/analyst_consensus.py`

Added `_int()` helper and wired `analyst_count` from CSV:

```python
def _int(key: str) -> Optional[int]:
    v = row.get(key, "").strip()
    try:
        return int(v) if v else None
    except ValueError:
        return None

result[sym] = AnalystConsensus(
    ...
    analyst_count=_int("analyst_count"),   # ISSUE-08: populated from CSV
    ...
)
```

**Comment removed:** "not available in current Yahoo data feed"

---

## 4. Data Updated

Re-fetched 53 portfolio equity symbols directly via `yf.Ticker(sym).info["numberOfAnalystOpinions"]`. Updated both `2026-06-05_yahoo_supplemental.csv` and `latest_yahoo_supplemental.csv`.

| Symbol | analyst_count |
|--------|---------------|
| DELL | 23 |
| NVDA | 58 |
| MSFT | 55 |
| TSLA | 41 |
| VRT | 25 |
| LRCX | 32 |
| PSX | 19 |
| AEIS | 9 |

Full universe re-fetch (2,570 symbols) will populate `analyst_count` for all symbols on the next scheduled refresh.

---

## 5. No UI Changes Required

The ISSUE-10 ATI block (`_dqAnalystTargetHtml`) was already wired to conditionally show `analyst_count` when non-null:

```javascript
const countHtml = (ac.analyst_count != null && ac.analyst_count > 0)
  ? `<span class="dq-ati-item">...<span class="dq-ati-val">${ac.analyst_count} analysts</span></span>`
  : "";
```

No ISSUE-10 code changes needed. The "Coverage: N analysts" row appeared automatically.

---

## 6. Test Fix

One existing test (`test_signal_fetch_resume.py`) mocked `fetch_yahoo_supplemental` with the old 4-key dict shape. The initial `data["analyst_count"]` access raised a `KeyError`. Fixed to `data.get("analyst_count")`. Test now passes.

---

## 7. Validation Summary

| Step | Result |
|------|--------|
| `numberOfAnalystOpinions` in yfinance info for DELL | 23 ✅ |
| `analyst_count` in `_OUTPUT_HEADERS` | ✅ |
| `analyst_count` written to dated CSV | ✅ (53 portfolio symbols) |
| `analyst_count` written to `latest_yahoo_supplemental.csv` | ✅ |
| `load_analyst_consensus()` returns `analyst_count=23` for DELL | ✅ |
| `analyst_consensus_by_symbol['DELL']['analyst_count']` in API response | 23 ✅ |
| ATI block shows "Coverage: 23 analysts" | ✅ |
| Recommendation panel shows analyst_count | ✅ (via `ac.analyst_count`) |
| 1,037 tests passing | ✅ |
