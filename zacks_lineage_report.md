# Zacks Lineage Audit Report
**Phase:** 7.5M — Signal Provenance, Lineage & Freshness Audit  
**Date:** 2026-05-31  
**Status:** COMPLETE

---

## Summary

The Zacks signal is correctly transformed and correctly displayed. The apparent discrepancy between "UI shows 4.0" and "live Zacks shows #2 BUY" is **not a bug** — it is a deliberate and correct inversion that maps Zacks' native descending rank (1=best) to the SIH ascending score scale (5=best).

---

## What Is Stored

The file `data/signals/zacks/latest_zacks.csv` stores two distinct fields per symbol:

| Field | Meaning | Scale |
|-------|---------|-------|
| `zacks_rank` | Native Zacks rank (1=Strong Buy, 5=Strong Sell) | 1–5 **descending** (1=best) |
| `zacks_score` | SIH-normalized score = `6.0 − zacks_rank` | 1–5 **ascending** (5=best) |

**Source:** `src/scoring/fetch_zacks_scores.py`, line 226:
```python
score = round(6.0 - rank, 2) if rank is not None else None
```

This inversion is applied at fetch time (via `quote-feed.zacks.com` API) and written to `latest_zacks.csv`.

**Text fallback mapping** (when no numeric fetch is available):
```
STRONG BUY / STRONG_BUY → 5.0
BUY / OUTPERFORM / OVERWEIGHT → 4.0
HOLD / NEUTRAL / MARKET PERFORM / EQUAL WEIGHT → 3.0
SELL / UNDERPERFORM / UNDERWEIGHT → 2.0
STRONG SELL → 1.0
```

Defined in `src/history/analytical_universe_manager._ZACKS_TEXT_SCORE_MAP`.

---

## VRT Case Study

| Step | Location | Field | Value | Meaning |
|------|----------|-------|-------|---------|
| 1. Fetch | `quote-feed.zacks.com` (scraped) | rank | 2 | "#2 BUY" on Zacks.com |
| 2. Inversion | `fetch_zacks_scores.py` line 226 | `score = 6.0 − 2.0` | 4.0 | Ascending: 4 = Buy |
| 3. Signal file | `data/signals/zacks/latest_zacks.csv` | `zacks_rank=2.0, zacks_score=4.0` | 4.0 | Stored correctly |
| 4. Universe build | `analytical_universe_manager._score_from_inputs()` | `zacks_rating = 4.0` | 4.0 | Direct pass-through of `zacks_score` |
| 5. Analytical universe | `data/current/analytical_universe.csv` | `zacks_rating=4.0` | 4.0 | Stored in universe |
| 6. Overlay builder | `src/portfolio/recommendations.build_security_overlays()` | `zacks_rating=4.0` | 4.0 | Passed to SecurityIntelligenceOverlay |
| 7. API response | `load_analysis_run()` → JSON | `security_overlays[].zacks_rating` | `"4.0"` | Serialized as string |
| 8. UI display | `app.js renderSecurityOverlays()` | `ov.zacks_rating` | **4.0** | Displayed directly |

**Live Zacks shows: "#2 BUY" → SIH normalized score: 4.0**  
**This is CORRECT.** The inversion is intentional and documented.

---

## Why the UI Shows 4.0 While Zacks Shows "#2 BUY"

This is a **labeling ambiguity, not a bug**:

- Zacks uses **rank** semantics (1=best, like a horse race position)
- SIH uses **score** semantics (5=best, like a grade)
- `score = 6 − rank` maps the two correctly: rank 1 → score 5.0 (Strong Buy), rank 2 → score 4.0 (Buy)

A user unfamiliar with the inversion might see 4.0 and assume it means "4th best" when it actually means "BUY" on the composite scale.

**Recommendation (display only, not in scope for this phase):** Consider displaying both — e.g., "Zacks #2 (4.0)" — to make the native rank visible alongside the normalized score.

---

## Fallback Behavior

When `latest_zacks.csv` does not contain a symbol:

1. `analytical_universe_manager._score_from_inputs()` checks `ess_zacks_rating` — the Zacks rank embedded in the Fidelity ESS source file
2. If `ess_zacks_rating` is available (1–5 range), applies inversion: `score = 6.0 − ess_zacks_rating`
3. Last resort: `zacks_score = 3.0` (NEUTRAL)

---

## Composite Score Contribution

Zacks carries **25% weight** in the production composite (v1):

```
composite = (ESS×0.55 + Zacks×0.25 + Yahoo×0.10 + Danelfin×0.10) / total_available_weight
```

Defined in `src/history/analytical_universe_manager._score_from_inputs()`.

---

## AEIS Case

AEIS has `zacks_rank=1.0, zacks_score=5.0` (Strong Buy) in `latest_zacks.csv`, but `ess_score_text=BEARISH` (score=2.0). The ESS signal (55% weight) heavily outweighs Zacks (25%) in the composite. Despite Zacks=5.0, the composite=3.055556, reflecting ESS dominance. This is correct behavior — ESS is intentionally weighted as the primary signal.

---

## Freshness

| Field | Latest sourced_date | Age (2026-05-31) | Status |
|-------|--------------------|----|--------|
| `zacks_score` in `latest_zacks.csv` | 2026-05-29 | 2 days | **FRESH** |
| `zacks_rating` in `analytical_universe.csv` | Rebuilt 2026-05-31 | 0 days | **FRESH** |
