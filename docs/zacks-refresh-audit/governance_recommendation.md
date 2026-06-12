# Governance Recommendation: Zacks Refresh Universe
**Audit Date**: 2026-06-12  
**Issue**: ZACKS-REFRESH-UNIVERSE-01  
**Status**: APPROVED — implementation required

---

## 1. Governance Principle

> **All currently held portfolio positions must receive regular Zacks refresh coverage regardless of their ESS category, ESS trend, or cache status.**

This principle exists because:
1. Portfolio positions represent real capital at risk
2. Conviction scores for held positions drive hold/reduce decisions
3. Stale Zacks data in a conviction score is a data quality failure, not an optimization
4. The ESS-based smart refresh is a universe-wide optimization — it should not override mandatory coverage for held positions

---

## 2. Root Cause

`build_smart_refresh_list()` optimizes for **signal quality breadth** across the research universe. It correctly excludes non-bullish, cached symbols to reduce unnecessary API calls across 2,523 universe symbols.

The function was designed without awareness of the portfolio holdings layer. Portfolio-specific coverage guarantees were not built into the refresh architecture. The result is that held positions can fall off the daily refresh list the moment their ESS degrades below BULLISH.

---

## 3. Recommended Fix

### 3a. Modify `build_smart_refresh_list()` in `src/scoring/fetch_zacks_scores.py`

Add an optional `forced_symbols` parameter. Any symbol in `forced_symbols` is guaranteed inclusion in the output list, prepended before bullish candidates.

```python
def build_smart_refresh_list(
    universe_csv: Path | str = _REPO_ROOT / "data" / "current" / "base_equity_universe.csv",
    zacks_cache_csv: Path | str = _DEFAULT_OUTPUT_DIR / "latest_zacks.csv",
    bullish_ess_texts: frozenset[str] | None = None,
    forced_symbols: set[str] | None = None,   # NEW PARAMETER
) -> list[str]:
```

Logic addition (after existing Priority 1/2 logic):

```python
forced_list: list[str] = []
if forced_symbols:
    for sym in sorted(forced_symbols):
        sym = sym.strip().upper()
        if sym and sym not in seen:
            forced_list.append(sym)
            seen.add(sym)

return forced_list + bullish_list + uncached_list
```

Forced symbols are prepended (highest priority) so they are fetched first in case of partial run interruption.

### 3b. Modify `scripts/refresh_signals.py` — Inject Portfolio Holdings

Load the most recent PAR holdings file and pass equity holdings as `forced_symbols`:

```python
from src.scoring.fetch_zacks_scores import build_smart_refresh_list
import csv, os

def _load_portfolio_equity_holdings() -> set[str]:
    """Return equity holding symbols from the most recent PAR run."""
    par_root = Path("data/portfolio_ingestion/analysis_runs")
    # Sort PAR directories; pick the latest date-stamped one (PAR-YYYYMMDD-*)
    date_pars = sorted(
        [d for d in par_root.iterdir() if d.name.startswith("PAR-2")],
        key=lambda p: p.name,
        reverse=True,
    )
    if not date_pars:
        return set()
    holdings_path = date_pars[0] / "holdings.csv"
    if not holdings_path.exists():
        return set()
    syms = set()
    with holdings_path.open() as f:
        for row in csv.DictReader(f):
            sym = (row.get("symbol") or "").strip().upper()
            asset = (row.get("asset_class") or "").strip().upper()
            if sym and asset == "EQUITIES":
                syms.add(sym)
    return syms

# In the Zacks smart-refresh call:
forced = _load_portfolio_equity_holdings()
symbols_to_fetch = build_smart_refresh_list(forced_symbols=forced)
```

---

## 4. Alternative Approaches Considered

| Approach | Verdict |
|----------|---------|
| **Full universe refresh** (remove smart-refresh entirely) | Rejected — 2,523 symbols/day is unnecessary; ~42–84 min runtime |
| **Separate holdings-only refresh job** | Rejected — two Zacks jobs creates scheduling complexity and split cache management |
| **Lower the ESS threshold** (include NEUTRAL in smart refresh) | Partial — would fix 13 of 24 gaps but miss BEARISH/NO_ESS holdings; also inflates refresh by ~774 symbols |
| **`forced_symbols` parameter (recommended)** | Accepted — surgical, minimal runtime cost, clean API surface |

---

## 5. Data Contract Changes

| Component | Change |
|-----------|--------|
| `build_smart_refresh_list()` signature | Add `forced_symbols: set[str] | None = None` — backward compatible (default=None) |
| `refresh_signals.py` | Add `_load_portfolio_equity_holdings()` helper; pass to `build_smart_refresh_list()` |
| `latest_zacks.csv` | No schema change — forced symbols use same fetch/write path |

No breaking changes. The `forced_symbols=None` default preserves existing behavior for all callers that don't pass it.

---

## 6. Acceptance Criteria

After implementation:

1. All 24 currently excluded equity holdings appear in the smart refresh list
2. `build_smart_refresh_list(forced_symbols={"TSLA", "CMCO", ...})` returns a list containing all forced symbols
3. Regression suite passes: target 1,172 passed, 32 skipped, 0 failed
4. `refresh_signals.py` logs the count of forced portfolio holdings at INFO level

---

## 7. Priority

**P1 — Implement immediately.** This is an active data quality defect affecting held portfolio positions. Bearish holdings (CMCO, DVN, KGC, PRIM, TSLA) receiving stale Zacks data are the immediate risk. Every day without the fix is another day of potential stale conviction scores for reduction candidates.
