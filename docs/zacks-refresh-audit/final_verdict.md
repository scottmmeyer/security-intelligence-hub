# Final Verdict: ZACKS-REFRESH-UNIVERSE-01
**Audit Date**: 2026-06-12  
**Auditor**: Security Intelligence Hub governance review  
**Status**: CONFIRMED DEFECT — Fix Required

---

## Governing Question

> Do ALL currently held portfolio positions receive regular Zacks refresh coverage?

**Answer: NO.**

---

## Q1 — What is the 683-symbol refresh universe and how is it constructed?

**Verified.** The smart refresh list is built by `build_smart_refresh_list()` in `src/scoring/fetch_zacks_scores.py`. It reads `base_equity_universe.csv` (2,523 symbols) and produces a deduplicated ordered list of:

- **Priority 1** (519 symbols): Any symbol with `starmine_ess_text` in `{"BULLISH", "VERY_BULLISH"}`
- **Priority 2** (164 symbols): Any symbol NOT already in `latest_zacks.csv` cache

Total: 683 symbols. All other universe symbols (NEUTRAL, BEARISH, VERY_BEARISH, NO_ESS + cached) are excluded.

The previous 112-symbol count observed in earlier sessions reflected a prior, smaller snapshot. As of 2026-06-12 post-intake, the count is 683.

---

## Q2 — Are NEUTRAL or BEARISH holdings excluded from smart refresh?

**Confirmed: YES.** Any holding that is:
- In `base_equity_universe.csv`
- Has ESS of NEUTRAL, BEARISH, VERY_BEARISH, or NO_ESS  
- AND is already present in `latest_zacks.csv`

...is **excluded** from the smart refresh list. It receives no Zacks data update.

Current excluded equity holdings: **24 symbols** (13 NEUTRAL, 4 BEARISH, 1 VERY_BEARISH, 6 NO_ESS).

---

## Q3 — Can holdings become permanently stale?

**Confirmed: YES.** The staleness pathway is:

```
Symbol enters cache (first fetch) → ESS degrades below BULLISH → 
dropped from smart refresh list → cached data never updated → 
composite score runs on stale Zacks indefinitely
```

There is no maximum staleness age enforcement. No alert fires when cached data ages. The only exit from permanent staleness is if ESS recovers to BULLISH/VERY_BULLISH, which is directionally unlikely for deteriorating holdings.

---

## Q4 — Should all portfolio holdings receive forced Zacks refresh?

**Confirmed: YES.** The principle is unambiguous: real capital is deployed in held positions. Conviction scoring for hold/reduce decisions must use current data. An optimization designed for the research universe (skip non-bullish cached symbols) should not silently exclude held positions from mandatory data refresh.

The 24 excluded equity holdings represent an active data quality defect. The 5 bearish/very-bearish holdings (CMCO, DVN, KGC, PRIM, TSLA) are the highest-risk cases — these are likely reduction candidates running on stale conviction data.

---

## Q5 — What is the recommended architecture?

**Recommended fix:**

1. **Add `forced_symbols: set[str] | None = None`** to `build_smart_refresh_list()` in `src/scoring/fetch_zacks_scores.py`
2. **Prepend forced symbols** to the output list (highest priority fetch order)
3. **In `refresh_signals.py`**: Load the most recent PAR `holdings.csv`, filter to `asset_class == "EQUITIES"`, pass as `forced_symbols`
4. **Log**: Include forced holdings count in refresh run log at INFO level

This is backward-compatible (default `None` preserves current behavior), minimal-runtime-cost (+24 symbols = +~30 seconds/day), and architecturally clean.

---

## Summary Matrix

| Question | Answer | Severity |
|----------|--------|----------|
| Is the 683-symbol universe correctly described? | YES | N/A |
| Are NEUTRAL/BEARISH holdings excluded? | YES — confirmed | DEFECT |
| Can holdings become permanently stale? | YES — no staleness cap | DEFECT |
| Should holdings be force-included? | YES — governance requirement | REQUIREMENT |
| Recommended architecture | `forced_symbols` parameter | APPROVED |
| Runtime impact of fix | +24 symbols, ~+30 sec/day | ACCEPTABLE |
| Breaking changes? | None (backward-compatible) | SAFE |

---

## Disposition

**ZACKS-REFRESH-UNIVERSE-01**: CONFIRMED DEFECT  
**Resolution**: Implement `forced_symbols` parameter — see `governance_recommendation.md`  
**Priority**: P1 — active data quality defect on held positions  
**Target**: Next available sprint; bearish holding staleness risk is immediate
