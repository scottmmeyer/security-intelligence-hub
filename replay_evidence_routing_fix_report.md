# Phase 7.4D — Replay Evidence Routing Fix Report

**Date:** 2026-05-30  
**Fix Target:** `src/portfolio/recommendations.py` — `_load_replay_evidence()`  
**Analysis Run:** `PAR-20260530-3A136D4F`  
**Test File:** `tests/test_7_4d_replay_evidence_routing.py`  

> This is a replay evidence recognition fix only.
> No replay generation changed. No composite scoring changed. No DAS changed.
> No portfolio targets changed. No recommendation ordering changed for unaffected holdings.

---

## Summary

`_load_replay_evidence()` contained a filter that silently discarded all industry-specific
replay selections from `replay_inputs.csv`. Only cross-sector ALL-industry replays contributed
to the `symbol_tier` dict used to set `replay_supported=True` in security overlays.

The fix removes the filter restriction and allows industry-specific replay selections
to count as valid replay evidence, subject to canonical tier compatibility:
the replay's `filter_geography`, `filter_market_cap_bucket`, and `filter_industry`
must match the holding's classification.

**Net result:** Replay-supported holdings increased from 21 → 46 (+25 holdings, +14.37pp).

---

## Before / After

| Metric | Before (ALL-only) | After (Fix) | Delta |
|---|---|---|---|
| Replay-supported holding count | 21 | 46 | +25 |
| Replay-supported portfolio value | $180,132 | $247,684 | +$67,552 |
| Replay-supported portfolio weight | 37.89% | 52.26% | +14.37pp |
| Total portfolio value | $472,220 | $472,220 | — |

---

## Root Cause

**File:** `src/portfolio/recommendations.py`  
**Function:** `_load_replay_evidence()` (previously ~line 57)

**Before (broken filter):**
```python
if row.get("filter_industry", "").upper() != "ALL":
    continue
```

This guard caused the loop over `replay_inputs.csv` rows to skip every
industry-specific row (TECHNOLOGY, HEALTHCARE, FINANCIAL SERVICES, BASIC MATERIALS,
INDUSTRIALS, etc.). Only rows where `filter_industry == "ALL"` added symbols to
`symbol_tier`, which was the sole input to `replay_supported` in the overlay.

**After (fixed routing):**
```python
if ind == "ALL":
    # Cross-sector ALL replay — highest priority, existing behavior preserved.
    if sym not in symbol_tier:
        symbol_tier[sym] = f"{geo}.{cap}"
        symbol_replay[sym] = replay_id
else:
    # Industry-specific replay — record dimensions for canonical tier
    # compatibility check during overlay construction.
    if sym not in symbol_tier and sym not in industry_replay_evidence:
        industry_replay_evidence[sym] = {
            "geo": geo, "cap": cap, "industry": ind, "replay_id": replay_id,
        }
```

Tier compatibility check applied in `build_security_overlays()`:
```python
if not in_replay and sym in industry_replay_evidence:
    ev = industry_replay_evidence[sym]
    if (
        ev["geo"] == h.geography
        and ev["cap"] == h.market_cap_bucket
        and ev["industry"] == (h.industry or "").strip().upper()
    ):
        in_replay = True
        replay_id = ev["replay_id"]
        replay_tier = f"{ev['geo']}.{ev['cap']}.{ev['industry']}"
```

**Invariants preserved:**
- ALL-replay symbols remain in `symbol_tier` (highest priority, existing behavior).
- A symbol that appears in both ALL and industry replay keeps the ALL tier.
- Industry replay only grants `replay_supported=True` when the holding's
  geo/cap/industry matches the replay's filter dimensions exactly.
- Symbols not selected in any replay remain `replay_supported=False`.

---

## Symbols Upgraded by Fix (+25)

| Symbol | Replay Tier | Weight | MV |
|---|---|---|---|
| CIEN | US/MID/TECHNOLOGY | 1.20% | $5,703 |
| CAH | US/MID/HEALTHCARE | 1.04% | $4,922 |
| PCB | US/MICRO/FINANCIAL SERVICES | 0.94% | $4,451 |
| AVT | US/SMALL/TECHNOLOGY | 0.91% | $4,340 |
| ATLC | US/MICRO/FINANCIAL SERVICES | 0.90% | $4,280 |
| DVN | US/MID/ENERGY | 0.94% | $4,457 |
| NUE | US/MID/BASIC MATERIALS | 0.79% | $3,758 |
| XYZ | US/MID/TECHNOLOGY | 0.80% | $3,782 |
| CBOE | US/MID/FINANCIAL SERVICES | 0.69% | $3,298 |
| HALO | US/SMALL/HEALTHCARE | 0.70% | $3,341 |
| BSVN | US/MICRO/FINANCIAL SERVICES | 0.56% | $2,659 |
| STLD | US/MID/BASIC MATERIALS | 0.55% | $2,609 |
| AZZ | US/SMALL/INDUSTRIALS | 0.43% | $2,035 |
| ANGO | US/MICRO/HEALTHCARE | 0.83% | $3,947 |
| ANIP | US/MICRO/HEALTHCARE | 0.83% | $3,952 |
| FSLR | US/MID/TECHNOLOGY | 0.63% | $3,018 |
| GFF | US/SMALL/INDUSTRIALS | 0.37% | $1,770 |
| UHS | US/SMALL/HEALTHCARE | 0.25% | $1,180 |
| UTHR | US/MID/HEALTHCARE | 0.23% | $1,106 |
| MTZ | US/MID/INDUSTRIALS | 0.24% | $1,123 |
| ALNT | US/MICRO/TECHNOLOGY | 0.16% | $784 |
| YELP | US/MICRO/COMMUNICATION SERVICES | 0.18% | $850 |
| CRS | US/MID/INDUSTRIALS | 0.10% | $465 |
| CMCO | US/MICRO/INDUSTRIALS | 0.03% | $160 |
| AGEN | US/MICRO/HEALTHCARE | 0.07% | $346 |

**Note:** Phase 7.4B identified 8 specific gap candidates (ATLC, AVT, BSVN, CAH, CBOE, CIEN, NUE, PCB)
as the highest-quality affected symbols. The fix correctly upgrades all 8. An additional
17 holdings also had industry-specific replay selections that were ignored by the old filter —
these are now correctly recognized as well.

---

## Symbols Not Upgraded

| Symbol | Reason | Status |
|---|---|---|
| PRG | Not selected in top-N for MICRO/US/INDUSTRIALS replay. The category has a replay (AVAILABLE) but PRG ranked below the top-N threshold at composite snapshot date. | Expected — replay_supported=False correct |

PRG has no entry in `replay_inputs.csv` selected_symbols for any row. The fix
correctly leaves PRG as `replay_supported=False`.

---

## Symbols Unchanged (pre-existing ALL-replay support)

The following 21 symbols were replay-supported before the fix and remain so after.
No pre-existing replay support was removed.

| Symbol | Tier |
|---|---|
| AEIS | US.LARGE |
| AMZN | US.MEGA |
| ARW | US.MID |
| ASML | US.LARGE |
| AVGO | US.MEGA |
| CVE | US.MID |
| DELL | US.LARGE |
| GTX | US.MICRO |
| LRCX | US.LARGE |
| MSFT | US.MEGA |
| MU | US.MEGA |
| NVDA | US.MEGA |
| PSX | US.MID |
| SANM | US.SMALL |
| SBS | US.MID |
| SIMO | US.SMALL |
| SNX | US.LARGE |
| STNG | US.SMALL |
| TSLA | US.MEGA |
| TSM | US.MEGA |
| VRT | US.LARGE |

---

## Tests Added

**File:** `tests/test_7_4d_replay_evidence_routing.py` — 27 tests, all passing.

| Test # | Class | Description | Pass |
|---|---|---|---|
| 1a | TestAllReplayStillWorks | ALL replay symbol appears in symbol_tier | ✓ |
| 1b | TestAllReplayStillWorks | ALL replay takes priority over industry replay | ✓ |
| 2a | TestIndustryReplayCountsWhenTierMatches | Industry symbol in industry_replay_evidence dict | ✓ |
| 2b | TestIndustryReplayCountsWhenTierMatches | Tier match grants replay_supported=True | ✓ |
| 3a | TestTierMismatchBlocksIndustryReplay | Geography mismatch → replay_supported=False | ✓ |
| 3b | TestTierMismatchBlocksIndustryReplay | Market cap mismatch → replay_supported=False | ✓ |
| 3c | TestTierMismatchBlocksIndustryReplay | Industry mismatch → replay_supported=False | ✓ |
| 4a | TestSymbolNotSelectedInAnyReplay | Absent symbol not in any evidence dict | ✓ |
| 4b | TestSymbolNotSelectedInAnyReplay | Absent symbol replay_supported=False | ✓ |
| 5 | TestPRGRemainsNotReplaySupported | PRG replay_supported=False | ✓ |
| 6–10 | TestIndustryReplaySymbolsUpgraded (parametrized) | ATLC, CIEN, CAH, AVT, NUE → replay_supported=True | ✓ (5 tests) |
| 6b | TestIndustryReplaySymbolsUpgraded | ATLC dedicated test | ✓ |
| 7b | TestIndustryReplaySymbolsUpgraded | CIEN dedicated test | ✓ |
| 8b | TestIndustryReplaySymbolsUpgraded | CAH dedicated test | ✓ |
| 9b | TestIndustryReplaySymbolsUpgraded | AVT dedicated test | ✓ |
| 10b | TestIndustryReplaySymbolsUpgraded | NUE dedicated test | ✓ |
| 11a | TestReplaySupportedCountIncrease | Count ≥ 29 after fix | ✓ |
| 11b | TestReplaySupportedCountIncrease | Pre-fix ALL-only count ≤ 22 (confirms fix is real) | ✓ |
| 12 | TestReplaySupportedWeightIncrease | Portfolio weight gain ≥ 7pp | ✓ |
| 13a | TestHighConvictionRetainGate | replay_supported=False blocks HCR | ✓ |
| 13b | TestHighConvictionRetainGate | replay_supported=True allows HCR when all gates pass | ✓ |
| 13c | TestHighConvictionRetainGate | BEARISH signal blocks HCR even with replay | ✓ |
| 14 | TestExistingReplaySupportedSymbolsUnchanged | All 21 pre-fix symbols still replay_supported=True | ✓ |
| 15 | (full suite) | 560/560 passing | ✓ |

---

## Regression Suite

```
533 pre-existing tests:  passed
 27 new 7.4D tests:      passed
─────────────────────────────
560 total:               passed  (0 failures)
```

---

## HIGH_CONVICTION_RETAIN Eligibility Impact

`HIGH_CONVICTION_RETAIN` in `_classify_holding()` (src/portfolio/trim_intelligence.py)
requires four gates:

| Gate | Threshold | Source |
|---|---|---|
| signal | BULLISH | overlay.signal_direction |
| replay_ok | True | overlay.replay_supported ← **fixed here** |
| thematic_redundancy | < 35 | computed at run time |
| trim_score | < 30 | computed at run time |

The fix removes the `replay_ok` blocker for 25 holdings. Whether each upgraded
holding actually achieves HIGH_CONVICTION_RETAIN in a full pipeline run depends
on the remaining three gates evaluated at run time.

The 8 Phase 7.4B gap candidates (ATLC, AVT, BSVN, CAH, CBOE, CIEN, NUE, PCB) are
all confirmed `replay_supported=True` after the fix and are now eligible for
HCA reclassification subject to `thematic_redundancy` and `trim_score` evaluation.

---

## Recommendation Ordering Impact

The fix changes `replay_supported` on overlays but does not modify:
- Composite scores
- ESS scores
- DAS formula
- Allocation alignment results
- Signal directions

The `opportunity_flag` for BULLISH + replay_supported holdings changes from
`HOLD` → `ACCUMULATE` for newly upgraded symbols. This is the correct and
intended behavior — it reflects that these holdings now have confirmed
replay evidence. Recommendation ordering is unchanged for all pre-existing
replay-supported holdings.

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Stale industry replay data counted as current evidence | Low | Tier compatibility check (geo/cap/industry) ensures the replay was generated for the correct category. Replay validity/currency is governed by `replay_availability.csv` status fields. |
| Symbol appearing in wrong-industry replay | None | Canonical tier compatibility check blocks cross-industry false positives. Verified by 3 tier-mismatch tests. |
| ALL replay priority override | None | ALL-replay symbols are written to `symbol_tier` first; `industry_replay_evidence` only records symbols not already in `symbol_tier`. |
| PRG incorrectly upgraded | None | PRG has no entry in any replay `selected_symbols`. Not in `industry_replay_evidence`. Verified by test 5. |
| Pre-existing coverage reduced | None | `symbol_tier` (ALL replays) is populated identically to before. Verified by test 14 (all 21 pre-fix symbols still True). |

---

*Fix applied to: `src/portfolio/recommendations.py`*  
*Tests added: `tests/test_7_4d_replay_evidence_routing.py`*  
*This is a replay evidence recognition fix only. No replay generation, scoring, or portfolio targets were modified.*
