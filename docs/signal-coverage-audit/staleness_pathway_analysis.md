# Staleness Pathway Analysis
**Audit Date**: 2026-06-12  
**Scope**: SIGNAL-COVERAGE-01 — Per-Provider Staleness Pathways

---

## Framework

For each provider, staleness is analyzed through the lens of the governance concern:

```
Current → Cached → Refresh Excluded → Permanently Stale
```

A provider is rated HIGH risk if a held position can enter the stale path 
through normal operations (e.g. the standard UI-triggered refresh).

---

## 1. Zacks

**Status**: ✅ FIXED (ZACKS-REFRESH-UNIVERSE-01)

### Staleness Pathway (Pre-Fix)
```
Holding is BULLISH     → daily refresh (Priority 1)
Holding turns NEUTRAL  → dropped from smart list once cached
Holding turns BEARISH  → permanently excluded → stale
No recovery until ESS recovers to BULLISH
```

### Staleness Pathway (Post-Fix)
```
Holding is BULLISH     → daily refresh (Priority 1)
Holding turns BEARISH  → still forced into refresh (Priority 0)
Holding removed        → forced set updated dynamically from latest PAR
```

| Metric | Value |
|--------|-------|
| Max staleness | 0 days (daily forced refresh for all holdings) |
| Refresh cadence | Daily |
| Alert mechanism | None (no staleness alarm) |
| Recovery path | Automatic — forced refresh regardless of ESS |

---

## 2. Danelfin

**Status**: ⚠️ ACTIVE DEFECT — conditional on invocation path

### Staleness Pathway (Standard Path — `smart=False`)
```
Holding is any ESS     → full universe refresh daily
No holdings gap
```
This path is triggered by `ensure_signals_fresh()` (default), diagnostics builders, 
and direct script invocation without `--smart`. **This path is safe.**

### Staleness Pathway (UI Smart Path — `smart=True`)
```
Holding is BULLISH/VERY_BULLISH  → included in _smart_universe_symbols() → refreshed
Holding turns NEUTRAL (ESS ≥ 6.5) → near-bullish threshold → still included
Holding turns NEUTRAL (ESS < 6.5) → excluded from smart path → stale (if UI path used)
Holding turns BEARISH/VERY_BEARISH → excluded from smart path → stale (if UI path used)
Holding has NO_ESS               → excluded from smart path → stale (if UI path used)
```

**The UI "Refresh Signals" button (`/api/signal-refresh`) always invokes `--smart`.**  
There is no fallback. When the operator uses the UI to refresh signals, Danelfin 
is not refreshed for bearish/no-ESS holdings.

Current affected equity holdings: **37 of 71** (52%)

This includes:
- 5 bearish/very-bearish holdings: CMCO, DVN, KGC, PRIM, TSLA (highest risk)
- 6 no-ESS equity holdings: AEIS, BSVN, CBOE, MTZ, SIMO, STNG (no fallback signal)
- ~26 NEUTRAL holdings with ESS raw score < 6.5

| Metric | Value |
|--------|-------|
| Max staleness | Unbounded — no staleness cap for excluded holdings |
| Refresh cadence (excluded) | Never (until ESS improves or full-universe mode run manually) |
| Alert mechanism | None |
| Recovery path | Manual: run `refresh_signals.py` without `--smart`, or fix UI endpoint |

### Asymmetric Risk

The worst case is identical to the Zacks pre-fix scenario:
1. Position is BULLISH → Danelfin refreshed daily
2. ESS degrades: BULLISH → NEUTRAL → BEARISH  
3. With each degradation step, Danelfin smart-refresh excludes the symbol
4. By the time the position is under reduction review (BEARISH), Danelfin data is stale
5. Composite score for the reduction decision uses outdated Danelfin component

Danelfin feeds the CW-DAS composite score. This is a **scoring-level staleness risk**.

---

## 3. Yahoo Supplemental (ABR / Price Target / Analyst Consensus)

**Status**: ⚠️ ACTIVE DEFECT — same structural defect as Danelfin

### Staleness Pathway

Identical architecture to Danelfin. Both providers use the same `_smart_universe_symbols()` 
gate in `_refresh_yahoo()`.

```
UI /api/signal-refresh → refresh_signals.py --smart
→ _refresh_yahoo(smart=True) → _smart_universe_symbols()
→ BEARISH/NO_ESS holdings excluded → Yahoo data stale for 37 holdings
```

| Metric | Value |
|--------|-------|
| Max staleness | Unbounded |
| Refresh cadence (excluded) | Never via UI path |
| Alert mechanism | None |
| Recovery path | Same as Danelfin |

### Impact vs. Danelfin

Yahoo's impact is lower than Danelfin because:
- `abr` (analyst consensus) is informational only — not in primary CW-DAS composite score
- Price targets are display-only in DIL
- However: stale analyst consensus for a bearish holding is a decision-context failure

The secondary concern is `composite_v2_yahoo` — a secondary composite score column
that does include Yahoo ABR. If this is used in any ranking or allocation logic, 
staleness here becomes a scoring-tier issue.

---

## 4. FMP

**Status**: ✅ NO STALENESS PATHWAY FOR HOLDINGS

FMP's `_refresh_fmp()` always calls `_all_universe_symbols()`. There is no `--smart` 
equivalent for FMP. Every universe symbol is refreshed on every stale day.

| Metric | Value |
|--------|-------|
| Daily staleness | Resolved by full-universe daily refresh |
| Quarterly staleness | Resolved if data is > 90 days old (quarterly trigger) |
| Alert mechanism | `get_fmp_freshness_report()` available |
| Recovery path | Automatic — full universe |

---

## 5. ESS (StarMine / Fidelity)

**Status**: ⚠️ PASSIVE RISK — externally determined

ESS is not actively fetched. Coverage is determined by what Fidelity/StarMine includes 
in their daily file. The staleness pathway is passive:

```
Holding is covered → ESS updated when new file is placed in incoming/
Holding ESS not in file → ESS remains at prior value (no update, no alert)
```

If StarMine drops a holding from coverage (e.g. small-cap delisting, IPO lockout), 
SIH continues using the last-known ESS value indefinitely. There is no:
- Maximum staleness cap on ESS values  
- Alert when a previously-present symbol is absent from the new file
- Recovery path other than the symbol reappearing in the next file

This is a passive structural risk, not an architecture defect. The intake pipeline 
performs an upsert (new data overwrites old), but does not detect and flag dropped symbols.

| Metric | Value |
|--------|-------|
| Max staleness | Unbounded if Fidelity drops coverage |
| Refresh cadence | Daily when operator places new file |
| Alert mechanism | None for dropped symbols |
| Recovery path | Manual re-ingestion if symbol reappears |

---

## 6. `refresh_portfolio_signals.py` — Hardcoded List

**Status**: ⚠️ GOVERNANCE RISK — on-demand script only

This script has a hardcoded `_PORTFOLIO_SYMBOLS` list. Unlike the automated daily 
refresh, it is not run automatically. When run, it fetches Danelfin + Yahoo for 
specifically-listed symbols.

Risk: Any position added after the last time the code was updated will not be 
in `_PORTFOLIO_SYMBOLS`. The script silently succeeds without covering new holdings.

The fix is straightforward: replace `_PORTFOLIO_SYMBOLS` with a dynamic load 
from the latest PAR `holdings.csv` (identical to `_load_portfolio_equity_holdings()`).

---

## Staleness Pathway Summary

| Provider | Max Staleness | Affected Holdings | Scoring Impact | Alert? |
|----------|--------------|-------------------|---------------|--------|
| Zacks | 0 days (post-fix) | 0 | HIGH | No |
| Danelfin (UI path) | Unbounded | 37 of 71 | HIGH (CW-DAS) | No |
| Yahoo (UI path) | Unbounded | 37 of 71 | MEDIUM (informational) | No |
| FMP | 0 days (daily) | 0 | LOW (informational) | Partial |
| ESS | Unbounded (passive) | Unknown | HIGH (primary signal) | No |
| Analyst Consensus | Unbounded (via Yahoo) | 37 of 71 | LOW (informational) | No |
| Price Targets | Unbounded (via Yahoo) | 37 of 71 | LOW (informational) | No |
