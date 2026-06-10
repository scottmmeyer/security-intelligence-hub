# Zacks Source Governance — Final Recommendation

**Date:** 2026-06-10

---

## Executive Summary

The core concern of the ZACKS-SOURCE-01 audit — **whether Fidelity-embedded Zacks data can incorrectly make Zacks appear FRESH** — is answered definitively: **No, for the freshness badge.** The badge reads `latest_zacks.csv` only.

However, three secondary issues were identified that warrant a follow-up implementation sprint.

---

## Final Q&A

### Q1: Where does Zacks data currently enter SIH?

**Two sources:**

1. **Direct Zacks fetch** (`fetch_zacks_scores.py` → `data/signals/zacks/latest_zacks.csv`) — authoritative, dated, primary
2. **Fidelity ESS embedded** (column `"Zacks Investment Research"` in Fidelity ESS CSV → `ess_zacks_rating` in base universe) — indirect, no per-symbol date, fallback only

A third entry point (`incoming/ess/non_starmine_zacks/non_ess.csv`) is defined but not currently populated.

### Q2: Which Zacks source is currently used for freshness badges?

**Source 1 only (direct Zacks, `latest_zacks.csv`).** The freshness badge in the Outcome Visualization UI reads `_signal_status()` which only inspects `latest_zacks.csv`. Fidelity ESS Zacks data does not contribute to this badge.

### Q3: Can Fidelity embedded Zacks data incorrectly make Zacks appear FRESH?

**No — for the freshness badge (badge_state in _signal_status()).** The Fidelity ESS path writes to `ess_zacks_rating` in the base universe and is only used in composite score computation via `_score_from_inputs()`. It never touches `latest_zacks.csv` and therefore cannot affect `badge_state`.

However, the Fidelity ESS fallback **is used silently in composite score calculation** when direct Zacks is absent, without any record of the substitution. This is a governance gap, not a freshness badge issue.

### Q4: Which Zacks source is used in Security Overlay, DIL, Deployment Candidates, and Reduction Queue?

All four surfaces read `zacks_rating` from `SecurityIntelligenceOverlay`, which is populated from `PortfolioHolding.zacks_rating`, which comes from `analytical_universe.csv`. That field may contain a value derived from either direct Zacks or Fidelity ESS fallback — with no indication of which source.

**The date shown in DIL evidence** (`[Zacks, 2026-06-10]`) is computed from `today_str` (current date) — it does not reflect the per-symbol `sourced_date` from `latest_zacks.csv`, nor does it indicate when PRIM's Zacks data was specifically fetched (which may be 2026-05-21).

### Q5: What should the correct source precedence be?

1. **Direct Zacks** (`latest_zacks.csv`, `sourced_date ≤ 7 days`) → FRESH, labeled `[Zacks Direct, {per-symbol date}]`
2. **Direct Zacks stale** (> 7 days) → STALE, labeled `[Zacks Direct, {per-symbol date} — stale]`
3. **Fidelity ESS fallback** (no direct, or direct too stale) → FALLBACK, labeled `[Zacks (Fidelity fallback)]`
4. **No data** → DEFAULT_NEUTRAL, labeled `[Zacks (unavailable)]`

### Q6: Is an implementation fix required?

**Yes — three issues require implementation fixes:**

**Issue A (HIGH): Per-Symbol Zacks Date in DIL Evidence**  
The DIL evidence list currently shows `[Zacks, {today}]` — using the current date regardless of when the specific symbol's Zacks data was actually fetched. This is misleading. PRIM's Zacks data from 2026-05-21 displayed with today's date creates a false impression of freshness.

**Issue B (MEDIUM): Source Provenance Tracking**  
When `ess_zacks_rating` (Fidelity fallback) is used in composite scoring, no record is kept. A `zacks_source` field should be added to the overlay/analytical_universe to enable operators and future logic to distinguish direct from fallback.

**Issue C (LOW): Max-Date Freshness Badge Granularity**  
`_sourced_date()` returns the max date across all rows, so the FRESH badge can show when only 1 of 2,647 symbols has been fetched today. This should use a per-portfolio-symbol coverage check rather than a universe-wide max date. (This does not involve Fidelity ESS but is a related data quality issue.)

### Q7: What backlog item should be created?

---

## Recommended Backlog Issue: ZACKS-SOURCE-02

**Title:** ZACKS-SOURCE-02 — Enforce Direct-Zacks-First Freshness and Source Provenance Labeling

**Priority:** MEDIUM

**Acceptance Criteria:**

1. **DIL evidence dates are per-symbol**: `computeDIL()` reads per-symbol `sourced_date` from `latest_zacks.csv` (passed via overlay or loaded on demand). Evidence shows `[Zacks Direct, {per-symbol sourced_date}]` or `[Zacks (Fidelity fallback)]` as appropriate.

2. **Source provenance field added**: A `zacks_source` field is added to `SecurityIntelligenceOverlay` with values: `DIRECT` / `FIDELITY_ESS_FALLBACK` / `DEFAULT_NEUTRAL`. This propagates from `analytical_universe_manager.py` through enrichment to the overlay.

3. **Staleness badge unchanged**: The existing `_signal_status()` freshness badge logic is correct and does not need modification for Fidelity ESS issues.

4. **No scoring changes**: `_score_from_inputs()` fallback logic is correct by design. Fidelity ESS is an appropriate computational fallback. The fix is display/provenance only.

5. **Badge per-portfolio (optional, lower priority)**: `_sourced_date()` could be enhanced to check portfolio symbol coverage rather than universe max date. Separate from the core issue.

**Files affected:**
- `src/history/analytical_universe_manager.py` — add `zacks_source` to `AnalyticalUniverseRow`
- `src/portfolio/enrichment.py` — propagate `zacks_source`
- `src/portfolio/recommendations.py` (overlay) — add `zacks_source` field
- `ui/portfolio_alignment/app.js` — `computeDIL()` — per-symbol date from overlay
- `ui/portfolio_alignment/app.js` — ARCH-05 profile — show `zacks_source`

---

## What Does NOT Need Fixing

1. ✓ **Freshness badge** (`badge_state`) — correctly based on direct Zacks only
2. ✓ **Composite score fallback** — Fidelity ESS as fallback is correct by design
3. ✓ **Scale conversion** — `6.0 - ess_zacks_raw` correctly inverts the Fidelity ESS scale
4. ✓ **Policy engine** — not affected by Zacks source
5. ✓ **CW-DAS** — not affected; uses `composite_score` (already computed)
