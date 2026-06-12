# Runtime Impact Assessment
**Audit Date**: 2026-06-12  
**Scope**: ZACKS-REFRESH-UNIVERSE-01 — proposed fix runtime cost

---

## 1. Current Runtime Baseline

| Metric | Value |
|--------|-------|
| Current smart refresh list size | 683 symbols |
| Typical Zacks fetch rate | ~1–2 seconds per symbol (rate-limited HTTP) |
| Estimated current runtime | ~11–23 minutes per run |
| Refresh frequency | Daily (scheduled via `refresh_signals.py`) |

---

## 2. Proposed Change: Force Portfolio Holdings Into Refresh List

The governance recommendation adds all current portfolio equity holdings to the refresh list as a mandatory set, regardless of ESS category or cache status.

**Holdings eligible for forced inclusion** (equity holdings in universe currently excluded from smart refresh):

| ESS Category | Count |
|-------------|-------|
| BEARISH | 4 (CMCO, DVN, KGC, PRIM) |
| VERY_BEARISH | 1 (TSLA) |
| NEUTRAL | 13 |
| NO_ESS | 6 |
| **Total new forced symbols** | **24** |

Non-equity holdings (ETFs, funds, crypto, cash — 20 symbols) are not added to the Zacks fetch list. Zacks data is not available or applicable for these instruments.

---

## 3. Net Runtime Impact

| Scenario | Symbols Fetched | Est. Runtime |
|----------|----------------|-------------|
| Current (smart only) | 683 | ~11–23 min |
| After fix (smart + forced holdings) | 707 | ~12–24 min |
| **Incremental cost** | **+24 symbols** | **+24–48 seconds** |

The incremental cost is **under 1 minute** on a daily run cadence. This is negligible.

---

## 4. Caching Efficiency

The forced holdings set is small and stable. Portfolio turnover is low — the set of forced symbols changes only when:
- A new position is initiated (rare)
- An existing position is closed (rare)
- An equity holding's ESS improves to BULLISH (it would then already be in the smart list anyway)

The forced set will typically be 20–30 symbols. The daily marginal cost stabilizes around +24–48 seconds once all forced symbols are initially cached.

---

## 5. Memory / Storage Impact

Each Zacks fetch result is a small JSON/CSV record (~200 bytes). Adding 24 symbols to `latest_zacks.csv` adds approximately 5 KB to the cache file. Negligible.

---

## 6. Implementation Risk

The proposed change is additive: `build_smart_refresh_list()` already returns a deduplicated list. Adding a `forced_symbols` parameter with `set.union()` semantics cannot reduce coverage, only increase it. There is no risk of removing currently-covered symbols.

The only potential regression is if the Zacks API rate limiter triggers on the additional 24 symbols. At current usage levels (~683/day), 707 is well within documented rate limits.

---

## 7. Conclusion

**Approve.** The governance benefit (eliminating staleness risk for 24 held positions including 5 bearish/very-bearish reduction candidates) far outweighs a ~30-second runtime increase. Proceed with implementation as specified in `governance_recommendation.md`.
