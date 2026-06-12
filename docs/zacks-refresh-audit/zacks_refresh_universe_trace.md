# Zacks Refresh Universe Trace
**Audit Date**: 2026-06-12  
**Scope**: `src/scoring/fetch_zacks_scores.py` — `build_smart_refresh_list()`  
**Trigger**: ZACKS-REFRESH-UNIVERSE-01 governance review

---

## 1. Code Location

| File | Function | Line |
|------|----------|------|
| `src/scoring/fetch_zacks_scores.py` | `build_smart_refresh_list()` | ~385 |
| `scripts/refresh_signals.py` | Zacks smart-refresh invocation | ~150 |

---

## 2. Algorithm Trace

```
build_smart_refresh_list(
    universe_csv  = data/current/base_equity_universe.csv,   # 2523 symbols
    zacks_cache   = data/signals/zacks/latest_zacks.csv,      # 2649 cached symbols
    bullish_texts = {"BULLISH", "VERY_BULLISH"}               # _BULLISH_ESS_TEXTS
) -> list[str]
```

**Step 1 — Load cache**: Read `latest_zacks.csv`. Build `cached_symbols` set.

**Step 2 — Walk universe**: For each symbol in `base_equity_universe.csv`:
- If `starmine_ess_text` is in `{"BULLISH", "VERY_BULLISH"}` → **Priority 1** (`bullish_list`)
- Else if symbol is NOT in `cached_symbols` → **Priority 2** (`uncached_list`)
- Else (NEUTRAL / BEARISH / VERY_BEARISH / NO_ESS and already cached) → **EXCLUDED**

**Step 3 — Return**: `bullish_list + uncached_list`

---

## 3. Observed Counts (2026-06-12)

| Category | Count |
|----------|-------|
| `base_equity_universe.csv` symbols | 2,523 |
| `latest_zacks.csv` cached symbols | 2,649 |
| Smart refresh list (returned) | **683** |
| ↳ Priority 1 — BULLISH/VERY_BULLISH | 519 |
| ↳ Priority 2 — uncached (non-bullish) | 164 |
| Excluded (non-bullish + cached) | 1,840 |

Universe ESS distribution:

| ESS Category | Count |
|--------------|-------|
| BULLISH / VERY_BULLISH | 519 |
| NEUTRAL | 774 |
| BEARISH / VERY_BEARISH | 918 |
| NO_ESS (blank) | 312 |

---

## 4. What Drives the 683 Number in the UI

The "112" number noted in earlier UI observations was from a prior snapshot. As of the 2026-06-12 intake cycle, the smart refresh list is **683 symbols**:

- All BULLISH/VERY_BULLISH symbols in the universe receive a daily Zacks refresh (519)
- All universe symbols not yet cached receive a one-time fetch (164)
- Once a non-bullish symbol is cached, it is **never refreshed again** under the current logic

---

## 5. Inputs / Outputs

| Input | Path |
|-------|------|
| Universe | `data/current/base_equity_universe.csv` |
| Zacks cache | `data/signals/zacks/latest_zacks.csv` |

| Output | Description |
|--------|-------------|
| `list[str]` | Ordered symbol list; bullish first, uncached second |

---

## 6. Invocation in refresh_signals.py

`scripts/refresh_signals.py` calls `build_smart_refresh_list()` for Zacks and passes the result directly to the fetch loop. Line 150 explicitly notes: _"Zacks always uses smart-refresh (bullish first + uncached); full universe is never needed."_

Portfolio holdings are **not injected** into the fetch list at any point in `refresh_signals.py`. The function has no `forced_symbols` parameter.

---

## 7. Governance Gap Identified

The algorithm is correct for optimizing coverage of high-signal bullish candidates. However, it contains a structural blind spot: **currently held portfolio positions that are NEUTRAL, BEARISH, or NO_ESS AND already cached receive zero Zacks refresh indefinitely.** See `portfolio_holdings_refresh_gap_analysis.md` for the full holdings-level impact.
